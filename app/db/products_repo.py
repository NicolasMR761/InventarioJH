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


def listar_productos() -> list[Product]:
    """Lista todos los productos (ordenados por id desc)."""
    with SessionLocal() as db:
        return db.query(Product).order_by(Product.id.desc()).all()
