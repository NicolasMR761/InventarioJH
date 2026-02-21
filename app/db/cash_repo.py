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
    """
    Saldo = sum(INGRESO) - sum(EGRESO).
    Si hasta viene, calcula saldo acumulado hasta esa fecha/hora (incluye <= hasta).
    """
    with SessionLocal() as db:
        q = db.query(CashMovement)
        if hasta is not None:
            q = q.filter(CashMovement.fecha <= hasta)

        ingresos = (
            q.filter(CashMovement.tipo == "INGRESO")
            .with_entities(func.coalesce(func.sum(CashMovement.monto), 0.0))
            .scalar()
        )
        egresos = (
            q.filter(CashMovement.tipo == "EGRESO")
            .with_entities(func.coalesce(func.sum(CashMovement.monto), 0.0))
            .scalar()
        )

        return float(ingresos or 0.0) - float(egresos or 0.0)


def listar_movimientos(
    limit: int = 300,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    tipo: str | None = None,
    q: str | None = None,
) -> list[CashMovement]:
    """
    Lista movimientos con filtros:
    - rango de fechas por día (fecha_desde/fecha_hasta)
    - tipo: INGRESO/EGRESO
    - q: texto que busca en concepto/referencia/observacion
    """
    with SessionLocal() as db:
        query = db.query(CashMovement)

        if fecha_desde:
            query = query.filter(
                CashMovement.fecha >= datetime.combine(fecha_desde, time.min)
            )
        if fecha_hasta:
            query = query.filter(
                CashMovement.fecha <= datetime.combine(fecha_hasta, time.max)
            )

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

        return query.order_by(CashMovement.id.desc()).limit(limit).all()


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
    """
    Registra movimiento en caja (transacción propia).
    BLOQUEA si el día está cerrado.
    """
    tipo = (tipo or "").strip().upper()
    if tipo not in ("INGRESO", "EGRESO"):
        raise ValueError("Tipo inválido. Use INGRESO o EGRESO.")
    if float(monto or 0) <= 0:
        raise ValueError("Monto debe ser > 0.")

    fecha = fecha or datetime.now()
    dia = fecha.date()

    if esta_cerrado(dia):
        raise ValueError(
            f"El día {dia} está cerrado. No se pueden registrar movimientos."
        )

    with SessionLocal() as db:
        mov = CashMovement(
            tipo=tipo,
            concepto=(concepto or "").strip() or ("Movimiento " + tipo),
            monto=float(monto),
            referencia=(referencia or "").strip() or None,
            observacion=(observacion or "").strip() or None,
            fecha=fecha,
        )
        db.add(mov)
        db.commit()
        db.refresh(mov)
        return mov


# ----------------------------
# Registrar movimiento dentro de otra transacción (ventas/entradas)
# ----------------------------
def registrar_movimiento_en_db(
    db,
    tipo: str,
    concepto: str,
    monto: float,
    referencia: str | None = None,
    observacion: str | None = None,
    fecha: datetime | None = None,
) -> CashMovement:
    """
    Registra movimiento usando el mismo 'db' (misma transacción).
    También BLOQUEA si el día está cerrado.
    """
    tipo = (tipo or "").strip().upper()
    if tipo not in ("INGRESO", "EGRESO"):
        raise ValueError("Tipo inválido. Use INGRESO o EGRESO.")
    if float(monto or 0) <= 0:
        raise ValueError("Monto debe ser > 0.")

    fecha = fecha or datetime.now()
    dia = fecha.date()

    c = db.query(CashClosure).filter(CashClosure.fecha == dia).first()
    if c:
        raise ValueError(
            f"El día {dia} está cerrado. No se pueden registrar movimientos."
        )

    mov = CashMovement(
        tipo=tipo,
        concepto=(concepto or "").strip() or ("Movimiento " + tipo),
        monto=float(monto),
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
    """
    Retorna:
    - ingresos, egresos del día
    - saldo_inicial (saldo hasta el día anterior 23:59:59)
    - saldo_final (saldo_inicial + ingresos - egresos)
    """
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

    # saldo inicial: saldo hasta el día anterior
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
    """
    Crea un cierre diario. Si ya existe, error.
    """
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
    """
    Resumen de un rango de fechas (incluye días completos).
    - saldo_inicial: saldo justo antes de d1
    - ingresos/egresos: sumas del rango
    - saldo_final: saldo_inicial + ingresos - egresos
    """
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
