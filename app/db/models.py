from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    unidad = Column(String(20), default="und")
    precio_venta = Column(Float, default=0.0)
    stock_minimo = Column(Float, default=0.0)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    from sqlalchemy import Column, Integer, String, Boolean


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
