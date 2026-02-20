from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base


from pathlib import Path


def get_app_data_dir() -> Path:
    # database.py está en app/db/database.py => subir 2 niveles al root del proyecto
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "app_data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_engine():
    db_path = get_app_data_dir() / "inventario.db"
    return create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db():
    Base.metadata.create_all(engine)
