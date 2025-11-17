from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models_sql.tables import Usuario


class UsersRepository:
    async def create_user(self, db: AsyncSession, email: str):
        nuevo = Usuario(email=email)
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        return nuevo

    async def get_user_by_email(self, db: AsyncSession, email: str):
        query = select(Usuario).where(Usuario.email == email)
        result = await db.execute(query)
        return result.scalars().first()

    async def list_all(self, db: AsyncSession):
        """
        Retorna todos los usuarios registrados en la BD.
        """
        query = select(Usuario).order_by(Usuario.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()
