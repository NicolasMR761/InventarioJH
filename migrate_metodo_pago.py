"""
Migración: agregar columna metodo_pago a tabla sales
Ejecutar una sola vez: python migrate_metodo_pago.py
"""
import sqlite3
from app.db.database import get_app_data_dir

db_path = get_app_data_dir() / "inventario.db"
con = sqlite3.connect(str(db_path))
try:
    con.execute("ALTER TABLE sales ADD COLUMN metodo_pago VARCHAR(30)")
    con.commit()
    print("✓ Columna metodo_pago agregada correctamente.")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("✓ La columna ya existe, no se necesita migración.")
    else:
        raise
finally:
    con.close()
