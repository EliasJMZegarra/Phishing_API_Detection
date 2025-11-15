from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.users_repository import UsersRepository
from app.repositories.emails_repository import EmailsRepository
from app.repositories.predicciones_repository import PrediccionesRepository


class DashboardService:
    """
    Servicio que centraliza todas las operaciones necesarias
    para el panel administrativo (dashboard).
    """

    def __init__(
        self,
        users_repo: UsersRepository = UsersRepository(),
        emails_repo: EmailsRepository = EmailsRepository(),
        preds_repo: PrediccionesRepository = PrediccionesRepository()
    ):
        self.users_repo = users_repo
        self.emails_repo = emails_repo
        self.preds_repo = preds_repo

    # ----------------------------------------------------------------------
    async def get_overall_stats(self, db: AsyncSession):
        """
        Retorna estadísticas generales del sistema:
        - total de usuarios
        - total de correos
        - total de predicciones
        """

        users = await self.users_repo.list_all(db)
        emails = await self.emails_repo.list_all(db)
        preds = await self.preds_repo.list_all(db)

        return {
            "total_usuarios": len(users),
            "total_correos": len(emails),
            "total_predicciones": len(preds),
        }

    # ----------------------------------------------------------------------
    async def get_all_emails(self, db: AsyncSession):
        """
        Retorna todos los correos registrados en BD,
        ordenados por fecha de recepción DESC.
        """
        return await self.emails_repo.list_all(db)

    # ----------------------------------------------------------------------
    async def get_all_predictions(self, db: AsyncSession):
        """
        Retorna todas las predicciones (manuales o automáticas).
        """
        return await self.preds_repo.list_all(db)

    # ----------------------------------------------------------------------
    async def get_predictions_by_email(self, db: AsyncSession, email_id: int):
        """
        Retorna todas las predicciones asociadas a un correo específico.
        """
        return await self.preds_repo.get_predictions_by_email(db, email_id)
