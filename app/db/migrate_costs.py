from pathlib import Path
import sqlite3

DB_PATH = Path("app_data/inventario.db")


def column_exists(cur, table: str, col: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos en: {DB_PATH.resolve()}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    if not column_exists(cur, "products", "costo_promedio"):
        cur.execute("ALTER TABLE products ADD COLUMN costo_promedio REAL DEFAULT 0")
        print("OK: products.costo_promedio agregado")
    else:
        print("SKIP: products.costo_promedio ya existe")

    if not column_exists(cur, "sale_details", "costo_unitario"):
        cur.execute("ALTER TABLE sale_details ADD COLUMN costo_unitario REAL DEFAULT 0")
        print("OK: sale_details.costo_unitario agregado")
    else:
        print("SKIP: sale_details.costo_unitario ya existe")

    if not column_exists(cur, "sale_details", "utilidad"):
        cur.execute("ALTER TABLE sale_details ADD COLUMN utilidad REAL DEFAULT 0")
        print("OK: sale_details.utilidad agregado")
    else:
        print("SKIP: sale_details.utilidad ya existe")

    con.commit()
    con.close()
    print("✅ Migración lista.")


if __name__ == "__main__":
    main()
