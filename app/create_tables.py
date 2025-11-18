# app/create_tables.py

from app.database import engine, Base
import app.models_sql   # <-- IMPORTANTE: activa los modelos

def create_tables():
    print("Creando tablas en PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas correctamente.")

if __name__ == "__main__":
    create_tables()

