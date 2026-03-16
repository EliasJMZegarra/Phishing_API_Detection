from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import os, json
from google_auth_oauthlib.flow import Flow
import requests
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.users_service import UsersService, get_users_service
from app.services.oauth_tokens_service import OAuthTokensService, get_oauth_tokens_service


router = APIRouter()

# === Variables ===
LOCAL_ENV = os.getenv("RENDER", "false").lower() == "false"  # Detecta entorno local

# === Configuración de scopes ===
scopes_env = os.getenv("GMAIL_SCOPES")

if scopes_env:
    SCOPES = scopes_env.split()
else:
    SCOPES = [
    "https://www.googleapis.com/auth/gmail.addons.execute",
    "https://www.googleapis.com/auth/script.external_request",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.addons.current.message.readonly",
    "https://www.googleapis.com/auth/gmail.addons.current.message.metadata",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
 ]

# === Ruta y credenciales ===
if LOCAL_ENV:
    # Entorno local
    CLIENT_SECRET_FILE = "app/credentials/client_secret.json"
    redirect_index = 0          # primer redirect_uri: localhost
else:
    # Entorno Render (producción)
    CLIENT_SECRET_FILE = "/etc/secrets/client_secret.json"
    redirect_index = 1          # segundo redirect_uri: Render

with open(CLIENT_SECRET_FILE, "r") as f:
    secrets = json.load(f)["web"]


REDIRECT_URI = secrets["redirect_uris"][redirect_index]


# === Endpoint /authorize ===
@router.get("/authorize")
def authorize():
    flow = Flow.from_client_secrets_file(
       CLIENT_SECRET_FILE,
       scopes=SCOPES,
       redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(
        prompt="consent", access_type="offline", include_granted_scopes="true"
    )
    return RedirectResponse(auth_url)

# === Endpoint /oauth2callback ===
@router.get("/oauth2callback")
def oauth2callback(
    request: Request,
    db: Session = Depends(get_db),
    users_service: UsersService = Depends(get_users_service),
    tokens_service: OAuthTokensService = Depends(get_oauth_tokens_service),
):
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

        params = dict(request.query_params)
        if "error" in params:
            return JSONResponse({"error": params.get("error")}, status_code=400)

        code = params.get("code")
        if not code:
            return JSONResponse({"error": "Authorization code missing."}, status_code=400)

        # 1) Intercambio del código por tokens
        flow.fetch_token(code=code)
        creds = flow.credentials

        # 2) Obtener userinfo (email, id, name)
        headers = {"Authorization": f"Bearer {creds.token}"}
        resp = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=headers, timeout=10)

        if resp.status_code != 200:
            return JSONResponse(
                {"error": "No se pudo obtener userinfo", "details": resp.text},
                status_code=400
            )

        userinfo = resp.json()
        email = userinfo.get("email")
        google_id = userinfo.get("id")
        name = userinfo.get("name")

        if not email:
            return JSONResponse({"error": "userinfo sin email"}, status_code=400)

        # 3) Upsert usuario
        usuario = users_service.create_if_not_exists(db, email)

        # Completar google_id / name si están vacíos
        changed = False
        current_google_id = getattr(usuario, "google_id", None)
        current_name = getattr(usuario, "name", None)
        
        if google_id:
            if current_google_id in (None, ""):
                usuario.google_id = google_id
                changed = True
        
        if name:
            if current_name in (None, ""):
                usuario.name = name
                changed = True
                
        if changed:
            db.commit()
            db.refresh(usuario)
        
                
        user_id_int = int(getattr(usuario, "id"))

        
        # 4) Guardar credenciales en BD preservando refresh_token
        existing = tokens_service.get_by_user_id(db, user_id_int)
        new_creds_dict = json.loads(creds.to_json())
        
        if existing:
            old_creds_dict = json.loads(existing.credentials_json)
            if not new_creds_dict.get("refresh_token") and old_creds_dict.get("refresh_token"):
                new_creds_dict["refresh_token"] = old_creds_dict["refresh_token"]
        
        tokens_service.upsert(db, user_id_int, json.dumps(new_creds_dict))

        return JSONResponse({"message": f"✅ Authentication successful. Tokens saved for {email}."})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)