from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import joinedload

from app.db.database import SessionLocal
from app.db.models import Sale, SaleDetail, Product, Customer
from app.db.cash_repo import registrar_movimiento_en_db


def _fmt_cop(value: float) -> str:
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
        return (
            db.query(Sale)
            .options(joinedload(Sale.customer))
            .order_by(Sale.id.desc())
            .limit(limit)
            .all()
        )


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
        return (
            db.query(Sale)
            .options(
                joinedload(Sale.details).joinedload(SaleDetail.product),
                joinedload(Sale.customer),
            )
            .filter(Sale.id == int(sale_id))
            .first()
        )


def listar_ventas_pendientes() -> list[Sale]:
    """Ventas con estado_pago = PENDIENTE (fiadas) no anuladas."""
    with SessionLocal() as db:
        return (
            db.query(Sale)
            .options(joinedload(Sale.customer))
            .filter(Sale.estado_pago == "PENDIENTE", Sale.anulada.is_(False))
            .order_by(Sale.id.desc())
            .all()
        )


# ----------------------------
# Crear venta
# ----------------------------
def crear_venta(
    items: list[dict],
    metodo_pago: str = "Efectivo",
    customer_id: int | None = None,
    estado_pago: str = "PAGADO",
    numero_factura: str | None = None,
) -> Sale:
    """
    estado_pago: "PAGADO" | "PENDIENTE"
    - PAGADO   → registra INGRESO en caja inmediatamente
    - PENDIENTE → no toca caja (se cobra después con registrar_pago_pendiente)
    """
    if not items:
        raise ValueError("La venta debe tener al menos 1 producto.")

    metodo_pago = (metodo_pago or "Efectivo").strip()
    estado_pago = (estado_pago or "PAGADO").strip().upper()
    if estado_pago not in ("PAGADO", "PENDIENTE"):
        raise ValueError("estado_pago debe ser PAGADO o PENDIENTE.")

    with SessionLocal() as db:
        # Validar cliente si se proporcionó
        if customer_id:
            cliente = db.query(Customer).filter(Customer.id == int(customer_id)).first()
            if not cliente:
                raise ValueError("Cliente no encontrado.")
        else:
            cliente = None

        sale = Sale(
            total=0.0,
            customer_id=int(customer_id) if customer_id else None,
            estado_pago=estado_pago,
            metodo_pago=metodo_pago,
            numero_factura=(numero_factura or "").strip() or None,
            anulada=False,
            motivo_anulacion=None,
            anulada_en=None,
            pagado_en=datetime.now() if estado_pago == "PAGADO" else None,
        )
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
                    raise ValueError(f"Producto inactivo: {product.nombre}.")

                stock = float(getattr(product, "stock_actual", 0.0) or 0.0)
                if stock < cantidad:
                    raise ValueError(
                        f"Stock insuficiente para '{product.nombre}'. "
                        f"Disponible: {stock}, requerido: {cantidad}."
                    )

                subtotal = cantidad * precio_venta
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
            db.add(sale)
            db.flush()

            # Caja solo si está pagado
            if estado_pago == "PAGADO":
                observacion = "\n".join(detalle_lineas) or None
                if metodo_pago:
                    observacion = (
                        (observacion + f"\nMétodo: {metodo_pago}")
                        if observacion
                        else f"Método: {metodo_pago}"
                    )
                if cliente:
                    observacion = (
                        (observacion + f"\nCliente: {cliente.nombre}")
                        if observacion
                        else f"Cliente: {cliente.nombre}"
                    )

                registrar_movimiento_en_db(
                    db,
                    tipo="INGRESO",
                    concepto=f"Venta {sale.numero_factura or f'#{sale.id}'}",
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
# Registrar pago de venta pendiente (cobrar fiado)
# ----------------------------
def registrar_pago_pendiente(sale_id: int, metodo_pago: str = "Efectivo") -> Sale:
    """
    Marca una venta PENDIENTE como PAGADO y registra el INGRESO en caja.
    """
    metodo_pago = (metodo_pago or "Efectivo").strip()

    with SessionLocal() as db:
        try:
            sale = (
                db.query(Sale)
                .options(joinedload(Sale.customer))
                .filter(Sale.id == int(sale_id))
                .first()
            )
            if not sale:
                raise ValueError("Venta no encontrada.")
            if getattr(sale, "anulada", False):
                raise ValueError("La venta está anulada.")
            if sale.estado_pago == "PAGADO":
                raise ValueError("Esta venta ya está pagada.")

            sale.estado_pago = "PAGADO"
            sale.metodo_pago = metodo_pago
            sale.pagado_en = datetime.now()
            db.flush()

            cliente_nombre = sale.customer.nombre if sale.customer else "Sin cliente"
            observacion = (
                f"Cobro de fiado\nCliente: {cliente_nombre}\nMétodo: {metodo_pago}"
            )

            registrar_movimiento_en_db(
                db,
                tipo="INGRESO",
                concepto=f"Cobro venta {sale.numero_factura or f'#{sale.id}'}",
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

                    if costo_venta > 0 and devolucion > 0:
                        stock_nuevo = stock + devolucion
                        product.costo_promedio = (
                            stock * costo_actual + devolucion * costo_venta
                        ) / stock_nuevo
                    product.stock_actual = stock + devolucion

            sale.anulada = True
            sale.motivo_anulacion = motivo_txt
            sale.anulada_en = datetime.now()
            db.add(sale)
            db.flush()

            # Solo revertir caja si la venta estaba pagada
            total_venta = float(sale.total or 0.0)
            if total_venta > 0 and sale.estado_pago == "PAGADO":
                obs_parts = []
                if metodo_pago:
                    obs_parts.append(f"Método: {metodo_pago}")
                if motivo_txt:
                    obs_parts.append(f"Motivo: {motivo_txt}")

                registrar_movimiento_en_db(
                    db,
                    tipo="EGRESO",
                    concepto=f"Anulación venta {sale.numero_factura or f'#{sale.id}'}",
                    monto=total_venta,
                    referencia=f"Venta #{sale.id}",
                    observacion="\n".join(obs_parts) or None,
                )

            db.commit()
            db.refresh(sale)
            return sale

        except Exception:
            db.rollback()
            raise
