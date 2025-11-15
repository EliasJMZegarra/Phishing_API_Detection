from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.users_repository import UsersRepository
from app.models_sql.tables import Usuario


class UsersService:
    def __init__(self, repo: UsersRepository = UsersRepository()):
        self.repo = repo

    async def create_user(self, db: AsyncSession, email: str) -> Usuario:
        return await self.repo.create_user(db, email)

    async def get_user_by_email(self, db: AsyncSession, email: str) -> Usuario | None:
        return await self.repo.get_user_by_email(db, email)

    async def create_if_not_exists(self, db: AsyncSession, email: str) -> Usuario:
        existing = await self.repo.get_user_by_email(db, email)
        if existing:
            return existing
        return await self.repo.create_user(db, email)
