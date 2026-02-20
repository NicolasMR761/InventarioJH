import sqlite3
from pathlib import Path

db_path = Path("app_data") / "inventario.db"
con = sqlite3.connect(db_path)
cur = con.cursor()

print("BD:", db_path.resolve())

def show(sql, params=()):
    cur.execute(sql, params)
    rows = cur.fetchall()
    for r in rows:
        print(r)

print("\n== PRAGMA products ==")
show("PRAGMA table_info(products)")

print("\n== ULTIMOS 10 PRODUCTS (id, codigo, nombre, stock_actual) ==")
try:
    show("SELECT id, codigo, nombre, stock_actual FROM products ORDER BY id DESC LIMIT 10")
except Exception as e:
    print("ERROR:", e)

print("\n== ULTIMAS 10 ENTRIES (id, supplier_id, total) ==")
try:
    show("SELECT id, supplier_id, total FROM entries ORDER BY id DESC LIMIT 10")
except Exception as e:
    print("ERROR:", e)

print("\n== ULTIMOS 20 ENTRY_DETAILS (entry_id, product_id, cantidad, precio_compra) ==")
try:
    show("SELECT entry_id, product_id, cantidad, precio_compra FROM entry_details ORDER BY rowid DESC LIMIT 20")
except Exception as e:
    print("ERROR:", e)

con.close()
