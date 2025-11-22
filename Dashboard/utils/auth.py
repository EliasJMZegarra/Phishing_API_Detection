import streamlit as st
import requests
import os
from urllib.parse import urlencode

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# Alcances mínimos para identificar al usuario
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
        # sin "prompt=consent" para no forzar pantallas de permiso cada vez
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
        "grant_type": "authorization_code",
    }

    res = requests.post(token_url, data=data)

    # Si el code es inválido / reutilizado, devolvemos None
    if res.status_code != 200:
        # Opcional: descomenta si quieres ver el detalle para debug
        # st.write("Respuesta de Google:", res.status_code, res.text)
        return None

    return res.json()

# ----------------------------------------------------
# Refresca el access_token usando refresh_token
# ----------------------------------------------------
def refresh_access_token(refresh_token: str):
    if not refresh_token:
        return None

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

    return res.json()

# ----------------------------------------------------
# Obtiene info del usuario
# ----------------------------------------------------
def get_user_info(access_token: str):
    url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}

    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        return None

    return res.json()

# ----------------------------------------------------
# FLUJO PRINCIPAL OAuth
# ----------------------------------------------------
def login_flow():
    # 0) Si ya hay sesión válida, no hacemos nada
    if st.session_state.get("logged_in") and st.session_state.get("access_token"):
        return

    # 1) Si tenemos refresh_token pero perdimos el access_token,
    #    intentamos renovarlo silenciosamente.
    refresh_token = st.session_state.get("refresh_token")
    if refresh_token and not st.session_state.get("access_token"):
        token_data = refresh_access_token(refresh_token)
        if token_data and token_data.get("access_token"):
            access_token = token_data["access_token"]
            st.session_state["access_token"] = access_token
            st.session_state["id_token"] = token_data.get("id_token")
            st.session_state["expires_in"] = token_data.get("expires_in")

            user = get_user_info(access_token)
            if user:
                st.session_state["logged_in"] = True
                st.session_state["user"] = user
                return
        # Si el refresh falla, continuamos y forzamos login normal.

    # 2) Leer parámetros de la URL (para capturar ?code=)
    params = st.query_params
    auth_code = params.get("code", None)

    # Si no hay code, salimos: el usuario verá el botón en require_login()
    if not auth_code:
        return

    # 3) Intercambiar code por tokens
    token_data = exchange_code(auth_code)

    # Si el code ya caducó o no es válido, limpiamos el parámetro
    # y dejamos que el usuario vuelva a iniciar sesión sin mostrar error rojo.
    if not token_data or not token_data.get("access_token"):
        if "code" in st.query_params:
            st.query_params.pop("code")
        return

    access_token = token_data["access_token"]

    # Guardar tokens en sesión
    st.session_state["access_token"] = access_token

    # Guardar / preservar refresh_token
    new_refresh = token_data.get("refresh_token")
    if new_refresh:
        st.session_state["refresh_token"] = new_refresh
    elif "refresh_token" not in st.session_state:
        st.session_state["refresh_token"] = None

    st.session_state["id_token"] = token_data.get("id_token")
    st.session_state["expires_in"] = token_data.get("expires_in")

    # Obtener datos del usuario
    user = get_user_info(access_token)
    if not user:
        # Algo falló: limpiamos estado y code
        st.session_state.clear()
        if "code" in st.query_params:
            st.query_params.pop("code")
        return

    # Marcar sesión como autenticada
    st.session_state["logged_in"] = True
    st.session_state["user"] = user

    # 4) Limpiar la URL (quitar ?code=) y recargar sin parámetro
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
        unsafe_allow_html=True,
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

