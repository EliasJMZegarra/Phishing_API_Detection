import streamlit as st
import pandas as pd
from utils.api_client import _get

def render():
    st.header("👥 Usuarios más afectados")

    # Obtenemos todos los correos
    emails = _get("/dashboard/emails")

    if "error" in emails:
        st.error(f"Error al obtener datos: {emails['error']}")
        return

    results = emails["results"]

    # Conteo por usuario
    user_counts = {}
    for e in results:
        uid = e["user_id"]  # type: ignore
        user_counts[uid] = user_counts.get(uid, 0) + 1

    st.subheader("📌 Ranking de usuarios según cantidad de correos analizados")

    if not user_counts:
        st.info("No existen datos suficientes.")
        return

    # Ordenar usuarios por mayor cantidad
    sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)

    # Convertimos a DataFrame para una mejor visualización
    df = pd.DataFrame(sorted_users, columns=["ID Usuario", "Correos Analizados"])

    # Mostrar tabla interactiva
    st.dataframe(df, use_container_width=True)
