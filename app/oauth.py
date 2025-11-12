from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
import os, json
from google_auth_oauthlib.flow import Flow

router = APIRouter()

# === Variables ===
LOCAL_ENV = os.getenv("RENDER", "false").lower() == "false"  # Detecta entorno local
TOKEN_PATH = "app/credentials/token.json"

# === Configuración de scopes ===
if os.getenv("GMAIL_SCOPES"):
    SCOPES = os.getenv("GMAIL_SCOPES").split()
else:
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.addons.execute",
        "https://www.googleapis.com/auth/script.external_request",
        "https://www.googleapis.com/auth/gmail.readonly"
    ]

# === Ruta y credenciales ===
if LOCAL_ENV:
    CLIENT_SECRET_FILE = "app/credentials/client_secret.json"
    with open(CLIENT_SECRET_FILE, "r") as f:
        secrets = json.load(f)["web"]
    CLIENT_ID = secrets["client_id"]
    CLIENT_SECRET = secrets["client_secret"]
    REDIRECT_URI = secrets["redirect_uris"][0]
else:
    CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# === Endpoint /authorize ===
@router.get("/authorize")
def authorize():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES
    )
    auth_url, _ = flow.authorization_url(
        prompt="consent", access_type="offline", include_granted_scopes="true"
    )
    return RedirectResponse(auth_url)

# === Endpoint /oauth2callback ===
@router.get("/oauth2callback")
async def oauth2callback(request: Request):
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI],
                }
            },
            scopes=SCOPES
        )

        params = dict(request.query_params)
        if "error" in params:
            return JSONResponse({"error": params.get("error")}, status_code=400)

        code = params.get("code")
        if not code:
            return JSONResponse({"error": "Authorization code missing."}, status_code=400)

        flow.fetch_token(code=code)
        creds = flow.credentials

        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

        return JSONResponse({"message": "✅ Authentication successful. Token saved."})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
