from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QCursor
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QFrame,
    QGridLayout,
)

from app.db.database import init_db, get_app_data_dir
from app.utils.backup import crear_backup


APP_VERSION = "v1.1.0"  # <-- actualiza cuando hagas tag


class DashboardTile(QFrame):
    """Tarjeta clickeable para el dashboard."""

    clicked = Signal()

    def __init__(self, title: str, desc: str):
        super().__init__()
        self.setObjectName("tile")
        self.setCursor(QCursor(Qt.PointingHandCursor))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        lbl_t = QLabel(title)
        lbl_t.setObjectName("tileTitle")
        lbl_t.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(lbl_t)

        lbl_d = QLabel(desc)
        lbl_d.setObjectName("tileDesc")
        lbl_d.setWordWrap(True)
        lbl_d.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(lbl_d)

        lay.addStretch(1)

        hint = QLabel("Abrir →")
        hint.setObjectName("tileHint")
        hint.setAlignment(Qt.AlignRight)
        hint.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(hint)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventario JH - Dashboard")
        self.resize(980, 580)

        init_db()

        # ----- UI ROOT -----
        root = QWidget()
        root.setObjectName("root")
        main = QVBoxLayout(root)
        main.setContentsMargins(18, 18, 18, 18)
        main.setSpacing(12)

        # ----- HEADER -----
        header = QHBoxLayout()
        header.setSpacing(14)

        # Logo card — clickeable directamente, sin botón
        logo_card = QFrame()
        logo_card.setObjectName("card")
        logo_lay = QVBoxLayout(logo_card)
        logo_lay.setContentsMargins(12, 12, 12, 12)
        logo_lay.setSpacing(0)

        self.lbl_logo = QLabel("＋  LOGO")
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        self.lbl_logo.setFixedSize(150, 110)
        self.lbl_logo.setObjectName("logoBox")
        self.lbl_logo.setCursor(QCursor(Qt.PointingHandCursor))
        self.lbl_logo.setToolTip("Clic para cargar logo")
        # Hacer el label clickeable
        self.lbl_logo.mousePressEvent = lambda _: self.cargar_logo()
        logo_lay.addWidget(self.lbl_logo, alignment=Qt.AlignLeft)

        header.addWidget(logo_card)

        # Title / subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        self.lbl_title = QLabel("Sistema de Inventario")
        self.lbl_title.setObjectName("title")
        title_box.addWidget(self.lbl_title)

        self.lbl_sub = QLabel("Control de productos, compras, ventas y caja")
        self.lbl_sub.setObjectName("subtitle")
        title_box.addWidget(self.lbl_sub)

        header.addLayout(title_box, 1)

        # Backup quick button
        self.btn_backup = QPushButton("Crear Backup")
        self.btn_backup.setObjectName("btnPrimary")
        self.btn_backup.clicked.connect(self.hacer_backup)
        header.addWidget(self.btn_backup)

        main.addLayout(header)

        # ----- GRID / DASHBOARD -----
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        grid.addWidget(
            self._make_tile("📦 Productos", "Gestionar catálogo", self.abrir_productos),
            0,
            0,
        )
        grid.addWidget(
            self._make_tile(
                "🏭 Proveedores", "Gestionar proveedores", self.abrir_proveedores
            ),
            0,
            1,
        )
        grid.addWidget(
            self._make_tile("🧾 Entradas", "Compras y stock", self.abrir_entradas), 1, 0
        )
        grid.addWidget(
            self._make_tile("🛒 Ventas", "Ventas y salida de stock", self.abrir_ventas),
            1,
            1,
        )
        grid.addWidget(
            self._make_tile(
                "💰 Caja", "Movimientos, cierres y reportes", self.abrir_caja
            ),
            2,
            0,
        )
        grid.addWidget(
            self._make_tile("📒 Kardex", "Movimientos por producto", self.abrir_kardex),
            2,
            1,
        )

        main.addLayout(grid, 1)

        # ----- FOOTER -----
        footer = QHBoxLayout()
        self.lbl_footer = QLabel(
            f"Versión: {APP_VERSION}   •   Base de datos local   •   Backups automáticos al cerrar"
        )
        self.lbl_footer.setObjectName("footer")
        footer.addWidget(self.lbl_footer, 1)
        main.addLayout(footer)

        self.setCentralWidget(root)
        self._apply_styles()
        self._load_logo_if_exists()

    # ---------------- UI helpers ----------------

    def _make_tile(self, title: str, desc: str, callback):
        card = DashboardTile(title, desc)
        card.clicked.connect(callback)
        return card

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QWidget {
                color: #e2e8f0;
                font-size: 14px;
            }
            QLabel { color: #e2e8f0; }

            #root { background: #0f172a; }

            #card, #tile {
                background: #111c33;
                border: 1px solid #223152;
                border-radius: 12px;
            }
            #tile:hover {
                border: 1px solid #3b82f6;
                background: #101e3a;
            }

            #title    { font-size: 22px; font-weight: 800; }
            #subtitle { color: #b6c2d2; font-size: 13px; }
            #footer   { color: #94a3b8; font-size: 12px; }

            #logoBox {
                border: 1px dashed #334155;
                border-radius: 12px;
                background: #0b1224;
                color: #94a3b8;
                font-weight: 700;
                font-size: 13px;
                letter-spacing: 1px;
            }
            #logoBox:hover {
                border: 1px dashed #3b82f6;
                background: #0d1a33;
                color: #93c5fd;
            }

            #btnPrimary {
                background: #2563eb;
                border: none;
                padding: 10px 14px;
                border-radius: 10px;
                font-weight: 700;
                color: white;
            }
            #btnPrimary:hover { background: #1d4ed8; }

            #tileTitle { font-size: 17px; font-weight: 800; }
            #tileDesc  { color: #b6c2d2; font-size: 13px; }
            #tileHint  { color: #93c5fd; font-weight: 700; font-size: 12px; }
        """
        )

    # ---------------- Logo handling ----------------

    def _logo_path(self) -> Path:
        return get_app_data_dir() / "logo.png"

    def _load_logo_if_exists(self):
        path = self._logo_path()
        if path.exists():
            pix = QPixmap(str(path))
            if not pix.isNull():
                scaled = pix.scaled(
                    self.lbl_logo.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.lbl_logo.setPixmap(scaled)
                self.lbl_logo.setText("")
            else:
                self.lbl_logo.setPixmap(QPixmap())
                self.lbl_logo.setText("＋  LOGO")

    def cargar_logo(self):
        try:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Seleccionar logo",
                "",
                "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp)",
            )
            if not path:
                return
            src = Path(path)
            if not src.exists():
                return
            dest = self._logo_path()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            self._load_logo_if_exists()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el logo:\n{e}")

    # ---------------- Navegación módulos ----------------

    def abrir_productos(self):
        from app.ui.products_window import ProductsWindow

        self.win_productos = ProductsWindow()
        self.win_productos.show()

    def abrir_proveedores(self):
        from app.ui.suppliers_window import SuppliersWindow

        self.win_suppliers = SuppliersWindow()
        self.win_suppliers.show()

    def abrir_entradas(self):
        from app.ui.entries_window import EntriesWindow

        self.win_entries = EntriesWindow()
        self.win_entries.show()

    def abrir_ventas(self):
        from app.ui.sales_window import SalesWindow

        self.win_sales = SalesWindow()
        self.win_sales.show()

    def abrir_caja(self):
        from app.ui.cash_window import CashWindow

        self.win_caja = CashWindow()
        self.win_caja.show()

    def abrir_kardex(self):
        from app.ui.kardex_window import KardexWindow

        self.win_kardex = KardexWindow()
        self.win_kardex.show()

    def _prox(self):
        QMessageBox.information(
            self, "Próximamente", "Este módulo lo agregamos en una siguiente versión."
        )

    # ---------------- Backup ----------------

    def hacer_backup(self):
        try:
            ruta_db = get_app_data_dir() / "inventario.db"
            ruta_backup = crear_backup(str(ruta_db))
            QMessageBox.information(
                self, "Backup creado", f"Backup guardado en:\n{ruta_backup}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudo crear el backup:\n{str(e)}"
            )

    def closeEvent(self, event):
        try:
            ruta_db = get_app_data_dir() / "inventario.db"
            crear_backup(str(ruta_db))
        except Exception:
            pass
        event.accept()
