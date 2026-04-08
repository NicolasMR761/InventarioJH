from __future__ import annotations

from sqlalchemy import or_
from app.db.database import SessionLocal
from app.db.models import Customer, Sale


def crear_cliente(
    nombre: str, telefono: str | None = None, documento: str | None = None
) -> Customer:
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El nombre del cliente es obligatorio.")

    with SessionLocal() as db:
        c = Customer(
            nombre=nombre,
            telefono=(telefono or "").strip() or None,
            documento=(documento or "").strip() or None,
            activo=True,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return c


def listar_clientes(texto: str = "", incluir_inactivos: bool = False) -> list[Customer]:
    with SessionLocal() as db:
        q = db.query(Customer)
        if not incluir_inactivos:
            q = q.filter(Customer.activo.is_(True))
        if texto:
            like = f"%{texto.strip()}%"
            q = q.filter(
                or_(Customer.nombre.ilike(like), Customer.documento.ilike(like))
            )
        return q.order_by(Customer.nombre.asc()).all()


def obtener_cliente(customer_id: int) -> Customer | None:
    with SessionLocal() as db:
        return db.query(Customer).filter(Customer.id == int(customer_id)).first()


def actualizar_cliente(
    customer_id: int,
    nombre: str,
    telefono: str | None = None,
    documento: str | None = None,
) -> Customer:
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El nombre del cliente es obligatorio.")

    with SessionLocal() as db:
        c = db.query(Customer).filter(Customer.id == int(customer_id)).first()
        if not c:
            raise ValueError("Cliente no encontrado.")
        c.nombre = nombre
        c.telefono = (telefono or "").strip() or None
        c.documento = (documento or "").strip() or None
        db.commit()
        db.refresh(c)
        return c


def cambiar_estado_cliente(customer_id: int) -> None:
    with SessionLocal() as db:
        c = db.query(Customer).filter(Customer.id == int(customer_id)).first()
        if not c:
            raise ValueError("Cliente no encontrado.")
        c.activo = not c.activo
        db.commit()


def contar_ventas_cliente(customer_id: int) -> int:
    """Retorna el número de ventas (no anuladas) asociadas al cliente."""
    with SessionLocal() as db:
        return (
            db.query(Sale)
            .filter(
                Sale.customer_id == int(customer_id),
                Sale.anulada.is_(False),
            )
            .count()
        )


def eliminar_cliente(customer_id: int, forzar: bool = False) -> None:
    """
    Elimina un cliente de la base de datos.

    - Si el cliente tiene ventas activas y forzar=False → lanza ValueError.
    - Si forzar=True → elimina de todas formas (el historial de ventas
      queda en BD con customer_id huérfano, sin afectar el inventario).
    """
    with SessionLocal() as db:
        c = db.query(Customer).filter(Customer.id == int(customer_id)).first()
        if not c:
            raise ValueError("Cliente no encontrado.")

        if not forzar:
            num_ventas = (
                db.query(Sale)
                .filter(
                    Sale.customer_id == int(customer_id),
                    Sale.anulada.is_(False),
                )
                .count()
            )
            if num_ventas > 0:
                raise ValueError(
                    f"El cliente tiene {num_ventas} venta(s) registrada(s). "
                    "Usa forzar=True para eliminar de todas formas."
                )

        db.delete(c)
        db.commit()
