from app.db.database import engine
from app.db.models import Base  # importa todos los modelos


def main():
    Base.metadata.create_all(bind=engine)
    print("OK: Tablas creadas/verificadas.")


if __name__ == "__main__":
    main()
