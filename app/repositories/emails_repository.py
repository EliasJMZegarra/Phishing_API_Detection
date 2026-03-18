from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models_sql.tables import Email


class EmailsRepository:
    def save_email(self, db: Session, data: dict):
        # data se espera con claves: user_id, message_id, subject, sender, date, body
        user_id = int(data["user_id"])
        message_id = str(data["message_id"])

        q = select(Email).where(Email.user_id == user_id, Email.message_id == message_id)
        existing = db.execute(q).scalars().first()
        if existing:
            return existing
        
        new_email = Email(**data)
        db.add(new_email)
        db.commit()
        db.refresh(new_email)
        return new_email

    def get_email_by_id(self, db: Session, email_id: int):
        query = select(Email).where(Email.id == email_id)
        result = db.execute(query)
        return result.scalars().first()
    
    def list_all(self, db: Session):
        """
        Retorna todos los correos almacenados.
        """
        query = select(Email).order_by(Email.received_date.desc())
        result = db.execute(query)
        return result.scalars().all()
    
    def list_by_user_id(self, db: Session, user_id: int):
        query = (
            select(Email)
            .where(Email.user_id == user_id)
            .order_by(Email.received_date.desc())
        )
        result = db.execute(query)
        return result.scalars().all()
    
    def count_all(self, db: Session) -> int:
        q = select(func.count(Email.id))
        return int(db.execute(q).scalar() or 0)

    def count_by_user_id(self, db: Session, user_id: int) -> int:
        q = select(func.count(Email.id)).where(Email.user_id == user_id)
        return int(db.execute(q).scalar() or 0)


