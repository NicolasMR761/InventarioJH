from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.db.models import Base
from sqlalchemy.engine import Engine

from pathlib import Path


def get_app_data_dir() -> Path:
    import sys, os

    if getattr(sys, "frozen", False):
        # Ejecutable compilado → usar %LOCALAPPDATA%\InventarioJH
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "InventarioJH"
    else:
        # Desarrollo → usar app_data/ junto al proyecto
        project_root = Path(__file__).resolve().parents[2]
        base = project_root / "app_data"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_engine():
    db_path = get_app_data_dir() / "inventario.db"
    return create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()


def init_db():
    Base.metadata.create_all(engine)
