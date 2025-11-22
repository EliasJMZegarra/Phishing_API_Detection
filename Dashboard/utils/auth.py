import streamlit as st
import requests
import os
import time
from urllib.parse import urlencode
from streamlit_cookies_manager import EncryptedCookieManager

# ----------------------------------------------------
#   CONFIGURACIÓN DE COOKIES
# ----------------------------------------------------
cookies = EncryptedCookieManager(
    prefix="phishing_dashboard_",
    password=os.getenv("COOKIE_SECRET", "ultra_secret_key_change_me")
)

if not cookies.ready():
    st.stop()

# ----------------------------------------------------
#   VARIABLES DEL OAUTH
# ----------------------------------------------------
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

SCOPES = ["openid", "email", "profile"]

# ----------------------------------------------------
#   URL DE LOGIN
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
#   INTERCAMBIO DE CODE POR TOKENS
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
        st.error("Error al obtener tokens.")
        st.stop()
    return res.json()

# ----------------------------------------------------
#   REFRESCAR ACCESS TOKEN
# ----------------------------------------------------
def refresh_access_token(refresh_token: str):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    res = requests.post(token_url, data=data)
    if res.status_code != 200:
        return None

    return res.json()

# ----------------------------------------------------
#   OBTENER INFO DEL USUARIO
# ----------------------------------------------------
def get_user_info(access_token: str):
    url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        return None

    return res.json()

# ----------------------------------------------------
#   FLUJO PRINCIPAL DE LOGIN + COOKIES + REFRESH
# ----------------------------------------------------
def login_flow():
    # 1) Si tenemos cookies válidas → intentar reusarlas
    access_token = cookies.get("access_token")
    refresh_token = cookies.get("refresh_token")
    expires_at = cookies.get("expires_at")

    if access_token and refresh_token and expires_at:
        expires_at = float(expires_at)

        # Si token expiró → refrescar
        if time.time() >= expires_at:
            token_data = refresh_access_token(refresh_token)

            if token_data and token_data.get("access_token"):
                access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)

                cookies["access_token"] = access_token
                cookies["expires_at"] = str(time.time() + expires_in)
                cookies.save()

            else:
                # Borrar cookies si están expiradas 
                cookies.delete("access_token")  # type: ignore[attr-defined]
                cookies.delete("refresh_token") # type: ignore[attr-defined]
                cookies.delete("expires_at")    # type: ignore[attr-defined]
                cookies.delete("email")         # type: ignore[attr-defined]
                cookies.save()
                st.rerun()

        # Validar Access Token
        user_info = get_user_info(access_token)
        if user_info:
            st.session_state["logged_in"] = True
            st.session_state["user"] = user_info
            return

    # ----------------------------------------------------
    # 2) Si NO hay cookies → revisar si vino "code" en la URL
    # ----------------------------------------------------
    params = st.query_params
    auth_code = params.get("code", None)

    if not auth_code:
        return  # Aún no logueado

    # --- Intercambiar el code por tokens ---
    token_data = exchange_code(auth_code)
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    if not access_token:
        st.error("No fue posible obtener tokens.")
        st.stop()

    user_info = get_user_info(access_token)
    if not user_info:
        st.error("Error al obtener el usuario")
        st.stop()

    # Guardamos todo en cookies
    cookies["access_token"] = access_token
    cookies["refresh_token"] = refresh_token
    cookies["email"] = user_info.get("email", "")
    cookies["expires_at"] = str(time.time() + token_data.get("expires_in", 3600))
    cookies.save()

    st.session_state["logged_in"] = True
    st.session_state["user"] = user_info

    # Limpiar la URL
    if "code" in st.query_params:
        st.query_params.pop("code")

    st.rerun()

# ----------------------------------------------------
#   BOTÓN DE LOGIN
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
#   REQUERIR LOGIN
# ----------------------------------------------------
def require_login():
    if not st.session_state.get("logged_in"):
        st.warning("Debes iniciar sesión para acceder al dashboard.")
        login_button()
        st.stop()

# ----------------------------------------------------
#   LOGOUT
# ----------------------------------------------------
def logout_button():
    if st.sidebar.button("Cerrar sesión"):
        # Borrar cookies si están expiradas
        cookies.delete("access_token")         # type: ignore[attr-defined]
        cookies.delete("refresh_token")        # type: ignore[attr-defined]
        cookies.delete("email")                # type: ignore[attr-defined]
        cookies.delete("expires_at")           # type: ignore[attr-defined]
        cookies.save()
        st.session_state.clear()
        st.rerun()

