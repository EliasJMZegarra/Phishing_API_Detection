from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.emails_repository import EmailsRepository
from app.models_sql.tables import Email


class EmailsService:
    def __init__(self, repo: EmailsRepository = EmailsRepository()):
        self.repo = repo

    async def save_email(self, db: AsyncSession, data: dict) -> Email:
        return await self.repo.save_email(db, data)

    async def get_email_by_id(self, db: AsyncSession, email_id: int) -> Email | None:
        return await self.repo.get_email_by_id(db, email_id)

    async def list_all(self, db: AsyncSession):
        return await self.repo.list_all(db)
