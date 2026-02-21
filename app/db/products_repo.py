from __future__ import annotations

from sqlalchemy import or_
from app.db.database import SessionLocal
from app.db.models import Product


def _to_float(value, default: float = 0.0) -> float:
    """Convierte a float de forma segura."""
    if value is None or value == "":
        return float(default)
    return float(value)


def crear_producto(
    codigo: str,
    nombre: str,
    unidad: str = "und",
    precio_venta: float = 0.0,
    stock_minimo: float = 0.0,
) -> Product:
    """Crea un producto. Lanza ValueError si el código ya existe."""
    codigo = (codigo or "").strip()
    nombre = (nombre or "").strip()
    unidad = (unidad or "und").strip() or "und"

    if not codigo or not nombre:
        raise ValueError("Código y Nombre son obligatorios.")

    precio_venta = _to_float(precio_venta, 0.0)
    stock_minimo = _to_float(stock_minimo, 0.0)

    if precio_venta < 0:
        raise ValueError("El precio de venta no puede ser negativo.")
    if stock_minimo < 0:
        raise ValueError("El stock mínimo no puede ser negativo.")

    with SessionLocal() as db:
        existente = db.query(Product).filter(Product.codigo == codigo).first()
        if existente:
            raise ValueError(f"Ya existe un producto con código: {codigo}")

        p = Product(
            codigo=codigo,
            nombre=nombre,
            unidad=unidad,
            precio_venta=precio_venta,
            stock_minimo=stock_minimo,
            # stock_actual normalmente inicia en 0 y se maneja por Entradas/Ventas
            activo=True,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return p


def obtener_producto(product_id: int) -> Product | None:
    with SessionLocal() as db:
        return db.query(Product).filter(Product.id == int(product_id)).first()


def obtener_producto_por_codigo(codigo: str) -> Product | None:
    codigo = (codigo or "").strip()
    if not codigo:
        return None
    with SessionLocal() as db:
        return db.query(Product).filter(Product.codigo == codigo).first()


def listar_productos(
    texto: str = "",
    incluir_inactivos: bool = True,
) -> list[Product]:
    """Lista productos con filtro por código/nombre."""
    texto = (texto or "").strip()

    with SessionLocal() as db:
        q = db.query(Product)

        if not incluir_inactivos:
            q = q.filter(Product.activo.is_(True))

        if texto:
            like = f"%{texto}%"
            # Nota: ilike puede comportarse como like en SQLite dependiendo de collation
            q = q.filter(or_(Product.codigo.ilike(like), Product.nombre.ilike(like)))

        return q.order_by(Product.id.desc()).all()


def actualizar_producto(
    product_id: int,
    codigo: str,
    nombre: str,
    unidad: str = "und",
    precio_venta: float = 0.0,
    stock_minimo: float = 0.0,
) -> Product:
    """Edita un producto. Valida código único (excepto el mismo producto)."""
    product_id = int(product_id)
    codigo = (codigo or "").strip()
    nombre = (nombre or "").strip()
    unidad = (unidad or "und").strip() or "und"

    if not codigo or not nombre:
        raise ValueError("Código y Nombre son obligatorios.")

    precio_venta = _to_float(precio_venta, 0.0)
    stock_minimo = _to_float(stock_minimo, 0.0)

    if precio_venta < 0:
        raise ValueError("El precio de venta no puede ser negativo.")
    if stock_minimo < 0:
        raise ValueError("El stock mínimo no puede ser negativo.")

    with SessionLocal() as db:
        p = db.query(Product).filter(Product.id == product_id).first()
        if not p:
            raise ValueError("Producto no encontrado.")

        existente = (
            db.query(Product)
            .filter(Product.codigo == codigo, Product.id != product_id)
            .first()
        )
        if existente:
            raise ValueError(f"Ya existe un producto con código: {codigo}")

        p.codigo = codigo
        p.nombre = nombre
        p.unidad = unidad
        p.precio_venta = precio_venta
        p.stock_minimo = stock_minimo

        db.commit()
        db.refresh(p)
        return p


def cambiar_estado_producto(product_id: int) -> Product:
    """Activa/Desactiva un producto y devuelve el producto actualizado."""
    with SessionLocal() as db:
        p = db.query(Product).filter(Product.id == int(product_id)).first()
        if not p:
            raise ValueError("Producto no encontrado.")

        p.activo = not bool(p.activo)
        db.commit()
        db.refresh(p)
        return p


def desactivar_producto(product_id: int) -> None:
    """Soft delete (compatibilidad)."""
    with SessionLocal() as db:
        p = db.query(Product).filter(Product.id == int(product_id)).first()
        if not p:
            raise ValueError("Producto no encontrado.")
        p.activo = False
        db.commit()


def es_stock_bajo(p: Product) -> bool:
    """
    Helper para UI:
    - Solo alerta si stock_minimo > 0
    - Alerta si stock_actual <= stock_minimo
    """
    stock = float(getattr(p, "stock_actual", 0.0) or 0.0)
    minimo = float(getattr(p, "stock_minimo", 0.0) or 0.0)
    return minimo > 0 and stock <= minimo
