from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Date,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from sqlalchemy.sql import func

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    unidad = Column(String(20), default="und")
    precio_venta = Column(Float, default=0.0)
    stock_minimo = Column(Float, default=0.0)
    stock_actual = Column(Float, default=0.0)  # ← NUEVO
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    costo_promedio = Column(Float, default=0.0)


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    nit = Column(String(50), unique=True, nullable=True)
    telefono = Column(String(50), nullable=True)
    direccion = Column(String(200), nullable=True)
    activo = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Supplier {self.nombre}>"


class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)

    fecha = Column(DateTime, default=datetime.utcnow)
    total = Column(Float, default=0.0)

    supplier = relationship("Supplier")
    details = relationship(
        "EntryDetail", back_populates="entry", cascade="all, delete-orphan"
    )


class EntryDetail(Base):
    __tablename__ = "entry_details"

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey("entries.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    cantidad = Column(Float, nullable=False)
    precio_compra = Column(Float, default=0.0)
    subtotal = Column(Float, default=0.0)

    entry = relationship("Entry", back_populates="details")
    product = relationship("Product")


class CashMovement(Base):
    __tablename__ = "cash_movements"

    id = Column(Integer, primary_key=True, index=True)

    tipo = Column(String, nullable=False)
    # "INGRESO" o "EGRESO"

    concepto = Column(String, nullable=False)

    monto = Column(Float, nullable=False)

    fecha = Column(DateTime(timezone=True), server_default=func.now())

    referencia = Column(String, nullable=True)
    # ejemplo: "Venta #5" o "Compra #3"

    observacion = Column(String, nullable=True)


class CashClosure(Base):
    __tablename__ = "cash_closures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False, unique=True)  # 1 cierre por día

    total_ingresos = Column(Float, default=0.0)
    total_egresos = Column(Float, default=0.0)
    saldo_inicial = Column(Float, default=0.0)
    saldo_final = Column(Float, default=0.0)

    creado_en = Column(DateTime, default=datetime.now)
    cerrado_por = Column(String(120), nullable=True)  # opcional (usuario)


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    total = Column(Float, default=0.0)

    details = relationship(
        "SaleDetail", back_populates="sale", cascade="all, delete-orphan"
    )
    anulada = Column(Boolean, default=False)
    motivo_anulacion = Column(String(255), nullable=True)
    anulada_en = Column(DateTime, nullable=True)


class SaleDetail(Base):
    __tablename__ = "sale_details"

    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    cantidad = Column(Float, nullable=False)
    precio_venta = Column(Float, default=0.0)
    subtotal = Column(Float, default=0.0)
    costo_unitario = Column(Float, default=0.0)
    utilidad = Column(Float, default=0.0)

    sale = relationship("Sale", back_populates="details")
    product = relationship("Product")
