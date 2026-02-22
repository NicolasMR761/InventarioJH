import shutil
from datetime import datetime
from pathlib import Path


def _limpiar_backups(carpeta_backup: Path, max_backups: int = 10) -> None:
    """
    Mantiene solo los últimos `max_backups` backups (por fecha de modificación).
    """
    backups = sorted(
        carpeta_backup.glob("inventario_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # Si hay más de max_backups, borra los más antiguos
    for old in backups[max_backups:]:
        try:
            old.unlink()
        except Exception:
            pass


def crear_backup(ruta_db: str, max_backups: int = 10) -> str:
    """
    Crea una copia de seguridad del archivo SQLite.
    Retorna la ruta del backup creado.

    - Guarda en app_data/backups/
    - Mantiene solo los últimos `max_backups` backups.
    """
    ruta_db = Path(ruta_db)

    if not ruta_db.exists():
        raise FileNotFoundError(f"No se encontró la base de datos en:\n{ruta_db}")

    # Carpeta backups dentro de app_data
    carpeta_backup = ruta_db.parent / "backups"
    carpeta_backup.mkdir(exist_ok=True)

    # Nombre con fecha y hora
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_backup = f"inventario_backup_{fecha}.db"
    ruta_destino = carpeta_backup / nombre_backup

    shutil.copy2(ruta_db, ruta_destino)

    # Limpieza automática: conservar solo los últimos N
    _limpiar_backups(carpeta_backup, max_backups=max_backups)

    return str(ruta_destino)
