import asyncio
from app.database import engine, Base

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tablas creadas correctamente en PostgreSQL.")

if __name__ == "__main__":
    asyncio.run(create_tables())
