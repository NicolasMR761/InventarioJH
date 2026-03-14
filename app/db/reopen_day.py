import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path("app_data/inventario.db")


def main():
    # Uso: python reopen_day.py DD/MM/AAAA
    if len(sys.argv) < 2:
        today = datetime.today().strftime("%d/%m/%Y")
        print(f"Uso: python reopen_day.py DD/MM/AAAA")
        print(f"Ejemplo: python reopen_day.py {today}")
        sys.exit(1)

    entrada = sys.argv[1]

    # Validar y convertir DD/MM/AAAA → YYYY-MM-DD (formato SQLite)
    try:
        dt = datetime.strptime(entrada, "%d/%m/%Y")
        fecha_db = dt.strftime("%Y-%m-%d")
    except ValueError:
        print(
            f"❌ Fecha inválida: '{entrada}'. Usa formato DD/MM/AAAA (ej: 12/03/2026)"
        )
        sys.exit(1)

    if not DB_PATH.exists():
        print(f"❌ Base de datos no encontrada en: {DB_PATH}")
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM cash_closures WHERE fecha = ?", (fecha_db,))
    eliminados = cur.rowcount
    con.commit()
    con.close()

    if eliminados:
        print(f"✅ Día {entrada} reabierto (cierre eliminado).")
    else:
        print(f"⚠️  No se encontró cierre para el día {entrada}.")


if __name__ == "__main__":
    main()
