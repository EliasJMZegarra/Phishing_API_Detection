from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models_sql.tables import Email


class EmailsRepository:
    async def save_email(self, db: AsyncSession, data: dict) -> Email:
        # data se espera con claves: user_id, message_id, subject, sender, date, body
        new_email = Email(**data)
        db.add(new_email)
        await db.commit()
        await db.refresh(new_email)
        return new_email

    async def get_email_by_id(self, db: AsyncSession, email_id: int) -> Email | None:
        query = select(Email).where(Email.id == email_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    async def list_all(self, db: AsyncSession):
        """
        Retorna todos los correos almacenados.
        """
        query = select(Email).order_by(Email.received_date.desc())
        result = await db.execute(query)
        return result.scalars().all()

