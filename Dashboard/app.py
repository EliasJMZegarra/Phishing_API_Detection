import streamlit as st
from sections import global_stats, user_stats, timeline
from utils.auth import login_flow, require_login, logout_button
from utils.api_client import _get

# Configuración general del Dashboard
st.set_page_config(
    page_title="Phishing Detection Dashboard",
    page_icon="📊",
    layout="wide"
)

# Ejecutar flujo OAuth 
login_flow()

# verrificar el rol del usuario para mostrar secciones específicas
def _ensure_admin_flag():
    if "is_admin" in st.session_state:
        return

    resp = _get("/dashboard/me")

    if isinstance(resp, dict) and resp.get("status") == "ok":
        user_obj = resp.get("user")
        role = user_obj.get("role", "user") if isinstance(user_obj, dict) else "user"
        st.session_state["is_admin"] = (role == "admin")
    else:
        st.session_state["is_admin"] = False

# Requerir que el usuario esté autenticado
require_login()
_ensure_admin_flag()

# Mostrar usuario conectado
user = st.session_state["user"]
st.success(f"🔓 Usuario autenticado: **{user.get('email')}**")

# Título principal
st.title("Panel Administrativo – Phishing Detection System")

# Menú lateral (solo admins ven "Usuarios afectados")
options = ["Resumen global", "Tendencia temporal"]
if st.session_state.get("is_admin"):
    options.insert(1, "Usuarios afectados")  # aparece solo para admin

menu = st.sidebar.radio("Navegación", options)

# Botón de cerrar sesión
logout_button()

# Enrutamiento básico
if menu == "Resumen global":
    global_stats.render()

elif menu == "Usuarios afectados":
    if st.session_state.get("is_admin"):
        user_stats.render()

elif menu == "Tendencia temporal":
    timeline.render()
