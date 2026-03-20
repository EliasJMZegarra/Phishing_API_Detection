import streamlit as st
import plotly.express as px
from utils.api_client import get_global_stats

def render():
    st.header("📊 Resumen Global del Sistema")

    user_email = st.session_state["user"]["email"]
    access_token = st.session_state.get("access_token")

    data = get_global_stats(user_email, access_token)

    if not isinstance(data, dict):
        st.error("Error: respuesta inválida del backend.")
        st.write(data)
        return

    if data.get("error"):
        st.error(f"Error al obtener datos: {data['error']}")
        if data.get("details"):
            st.code(data["details"])
        return
    
    stats = data.get("statistics")
    if not isinstance(stats, dict):
        st.error("Error: la API no devolvió 'statistics' con el formato esperado.")
        st.json(data)
        return
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total de correos", stats["total_emails"])               # type: ignore
    col2.metric("Total de predicciones", stats["total_predictions"])     # type: ignore
    col3.metric("Correos phishing", stats["phishing"])                   # type: ignore
    col4.metric("Correos legítimos", stats["legitimate"])                # type: ignore

    st.subheader("📈 Distribución de Predicciones")

    fig = px.bar(
        x=["Phishing", "Legítimos"],
        y=[stats["phishing"], stats["legitimate"]],                      # type: ignore
        color=["Phishing", "Legítimos"],
        labels={"x": "Tipo", "y": "Cantidad"},
        title="Distribución general"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📌 Resumen general de métricas")
    st.table(stats)
