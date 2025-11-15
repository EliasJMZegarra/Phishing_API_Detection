from app.repositories.users_repository import UsersRepository
from sqlalchemy.ext.asyncio import AsyncSession

class UsersService:
    def __init__(self, repo: UsersRepository = UsersRepository()):
        self.repo = repo

    async def create_user(self, db: AsyncSession, email: str):
        # Validar si el usuario ya existe
        existing = await self.repo.get_user_by_email(db, email)
        if existing:
            return existing

        # Crear si no existe
        return await self.repo.create_user(db, email=email)

    async def get_user_by_email(self, db: AsyncSession, email: str):
        return await self.repo.get_user_by_email(db, email)
