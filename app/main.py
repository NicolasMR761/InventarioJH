from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.db.database import init_db

import sys
from pathlib import Path
from PySide6.QtGui import QIcon


def main():
    init_db()

    app = QApplication(sys.argv)

    # Subimos un nivel porque main.py está dentro de app/
    base_dir = Path(__file__).resolve().parent.parent
    icon_path = base_dir / "assets" / "icon.ico"

    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    w = MainWindow()

    if icon_path.exists():
        ico = QIcon(str(icon_path))
        app.setWindowIcon(ico)
        w.setWindowIcon(ico)

    w.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
