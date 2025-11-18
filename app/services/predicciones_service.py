from sqlalchemy.orm import Session
from app.repositories.predicciones_repository import PrediccionesRepository
from app.models_sql.tables import Prediccion


class PrediccionesService:
    def __init__(self, repo: PrediccionesRepository = PrediccionesRepository()):
        self.repo = repo

    def save_prediction(self, db: Session, data: dict):
        return self.repo.save_prediction(db, data)

    def get_predictions_by_email(self, db: Session, email_id: int):
        return self.repo.get_predictions_by_email(db, email_id)

    def list_all(self, db: Session):
        return self.repo.list_all(db)

def get_predicciones_service():
    return PrediccionesService()
