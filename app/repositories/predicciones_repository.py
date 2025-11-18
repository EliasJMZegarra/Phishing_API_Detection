from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models_sql.tables import Prediccion
class PrediccionesRepository:
    def save_prediction(self, db: Session, data: dict):
        new_pred = Prediccion(
            email_id=data["email_id"],
            prediccion=data["prediccion"],
            risk_level=data.get("risk_level"),   # puede ser None
        )
        db.add(new_pred)
        db.commit()
        db.refresh(new_pred)
        return new_pred

    def get_predictions_by_email(self, db: Session, email_id: int):
        query = select(Prediccion).where(Prediccion.email_id == email_id)
        result = db.execute(query)
        return result.scalars().all()
    
    def list_all(self, db: Session):
        """
        Retorna todas las predicciones generadas o manuales.
        """
        query = select(Prediccion).order_by(Prediccion.created_at.desc())
        result = db.execute(query)
        return result.scalars().all()

