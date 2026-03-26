import streamlit as st
import pandas as pd
import plotly.express as px
from utils.api_client import get_timeline, get_users_list

def render():
    st.header("📈 Tendencia Temporal de Actividad")

    is_admin = st.session_state.get("is_admin", False)

    # 1) Selector group_by (simple)
    group_label = st.selectbox("Agrupar por", ["Semana", "Día", "Mes"], index=0)
    group_by = {"Día": "day", "Semana": "week", "Mes": "month"}[group_label]

    # 2) Filtro por usuario (solo admin)
    selected_email = None
    if is_admin:
        users = get_users_list()
        if "error" in users:
            st.error(f"Error al obtener usuarios: {users['error']}")
            return
        results = users.get("results", [])
        emails: list[str] = []
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    email = item.get("email")
                    if isinstance(email, str) and email:
                        emails.append(email)
        options = ["(Todos)"] + emails
        pick = st.selectbox("Filtrar por usuario (email)", options, index=0)
        selected_email = None if pick == "(Todos)" else pick

    # 3) days fijo (90)
    data = get_timeline(group_by=group_by, days=90, target_email=selected_email)

    if "error" in data:
        st.error(f"Error al obtener datos: {data['error']}")
        st.code(data.get("details", "sin detalles"))
        st.caption(f"URL: {data.get('url', 'desconocida')}")
        return

    series = data.get("series", [])
    if not series:
        st.info("No existen datos suficientes para mostrar tendencia.")
        return

    df = pd.DataFrame(series)
    df["date"] = pd.to_datetime(df["date"])

    metric = st.selectbox("Métrica", ["Total", "Phishing", "Legítimos"], index=0)
    y = {"Total": "total", "Phishing": "phishing", "Legítimos": "legitimate"}[metric]

    fig = px.line(df, x="date", y=y, markers=True, title="Tendencia temporal de análisis")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Datos")
    st.dataframe(df[["date", "total", "phishing", "legitimate"]], use_container_width=True)