from fastapi import APIRouter,Request,HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text, Integer
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.services.emails_service import EmailsService, get_emails_service
from app.services.users_service import UsersService, get_users_service
from app.services.predicciones_service import PrediccionesService, get_predicciones_service
from app.models_sql.tables import Usuario, Email, Prediccion

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def _get_current_user(db: Session, request: Request) -> Usuario:
    email = request.headers.get("X-User-Email")
    if not email:
        raise HTTPException(status_code=401, detail="Falta X-User-Email (usuario no autenticado).")

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=403, detail="Usuario no registrado en el sistema.")
    return usuario

def _is_admin(usuario: Usuario) -> bool:
    return (getattr(usuario, "role", "user") or "user") == "admin"

# ============================================================
# 0. Endpoint de prueba para verificar roles y autenticación
# ============================================================
@router.get("/me")
def me(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    usuario = _get_current_user(db, request)
    return {
        "status": "ok",
        "user": {
            "id": usuario.id,
            "email": usuario.email,
            "role": getattr(usuario, "role", "user"),
            "name": getattr(usuario, "name", None),
        }
    }


# ============================================================
# 1. Obtener información detallada de un email por ID
# ============================================================
@router.get("/emails/{email_id}")
def get_email_by_id(
    email_id: int,
    db: Session = Depends(get_db),
    emails_service: EmailsService = Depends(get_emails_service),
) -> dict:
    """
    Retorna la información almacenada de un correo específico.
    Ideal para que el dashboard muestre detalles del correo.
    """
    record = emails_service.get_email_by_id(db, email_id)
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
def get_predictions_for_email(
    email_id: int,
    db: Session = Depends(get_db),
    pred_service: PrediccionesService = Depends(get_predicciones_service)
) -> dict:
    """
    Retorna todas las predicciones asociadas a ese correo.
    Muy útil para ver historial de clasificaciones y niveles de riesgo.
    """
    preds = pred_service.get_predictions_by_email(db, email_id)

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
def get_user_info(
    email: str,
    db: Session = Depends(get_db),
    users_service: UsersService = Depends(get_users_service)
) -> dict:
    """
    Devuelve los datos del usuario que reportó o analizó correos.
    """
    usuario = users_service.get_user_by_email(db, email)
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
def list_emails(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    emails_service: EmailsService = Depends(get_emails_service),
) -> dict:
    usuario = _get_current_user(db, request)

    if _is_admin(usuario):
        all_emails = emails_service.repo.list_all(db)
    else:
        user_id_int = int(getattr(usuario, "id"))
        all_emails = emails_service.repo.list_by_user_id(db, user_id_int)
    
    sliced = all_emails[offset : offset + limit]

    return {
        "status": "ok",
        "total": len(all_emails),
        "returned": len(sliced),
        "results": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "user_email": e.usuario.email if e.usuario else None,
                "user_name": (getattr(e.usuario, "name", None) if e.usuario else None),
                "subject": e.subject,
                "sender": e.sender,
                "received_date": e.received_date
            }
            for e in sliced
        ]
    }

# ============================================================
# 5. Listado de usuarios (solo para admin)
# ============================================================
@router.get("/users")
def list_users(
    request: Request,
    db: Session = Depends(get_db),
):
    usuario = _get_current_user(db, request)
    if not _is_admin(usuario):
        return {"status": "ok", "results": [{"email": getattr(usuario, "email", None)}]}

    users = db.query(Usuario).order_by(Usuario.email.asc()).all()
    return {
        "status": "ok",
        "results": [{"email": u.email} for u in users if u.email is not None and u.email.strip() != ""]
    }

