import streamlit as st
import google.oauth2.credentials
import google_auth_oauthlib.flow
import requests
import json
import os
from urllib.parse import urlencode, urlparse, parse_qs

# --- Obtener variables de entorno ---
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# --- Configuración del alcance ---
SCOPES = ["openid", "email", "profile"]

def get_login_url():
    """Genera la URL a Google OAuth2 para iniciar sesión."""
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def exchange_code_for_tokens(auth_code: str):
    """Intercambia el 'code' de Google por tokens."""
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    response = requests.post(token_url, data=data)

    if response.status_code != 200:
        st.error("Error al obtener los tokens de Google.")
        st.stop()

    return response.json()


def get_user_info(access_token: str):
    """Obtiene la información del usuario desde Google."""
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(userinfo_url, headers=headers)

    if response.status_code != 200:
        st.error("Error al obtener la información del usuario.")
        st.stop()

    return response.json()


def login_flow():
    """Lógica principal del flujo OAuth2 en Streamlit."""
    # 1. Revisar si Google envió un "code"
    parsed_url = urlparse(st.experimental_get_query_params().get("url", [""])[0])
    params = parse_qs(parsed_url.query)

    if "code" in params:
        auth_code = params["code"][0]

        token_data = exchange_code_for_tokens(auth_code)
        access_token = token_data.get("access_token")

        if access_token:
            user_info = get_user_info(access_token)

            # Guardar sesión
            st.session_state["logged_in"] = True
            st.session_state["user_email"] = user_info.get("email")
            st.session_state["user_name"] = user_info.get("name")
            st.session_state["user_picture"] = user_info.get("picture")

            st.success("Autenticación exitosa. Redirigiendo...")
            st.experimental_set_query_params()  # limpiar la URL
            st.rerun()


def require_login():
    """Bloquea el acceso a las páginas si el usuario no ha iniciado sesión."""
    if not st.session_state.get("logged_in"):
        st.warning("Debes iniciar sesión para acceder al dashboard.")
        login_button()


def login_button():
    """Muestra el botón de login."""
    login_url = get_login_url()

    st.markdown(
        f"""
        <a href="{login_url}">
            <button style="
                padding:10px 20px;
                background:#1769aa;
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

def logout_button():
    """Cierra sesión."""
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()
