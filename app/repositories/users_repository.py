from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models_sql.tables import Usuario


class UsersRepository:

    async def create_user(self, db: AsyncSession, email: str) -> Usuario:
        new_user = Usuario(email=email)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    async def get_user_by_email(self, db: AsyncSession, email: str) -> Usuario | None:
        query = select(Usuario).where(Usuario.email == email)
        result = await db.execute(query)
        return result.scalars().first()
