from sqlalchemy import or_
from app.db.database import SessionLocal
from app.db.models import Supplier


def crear_proveedor(nombre, nit=None, telefono=None, direccion=None):
    with SessionLocal() as db:
        if nit:
            existente = db.query(Supplier).filter(Supplier.nit == nit).first()
            if existente:
                raise ValueError("Ya existe un proveedor con ese NIT.")

        p = Supplier(
            nombre=nombre.strip(),
            nit=nit.strip() if nit else None,
            telefono=telefono,
            direccion=direccion,
            activo=True,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return p


def listar_proveedores(texto="", incluir_inactivos=True):
    with SessionLocal() as db:
        q = db.query(Supplier)

        if not incluir_inactivos:
            q = q.filter(Supplier.activo == True)  # noqa

        if texto:
            like = f"%{texto}%"
            q = q.filter(
                or_(
                    Supplier.nombre.ilike(like),
                    Supplier.nit.ilike(like),
                )
            )

        return q.order_by(Supplier.id.desc()).all()


def obtener_proveedor(supplier_id):
    with SessionLocal() as db:
        return db.query(Supplier).filter(Supplier.id == supplier_id).first()


def actualizar_proveedor(supplier_id, nombre, nit=None, telefono=None, direccion=None):
    with SessionLocal() as db:
        p = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not p:
            raise ValueError("Proveedor no encontrado.")

        if nit:
            existente = (
                db.query(Supplier)
                .filter(Supplier.nit == nit, Supplier.id != supplier_id)
                .first()
            )
            if existente:
                raise ValueError("Ya existe un proveedor con ese NIT.")

        p.nombre = nombre.strip()
        p.nit = nit.strip() if nit else None
        p.telefono = telefono
        p.direccion = direccion

        db.commit()
        db.refresh(p)
        return p


def desactivar_proveedor(supplier_id):
    with SessionLocal() as db:
        p = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not p:
            raise ValueError("Proveedor no encontrado.")

        p.activo = False
        db.commit()


def cambiar_estado_proveedor(supplier_id: int) -> None:
    with SessionLocal() as db:
        p = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not p:
            raise ValueError("Proveedor no encontrado.")

        p.activo = not p.activo
        db.commit()
