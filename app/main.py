from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.gmail_service import get_gmail_service_for_user
from app.gmail_service import get_email_details
#from langdetect import detect
#from deep_translator import GoogleTranslator
import os
#import joblib
#import numpy as np
from typing import Optional, Any, cast
#from sentence_transformers import SentenceTransformer
from app.oauth import router as oauth_router
from app.services.users_service import UsersService, get_users_service
from app.services.emails_service import EmailsService, get_emails_service
from app.services.predicciones_service import PrediccionesService, get_predicciones_service
from app.services.oauth_tokens_service import OAuthTokensService, get_oauth_tokens_service
from app.database import get_db
from sqlalchemy.orm import Session
from app.routers.dashboard import router as dashboard_router


import logging

# Permitir el uso de OAuth2 detrás de proxy HTTPS (Render usa HTTP interno)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Crear la carpeta de logs si no existe (evita error en Render)
log_dir = "app/logs"
os.makedirs(log_dir, exist_ok=True)

# Configurar el sistema de logs
logging.basicConfig(
    level=logging.INFO,                              # Nivel de detalle (INFO, WARNING, ERROR, etc.)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Formato de cada mensaje
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "api.log")),  # Guarda los logs en un archivo
        logging.StreamHandler()                      # Muestra también en la consola
    ]
)

logger = logging.getLogger(__name__)


# Inicializar la aplicación FastAPI
app = FastAPI(title="Phishing Detection API", version="1.0", 
              description="Esta API permite detectar si un correo electrónico es **Phishing** o **Seguro** utilizando un modelo de aprendizaje automático basado en *Sentence Transformers (all-MiniLM-L6-v2)*.")

# Registrar las rutas OAuth (autenticación Google)
app.include_router(oauth_router)

# Registrar los routers del dashboard
app.include_router(dashboard_router)

# Modelo de entrada
class EmailRequest(BaseModel):
    text: str

# Rutas de los modelos - ML Assets (Lazy + Cache)

MODEL_CLF = None
LABEL_ENCODER = None
BEST_THRESHOLD = None
EMBEDDING_MODEL = None
ML_READY = False

def get_ml_assets():
    """
    Carga y retorna los assets ML una sola vez (cache).
    En producción puedes precargar con PRELOAD_ML=true.
    """
    global MODEL_CLF, LABEL_ENCODER, BEST_THRESHOLD, EMBEDDING_MODEL, ML_READY

    if ML_READY and all([MODEL_CLF, LABEL_ENCODER, BEST_THRESHOLD, EMBEDDING_MODEL]):
        return MODEL_CLF, LABEL_ENCODER, BEST_THRESHOLD, EMBEDDING_MODEL

    # Lazy imports (evitan que el server falle si ML libs no están instaladas)
    import joblib
    from sentence_transformers import SentenceTransformer

    model_path = "app/models/model_clf.pkl"
    encoder_path = "app/models/label_encoder.pkl"
    threshold_path = "app/models/best_threshold.pkl"

    MODEL_CLF = joblib.load(model_path)
    LABEL_ENCODER = joblib.load(encoder_path)
    BEST_THRESHOLD = joblib.load(threshold_path)

    # Verificar si el modelo local existe; si no, descargarlo automáticamente
    is_prod = os.getenv("RENDER", "false").lower() == "true"

    if not os.path.exists("app/models/bert"):
        if is_prod:
            raise RuntimeError("Modelo BERT no encontrado en producción. Debe estar predescargado.")
        logger.warning("Descargando modelo en local...")
        model_temp = SentenceTransformer("all-MiniLM-L6-v2")
        model_temp.save("app/models/bert")

    EMBEDDING_MODEL = SentenceTransformer("app/models/bert")

    ML_READY = True
    logger.info("✅ ML assets cargados correctamente.")
    # Hint para Pylance: 
    MODEL_CLF = cast(Any, MODEL_CLF)
    LABEL_ENCODER = cast(Any, LABEL_ENCODER)
    EMBEDDING_MODEL = cast(Any, EMBEDDING_MODEL)
    return MODEL_CLF, LABEL_ENCODER, BEST_THRESHOLD, EMBEDDING_MODEL


@app.on_event("startup")
def preload_models_if_needed():
    """
    Precarga opcional en startup (producción).
    En local puedes dejar PRELOAD_ML=false para probar OAuth sin ML.
    """
    preload = os.getenv("PRELOAD_ML", "false").lower() == "true"
    if preload:
        try:
            get_ml_assets()
        except Exception as e:
            logger.error(f"❌ Error precargando ML assets: {str(e)}")

# Endpoint principal
@app.post("/predict",
    summary="Clasifica un correo electrónico",
    response_description="Devuelve la etiqueta y el nivel de confianza del análisis.")
