from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.gmail_service import get_gmail_service
from app.gmail_service import get_email_details
from langdetect import detect
from deep_translator import GoogleTranslator
import os
import joblib
import numpy as np
from typing import Optional
from sentence_transformers import SentenceTransformer
from app.oauth import router as oauth_router
from app.services.users_service import UsersService
from app.services.emails_service import EmailsService
from app.services.predicciones_service import PrediccionesService
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
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

# Rutas de los modelos
model_path = "app/models/model_clf.pkl"
encoder_path = "app/models/label_encoder.pkl"
threshold_path = "app/models/best_threshold.pkl"

# Cargar los modelos
model_clf = joblib.load(model_path)
label_encoder = joblib.load(encoder_path)
best_threshold = joblib.load(threshold_path)

# Verificar si el modelo local existe; si no, descargarlo automáticamente
if not os.path.exists("app/models/bert"):
    print("⚠️ Carpeta del modelo no encontrada. Descargando modelo 'all-MiniLM-L6-v2'...")
    model_temp = SentenceTransformer('all-MiniLM-L6-v2')
    model_temp.save('app/models/bert')
    print("✅ Modelo descargado y guardado en app/models/bert")

# Cargar el modelo de embeddings
embedding_model = SentenceTransformer('app/models/bert')  #Carga el modelo en local

print("Modelos cargados correctamente.")
print("Clases del LabelEncoder:", label_encoder.classes_)

# Endpoint principal
@app.post("/predict",
    summary="Clasifica un correo electrónico",
    response_description="Devuelve la etiqueta y el nivel de confianza del análisis.")
def predict_email(data: EmailRequest):
    try:

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
        embedding = embedding_model.encode([text])

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
    """
    Verifica el estado de la API.
    Retorna 'status: ok' si el servidor está activo y los modelos se cargaron correctamente.
    """
    try:
        _ = model_clf and label_encoder and best_threshold and embedding_model
        return {"status": "ok", "message": "API is running and models are loaded successfully."}
    except Exception as e:
        return {"status": "error", "message": f"Model loading issue: {str(e)}"}


@app.get("/gmail/test")
def test_gmail_connection():
    """
    Prueba la conexión con Gmail API y lista los últimos 5 correos recibidos.
    """
    try:
        service = get_gmail_service()
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
        service = get_gmail_service()
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
def classify_email(message_id: Optional[str] = None):
    """
    Clasifica rápidamente un correo específico.
    Uso exclusivo para el Add-on de Gmail.
    """
    try:
        if not message_id:
            return {"error": "Se requiere message_id para clasificar el correo."}

        service = get_gmail_service()
        email_data = get_email_details(service, message_id)
        text = email_data.get("body", "").strip()

        if not text:
            return {
                "status": "OK",
                "id": message_id,
                "classification": "Sin contenido",
                "risk_level": 0.0
            }

        # --- Detección y traducción ---
        detected_lang = detect(text)
        translated_text = (
            text if detected_lang == "en"
            else GoogleTranslator(source="auto", target="en").translate(text)
        )

        # --- Embedding + predicción ---
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

    except Exception as e:
        return {"error": str(e)}


# Endpoints para reportes de phishing manuales desde el Add-on
@app.post("/gmail/report")
async def report_phishing(
    data: dict,
    db=Depends(get_db),
    users_service: UsersService = Depends(),
    emails_service: EmailsService = Depends(),
    pred_service: PrediccionesService = Depends(),
):
    """
    Guarda un reporte explícito de phishing desde el Add-on.
    """
    message_id = data.get("message_id")
    user_email = data.get("user_email")

    if not message_id or not user_email:
        return {"status": "error", "message": "Faltan parámetros obligatorios."}

    # 1. Registrar usuario si no existe
    usuario = await users_service.create_if_not_exists(db, user_email)

    # 2. Obtener el correo desde Gmail
    service = get_gmail_service()
    email_data = get_email_details(service, message_id)

    # 3. Preparar datos para la tabla Emails
    email_data_to_save = {
        "user_id": usuario.id,                     # ← FK
        "message_id": email_data.get("id"),
        "subject": email_data.get("subject"),
        "sender": email_data.get("from"),
        "date": email_data.get("date"),
        "body": email_data.get("body"),
    }

    # 4. Guardar correo en BD 
    email_record = await emails_service.save_email(db, email_data_to_save)

    # 5. Guardar predicción manual (phishing)
    await pred_service.save_prediction(db, {
        "email_id": email_record.id,
        "prediccion": "phishing",
        "risk_level": None,   # manual, sin probabilidad
    })

    return {"status": "ok", "message": "Reporte de phishing registrado correctamente."}


# Endpoint para marcar un correo como seguro desde el Add-on
@app.post("/gmail/safe")
async def mark_safe(
    data: dict,
    db=Depends(get_db),
    users_service: UsersService = Depends(),
    emails_service: EmailsService = Depends(),
    pred_service: PrediccionesService = Depends(),
):
    """
    Guarda un reporte explícito de correo seguro desde el Add-on.
    """
    message_id = data.get("message_id")
    user_email = data.get("user_email")

    if not message_id or not user_email:
        return {"status": "error", "message": "Faltan parámetros obligatorios."}

    # 1. Registrar usuario si no existe
    usuario = await users_service.create_if_not_exists(db, user_email)

    # 2. Obtener el correo desde Gmail
    service = get_gmail_service()
    email_data = get_email_details(service, message_id)

    # 3. Preparar datos para la tabla Emails
    email_data_to_save = {
        "user_id": usuario.id,
        "message_id": email_data.get("id"),
        "subject": email_data.get("subject"),
        "sender": email_data.get("from"),
        "date": email_data.get("date"),
        "body": email_data.get("body"),
    }

    # 4. Guardar correo
    email_record = await emails_service.save_email(db, email_data_to_save)

    # 5. Guardar predicción manual (legitimate)
    await pred_service.save_prediction(db, {
        "email_id": email_record.id,
        "prediccion": "legitimate",
        "risk_level": None,
    })

    return {"status": "ok", "message": "Correo marcado como seguro correctamente."}


# Redirigir la ruta raíz hacia la documentación Swagger
@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")
