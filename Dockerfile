# ---- Fase base ----
FROM python:3.10-slim

# ---- Configuración del entorno ----
WORKDIR /code
COPY . /code

# ---- Dependencias del sistema ----
RUN apt-get update && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

# ---- Instalación de dependencias ----
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# ---- Exponer puerto y comando ----
EXPOSE 10000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]

