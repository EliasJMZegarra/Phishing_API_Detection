import streamlit as st
import pandas as pd
from utils.api_client import _get

def render():
    st.header("👥 Usuarios más afectados")

    # 1)Solo admin
    if not st.session_state.get("is_admin", False):
        st.info("Esta sección solo está disponible para administradores.")
        return
    
    # 2) Obtenemos todos los correos (admin recibirá todos; usuario normal nunca llega aquí)
    emails = _get("/dashboard/emails")

    # Manejo de error estructurado desde api_client.py
    if isinstance(emails, dict) and "error" in emails:
        st.error(f"Error al obtener datos: {emails['error']}")
        return

    # 3) Extraer resultados de forma segura
    results = emails.get("results", []) if isinstance(emails, dict) else []
    if not isinstance(results, list) or not results:
        st.info("No existen datos suficientes.")
        return

    # 4) Contar correos por usuario (preferimos email; fallback a user_id)
    user_counts: dict[str, int] = {}
    for item in results:
        if not isinstance(item, dict):
            continue

        # Preferir email si viene en la respuesta del backend
        user_email = item.get("user_email")
        if isinstance(user_email, str) and user_email:
            key = user_email
        else:
            # Fallback: mostrar ID (por si faltara el email)
            uid = item.get("user_id")
            key = f"ID {uid}" if uid is not None else "Desconocido"

        user_counts[key] = user_counts.get(key, 0) + 1

    if not user_counts:
        st.info("No existen datos suficientes.")
        return

    # 5) Ordenar y mostrar ranking
    df = pd.DataFrame(
        sorted(user_counts.items(), key=lambda x: x[1], reverse=True),
        columns=["Email", "Correos Analizados"]
    )

    st.subheader("📌 Ranking de usuarios según cantidad de correos analizados")
    st.dataframe(df, use_container_width=True)