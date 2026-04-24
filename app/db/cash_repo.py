from __future__ import annotations

from datetime import datetime, date, time, timedelta

from sqlalchemy import func, or_

from app.db.database import SessionLocal
from app.db.models import CashMovement, CashClosure


def _today_date() -> date:
    return datetime.now().date()


def _dt_range(d: date):
    start = datetime.combine(d, time.min)
    end = datetime.combine(d, time.max)
    return start, end


def _to_dt_start(x) -> datetime | None:
    if x is None:
        return None
    if isinstance(x, datetime):
        return x
    if isinstance(x, date):
        return datetime.combine(x, time.min)
    return None


def _to_dt_end(x) -> datetime | None:
    if x is None:
        return None
    if isinstance(x, datetime):
        return x
    if isinstance(x, date):
        return datetime.combine(x, time.max)
    return None


def _apply_filters(
    query,
    fecha_desde=None,
    fecha_hasta=None,
    tipo: str | None = None,
    q: str | None = None,
):
    d1 = _to_dt_start(fecha_desde)
    d2 = _to_dt_end(fecha_hasta)

    if d1 is not None:
        query = query.filter(CashMovement.fecha >= d1)
    if d2 is not None:
        query = query.filter(CashMovement.fecha <= d2)

    if tipo and tipo.strip():
        query = query.filter(CashMovement.tipo == tipo.strip().upper())

    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                CashMovement.concepto.ilike(term),
                CashMovement.referencia.ilike(term),
                CashMovement.observacion.ilike(term),
            )
        )

    return query


def _validar_movimiento(
    tipo: str, concepto: str, monto: float
) -> tuple[str, str, float]:
    """
    Valida y normaliza tipo, concepto y monto.
    ✅ FIX #2: concepto no puede quedar vacío (campo NOT NULL en DB).
    Lanza ValueError con mensaje claro en lugar de error de integridad de SQLite.
    """
    tipo = (tipo or "").strip().upper()
    if tipo not in ("INGRESO", "EGRESO"):
        raise ValueError("Tipo inválido. Use INGRESO o EGRESO.")

    monto = float(monto or 0)
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a 0.")

    concepto = (concepto or "").strip()
    if not concepto:
        raise ValueError("El concepto no puede estar vacío.")

    return tipo, concepto, monto


# ----------------------------
# Cierres
# ----------------------------
def esta_cerrado(d: date) -> bool:
    with SessionLocal() as db:
        c = db.query(CashClosure).filter(CashClosure.fecha == d).first()
        return c is not None


def obtener_cierre(d: date) -> CashClosure | None:
    with SessionLocal() as db:
        return db.query(CashClosure).filter(CashClosure.fecha == d).first()


# ----------------------------
# Saldos / Listados
# ----------------------------
def obtener_saldo(hasta: datetime | None = None) -> float:
    with SessionLocal() as db:
        # ✅ FIX: queries separados para evitar acumulación de filtros en SQLAlchemy
        q_ingresos = db.query(func.coalesce(func.sum(CashMovement.monto), 0.0)).filter(
            CashMovement.tipo == "INGRESO"
        )
        q_egresos = db.query(func.coalesce(func.sum(CashMovement.monto), 0.0)).filter(
            CashMovement.tipo == "EGRESO"
        )

        if hasta is not None:
            q_ingresos = q_ingresos.filter(CashMovement.fecha <= hasta)
            q_egresos = q_egresos.filter(CashMovement.fecha <= hasta)

        ingresos = q_ingresos.scalar()
        egresos = q_egresos.scalar()

        return float(ingresos or 0.0) - float(egresos or 0.0)


def listar_movimientos(
    limit: int = 200,
    offset: int = 0,
    fecha_desde: date | datetime | None = None,
    fecha_hasta: date | datetime | None = None,
    tipo: str | None = None,
    q: str | None = None,
) -> list[CashMovement]:
    with SessionLocal() as db:
        query = db.query(CashMovement).order_by(CashMovement.id.desc())
        query = _apply_filters(query, fecha_desde, fecha_hasta, tipo, q)
        return query.offset(int(offset)).limit(int(limit)).all()


def contar_movimientos(
    fecha_desde: date | datetime | None = None,
    fecha_hasta: date | datetime | None = None,
    tipo: str | None = None,
    q: str | None = None,
) -> int:
    with SessionLocal() as db:
        query = db.query(CashMovement)
        query = _apply_filters(query, fecha_desde, fecha_hasta, tipo, q)
        return int(query.count())


