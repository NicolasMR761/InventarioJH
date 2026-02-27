from __future__ import annotations

from app.db.database import SessionLocal
from app.db.models import Entry, EntryDetail, Product, Supplier
from app.db.cash_repo import registrar_movimiento_en_db
from app.utils.formatters import fmt_cop, fmt_qty  # ← centralizado


def crear_entrada(
    supplier_id: int,
    items: list[dict],
    pagado: bool = True,
    metodo_pago: str = "Efectivo",
) -> Entry:
    """
    items = [
        {"product_id": 1, "cantidad": 2, "precio_compra": 3500},
        ...
    ]
    Crea entry + details, suma stock_actual a Product.
    Si pagado=True => registra EGRESO en caja (misma transacción).
    """
    if not items:
        raise ValueError("La entrada debe tener al menos 1 producto.")

    supplier_id = int(supplier_id)
    metodo_pago = (metodo_pago or "Efectivo").strip()

    with SessionLocal() as db:
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise ValueError("Proveedor no encontrado.")
        if not supplier.activo:
            raise ValueError("Proveedor inactivo. Actívalo para usarlo.")

        entry = Entry(supplier_id=supplier_id, total=0.0)
        total = 0.0
        detalles_txt: list[str] = []

        try:
            for it in items:
                product_id = int(it.get("product_id"))
                cantidad = float(it.get("cantidad", 0))
                precio = float(it.get("precio_compra", 0))

                if cantidad <= 0:
                    raise ValueError("La cantidad debe ser mayor a 0.")
                if precio < 0:
                    raise ValueError("El precio de compra no puede ser negativo.")

                product = db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    raise ValueError(f"Producto no encontrado (id={product_id}).")
                if not getattr(product, "activo", True):
                    raise ValueError(
                        f"Producto inactivo: {product.nombre}. Actívalo para usarlo."
                    )

                subtotal = cantidad * precio
                total += subtotal

                detail = EntryDetail(
                    product_id=product_id,
                    cantidad=cantidad,
                    precio_compra=precio,
                    subtotal=subtotal,
                )
                entry.details.append(detail)

                # Línea de detalle para Caja — usa formatters centralizados
                detalles_txt.append(
                    f"{product.nombre} x{fmt_qty(cantidad)} a {fmt_cop(precio)} c/u"
                )

                # Actualizar stock
                stock = float(getattr(product, "stock_actual", 0.0) or 0.0)
                product.stock_actual = stock + cantidad

            entry.total = float(total)
            db.add(entry)
            db.flush()

            if pagado:
                concepto = f"Compra (Entrada #{entry.id}) - {supplier.nombre}"
                observacion = "\n".join(detalles_txt).strip() if detalles_txt else None
                if metodo_pago:
                    observacion = (
                        (observacion + f"\nMétodo: {metodo_pago}")
                        if observacion
                        else f"Método: {metodo_pago}"
                    )

                registrar_movimiento_en_db(
                    db,
                    tipo="EGRESO",
                    concepto=concepto,
                    monto=float(entry.total),
                    referencia=f"Entrada {entry.id}",
                    observacion=observacion,
                )

            db.commit()
            db.refresh(entry)
            return entry

        except Exception:
            db.rollback()
            raise
