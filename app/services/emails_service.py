from sqlalchemy.orm import Session
from app.repositories.emails_repository import EmailsRepository
from app.models_sql.tables import Email


class EmailsService:
    def __init__(self, repo: EmailsRepository = EmailsRepository()):
        self.repo = repo

    def save_email(self, db: Session, data: dict):
        return self.repo.save_email(db, data)

    def get_email_by_id(self, db: Session, email_id: int):
        return self.repo.get_email_by_id(db, email_id)

    def list_all(self, db: Session):
        return self.repo.list_all(db)

def get_emails_service():
        return EmailsService()
    
