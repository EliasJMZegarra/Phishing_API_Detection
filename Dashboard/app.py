import streamlit as st
from sections import global_stats, user_stats, timeline
from utils.auth import login_flow, require_login, logout_button

# Configuración general del Dashboard
st.set_page_config(
    page_title="Phishing Detection Dashboard",
    page_icon="📊",
    layout="wide"
)

# Ejecutar flujo OAuth 
login_flow()

# Requerir que el usuario esté autenticado
user = require_login()

# Si el usuario está autenticado, mostrar su email arriba
if user:
    st.success(f"🔓 Usuario autenticado: **{user.get('email', 'Usuario') }**")

# Título principal
st.title("Panel Administrativo – Phishing Detection System")

# Menú lateral
menu = st.sidebar.radio(
    "Navegación",
    (
        "Resumen global",
        "Usuarios afectados",
        "Tendencia temporal"
    )
)

# Botón de cerrar sesión
logout_button()

# Enrutamiento básico
if menu == "Resumen global":
    global_stats.render()

elif menu == "Usuarios afectados":
    user_stats.render()

elif menu == "Tendencia temporal":
    timeline.render()
