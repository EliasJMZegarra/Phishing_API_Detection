import os
import time
import json
from urllib.parse import urlencode

import requests
import streamlit as st

# ---------------------------------------------------------------------
# CONFIGURACIÓN OAuth
# ---------------------------------------------------------------------
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

SCOPES = ["openid", "email", "profile"]

# Archivo local donde se guardan los tokens en el servidor
TOKENS_FILE = os.path.join(os.path.dirname(__file__), ".oauth_tokens.json")


# ---------------------------------------------------------------------
# UTILIDADES PARA ARCHIVO DE TOKENS
# ---------------------------------------------------------------------
def _load_tokens_from_disk():
    """Lee los tokens guardados en disco (si existen)."""
    try:
        if not os.path.exists(TOKENS_FILE):
            return None
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_tokens_to_disk(token_data: dict):
    """Guarda los tokens en disco."""
    try:
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump(token_data, f)
    except Exception:
        pass


def _clear_tokens_on_disk():
    """Elimina el archivo de tokens del servidor."""
    try:
        if os.path.exists(TOKENS_FILE):
            os.remove(TOKENS_FILE)
    except Exception:
        pass


# ---------------------------------------------------------------------
# GENERAR URL DE LOGIN
# ---------------------------------------------------------------------
def get_login_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        
    }

    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


# ---------------------------------------------------------------------
# INTERCAMBIAR CODE POR TOKENS
# ---------------------------------------------------------------------
def exchange_code(auth_code: str):
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    res = requests.post(token_url, data=data)

    if res.status_code != 200:
        st.error("Error al obtener tokens")
        st.stop()

    token_data = res.json()

    # Calcular momento de expiración absoluta (epoch)
    expires_in = token_data.get("expires_in", 3600)
    # Resta 60s para refrescar un poco antes de expirar
    token_data["expires_at"] = time.time() + float(expires_in) - 60

    return token_data


# ---------------------------------------------------------------------
# REFRESCAR ACCESS TOKEN CON EL REFRESH TOKEN
# ---------------------------------------------------------------------
def refresh_access_token(refresh_token: str):
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    res = requests.post(token_url, data=data)

    if res.status_code != 200:
        return None

    new_tokens = res.json()
    expires_in = new_tokens.get("expires_in", 3600)
    new_tokens["expires_at"] = time.time() + float(expires_in) - 60

    # Mantener el mismo refresh_token si Google no devuelve uno nuevo
    if "refresh_token" not in new_tokens or not new_tokens["refresh_token"]:
        new_tokens["refresh_token"] = refresh_token

    return new_tokens


# ---------------------------------------------------------------------
# OBTENER INFO DEL USUARIO
# ---------------------------------------------------------------------
def get_user_info(access_token: str):
    url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}

    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        st.error("Error al obtener la información del usuario")
        st.stop()

    return res.json()


# ---------------------------------------------------------------------
# RESTAURAR SESIÓN DESDE DISCO (AL INICIAR)
# ---------------------------------------------------------------------
def _restore_session_from_disk():
    """Intenta restaurar sesión leyendo tokens del servidor."""
    if st.session_state.get("logged_in"):
        return  # ya hay sesión activa en memoria

    stored = _load_tokens_from_disk()
    if not stored:
        return

    access_token = stored.get("access_token")
    refresh_token = stored.get("refresh_token")
    expires_at = stored.get("expires_at")

    if not access_token or not refresh_token or not expires_at:
        return

    # Si el token está caducado → refrescar
    if time.time() >= float(expires_at):
        refreshed = refresh_access_token(refresh_token)
        if not refreshed or not refreshed.get("access_token"):
            # No se pudo refrescar → limpiar y salir
            _clear_tokens_on_disk()
            return
        stored = refreshed
        access_token = stored.get("access_token")
        # Guardar de nuevo tokens actualizados
        _save_tokens_to_disk(stored)

    # Con access_token válido obtenemos datos del usuario
    user = get_user_info(access_token)
    st.session_state["logged_in"] = True
    st.session_state["user"] = user
    st.session_state["access_token"] = access_token
    st.session_state["refresh_token"] = stored.get("refresh_token")
    st.session_state["expires_at"] = stored.get("expires_at")


# ---------------------------------------------------------------------
# FLUJO PRINCIPAL OAuth
# ---------------------------------------------------------------------
def login_flow():
    """
    1) Intenta restaurar sesión desde disco.
    2) Si viene un 'code' en la URL, intercambia por tokens, guarda en disco y en sesión.
    """

    # 1) Intentar restaurar sesión existente
    _restore_session_from_disk()

    # Si ya estamos logueados después de restaurar, no hacemos nada más
    if st.session_state.get("logged_in"):
        return

    # 2) Leer parámetros de la URL
    params = st.query_params
    auth_code = params.get("code", None)
    if not auth_code:
        return  # no hay código, el usuario aún no ha hecho login

    # 3) Intercambiar code por tokens
    token_data = exchange_code(auth_code)
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    if not access_token:
        st.error("Error al obtener tokens")
        return

    # Guardar en disco
    _save_tokens_to_disk(token_data)

    # Obtener info de usuario
    user = get_user_info(access_token)

    # Guardar en sesión (memoria)
    st.session_state["logged_in"] = True
    st.session_state["user"] = user
    st.session_state["access_token"] = access_token
    st.session_state["refresh_token"] = refresh_token
    st.session_state["expires_at"] = token_data.get("expires_at")

    # Limpiar 'code' de la URL para evitar reusarlo
    if "code" in st.query_params:
        st.query_params.pop("code")
    st.rerun()


# ---------------------------------------------------------------------
# BOTÓN DE LOGIN
# ---------------------------------------------------------------------
def login_button():
    url = get_login_url()
    st.markdown(
        f"""
        <a href="{url}">
            <button style="
                padding:10px 20px;
                background:#1a73e8;
                color:white;
                border:none;
                border-radius:8px;
                font-size:16px;">
                Iniciar sesión con Google
            </button>
        </a>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# BLOQUEAR ACCESO (DETENER RENDER)
# ---------------------------------------------------------------------
def require_login():
    if not st.session_state.get("logged_in"):
        st.warning("Debes iniciar sesión para acceder al dashboard.")
        login_button()
        st.stop()


# ---------------------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------------------
def logout_button():
    if st.sidebar.button("Cerrar sesión"):
        _clear_tokens_on_disk()
        st.session_state.clear()
        st.rerun()


