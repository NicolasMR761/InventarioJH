from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import joinedload

from app.db.database import SessionLocal
from app.db.models import Sale, SaleDetail, Product
from app.db.cash_repo import registrar_movimiento_en_db


def _fmt_cop(value: float) -> str:
    """Formatea a pesos COP estilo $5.000 (sin decimales)."""
    try:
        n = int(round(float(value)))
    except Exception:
        n = 0
    return "$" + f"{n:,}".replace(",", ".")


# ----------------------------
# Consultas
# ----------------------------
def listar_ventas(limit: int = 200) -> list[Sale]:
    with SessionLocal() as db:
        return db.query(Sale).order_by(Sale.id.desc()).limit(limit).all()


def obtener_venta(sale_id: int) -> Sale | None:
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

    Crea Sale + SaleDetail, resta stock_actual a Product.
    Calcula costo_unitario (costo_promedio actual) y utilidad por línea.
    Registra movimiento en caja (INGRESO) en la misma transacción.
    """
    if not items:
        raise ValueError("La venta debe tener al menos 1 producto.")

    metodo_pago = (metodo_pago or "Efectivo").strip()

    with SessionLocal() as db:
        sale = Sale(total=0.0)
        total = 0.0
        detalle_lineas: list[str] = []

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

                # ✅ FIX #1: Calcular costo_unitario y utilidad
                costo_unitario = float(getattr(product, "costo_promedio", 0.0) or 0.0)
                utilidad = (precio_venta - costo_unitario) * cantidad

                detail = SaleDetail(
                    product_id=product_id,
                    cantidad=cantidad,
                    precio_venta=precio_venta,
                    subtotal=subtotal,
                    costo_unitario=costo_unitario,
                    utilidad=utilidad,
                )
                sale.details.append(detail)

                product.stock_actual = stock - cantidad
                total += subtotal

                cant_txt = (
                    f"{int(cantidad)}"
                    if float(cantidad).is_integer()
                    else f"{cantidad:g}"
                )
                detalle_lineas.append(
                    f"{product.nombre} x{cant_txt} a {_fmt_cop(precio_venta)} c/u"
                )

            sale.total = float(total)

            if hasattr(sale, "anulada"):
                sale.anulada = False
            if hasattr(sale, "motivo_anulacion"):
                sale.motivo_anulacion = None
            if hasattr(sale, "anulada_en"):
                sale.anulada_en = None

            db.add(sale)
            db.flush()

            observacion = "\n".join(detalle_lineas).strip() if detalle_lineas else None
            if metodo_pago:
                observacion = (
                    (observacion + f"\nMétodo: {metodo_pago}")
                    if observacion
                    else f"Método: {metodo_pago}"
                )

            registrar_movimiento_en_db(
                db,
                tipo="INGRESO",
                concepto="Venta",
                monto=float(sale.total),
                referencia=f"Venta #{sale.id}",
                observacion=observacion,
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
    - Marca Sale.anulada = True
    - Devuelve stock de cada producto
    - Registra EGRESO en caja (devolución) en la misma transacción

    ✅ FIX #2: Si total es 0, omite el movimiento de caja (evita error monto > 0).
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

            for d in sale.details:
                product = db.query(Product).filter(Product.id == d.product_id).first()
                if product:
                    stock = float(getattr(product, "stock_actual", 0.0) or 0.0)
                    devolucion = float(d.cantidad or 0.0)
                    costo_actual = float(getattr(product, "costo_promedio", 0.0) or 0.0)
                    costo_venta = float(getattr(d, "costo_unitario", 0.0) or 0.0)

                    # ✅ FIX #2: Recalcular costo promedio ponderado al devolver stock
                    if costo_venta > 0 and devolucion > 0:
                        stock_nuevo = stock + devolucion
                        product.costo_promedio = (
                            stock * costo_actual + devolucion * costo_venta
                        ) / stock_nuevo

                    product.stock_actual = stock + devolucion

            if hasattr(sale, "anulada"):
                sale.anulada = True
            if hasattr(sale, "motivo_anulacion"):
                sale.motivo_anulacion = motivo_txt
            if hasattr(sale, "anulada_en"):
                sale.anulada_en = datetime.now()

            db.add(sale)
            db.flush()

            # ✅ FIX #2: Solo registrar movimiento de caja si el total es > 0
            total_venta = float(sale.total or 0.0)
            if total_venta > 0:
                obs_parts = []
                if metodo_pago:
                    obs_parts.append(f"Método: {metodo_pago}")
                if motivo_txt:
                    obs_parts.append(f"Motivo: {motivo_txt}")
                obs = "\n".join(obs_parts).strip() if obs_parts else None

                registrar_movimiento_en_db(
                    db,
                    tipo="EGRESO",
                    concepto="Anulación de venta",
                    monto=total_venta,
                    referencia=f"Venta #{sale.id}",
                    observacion=obs,
                )

            db.commit()
            db.refresh(sale)
            return sale

        except Exception:
            db.rollback()
            raise
