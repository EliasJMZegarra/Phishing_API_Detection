import streamlit as st
import pandas as pd
from utils.api_client import _get

def render():
    st.header("👥 Usuarios más afectados")

    # Solo admin
    if not st.session_state.get("is_admin", False):
        st.info("Esta sección solo está disponible para administradores.")
        return
    
    # Obtenemos todos los correos
    emails = _get("/dashboard/emails")

    if "error" in emails:
        st.error(f"Error al obtener datos: {emails['error']}")
        return

    results = emails.get("results", [])

    # Conteo por usuario
    user_counts = {}
    for e in results:
        email = e.get("user_email") or f"ID {e.get('user_id')}" # type: ignore
        user_counts[email] = user_counts.get(email, 0) + 1

    if not user_counts:
        st.info("No existen datos suficientes.")
        return

    # Ordenar usuarios por mayor cantidad
    sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)

    # Convertimos a DataFrame para una mejor visualización
    df = pd.DataFrame(sorted_users, columns=["Email", "Correos Analizados"])

    st.subheader("📌 Ranking de usuarios según cantidad de correos analizados")
    # Mostrar tabla interactiva
    st.dataframe(df, use_container_width=True)
