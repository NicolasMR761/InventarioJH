from __future__ import annotations

from app.db.database import SessionLocal
from app.db.models import Entry, EntryDetail, Product, Supplier

from app.db.cash_repo import registrar_movimiento_en_db


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
    Respeta cierres diarios (bloquea movimientos si el día está cerrado).
    """
    if not items:
        raise ValueError("La entrada debe tener al menos 1 producto.")

    metodo_pago = (metodo_pago or "Efectivo").strip()

    with SessionLocal() as db:
        supplier = db.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
        if not supplier:
            raise ValueError("Proveedor no encontrado.")
        if not supplier.activo:
            raise ValueError("Proveedor inactivo. Actívalo para usarlo.")

        entry = Entry(supplier_id=int(supplier_id), total=0.0)
        total = 0.0

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

                # ✅ Actualiza stock
                product.stock_actual = (
                    float(getattr(product, "stock_actual", 0.0) or 0.0) + cantidad
                )

            entry.total = float(total)

            db.add(entry)
            db.flush()  # para obtener entry.id sin cerrar transacción

            # ✅ Caja (misma transacción)
            if pagado:
                concepto = f"Compra (Entrada #{entry.id}) - {supplier.nombre}"
                registrar_movimiento_en_db(
                    db,
                    tipo="EGRESO",
                    concepto=concepto,
                    monto=float(entry.total),
                    referencia=f"Entrada {entry.id}",
                    observacion=f"Método: {metodo_pago}" if metodo_pago else None,
                )

            db.commit()
            db.refresh(entry)
            return entry

        except Exception:
            db.rollback()
            raise
