from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.predicciones_repository import PrediccionesRepository
from app.models_sql.tables import Prediccion


class PrediccionesService:
    def __init__(self, repo: PrediccionesRepository = PrediccionesRepository()):
        self.repo = repo

    async def save_prediction(self, db: AsyncSession, data: dict) -> Prediccion:
        return await self.repo.save_prediction(db, data)

    async def get_predictions_by_email(self, db: AsyncSession, email_id: int):
        return await self.repo.get_predictions_by_email(db, email_id)

    async def list_all(self, db: AsyncSession):
        return await self.repo.list_all(db)
