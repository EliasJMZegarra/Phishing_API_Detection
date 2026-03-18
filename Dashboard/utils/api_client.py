import requests
import os
import streamlit as st

# URL base de la API en Render
API_BASE_URL = (
    os.getenv("API_URL")
    or "https://phishing-api-detection.onrender.com"
)
# ---------------------------
#   Funciones de conexión
# ---------------------------

def _get(endpoint: str):
    """Realiza una petición GET a la API.
    Retorna el JSON o un error estructurado.
    """
    try:
        url = f"{API_BASE_URL}{endpoint}"
        # Email del usuario autenticado en el dashboard
        user = st.session_state.get("user") or {}
        email = user.get("email")

        headers = {}
        if email:
            headers["X-User-Email"] = email
        
        response = requests.get(url, timeout=10, headers=headers) 

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

def get_global_stats():
    """Obtiene estadísticas generales de la API."""
    return _get("/dashboard/stats/global")


def get_user_stats():
    """Obtiene ranking de usuarios más afectados."""
    return _get("/dashboard/stats/users")


def get_timeline():
    """Obtiene la tendencia temporal del phishing."""
    return _get("/dashboard/stats/timeline")
