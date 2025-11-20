import requests
import os

# URL base de la API en Render
API_BASE_URL = os.getenv("API_BASE_URL", "https://phishing-api-detection.onrender.com")

# ---------------------------
#   Funciones de conexión
# ---------------------------

def _get(endpoint: str):
    """Realiza una petición GET a la API.
    Retorna el JSON o un error estructurado.
    """
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}", "details": response.text}

        return response.json()

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
