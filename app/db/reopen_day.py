import sqlite3
from pathlib import Path

DB_PATH = Path("app_data/inventario.db")


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Cambia la fecha al día que cerraste (según tu mensaje)
    fecha = "2026-02-21"

    cur.execute("DELETE FROM cash_closures WHERE fecha = ?", (fecha,))
    con.commit()
    con.close()
    print(f"✅ Día {fecha} reabierto (cierre eliminado).")


if __name__ == "__main__":
    main()
