import requests
import os
import streamlit as st

# URL base de la API en Render
API_BASE_URL = (
    os.getenv("API_URL")
    or "https://phishing-api-detection.onrender.com"
)

# -------------------------------
#   Funciones de autenticación
# -------------------------------

def _headers(user_email: str | None = None, access_token: str | None = None) -> dict:
    h = {"Accept": "application/json"}
    if user_email:
        h["X-User-Email"] = user_email
   
    if access_token:
        h["Authorization"] = f"Bearer {access_token}"
    return h

# ---------------------------
#   Funciones de conexión
# ---------------------------

def _get(endpoint: str, user_email: str | None = None, access_token: str | None = None):
    try:
        # fallback: sacar email desde sesión si no se pasa
        if user_email is None:
            user = st.session_state.get("user") or {}
            user_email = user.get("email")

        url = f"{API_BASE_URL}{endpoint}"
        response = requests.get(url, headers=_headers(user_email, access_token), timeout=10)

        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}", "details": response.text}

        try:
            return response.json()
        except Exception:
            return {"error": "Respuesta no JSON", "details": response.text}

    except Exception as e:
        return {"error": str(e)}

# ---------------------------
#   Endpoints del dashboard
# ---------------------------

def get_global_stats(user_email: str, access_token: str | None = None):
    """Obtiene estadísticas generales de la API."""
    return _get("/dashboard/stats/global", user_email, access_token)

def get_user_stats(user_email: str, access_token: str | None = None):
    """Obtiene ranking de usuarios más afectados."""
    return _get("/dashboard/stats/users", user_email, access_token)

def get_timeline(user_email: str, access_token: str | None = None):
    """Obtiene la tendencia temporal del phishing."""
    return _get("/dashboard/stats/timeline", user_email, access_token)

def get_activity(user_email: str, access_token: str | None = None):
    return _get("/dashboard/stats/activity", user_email, access_token)

def get_emails(user_email: str, access_token: str | None = None):
    return _get("/dashboard/emails", user_email, access_token)
