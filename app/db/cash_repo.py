from sqlalchemy import func
from app.db.database import SessionLocal
from app.db.models import CashMovement

TIPOS_VALIDOS = {"INGRESO", "EGRESO"}


def registrar_movimiento(
    tipo: str,
    concepto: str,
    monto: float,
    referencia: str | None = None,
    observacion: str | None = None,
) -> CashMovement:
    tipo = (tipo or "").upper().strip()
    if tipo not in TIPOS_VALIDOS:
        raise ValueError("tipo debe ser 'INGRESO' o 'EGRESO'.")
    if not concepto or not concepto.strip():
        raise ValueError("concepto es obligatorio.")
    if monto is None or float(monto) <= 0:
        raise ValueError("monto debe ser > 0.")

    with SessionLocal() as db:
        mov = CashMovement(
            tipo=tipo,
            concepto=concepto.strip(),
            monto=float(monto),
            referencia=referencia,
            observacion=observacion,
        )
        db.add(mov)
        db.commit()
        db.refresh(mov)
        return mov


def listar_movimientos(limit: int = 200) -> list[CashMovement]:
    with SessionLocal() as db:
        return (
            db.query(CashMovement).order_by(CashMovement.id.desc()).limit(limit).all()
        )


def obtener_saldo() -> float:
    with SessionLocal() as db:
        ingresos = (
            db.query(func.coalesce(func.sum(CashMovement.monto), 0.0))
            .filter(CashMovement.tipo == "INGRESO")
            .scalar()
            or 0.0
        )
        egresos = (
            db.query(func.coalesce(func.sum(CashMovement.monto), 0.0))
            .filter(CashMovement.tipo == "EGRESO")
            .scalar()
            or 0.0
        )
        return float(ingresos) - float(egresos)
