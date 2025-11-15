from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Leer la URL de conexión desde variables de entorno
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL no está configurado en las variables de entorno.")

# Convertir a formato asíncrono si Render entrega URL 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")

# Crear motor de conexión asíncrono
engine = create_async_engine(
    DATABASE_URL,
    echo=False,        # Cambiar a True si quieres ver logs SQL
    future=True
)

# Crear fábrica de sesiones
AsyncSessionLocal = sessionmaker(            # type: ignore[call-arg]
    bind=engine,                             # type: ignore[arg-type]
    class_=AsyncSession,                     # type: ignore[arg-type]
    expire_on_commit=False,
    autoflush=False,
)


# Base para los modelos
Base = declarative_base()

# Dependencia para FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:    # type: ignore[misc]
        yield session
