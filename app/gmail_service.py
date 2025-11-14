# app/gmail_service.py
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
from email import message_from_bytes
import os
import re

def get_gmail_service():
    """
    Crea y devuelve una instancia autenticada del servicio Gmail.
    Si el token ha expirado, lo renueva automáticamente usando el refresh_token.
    """
    token_path = "app/credentials/token.json"
    
    # === Usar EXACTAMENTE los mismos scopes que usa OAuth ===
    scopes = [
        "https://www.googleapis.com/auth/gmail.addons.execute",
        "https://www.googleapis.com/auth/script.external_request",
        "https://www.googleapis.com/auth/gmail.readonly"
    ]

    # === Validar existencia de token.json ===
    if not os.path.exists(token_path):
        raise FileNotFoundError(
            "⚠️ token.json no existe. Debe completar /authorize primero."
        )

    # === Cargar credenciales ===
    creds = Credentials.from_authorized_user_file(token_path, scopes)

    # === Renovar token si expiró y tiene refresh_token ===
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    # === Crear servicio Gmail ===
    service = build("gmail", "v1", credentials=creds)
    return service


def get_email_details(service, msg_id):
    """
    Obtiene el contenido completo de un correo electrónico.
    Devuelve asunto, remitente, fecha y cuerpo del mensaje (texto plano o HTML).
    """
    message = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    # Extraer encabezados relevantes
    subject = sender = date = None
    for header in headers:
        name = header["name"].lower()
        if name == "subject":
            subject = header["value"]
        elif name == "from":
            sender = header["value"]
        elif name == "date":
            date = header["value"]

    # --- Función recursiva para extraer texto ---
    def extract_body(part):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        elif part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data")
            if data:
                text = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                # Limpieza básica de etiquetas HTML
                text = re.sub(r"<[^>]+>", " ", text)
                return text
        elif "parts" in part:
            for subpart in part["parts"]:
                text = extract_body(subpart)
                if text:
                    return text
        return ""

    # --- Obtener cuerpo principal ---
    body = extract_body(payload)
    if not body.strip():
        body = "Sin contenido"
    return {
        "id": msg_id,
        "subject": subject,
        "from": sender,
        "date": date,
        "body": body[:1000]  # solo muestra primeros 1000 caracteres para evitar respuestas muy largas
    }