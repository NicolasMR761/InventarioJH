from __future__ import annotations

import hashlib
import os

from app.db.database import SessionLocal
from app.db.models import AdminUser

# ── Clave maestra de recuperación (solo para el desarrollador) ──
MASTER_KEY = "AdminMaster2026"  # ⚠️ CAMBIAR antes de entregar al cliente


def _hash(value: str) -> str:
    """SHA-256 con salt fijo."""
    salt = "inventario_jh_salt_v1"
    return hashlib.sha256(f"{salt}{value.strip()}".encode()).hexdigest()


# ── Consultas ────────────────────────────────────────────────


def existe_admin() -> bool:
    with SessionLocal() as db:
        return db.query(AdminUser).first() is not None


def crear_admin(password: str, pregunta: str, respuesta: str) -> AdminUser:
    with SessionLocal() as db:
        admin = AdminUser(
            password_hash=_hash(password),
            security_question=pregunta,
            security_answer_hash=_hash(respuesta),
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin


def verificar_password(password: str) -> bool:
    if password == MASTER_KEY:
        return True
    with SessionLocal() as db:
        admin = db.query(AdminUser).first()
        if not admin:
            return False
        return admin.password_hash == _hash(password)


def obtener_pregunta() -> str | None:
    with SessionLocal() as db:
        admin = db.query(AdminUser).first()
        return admin.security_question if admin else None


def verificar_respuesta(respuesta: str) -> bool:
    with SessionLocal() as db:
        admin = db.query(AdminUser).first()
        if not admin:
            return False
        return admin.security_answer_hash == _hash(respuesta)


def cambiar_password(nueva: str) -> None:
    with SessionLocal() as db:
        admin = db.query(AdminUser).first()
        if admin:
            admin.password_hash = _hash(nueva)
            db.commit()


def cambiar_pregunta_respuesta(pregunta: str, respuesta: str) -> None:
    with SessionLocal() as db:
        admin = db.query(AdminUser).first()
        if admin:
            admin.security_question = pregunta
            admin.security_answer_hash = _hash(respuesta)
            db.commit()
