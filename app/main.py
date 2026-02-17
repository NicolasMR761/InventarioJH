from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow

from app.db.database import init_db


def main():
    init_db()
    app = QApplication([])
    w = MainWindow()
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
