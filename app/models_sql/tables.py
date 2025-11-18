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
    email = Column(String(255), unique=True, nullable=False)
    google_id = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    emails = relationship("Email", back_populates="usuario")


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
    body = Column(Text, nullable=True)
    date = Column(String(255), nullable=True)  # igual a como llega desde Gmail
    received_date = Column(TIMESTAMP(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="emails")

    # relación 1:N (un email puede tener varias predicciones)
    predicciones = relationship("Prediccion", back_populates="email")


# ============================================================
# Tabla: Predicciones
# ============================================================
class Prediccion(Base):
    __tablename__ = "predicciones"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"))
    prediccion = Column(String(50), nullable=False)
    risk_level = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    email = relationship("Email", back_populates="predicciones")
