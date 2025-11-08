# ---- Fase base ----
FROM python:3.10-slim

# ---- Configuración del entorno ----
WORKDIR /app
COPY . /app

# Instala dependencias del sistema (útil para torch, numpy, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ---- Instalación de dependencias ----
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# ---- Exponer puerto y comando de ejecución ----
EXPOSE 10000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
