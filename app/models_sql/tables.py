from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# ============================================================
# Tabla: Usuarios
# ============================================================
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String(255), unique=True, nullable=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relación 1:N con Emails
    emails = relationship("Emails", back_populates="usuario")


# ============================================================
# Tabla: Emails
# ============================================================
class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"))
    message_id = Column(String(255), unique=True, nullable=False)
    subject = Column(Text, nullable=True)
    sender = Column(String(255), nullable=True)
    body_excerpt = Column(Text, nullable=True)
    received_at = Column(TIMESTAMP(timezone=True), nullable=True)
    analyzed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relación con Usuarios
    usuario = relationship("Usuario", back_populates="emails")

    # Relación 1:1 con Predicciones
    prediccion = relationship("Prediccion", back_populates="email", uselist=False)


# ============================================================
# Tabla: Predicciones
# ============================================================
class Prediccion(Base):
    __tablename__ = "predicciones"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"))
    predicted_label = Column(String(50), nullable=False)
    risk_level = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relación con Emails
    email = relationship("Email", back_populates="prediccion")
