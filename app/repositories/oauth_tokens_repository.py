from sqlalchemy.orm import Session
from app.models_sql.oauth_tokens import OAuthToken

class OAuthTokensRepository:
    def get_by_user_id(self, db: Session, user_id: int):
        return db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()

    def upsert(self, db: Session, user_id: int, credentials_json: str):
        row = self.get_by_user_id(db, user_id)
        if row:
            row.credentials_json = credentials_json
        else:
            row = OAuthToken(user_id=user_id, credentials_json=credentials_json)
            db.add(row)
        db.commit()
        db.refresh(row)
        return row
