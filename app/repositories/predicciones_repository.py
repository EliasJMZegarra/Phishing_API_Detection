from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models_sql.tables import Prediccion


class PrediccionesRepository:
    async def save_prediction(self, db: AsyncSession, data: dict) -> Prediccion:
        new_pred = Prediccion(
            email_id=data["email_id"],
            prediccion=data["prediccion"],
            risk_level=data.get("risk_level"),   # puede ser None
        )
        db.add(new_pred)
        await db.commit()
        await db.refresh(new_pred)
        return new_pred

    async def get_predictions_by_email(
        self,
        db: AsyncSession,
        email_id: int,
    ) -> Sequence[Prediccion]:
        query = select(Prediccion).where(Prediccion.email_id == email_id)
        result = await db.execute(query)
        return result.scalars().all()
