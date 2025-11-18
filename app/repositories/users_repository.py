from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models_sql.tables import Usuario


class UsersRepository:
    def create_user(self, db: Session, email: str):
        nuevo = Usuario(email=email)
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return nuevo

    def get_user_by_email(self, db: Session, email: str):
        query = select(Usuario).where(Usuario.email == email)
        result = db.execute(query)
        return result.scalars().first()

    def list_all(self, db: Session):
        """
        Retorna todos los usuarios registrados en la BD.
        """
        query = select(Usuario).order_by(Usuario.created_at.desc())
        result = db.execute(query)
        return result.scalars().all()
