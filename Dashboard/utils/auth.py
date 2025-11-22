import streamlit as st
import requests
import os
import time
from urllib.parse import urlencode

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

SCOPES = ["openid", "email", "profile"]

# ----------------------------------------------------
# Genera URL de login
# ----------------------------------------------------
def get_login_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
    }

    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

# ----------------------------------------------------
# Intercambia el code por tokens
# ----------------------------------------------------
def exchange_code(auth_code: str):
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    res = requests.post(token_url, data=data)

    if res.status_code != 200:
        st.error("Error al obtener tokens")
        st.stop()

    return res.json()


# ----------------------------------------------------
# REFRESH AUTOMÁTICO DEL ACCESS_TOKEN
# ----------------------------------------------------
def refresh_access_token():
    refresh_token = st.session_state.get("refresh_token", None)
    if not refresh_token:
        return False  

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    res = requests.post(token_url, data=data)

    if res.status_code != 200:
        return False

    token_data = res.json()
    st.session_state["access_token"] = token_data.get("access_token")
    st.session_state["expires_at"] = time.time() + token_data.get("expires_in", 3600)

    return True


# ----------------------------------------------------
# Obtiene info del usuario
# ----------------------------------------------------
def get_user_info(access_token: str):
    url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}

    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        st.error("Error al obtener la información del usuario")
        st.stop()

    return res.json()

# ----------------------------------------------------
# FLUJO PRINCIPAL OAuth
# ----------------------------------------------------
def login_flow():
    # Si ya está autenticado, verificar expiración
    if (
        st.session_state.get("logged_in")
        and st.session_state.get("access_token")
    ):
        expires_at = st.session_state.get("expires_at", 0)

        # Si expira en menos de 60 segundos → refrescar
        if time.time() > expires_at - 60:
            refreshed = refresh_access_token()
            if not refreshed:
                # No se pudo refrescar, cerrar sesión segura
                st.session_state.clear()
                st.rerun()
        return

    # Flujo de autenticación desde cero
    params = st.query_params

    # Solo ejecutar si existe "code"
    auth_code = params.get("code", None)
    if not auth_code:
        return  

    # Intercambiar code por tokens
    token_data = exchange_code(auth_code)
    access = token_data.get("access_token")
    
    # Guardar tokens en sesión
    st.session_state["access_token"] = token_data.get("access_token")
    st.session_state["refresh_token"] = token_data.get("refresh_token")
    st.session_state["id_token"] = token_data.get("id_token")

    # Evitar perder refresh_token si Google no lo envía en nuevas autenticaciones
    if not st.session_state["refresh_token"]:
        st.session_state["refresh_token"] = token_data.get("refresh_token")
    
    # Calcular expiración exacta
    expires_in = token_data.get("expires_in", 3600)
    st.session_state["expires_in"] = expires_in
    st.session_state["expires_at"] = time.time() + expires_in

    if not access:
        st.error("Error al obtener tokens")
        return

    user = get_user_info(access)

    # Guardar sesión
    st.session_state["logged_in"] = True
    st.session_state["user"] = user

    # Limpiar URL
    if "code" in st.query_params:
        st.query_params.pop("code")
    st.rerun()

# ----------------------------------------------------
# BOTÓN DE LOGIN
# ----------------------------------------------------
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
        unsafe_allow_html=True
    )

# ----------------------------------------------------
# BLOQUEAR ACCESO (DETENER RENDER)
# ----------------------------------------------------
def require_login():
    if not st.session_state.get("logged_in"):
        st.warning("Debes iniciar sesión para acceder al dashboard.")
        login_button()
        st.stop()  

# ----------------------------------------------------
# LOGOUT
# ----------------------------------------------------
def logout_button():
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()