# ----------------------------
# Registrar movimiento (transacción propia)
# ----------------------------
def registrar_movimiento(
    tipo: str,
    concepto: str,
    monto: float,
    referencia: str | None = None,
    observacion: str | None = None,
    fecha: datetime | None = None,
) -> CashMovement:
    tipo, concepto, monto = _validar_movimiento(tipo, concepto, monto)

    fecha = fecha or datetime.now()
    dia = fecha.date()

    if esta_cerrado(dia):
        raise ValueError(
            f"El día {dia} está cerrado. No se pueden registrar movimientos."
        )

    with SessionLocal() as db:
        mov = CashMovement(
            tipo=tipo,
            concepto=concepto,
            monto=monto,
            referencia=(referencia or "").strip() or None,
            observacion=(observacion or "").strip() or None,
            fecha=fecha,
        )
        db.add(mov)
        db.commit()
        db.refresh(mov)
        return mov


# ----------------------------
# Registrar movimiento dentro de otra transacción
# ----------------------------
def registrar_movimiento_en_db(
    db,
    tipo: str,
    concepto: str,
    monto: float,
    referencia: str | None = None,
    observacion: str | None = None,
    fecha: datetime | None = None,
    forzar_fecha: bool = False,
) -> CashMovement:
    tipo, concepto, monto = _validar_movimiento(tipo, concepto, monto)

    fecha = fecha or datetime.now()
    dia = fecha.date()

    # Si el día está cerrado solo bloqueamos cuando es fecha actual (no histórica forzada)
    if not forzar_fecha:
        c = db.query(CashClosure).filter(CashClosure.fecha == dia).first()
        if c:
            raise ValueError(
                f"El día {dia} está cerrado. No se pueden registrar movimientos."
            )

    mov = CashMovement(
        tipo=tipo,
        concepto=concepto,
        monto=monto,
        referencia=(referencia or "").strip() or None,
        observacion=(observacion or "").strip() or None,
        fecha=fecha,
    )
    db.add(mov)
    return mov


# ----------------------------
# Resumen + Cierre diario
# ----------------------------
def resumen_del_dia(d: date) -> dict:
    start, end = _dt_range(d)

    with SessionLocal() as db:
        ingresos = (
            db.query(func.coalesce(func.sum(CashMovement.monto), 0.0))
            .filter(CashMovement.tipo == "INGRESO")
            .filter(CashMovement.fecha >= start, CashMovement.fecha <= end)
            .scalar()
        )
        egresos = (
            db.query(func.coalesce(func.sum(CashMovement.monto), 0.0))
            .filter(CashMovement.tipo == "EGRESO")
            .filter(CashMovement.fecha >= start, CashMovement.fecha <= end)
            .scalar()
        )

    saldo_inicial = obtener_saldo(
        hasta=datetime.combine(d, time.min) - timedelta(seconds=1)
    )
    ingresos = float(ingresos or 0.0)
    egresos = float(egresos or 0.0)
    saldo_final = float(saldo_inicial) + ingresos - egresos

    return {
        "fecha": d,
        "ingresos": ingresos,
        "egresos": egresos,
        "saldo_inicial": float(saldo_inicial),
        "saldo_final": float(saldo_final),
    }


def cerrar_dia(d: date, cerrado_por: str | None = None) -> CashClosure:
    if esta_cerrado(d):
        raise ValueError(f"El día {d} ya está cerrado.")

    data = resumen_del_dia(d)

    with SessionLocal() as db:
        c = CashClosure(
            fecha=d,
            total_ingresos=data["ingresos"],
            total_egresos=data["egresos"],
            saldo_inicial=data["saldo_inicial"],
            saldo_final=data["saldo_final"],
            cerrado_por=(cerrado_por or "").strip() or None,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return c


def resumen_rango(d1: date, d2: date) -> dict:
    if d2 < d1:
        d1, d2 = d2, d1

    start = datetime.combine(d1, time.min)
    end = datetime.combine(d2, time.max)

    with SessionLocal() as db:
        ingresos = (
            db.query(func.coalesce(func.sum(CashMovement.monto), 0.0))
            .filter(CashMovement.tipo == "INGRESO")
            .filter(CashMovement.fecha >= start, CashMovement.fecha <= end)
            .scalar()
        )
        egresos = (
            db.query(func.coalesce(func.sum(CashMovement.monto), 0.0))
            .filter(CashMovement.tipo == "EGRESO")
            .filter(CashMovement.fecha >= start, CashMovement.fecha <= end)
            .scalar()
        )

    saldo_inicial = obtener_saldo(hasta=start - timedelta(seconds=1))
    ingresos = float(ingresos or 0.0)
    egresos = float(egresos or 0.0)
    saldo_final = float(saldo_inicial) + ingresos - egresos

    return {
        "desde": d1,
        "hasta": d2,
        "ingresos": ingresos,
        "egresos": egresos,
        "saldo_inicial": float(saldo_inicial),
        "saldo_final": float(saldo_final),
    }
