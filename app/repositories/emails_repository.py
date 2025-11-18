from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models_sql.tables import Email


class EmailsRepository:
    def save_email(self, db: Session, data: dict):
        # data se espera con claves: user_id, message_id, subject, sender, date, body
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

