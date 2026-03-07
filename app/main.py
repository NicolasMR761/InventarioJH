from PySide6.QtWidgets import QApplication
from app.db.database import init_db
from app.ui.login_window import LoginWindow

import sys
from pathlib import Path
from PySide6.QtGui import QIcon


def main():
    init_db()

    app = QApplication(sys.argv)

    base_dir = Path(__file__).resolve().parent.parent
    icon_path = base_dir / "assets" / "icon.ico"

    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # ── Mostrar login ──────────────────────────────────────
    login = LoginWindow()

    if icon_path.exists():
        login.setWindowIcon(QIcon(str(icon_path)))

    def abrir_dashboard():
        from app.ui.main_window import MainWindow

        w = MainWindow()
        if icon_path.exists():
            w.setWindowIcon(QIcon(str(icon_path)))
        w.show()
        login.close()
        app._main_window = w  # evitar garbage collection

    login.login_exitoso.connect(abrir_dashboard)
    login.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
