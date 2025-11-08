# app/oauth.py
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
import json
from google_auth_oauthlib.flow import Flow

router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]

CLIENT_SECRET_FILE = "app/credentials/client_secret.json"
TOKEN_PATH = "app/credentials/token.json"
REDIRECT_URI = "http://localhost:8000/oauth2callback"

@router.get("/authorize")
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", include_granted_scopes="true")
    return RedirectResponse(auth_url)

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

        flow.fetch_token(code=code)
        creds = flow.credentials

        # Guardar credenciales
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

        return JSONResponse({"message": "Authentication successful. Token saved."})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
