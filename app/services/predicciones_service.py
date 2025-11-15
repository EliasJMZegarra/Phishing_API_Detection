from app.repositories.predicciones_repository import PrediccionesRepository
from sqlalchemy.ext.asyncio import AsyncSession

class PrediccionesService:
    def __init__(self, repo: PrediccionesRepository = PrediccionesRepository()):
        self.repo = repo

    async def save_prediction(self, db: AsyncSession, data: dict):
        return await self.repo.save_prediction(db, data)

    async def get_predictions_by_email(self, db: AsyncSession, email_id: int):
        return await self.repo.get_predictions_by_email(db, email_id)