def predict_email(data: EmailRequest):
    try:
        from langdetect import detect
        from deep_translator import GoogleTranslator

        model_clf, label_encoder, best_threshold, embedding_model = get_ml_assets()
        model_clf = cast(Any, model_clf)
        label_encoder = cast(Any, label_encoder)
        embedding_model = cast(Any, embedding_model)
        # registro de los primeros caracteres del correo
        logger.info(f"Solicitud recibida para análisis: {data.text[:60]}...")  
       
        # Obtener el texto del correo
        text = data.text.strip()

        # Validar si el texto está vacío
        if not text:
            return {"error": "El campo 'text' está vacío. Proporcione el contenido del correo."}
        
        # Detectar el idioma
        detected_lang = detect(text)
        translated_text = text  # Por defecto no se traduce

        # Traducir a inglés si no está en ese idioma
        if detected_lang != "en":
            translated_text = GoogleTranslator(source="auto", target="en").translate(text)
            print(f"[INFO] Texto traducido de '{detected_lang}' a inglés.")

        # Convertir el texto en embedding
        embedding = embedding_model.encode([translated_text])


        # Obtener probabilidad de phishing
        prediction_prob = model_clf.predict_proba(embedding)[0][1]

        # Calcular el porcentaje de riesgo
        risk_percent = round(float(prediction_prob) * 100, 2)

        # Aplicar umbral óptimo
        prediction = 1 if prediction_prob >= best_threshold else 0

        # Convertir a etiqueta original
        label = label_encoder.inverse_transform([prediction])[0]

        # Guardar la predicción en los logs
        logging.info(f"Solicitud recibida: {text[:60]}...")
        logger.info(f"Resultado: {label} ({prediction_prob:.2f})")

        # Estructura de respuesta optimizada para el Add-on
        return {
            "original_language": detected_lang,
            "translated_text": translated_text if detected_lang != "en" else None,
            "input_text": text,
            "predicted_label": label,
            "confidence": float(prediction_prob),
            "risk_percent": f"{risk_percent}%"
        }

    except Exception as e:
        logger.error(f"Error durante la predicción: {str(e)}")
        return {"error": str(e)}

# Endpoint de verificación del estado del servicio
@app.get("/healthcheck")
def healthcheck():
    preload = os.getenv("PRELOAD_ML", "false").lower() == "true"

    if preload:
        try:
            _ = get_ml_assets()
            return {"status": "ok", "message": "API is running and ML assets are loaded (PRELOAD_ML=true)."}
        except Exception as e:
            return {"status": "error", "message": f"Model loading issue: {str(e)}"}
    else:
        return {"status": "ok", "message": "API is running (PRELOAD_ML=false, ML loads on demand)."}

