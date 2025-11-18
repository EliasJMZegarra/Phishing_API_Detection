from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
import os, json
from google_auth_oauthlib.flow import Flow

router = APIRouter()

# === Variables ===
LOCAL_ENV = os.getenv("RENDER", "false").lower() == "false"  # Detecta entorno local
TOKEN_PATH = "app/credentials/token.json"

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
    "https://www.googleapis.com/auth/gmail.addons.current.message.metadata"
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

CLIENT_ID = secrets["client_id"]
CLIENT_SECRET = secrets["client_secret"]
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
async def oauth2callback(request: Request):
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
        
        # Intercambio del código por el token
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Guardar token
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

        return JSONResponse({"message": "✅ Authentication successful. Token saved."})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
