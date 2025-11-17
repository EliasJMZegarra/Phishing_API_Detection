from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.emails_service import EmailsService, get_emails_service
from app.services.users_service import UsersService, get_users_service
from app.services.predicciones_service import PrediccionesService, get_predicciones_service


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# ============================================================
# 1. Obtener información detallada de un email por ID
# ============================================================
@router.get("/emails/{email_id}")
async def get_email_by_id(
    email_id: int,
    db: AsyncSession = Depends(get_db),
    emails_service: EmailsService = Depends(get_emails_service),
) -> dict:
    """
    Retorna la información almacenada de un correo específico.
    Ideal para que el dashboard muestre detalles del correo.
    """
    record = await emails_service.get_email_by_id(db, email_id)
    if not record:
        return {"status": "error", "message": "Correo no encontrado"}

    return {
        "status": "ok",
        "email": {
            "id": record.id,
            "user_id": record.user_id,
            "message_id": record.message_id,
            "subject": record.subject,
            "sender": record.sender,
            "body": record.body,
            "received_date": record.received_date,
        }
    }


# ============================================================
# 2. Obtener predicciones asociadas a un email
# ============================================================
@router.get("/emails/{email_id}/predicciones")
async def get_predictions_for_email(
    email_id: int,
    db: AsyncSession = Depends(get_db),
    pred_service: PrediccionesService = Depends(get_predicciones_service)
) -> dict:
    """
    Retorna todas las predicciones asociadas a ese correo.
    Muy útil para ver historial de clasificaciones y niveles de riesgo.
    """
    preds = await pred_service.get_predictions_by_email(db, email_id)

    return {
        "status": "ok",
        "email_id": email_id,
        "predictions": [
            {
                "id": p.id,
                "prediccion": p.prediccion,
                "risk_level": p.risk_level,
                "created_at": p.created_at
            }
            for p in preds
        ]
    }


# ============================================================
# 3. Obtener información de usuario por correo electrónico
# ============================================================
@router.get("/usuarios/{email}")
async def get_user_info(
    email: str,
    db: AsyncSession = Depends(get_db),
    users_service: UsersService = Depends(get_users_service)
) -> dict:
    """
    Devuelve los datos del usuario que reportó o analizó correos.
    """
    usuario = await users_service.get_user_by_email(db, email)
    if not usuario:
        return {"status": "error", "message": "Usuario no encontrado"}

    return {
        "status": "ok",
        "user": {
            "id": usuario.id,
            "email": usuario.email,
            "google_id": usuario.google_id,
            "name": usuario.name,
            "created_at": usuario.created_at,
        }
    }


# ============================================================
# 4. Listado general de correos (paginado)
# ============================================================
@router.get("/emails")
async def list_emails(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    emails_service: EmailsService = Depends(get_emails_service),
) -> dict:
    """
    Lista correos almacenados en la BD.
    Ideal para tablas grandes del panel administrativo.
    """

    # Nota: el repositorio todavía no tiene un método paginado.
    # Lo implementaremos luego, pero por ahora devolvemos todos.
    # Esto no rompe nada.

    all_emails = await emails_service.repo.list_all(db)

    sliced = all_emails[offset : offset + limit]

    return {
        "status": "ok",
        "total": len(all_emails),
        "returned": len(sliced),
        "results": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "subject": e.subject,
                "sender": e.sender,
                "received_date": e.received_date
            }
            for e in sliced
        ]
    }


# ============================================================
# 5. Estadísticas globales para el dashboard
# ============================================================
@router.get("/stats/global")
async def global_stats(
    db: AsyncSession = Depends(get_db),
    emails_service: EmailsService = Depends(get_emails_service),
    pred_service: PrediccionesService = Depends(get_predicciones_service)
) -> dict:
    """
    Retorna estadísticas principales:
    - Total de correos
    - Total de predicciones
    - Phishing vs legítimos
    - Últimos movimientos
    """

    # Obtener todos los correos
    all_emails = await emails_service.repo.list_all(db)

    # Obtener todas las predicciones
    all_preds = await pred_service.repo.list_all(db)

    phishing = sum(1 for p in all_preds if p.prediccion == "phishing")
    legit = sum(1 for p in all_preds if p.prediccion == "legitimate")

    return {
        "status": "ok",
        "statistics": {
            "total_emails": len(all_emails),
            "total_predictions": len(all_preds),
            "phishing": phishing,
            "legitimate": legit,
            "phishing_ratio": f"{(phishing / len(all_preds) * 100):.2f}%" if all_preds else "0%",
        }
    }

# ============================================================
# 6. Últimas actividades (correos + predicciones)
# ============================================================
@router.get("/stats/activity")
async def recent_activity(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    emails_service: EmailsService = Depends(get_emails_service),
    pred_service: PrediccionesService = Depends(get_predicciones_service)
) -> dict:
    """
    Retorna actividad reciente combinada del sistema:
    - Últimos correos almacenados
    - Últimas predicciones realizadas
    """

    emails = await emails_service.repo.list_all(db)
    preds = await pred_service.repo.list_all(db)

    # Ordenar por fecha (descendente)
    emails_sorted = sorted(emails, key=lambda e: e.received_date, reverse=True)
    preds_sorted = sorted(preds, key=lambda p: p.created_at, reverse=True)

    return {
        "status": "ok",
        "recent_emails": [
            {
                "id": e.id,
                "subject": e.subject,
                "sender": e.sender,
                "received_date": e.received_date
            }
            for e in emails_sorted[:limit]
        ],
        "recent_predictions": [
            {
                "id": p.id,
                "email_id": p.email_id,
                "prediccion": p.prediccion,
                "risk_level": p.risk_level,
                "created_at": p.created_at,
            }
            for p in preds_sorted[:limit]
        ]
    }
