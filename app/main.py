from PySide6.QtWidgets import QApplication
from app.db.database import init_db
from app.ui.login_window import LoginWindow

import sys
from pathlib import Path
from PySide6.QtGui import QIcon

# ── Ícono global accesible desde cualquier ventana ────────────
_ICON: QIcon | None = None


def get_icon() -> QIcon | None:
    return _ICON


def _set_icon(window) -> None:
    if _ICON:
        window.setWindowIcon(_ICON)


def main():
    global _ICON
    init_db()

    app = QApplication(sys.argv)

    base_dir = Path(__file__).resolve().parent.parent
    icon_path = base_dir / "assets" / "icon.ico"

    if icon_path.exists():
        _ICON = QIcon(str(icon_path))
        app.setWindowIcon(_ICON)

    login = LoginWindow()
    _set_icon(login)

    def abrir_dashboard():
        from app.ui.main_window import MainWindow

        w = MainWindow()
        _set_icon(w)
        w.show()
        login.close()
        app._main_window = w

    login.login_exitoso.connect(abrir_dashboard)
    login.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
