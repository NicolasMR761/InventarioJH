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
