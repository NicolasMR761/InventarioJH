"""
Migración: agrega columnas nuevas a 'sales' y crea tabla 'customers'.
Ejecutar UNA sola vez antes de usar la nueva versión.

    python -m app.db.migrate_sales_v2
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("app_data/inventario.db")


def col_exists(cur, table: str, col: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())


def table_exists(cur, table: str) -> bool:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró la base de datos en: {DB_PATH.resolve()}"
        )

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # --- Tabla customers ---
    if not table_exists(cur, "customers"):
        cur.execute(
            """
            CREATE TABLE customers (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre    TEXT NOT NULL,
                telefono  TEXT,
                documento TEXT,
                activo    INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """
        )
        print("OK: tabla 'customers' creada")
    else:
        print("SKIP: tabla 'customers' ya existe")

    # --- Columnas nuevas en sales ---
    for col, definition in [
        ("customer_id", "INTEGER REFERENCES customers(id)"),
        ("numero_factura", "TEXT"),
        ("estado_pago", "TEXT DEFAULT 'PAGADO'"),
        ("pagado_en", "TEXT"),
    ]:
        if not col_exists(cur, "sales", col):
            cur.execute(f"ALTER TABLE sales ADD COLUMN {col} {definition}")
            print(f"OK: sales.{col} agregada")
        else:
            print(f"SKIP: sales.{col} ya existe")

    con.commit()
    con.close()
    print("\n✅ Migración completada.")


if __name__ == "__main__":
    main()


def main_v3():
    """Agrega numero_factura a la tabla entries."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró la base de datos en: {DB_PATH.resolve()}"
        )

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    if not col_exists(cur, "entries", "numero_factura"):
        cur.execute("ALTER TABLE entries ADD COLUMN numero_factura TEXT")
        print("OK: entries.numero_factura agregada")
    else:
        print("SKIP: entries.numero_factura ya existe")

    con.commit()
    con.close()
    print("✅ Migración v3 completada.")


if __name__ == "__main__":
    main()  # crea customers + columnas en sales
    main_v3()  # agrega numero_factura en entries
