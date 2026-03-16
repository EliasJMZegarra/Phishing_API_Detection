# app/gmail_service.py
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
import json
from email import message_from_bytes
import os
import re

 # === Usar EXACTAMENTE los mismos scopes que usa OAuth ===
SCOPES = [
    "https://www.googleapis.com/auth/gmail.addons.execute",
    "https://www.googleapis.com/auth/script.external_request",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.addons.current.message.readonly",
    "https://www.googleapis.com/auth/gmail.addons.current.message.metadata",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

def get_gmail_service_for_user(db, user_id: int, tokens_service):
    """
    Crea y devuelve una instancia autenticada del servicio Gmail para un usuario específico.
    Lee credenciales desde PostgreSQL (oauth_tokens.credentials_json), refresca si expira y persiste el JSON actualizado.
    """
    row = tokens_service.get_by_user_id(db, user_id)
    if not row:
        raise FileNotFoundError(
            "⚠️ Este usuario no tiene credenciales OAuth guardadas. Debe completar /authorize primero."
        )

    stored_dict = json.loads(row.credentials_json)
    creds = Credentials.from_authorized_user_info(stored_dict, SCOPES)

    # Refrescar si expiró
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        new_dict = json.loads(creds.to_json())

        # Preservar refresh_token si el JSON nuevo no lo trae
        if not new_dict.get("refresh_token") and stored_dict.get("refresh_token"):
            new_dict["refresh_token"] = stored_dict["refresh_token"]

        tokens_service.upsert(db, user_id, json.dumps(new_dict))

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
