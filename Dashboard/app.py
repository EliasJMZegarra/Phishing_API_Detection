import streamlit as st
from sections import global_stats, user_stats, timeline

# Configuración general del Dashboard
st.set_page_config(
    page_title="Phishing Detection Dashboard",
    page_icon="📊",
    layout="wide"
)

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

# Enrutamiento básico
if menu == "Resumen global":
    global_stats.render()

elif menu == "Usuarios afectados":
    user_stats.render()

elif menu == "Tendencia temporal":
    timeline.render()
