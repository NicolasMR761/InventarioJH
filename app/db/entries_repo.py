from app.db.database import SessionLocal
from app.db.models import Entry, EntryDetail, Product, Supplier


def crear_entrada(supplier_id: int, items: list[dict]) -> Entry:
    """
    items = [
        {"product_id": 1, "cantidad": 2, "precio_compra": 3500},
        ...
    ]
    Crea entry + details y suma stock_actual a Product.
    """
    if not items:
        raise ValueError("La entrada debe tener al menos 1 producto.")

    with SessionLocal() as db:
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise ValueError("Proveedor no encontrado.")
        if not supplier.activo:
            raise ValueError("Proveedor inactivo. Actívalo para usarlo.")

        entry = Entry(supplier_id=supplier_id, total=0.0)

        total = 0.0

        # Transacción
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
                if not product.activo:
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
                product.stock_actual = float(product.stock_actual or 0.0) + cantidad

            entry.total = total

            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry

        except Exception:
            db.rollback()
            raise
