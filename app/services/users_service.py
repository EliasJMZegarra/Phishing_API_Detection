from sqlalchemy.orm import Session
from app.repositories.users_repository import UsersRepository
from app.models_sql.tables import Usuario


class UsersService:
    def __init__(self, repo: UsersRepository = UsersRepository()):
        self.repo = repo

    def create_user(self, db: Session, email: str):
        return self.repo.create_user(db, email)

    def get_user_by_email(self, db: Session, email: str):
        return self.repo.get_user_by_email(db, email)

    def create_if_not_exists(self, db: Session, email: str):
        existing = self.repo.get_user_by_email(db, email)
        if existing:
            return existing
        return self.repo.create_user(db, email)
   
    def list_all(self, db: Session):
        return self.repo.list_all(db)

def get_users_service():
    return UsersService()
