import streamlit as st
import pandas as pd
import plotly.express as px
from utils.api_client import _get

def render():
    st.header("📈 Tendencia Temporal de Actividad")

    emails = _get("/dashboard/emails")

    if "error" in emails:
        st.error(f"Error al obtener datos: {emails['error']}")
        return

    results = emails["results"]

    # Convertimos a DataFrame
    df = pd.DataFrame(results)

    if df.empty:
        st.info("No existen datos suficientes para mostrar una tendencia.")
        return

    # Convertir fechas → pandas datetime
    df["received_date"] = pd.to_datetime(df["received_date"]).dt.date
        
    # Agrupar por fecha
    trend = df.groupby("received_date").size().reset_index(name="conteo")

    fig = px.line(
        trend,
        x="received_date",
        y="conteo",
        title="Tendencia temporal de análisis",
        labels={"received_date": "Fecha", "conteo": "Correos analizados"},
        markers=True
    )

    st.plotly_chart(fig, use_container_width=True)
    
    # Mostrar tabla de apoyo
    st.subheader("📋 Datos diarios")
    st.dataframe(trend, use_container_width=True)
