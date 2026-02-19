from sqlalchemy import or_
from app.db.database import SessionLocal
from app.db.models import Product


def crear_producto(
    codigo: str,
    nombre: str,
    unidad: str = "und",
    precio_venta: float = 0.0,
    stock_minimo: float = 0.0,
) -> Product:
    """Crea un producto. Lanza ValueError si el código ya existe."""
    with SessionLocal() as db:
        existente = db.query(Product).filter(Product.codigo == codigo).first()
        if existente:
            raise ValueError(f"Ya existe un producto con código: {codigo}")

        p = Product(
            codigo=codigo.strip(),
            nombre=nombre.strip(),
            unidad=unidad.strip() or "und",
            precio_venta=float(precio_venta),
            stock_minimo=float(stock_minimo),
            activo=True,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return p


def obtener_producto(product_id: int) -> Product | None:
    with SessionLocal() as db:
        return db.query(Product).filter(Product.id == product_id).first()


def listar_productos(
    texto: str = "",
    incluir_inactivos: bool = True,
) -> list[Product]:
    """Lista productos con filtro por código/nombre."""
    with SessionLocal() as db:
        q = db.query(Product)

        if not incluir_inactivos:
            q = q.filter(Product.activo == True)  # noqa: E712

        texto = (texto or "").strip()
        if texto:
            like = f"%{texto}%"
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
    with SessionLocal() as db:
        p = db.query(Product).filter(Product.id == product_id).first()
        if not p:
            raise ValueError("Producto no encontrado.")

        codigo = codigo.strip()
        nombre = nombre.strip()
        unidad = (unidad or "und").strip()

        if not codigo or not nombre:
            raise ValueError("Código y Nombre son obligatorios.")

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
        p.precio_venta = float(precio_venta)
        p.stock_minimo = float(stock_minimo)

        db.commit()
        db.refresh(p)
        return p


def desactivar_producto(product_id: int) -> None:
    """Soft delete."""
    with SessionLocal() as db:
        p = db.query(Product).filter(Product.id == product_id).first()
        if not p:
            raise ValueError("Producto no encontrado.")

        p.activo = False
        db.commit()
