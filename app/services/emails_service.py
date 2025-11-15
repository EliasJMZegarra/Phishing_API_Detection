from app.repositories.emails_repository import EmailsRepository
from sqlalchemy.ext.asyncio import AsyncSession

class EmailsService:
    def __init__(self, repo: EmailsRepository = EmailsRepository()):
        self.repo = repo

    async def save_email(self, db: AsyncSession, data: dict):
        return await self.repo.save_email(db, data)

    async def get_email_by_id(self, db: AsyncSession, email_id: int):
        return await self.repo.get_email_by_id(db, email_id)
