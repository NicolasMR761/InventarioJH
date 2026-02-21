from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import joinedload

from app.db.database import SessionLocal
from app.db.models import Sale, SaleDetail, Product, CashMovement
from app.db.cash_repo import registrar_movimiento_en_db


# ----------------------------
# Consultas
# ----------------------------
def listar_ventas(limit: int = 200) -> list[Sale]:
    """Lista ventas recientes (incluye flags de anulación si existen en el modelo)."""
    with SessionLocal() as db:
        return db.query(Sale).order_by(Sale.id.desc()).limit(limit).all()


def obtener_venta(sale_id: int) -> Sale | None:
    """Obtiene una venta con sus detalles."""
    with SessionLocal() as db:
        return (
            db.query(Sale)
            .options(joinedload(Sale.details))
            .filter(Sale.id == int(sale_id))
            .first()
        )


def obtener_venta_con_detalle(sale_id: int) -> Sale | None:
    with SessionLocal() as db:
        sale = (
            db.query(Sale)
            .options(joinedload(Sale.details).joinedload(SaleDetail.product))
            .filter(Sale.id == int(sale_id))
            .first()
        )
        return sale


# ----------------------------
# Crear venta
# ----------------------------
def crear_venta(items: list[dict], metodo_pago: str = "Efectivo") -> Sale:
    """
    items = [
        {"product_id": 1, "cantidad": 2, "precio_venta": 5000},
        ...
    ]

    Crea Sale + SaleDetail y RESTA stock_actual a Product.
    Valida stock suficiente.
    Registra movimiento en caja (INGRESO) EN LA MISMA TRANSACCIÓN.

    metodo_pago: texto que se guarda en observación del movimiento de caja.
    """
    if not items:
        raise ValueError("La venta debe tener al menos 1 producto.")

    metodo_pago = (metodo_pago or "Efectivo").strip()

    with SessionLocal() as db:
        sale = Sale(total=0.0)
        total = 0.0

        try:
            for it in items:
                product_id = int(it.get("product_id"))
                cantidad = float(it.get("cantidad", 0))
                precio_venta = float(it.get("precio_venta", 0))

                if cantidad <= 0:
                    raise ValueError("La cantidad debe ser mayor que 0.")
                if precio_venta < 0:
                    raise ValueError("El precio de venta no puede ser negativo.")

                product = db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    raise ValueError(f"Producto no encontrado (ID {product_id}).")
                if not getattr(product, "activo", True):
                    raise ValueError(
                        f"Producto inactivo: {product.nombre}. Actívalo para venderlo."
                    )

                stock = float(getattr(product, "stock_actual", 0.0) or 0.0)
                if stock < cantidad:
                    raise ValueError(
                        f"Stock insuficiente para '{product.nombre}'. "
                        f"Disponible: {stock}, requerido: {cantidad}."
                    )

                subtotal = cantidad * precio_venta

                detail = SaleDetail(
                    product_id=product_id,
                    cantidad=cantidad,
                    precio_venta=precio_venta,
                    subtotal=subtotal,
                )

                sale.details.append(detail)

                # Descontar stock
                product.stock_actual = stock - cantidad

                total += subtotal

            sale.total = float(total)

            # Por compatibilidad si tu modelo Sale tiene campos de anulación
            if hasattr(sale, "anulada"):
                sale.anulada = False
            if hasattr(sale, "motivo_anulacion"):
                sale.motivo_anulacion = None
            if hasattr(sale, "anulada_en"):
                sale.anulada_en = None

            db.add(sale)
            db.flush()  # para obtener sale.id

            # Movimiento de caja (misma transacción)
            registrar_movimiento_en_db(
                db,
                tipo="INGRESO",
                concepto="Venta",
                monto=float(sale.total),
                referencia=f"Venta #{sale.id}",
                observacion=f"Método: {metodo_pago}" if metodo_pago else None,
            )

            db.commit()
            db.refresh(sale)
            return sale

        except Exception:
            db.rollback()
            raise


# ----------------------------
# Anular venta
# ----------------------------
def anular_venta(
    sale_id: int, motivo: str | None = None, metodo_pago: str | None = None
) -> Sale:
    """
    Anula una venta:
    - Marca Sale.anulada = True (si existe)
    - Guarda motivo y fecha (si existen)
    - Devuelve stock de cada producto
    - Registra un EGRESO en caja (devolución) en la misma transacción

    metodo_pago (opcional): si lo pasas, queda en observación junto con el motivo.
    """
    metodo_pago = (metodo_pago or "").strip() or None
    motivo_txt = (motivo or "").strip() or None

    with SessionLocal() as db:
        try:
            sale = (
                db.query(Sale)
                .options(joinedload(Sale.details))
                .filter(Sale.id == int(sale_id))
                .first()
            )
            if not sale:
                raise ValueError("Venta no encontrada.")

            if hasattr(sale, "anulada") and sale.anulada:
                raise ValueError("La venta ya está anulada.")

            # Devolver stock
            for d in sale.details:
                product = db.query(Product).filter(Product.id == d.product_id).first()
                if product:
                    stock = float(getattr(product, "stock_actual", 0.0) or 0.0)
                    product.stock_actual = stock + float(d.cantidad or 0.0)

            # Marcar anulación si existen campos
            if hasattr(sale, "anulada"):
                sale.anulada = True
            if hasattr(sale, "motivo_anulacion"):
                sale.motivo_anulacion = motivo_txt
            if hasattr(sale, "anulada_en"):
                sale.anulada_en = datetime.now()

            db.add(sale)
            db.flush()

            obs_parts = []
            if metodo_pago:
                obs_parts.append(f"Método: {metodo_pago}")
            if motivo_txt:
                obs_parts.append(f"Motivo: {motivo_txt}")
            obs = " | ".join(obs_parts) if obs_parts else None

            registrar_movimiento_en_db(
                db,
                tipo="EGRESO",
                concepto="Anulación de venta",
                monto=float(sale.total or 0.0),
                referencia=f"Venta #{sale.id}",
                observacion=obs,
            )

            db.commit()
            db.refresh(sale)
            return sale

        except Exception:
            db.rollback()
            raise