# ============================================================
# 6. Estadísticas globales para el dashboard
# ============================================================
@router.get("/stats/global")
def global_stats(
    request: Request,
    db: Session = Depends(get_db),
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

    usuario = _get_current_user(db, request)

    if _is_admin(usuario):
        total_emails = emails_service.repo.count_all(db)
        counts = pred_service.repo.count_all(db)
        
    else:
        user_id_int = int(getattr(usuario, "id"))
        total_emails = emails_service.repo.count_by_user_id(db, user_id_int)
        counts = pred_service.repo.count_by_user_id(db, user_id_int)
        
    phishing = counts.get("phishing", 0)
    legit = counts.get("legitimate", 0)
    total_preds = int(sum(counts.values()))

    return {
        "status": "ok",
        "statistics": {
            "total_emails": total_emails,
            "total_predictions": total_preds,
            "phishing": phishing,
            "legitimate": legit,
            "phishing_ratio": f"{(phishing / total_preds * 100):.2f}%" if total_preds else "0%",
        }
    }

# ============================================================
# 7. Últimas actividades (correos + predicciones)
# ============================================================
@router.get("/stats/activity")
def recent_activity(
    request: Request,
    limit: int = 20,
    db: Session = Depends(get_db),
    emails_service: EmailsService = Depends(get_emails_service),
    pred_service: PrediccionesService = Depends(get_predicciones_service)
) -> dict:
    """
    Retorna actividad reciente combinada del sistema:
    - Últimos correos almacenados
    - Últimas predicciones realizadas
    """

    usuario = _get_current_user(db, request)

    if _is_admin(usuario):
        emails = emails_service.repo.list_all(db)
        preds = pred_service.repo.list_all(db)
    else:
        user_id_int = int(getattr(usuario, "id"))
        emails = emails_service.repo.list_by_user_id(db, user_id_int)
        preds = pred_service.repo.list_by_user_id(db, user_id_int)

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

# ============================================================
# 8. Estadísticas de predicciones a lo largo del tiempo (timeline)
# ============================================================

@router.get("/stats/timeline")
def timeline_stats(
    request: Request,
    days: int = 90,
    group_by: str = "week",  # day | week | month
    user_email: str | None = None,
    db: Session = Depends(get_db),
    users_service: UsersService = Depends(get_users_service),
):
    usuario = _get_current_user(db, request)

    if group_by not in {"day", "week", "month"}:
        raise HTTPException(status_code=400, detail="group_by inválido. Use: day, week, month.")

    # Rango temporal (UTC)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Base query: predicciones + email (para filtrar por user_id)
    q = (
        db.query(
            func.date_trunc(group_by, Prediccion.created_at).label("bucket"),
            func.cast(func.count(Prediccion.id), Integer).label("count"),
            func.cast(func.sum(func.case((Prediccion.prediccion == "phishing", 1), else_=0)), Integer).label("phishing"),
            func.cast(func.sum(func.case((Prediccion.prediccion == "legitimate", 1), else_=0)), Integer).label("legitimate"),
        )
        .join(Email, Prediccion.email_id == Email.id)
        .filter(Prediccion.created_at >= since)
    )

    # Filtro por usuario:
    # - si es admin: puede filtrar por user_email si lo envía
    # - si no es admin: siempre se fuerza a su propio user_id
    if _is_admin(usuario):
        if user_email:
            target = users_service.get_user_by_email(db, user_email)
            if not target:
                raise HTTPException(status_code=404, detail="user_email no existe.")
            q = q.filter(Email.user_id == int(getattr(target, "id")))
    else:
        q = q.filter(Email.user_id == int(getattr(usuario, "id")))

    rows = (
        q.group_by(text("bucket"))
         .order_by(text("bucket"))
         .all()
    )

    return {
        "status": "ok",
        "days": days,
        "group_by": group_by,
        "user_email": user_email if _is_admin(usuario) else getattr(usuario, "email", None),
        "series": [
            {
                "date": r.bucket.isoformat(),   # bucket datetime
                "total": r.count or 0,
                "phishing": r.phishing or 0,
                "legitimate": r.legitimate or 0,
            }
            for r in rows
        ],
    }