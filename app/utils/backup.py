import os
import shutil
from datetime import datetime
from pathlib import Path


def crear_backup(ruta_db: str) -> str:
    """
    Crea una copia de seguridad del archivo SQLite.
    Retorna la ruta del backup creado.
    """

    ruta_db = Path(ruta_db)

    if not ruta_db.exists():
        raise FileNotFoundError(f"No se encontró la base de datos en:\n{ruta_db}")

    # Carpeta backups dentro de app_data
    carpeta_backup = ruta_db.parent / "backups"
    carpeta_backup.mkdir(exist_ok=True)

    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_backup = f"inventario_backup_{fecha}.db"

    ruta_destino = carpeta_backup / nombre_backup

    shutil.copy2(ruta_db, ruta_destino)

    return str(ruta_destino)
