from __future__ import annotations

from app.db.database import SessionLocal
from app.db.models import Product, Sale, SaleDetail
from datetime import datetime


def crear_venta(items: list[dict]) -> Sale:
    """
    items = [
        {"product_id": 1, "cantidad": 2, "precio_venta": 5000},
        ...
    ]

    Crea Sale + SaleDetail y RESTA stock_actual a Product.
    Valida stock suficiente.
    """
    if not items:
        raise ValueError("La venta debe tener al menos 1 producto.")

    with SessionLocal() as db:
        sale = Sale(total=0.0)
        total = 0.0

        try:
            for it in items:
                # Validación de entrada
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
                if not product.activo:
                    raise ValueError(
                        f"Producto inactivo: {product.nombre}. Actívalo para venderlo."
                    )

                stock = float(product.stock_actual or 0.0)
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

            sale.total = total
            db.add(sale)
            db.commit()
            db.refresh(sale)
            return sale

        except Exception:
            db.rollback()
            raise


from sqlalchemy.orm import joinedload


def listar_ventas(limit: int = 200) -> list[Sale]:
    with SessionLocal() as db:
        return db.query(Sale).order_by(Sale.id.desc()).limit(limit).all()


def obtener_venta_con_detalle(sale_id: int) -> Sale | None:
    with SessionLocal() as db:
        return (
            db.query(Sale)
            .options(joinedload(Sale.details).joinedload(SaleDetail.product))
            .filter(Sale.id == sale_id)
            .first()
        )


def eliminar_venta(sale_id: int) -> None:
    """
    OJO: esto NO devuelve stock. (Por ahora)
    Luego, si quieres, implementamos 'anular venta' que sí devuelve stock.
    """
    with SessionLocal() as db:
        sale = db.query(Sale).filter(Sale.id == sale_id).first()
        if not sale:
            raise ValueError("Venta no encontrada.")
        db.delete(sale)
        db.commit()


def anular_venta(sale_id: int, motivo: str = "") -> Sale:
    """
    Anula una venta y devuelve stock.
    """
    with SessionLocal() as db:
        sale = (
            db.query(Sale)
            .options(joinedload(Sale.details))
            .filter(Sale.id == sale_id)
            .first()
        )
        if not sale:
            raise ValueError("Venta no encontrada.")

        if getattr(sale, "anulada", False):
            raise ValueError("La venta ya está anulada.")

        # devolver stock
        for d in sale.details:
            product = db.query(Product).filter(Product.id == d.product_id).first()
            if product:
                product.stock_actual = float(product.stock_actual or 0.0) + float(
                    d.cantidad or 0.0
                )

        sale.anulada = True
        sale.motivo_anulacion = motivo.strip() or None
        sale.anulada_en = datetime.utcnow()

        db.commit()
        db.refresh(sale)
        return sale
