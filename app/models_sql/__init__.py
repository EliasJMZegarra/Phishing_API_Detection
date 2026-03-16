# app/models_sql/__init__.py

from .tables import Usuario, Email, Prediccion
from .oauth_tokens import OAuthToken


__all__ = ["Usuario", "Email", "Prediccion", "OAuthToken"]
