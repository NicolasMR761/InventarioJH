import sqlite3
import shutil
from datetime import datetime
from pathlib import Path


def _limpiar_backups(carpeta_backup: Path, max_backups: int = 10) -> None:
    """Mantiene solo los últimos `max_backups` backups (por fecha de modificación)."""
    backups = sorted(
        carpeta_backup.glob("inventario_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in backups[max_backups:]:
        try:
            old.unlink()
        except Exception:
            pass


def crear_backup(ruta_db: str, max_backups: int = 10) -> str:
    """
    Crea una copia de seguridad consistente del archivo SQLite.

    Estrategia:
    - Intenta primero con VACUUM INTO (SQLite >= 3.27, 2019).
      Genera un archivo limpio y compacto en una sola operación atómica,
      sin riesgo de capturar la BD en estado inconsistente aunque haya
      escrituras en curso (WAL mode).
    - Si VACUUM INTO no está disponible (SQLite antiguo), cae a shutil.copy2
      como respaldo (comportamiento anterior).

    Retorna la ruta del backup creado.
    """
    ruta_db = Path(ruta_db)

    if not ruta_db.exists():
        raise FileNotFoundError(f"No se encontró la base de datos en:\n{ruta_db}")

    carpeta_backup = ruta_db.parent / "backups"
    carpeta_backup.mkdir(exist_ok=True)

    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_backup = f"inventario_backup_{fecha}.db"
    ruta_destino = carpeta_backup / nombre_backup

    _backup_vacuum_into(ruta_db, ruta_destino)

    _limpiar_backups(carpeta_backup, max_backups=max_backups)

    return str(ruta_destino)


def _backup_vacuum_into(origen: Path, destino: Path) -> None:
    """
    Usa VACUUM INTO para crear el backup.

    VACUUM INTO es atómico y consistente:
    - Lee toda la BD en un snapshot limpio.
    - Escribe en el destino sin tocar el archivo original.
    - Compatible con WAL mode (no necesita bloquear writers).
    - El archivo resultante está compactado (sin páginas libres).

    Si SQLite < 3.27 lanza OperationalError, cae a shutil.copy2.
    """
    try:
        con = sqlite3.connect(str(origen))
        try:
            # VACUUM INTO requiere ruta absoluta en algunas versiones
            con.execute(f"VACUUM INTO '{destino.as_posix()}'")
            con.commit()
        finally:
            con.close()

    except sqlite3.OperationalError as e:
        # SQLite demasiado antiguo para VACUUM INTO → fallback seguro
        if destino.exists():
            destino.unlink()
        shutil.copy2(str(origen), str(destino))
