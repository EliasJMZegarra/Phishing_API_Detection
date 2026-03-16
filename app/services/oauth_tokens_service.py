from sqlalchemy.orm import Session
from app.repositories.oauth_tokens_repository import OAuthTokensRepository

class OAuthTokensService:
    def __init__(self, repo: OAuthTokensRepository):
        self.repo = repo

    def get_by_user_id(self, db: Session, user_id: int):
        return self.repo.get_by_user_id(db, user_id)

    def upsert(self, db: Session, user_id: int, credentials_json: str):
        return self.repo.upsert(db, user_id, credentials_json)
    
   
def get_oauth_tokens_service():
    return OAuthTokensService(OAuthTokensRepository())