@app.get("/gmail/test")
def test_gmail_connection():
    """
    Prueba la conexión con Gmail API y lista los últimos 5 correos recibidos.
    """
    try:
        service = get_gmail_service_for_user(db=None, user_id=1, tokens_service=get_oauth_tokens_service())
        results = service.users().messages().list(userId="me", maxResults=5).execute()
        messages = results.get("messages", [])

        if not messages:
            return {"message": "No se encontraron correos recientes."}

        email_list = []
        for msg in messages:
            msg_data = service.users().messages().get(userId="me", id=msg["id"], format="metadata").execute()
            snippet = msg_data.get("snippet", "Sin contenido")
            email_list.append(snippet)

        return {
            "status": "Conexión exitosa ✅",
            "emails_sample": email_list
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/gmail/read")
def read_emails(limit: int = 3):
    """
    Lee los correos más recientes y devuelve su contenido completo.
    """
    try:
        service = get_gmail_service_for_user(db=None, user_id=1, tokens_service=get_oauth_tokens_service())
        results = service.users().messages().list(userId="me", maxResults=limit).execute()
        messages = results.get("messages", [])

        if not messages:
            return {"message": "No se encontraron correos."}

        detailed_emails = [get_email_details(service, msg["id"]) for msg in messages]
        return {
            "status": "Lectura completa exitosa ✅",
            "emails": detailed_emails
        }

    except Exception as e:
        return {"error": str(e)}
    

# Endpoint para clasificación compacta (para el Add-on)
@app.get("/gmail/classify")
def classify_email(
    message_id: Optional[str] = None,
    user_email: Optional[str] = None,
    db: Session = Depends(get_db),
    users_service: UsersService = Depends(get_users_service),
    tokens_service: OAuthTokensService = Depends(get_oauth_tokens_service),
):
    """
    Clasifica rápidamente un correo específico (Add-on).
    Multiusuario: usa tokens del usuario (oauth_tokens) en BD.
    """
    try:
        from langdetect import detect
        from deep_translator import GoogleTranslator
       
        # Validar parámetros obligatorios
        if not message_id or not user_email:
            raise HTTPException(status_code=400, detail="Se requiere message_id y user_email.")

        # ML assets (lazy load)
        model_clf, label_encoder, best_threshold, embedding_model = get_ml_assets()
        model_clf = cast(Any, model_clf)
        label_encoder = cast(Any, label_encoder)
        embedding_model = cast(Any, embedding_model)

        # 1) Resolver usuario
        usuario = users_service.create_if_not_exists(db, user_email)
        user_id_int = int(getattr(usuario, "id"))

        # 2) Gmail service por usuario (tokens en BD)
        service = get_gmail_service_for_user(db, user_id_int, tokens_service)

        # 3) Leer correo
        email_data = get_email_details(service, message_id)
        text = (email_data.get("body") or "").strip()

        if not text:
            return {
                "status": "OK",
                "id": message_id,
                "classification": "Sin contenido",
                "risk_level": 0.0
            }

        # 4) Detección y traducción de idioma
        detected_lang = detect(text)
        translated_text = (
            text if detected_lang == "en"
            else GoogleTranslator(source="auto", target="en").translate(text)
        )

        # 5) Embedding + predicción
        embedding = embedding_model.encode([translated_text])
        prediction_prob = model_clf.predict_proba(embedding)[0][1]
        prediction = 1 if prediction_prob >= best_threshold else 0
        label = label_encoder.inverse_transform([prediction])[0]

        return {
            "status": "Clasificación completada",
            "id": message_id,
            "classification": label,
            "risk_level": round(float(prediction_prob) * 100, 2)
        }

    except FileNotFoundError as e:
        # Caso típico: usuario existe pero no tiene oauth_tokens (no autorizó)
        raise HTTPException(status_code=401, detail=str(e))
    except HTTPException:
        # Re-lanzar errores controlados (400/401)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoints para reportes de phishing manuales desde el Add-on
@app.post("/gmail/report")
def report_phishing(
    data: dict,
    db: Session = Depends(get_db),
    users_service: UsersService = Depends(get_users_service),
    emails_service: EmailsService = Depends(get_emails_service),
    pred_service: PrediccionesService = Depends(get_predicciones_service),
    tokens_service: OAuthTokensService = Depends(get_oauth_tokens_service),
):
    """
    Guarda un reporte explícito de phishing desde el Add-on.
    Multiusuario: lee Gmail con tokens del usuario en BD.
    """
    message_id = data.get("message_id")
    user_email = data.get("user_email")

    if not message_id or not user_email:
        return {"status": "error", "message": "Faltan parámetros obligatorios."}

    # 1) Usuario
    usuario = users_service.create_if_not_exists(db, user_email)

    # 2) Gmail service por usuario
    try:
        user_id_int = int(getattr(usuario, "id"))
        service = get_gmail_service_for_user(db, user_id_int, tokens_service)
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}

    email_data = get_email_details(service, message_id)

    # 3) Guardar Email
    email_data_to_save = {
        "user_id": usuario.id,
        "message_id": email_data.get("id"),
        "subject": email_data.get("subject"),
        "sender": email_data.get("from"),
        "date": email_data.get("date"),
        "body": email_data.get("body"),
    }

    email_record = emails_service.save_email(db, email_data_to_save)

    # 4) Guardar predicción manual
    pred_service.save_prediction(db, {
        "email_id": email_record.id,
        "prediccion": "phishing",
        "risk_level": None,
    })

    return {"status": "ok", "message": "Reporte de phishing registrado correctamente."}

# Endpoint para marcar un correo como seguro desde el Add-on
@app.post("/gmail/safe")
def mark_safe(
    data: dict,
    db: Session = Depends(get_db),
    users_service: UsersService = Depends(get_users_service),
    emails_service: EmailsService = Depends(get_emails_service),
    pred_service: PrediccionesService = Depends(get_predicciones_service),
    tokens_service: OAuthTokensService = Depends(get_oauth_tokens_service),
):
    """
    Guarda un reporte explícito de correo seguro desde el Add-on.
    Multiusuario: lee Gmail con tokens del usuario en BD.
    """
    message_id = data.get("message_id")
    user_email = data.get("user_email")

    if not message_id or not user_email:
        return {"status": "error", "message": "Faltan parámetros obligatorios."}

    # 1) Usuario
    usuario = users_service.create_if_not_exists(db, user_email)

    # 2) Gmail service por usuario
    try:
        user_id_int = int(getattr(usuario, "id"))
        service = get_gmail_service_for_user(db, user_id_int, tokens_service)
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}

    email_data = get_email_details(service, message_id)

    # 3) Guardar Email
    email_data_to_save = {
        "user_id": usuario.id,
        "message_id": email_data.get("id"),
        "subject": email_data.get("subject"),
        "sender": email_data.get("from"),
        "date": email_data.get("date"),
        "body": email_data.get("body"),
    }

    email_record = emails_service.save_email(db, email_data_to_save)

    # 4) Guardar predicción manual
    pred_service.save_prediction(db, {
        "email_id": email_record.id,
        "prediccion": "legitimate",
        "risk_level": None,
    })

    return {"status": "ok", "message": "Correo marcado como seguro correctamente."}


# Redirigir la ruta raíz hacia la documentación Swagger
@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse(url="/docs")
