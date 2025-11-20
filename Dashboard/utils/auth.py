import streamlit as st
import requests
import os
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
        "prompt": "consent"
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

    params = st.query_params  # Obtener parámetros de la URL

    if "code" in params:
        auth_code = params["code"]

        token_data = exchange_code(auth_code)
        access = token_data.get("access_token")

        if access:
            user = get_user_info(access)

            st.session_state["logged_in"] = True
            st.session_state["user"] = user

            # Redirigir limpiando el código de la URL
            st.experimental_set_query_params()
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
