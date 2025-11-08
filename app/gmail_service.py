# app/gmail_service.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email import message_from_bytes
import os

def get_gmail_service():
    """
    Crea y devuelve una instancia autenticada del servicio Gmail.
    Utiliza el token.json generado previamente.
    """
    creds = None
    token_path = "app/credentials/token.json"

    # Carga el token de autenticación guardado
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path)
    else:
        raise FileNotFoundError("⚠️ No se encontró el archivo token.json. Realice la autorización primero.")

    # Construye el servicio Gmail
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

    # Decodificar el cuerpo del mensaje (soporta texto plano o HTML)
    body = "Sin contenido"
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    break
    else:
        data = payload.get("body", {}).get("data")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return {
        "id": msg_id,
        "subject": subject,
        "from": sender,
        "date": date,
        "body": body[:1000]  # solo muestra primeros 1000 caracteres para evitar respuestas muy largas
    }