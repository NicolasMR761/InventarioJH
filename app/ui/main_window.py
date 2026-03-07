from __future__ import annotations

from datetime import datetime, date
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer
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
    QScrollArea,
    QSizePolicy,
)

from app.db.database import init_db, get_app_data_dir
from PySide6.QtGui import QPainter, QPen, QLinearGradient, QColor as QColorG
from PySide6.QtCore import QRect, QPoint
from app.utils.backup import crear_backup

APP_VERSION = "v1.2.0"


# ─────────────────────────────────────────────
#  Helpers de formato
# ─────────────────────────────────────────────
def _fmt_cop(value) -> str:
    try:
        n = int(round(float(value or 0)))
        return "$" + f"{n:,}".replace(",", ".")
    except Exception:
        return "$0"


# ─────────────────────────────────────────────
#  Tile de módulo (clickeable)
# ─────────────────────────────────────────────
class DashboardTile(QFrame):
    clicked = Signal()

    def __init__(self, title: str, desc: str):
        super().__init__()
        self.setObjectName("tile")
        self.setCursor(QCursor(Qt.PointingHandCursor))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

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


# ─────────────────────────────────────────────
#  Tarjeta de métrica KPI
# ─────────────────────────────────────────────
class MetricCard(QFrame):
    def __init__(self, icon: str, label: str, accent: str = "#3b82f6"):
        super().__init__()
        self.setObjectName("metricCard")
        self._accent = accent

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)

        # Fila icono + label
        top = QHBoxLayout()
        top.setSpacing(6)
        lbl_icon = QLabel(icon)
        lbl_icon.setObjectName("metricIcon")
        lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top.addWidget(lbl_icon)

        self.lbl_label = QLabel(label)
        self.lbl_label.setObjectName("metricLabel")
        self.lbl_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top.addWidget(self.lbl_label, 1)
        lay.addLayout(top)

        # Valor principal
        self.lbl_value = QLabel("—")
        self.lbl_value.setObjectName("metricValue")
        self.lbl_value.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_value.setStyleSheet(f"color: {accent};")
        lay.addWidget(self.lbl_value)

        # Sub-valor opcional
        self.lbl_sub = QLabel("")
        self.lbl_sub.setObjectName("metricSub")
        self.lbl_sub.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(self.lbl_sub)

    def set_value(self, value: str, sub: str = ""):
        self.lbl_value.setText(value)
        self.lbl_sub.setText(sub)


# ─────────────────────────────────────────────
#  Gráfica de barras — ventas últimos 7 días
# ─────────────────────────────────────────────
class SalesChart(QWidget):
    """Gráfica de barras nativa (sin dependencias externas)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._data: list[tuple[str, float]] = []  # [(label, valor), ...]
        self._accent = "#3b82f6"

    def set_data(self, data: list[tuple[str, float]], accent: str = "#3b82f6"):
        self._data = data
        self._accent = accent
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        W, H = self.width(), self.height()
        PAD_L, PAD_R, PAD_T, PAD_B = 14, 14, 14, 36

        n = len(self._data)
        max_val = max(v for _, v in self._data) or 1
        available_w = W - PAD_L - PAD_R
        bar_w = max(8, int(available_w / n * 0.55))
        gap = (available_w - bar_w * n) // (n + 1)
        chart_h = H - PAD_T - PAD_B

        # Línea guía superior
        pen = QPen(QColorG("#1e293b"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(PAD_L, PAD_T, W - PAD_R, PAD_T)

        for i, (label, valor) in enumerate(self._data):
            x = PAD_L + gap + i * (bar_w + gap)
            bar_h = max(4, int(chart_h * valor / max_val))
            y = PAD_T + chart_h - bar_h

            # Gradiente de la barra
            grad = QLinearGradient(x, y, x, y + bar_h)
            is_today = i == n - 1
            if is_today:
                grad.setColorAt(0, QColorG("#60a5fa"))
                grad.setColorAt(1, QColorG("#2563eb"))
            else:
                grad.setColorAt(0, QColorG("#1e3a5f"))
                grad.setColorAt(1, QColorG("#0f1e36"))

            painter.setPen(Qt.NoPen)
            painter.setBrush(grad)
            rect = QRect(x, y, bar_w, bar_h)
            painter.drawRoundedRect(rect, 3, 3)

            # Valor encima de la barra (solo si tiene valor)
            if valor > 0:
                painter.setPen(QPen(QColorG("#60a5fa" if is_today else "#334155")))
                val_txt = _fmt_cop(valor) if valor >= 1000 else str(int(valor))
                font = painter.font()
                font.setPointSize(7)
                font.setBold(is_today)
                painter.setFont(font)
                painter.drawText(
                    QRect(x - 10, y - 16, bar_w + 20, 14),
                    Qt.AlignHCenter | Qt.AlignBottom,
                    val_txt,
                )

            # Label día debajo
            painter.setPen(QPen(QColorG("#4ade80" if is_today else "#334155")))
            font2 = painter.font()
            font2.setPointSize(8)
            font2.setBold(is_today)
            painter.setFont(font2)
            painter.drawText(
                QRect(x - 6, H - PAD_B + 4, bar_w + 12, 20),
                Qt.AlignHCenter,
                label,
            )

        painter.end()


# ─────────────────────────────────────────────
#  Ventana principal
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventario JH - Dashboard")
        self.resize(1060, 660)
        self.setMinimumSize(860, 540)

        init_db()
        self._build_ui()
        self.setStyleSheet(self._styles())
        self._load_logo_if_exists()

        # Refresco automático cada 60 s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_metrics)
        self._timer.start(60_000)
        self._refresh_metrics()

    # ── CONSTRUCCIÓN UI ──────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("mainScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("innerRoot")
        main = QVBoxLayout(inner)
        main.setContentsMargins(22, 20, 22, 20)
        main.setSpacing(16)
        scroll.setWidget(inner)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # ── HEADER ─────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(16)

        logo_card = QFrame()
        logo_card.setObjectName("card")
        logo_lay = QVBoxLayout(logo_card)
        logo_lay.setContentsMargins(10, 10, 10, 10)
        self.lbl_logo = QLabel("＋  LOGO")
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        self.lbl_logo.setFixedSize(130, 90)
        self.lbl_logo.setObjectName("logoBox")
        self.lbl_logo.setCursor(QCursor(Qt.PointingHandCursor))
        self.lbl_logo.setToolTip("Clic para cargar logo")
        self.lbl_logo.mousePressEvent = lambda _: self.cargar_logo()
        logo_lay.addWidget(self.lbl_logo, alignment=Qt.AlignLeft)
        header.addWidget(logo_card)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        self.lbl_title = QLabel("Sistema de Inventario")
        self.lbl_title.setObjectName("title")
        title_box.addWidget(self.lbl_title)
        self.lbl_sub = QLabel("Control de productos · compras · ventas · caja")
        self.lbl_sub.setObjectName("subtitle")
        title_box.addWidget(self.lbl_sub)
        # Fecha/hora
        self.lbl_datetime = QLabel()
        self.lbl_datetime.setObjectName("datetimeLabel")
        title_box.addWidget(self.lbl_datetime)
        self._update_datetime()
        dt_timer = QTimer(self)
        dt_timer.timeout.connect(self._update_datetime)
        dt_timer.start(30_000)
        header.addLayout(title_box, 1)

        btn_refresh = QPushButton("↺  Actualizar")
        btn_refresh.setObjectName("btnSecondary")
        btn_refresh.clicked.connect(self._refresh_metrics)
        btn_backup = QPushButton("💾  Backup")
        btn_backup.setObjectName("btnPrimary")
        btn_backup.clicked.connect(self.hacer_backup)
        hdr_btns = QVBoxLayout()
        hdr_btns.setSpacing(6)
        hdr_btns.addWidget(btn_refresh)
        hdr_btns.addWidget(btn_backup)
        header.addLayout(hdr_btns)
        main.addLayout(header)

        # ── SEPARADOR ──────────────────────────────────
        sep0 = QFrame()
        sep0.setFrameShape(QFrame.HLine)
        sep0.setObjectName("sep")
        main.addWidget(sep0)

        # ── KPI MÉTRICAS ───────────────────────────────
        lbl_kpi = QLabel("📊  Resumen de hoy")
        lbl_kpi.setObjectName("sectionTitle")
        main.addWidget(lbl_kpi)

        kpi_grid = QHBoxLayout()
        kpi_grid.setSpacing(10)

        self.card_ventas_hoy = MetricCard("🛒", "Ventas hoy", "#4ade80")
        self.card_ingresos_hoy = MetricCard("💵", "Ingresos hoy", "#34d399")
        self.card_saldo_caja = MetricCard("💰", "Saldo en caja", "#60a5fa")
        self.card_fiados = MetricCard("⏳", "Fiados pendientes", "#fbbf24")
        self.card_stock_bajo = MetricCard("⚠️", "Stock bajo", "#f87171")
        self.card_productos = MetricCard("📦", "Productos activos", "#a78bfa")

        for card in (
            self.card_ventas_hoy,
            self.card_ingresos_hoy,
            self.card_saldo_caja,
            self.card_fiados,
            self.card_stock_bajo,
            self.card_productos,
        ):
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            kpi_grid.addWidget(card)

        main.addLayout(kpi_grid)

        # ── SEPARADOR ──────────────────────────────────
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setObjectName("sep")
        main.addWidget(sep1)

        # ── GRÁFICA 7 DÍAS ─────────────────────────────
        lbl_chart = QLabel("📈  Ventas — últimos 7 días")
        lbl_chart.setObjectName("sectionTitle")
        main.addWidget(lbl_chart)

        chart_card = QFrame()
        chart_card.setObjectName("chartCard")
        chart_lay = QVBoxLayout(chart_card)
        chart_lay.setContentsMargins(12, 10, 12, 6)
        self.sales_chart = SalesChart()
        chart_lay.addWidget(self.sales_chart)
        main.addWidget(chart_card)

        # ── SEPARADOR ──────────────────────────────────
        sep1b = QFrame()
        sep1b.setFrameShape(QFrame.HLine)
        sep1b.setObjectName("sep")
        main.addWidget(sep1b)

        # ── GRID MÓDULOS ───────────────────────────────
        lbl_mod = QLabel("🗂  Módulos")
        lbl_mod.setObjectName("sectionTitle")
        main.addWidget(lbl_mod)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        tiles = [
            ("📦 Productos", "Catálogo · stock · precios", self.abrir_productos, 0, 0),
            ("🏭 Proveedores", "Gestionar proveedores", self.abrir_proveedores, 0, 1),
            (
                "🧾 Entradas",
                "Compras · actualiza stock y costos",
                self.abrir_entradas,
                0,
                2,
            ),
            ("🛒 Ventas", "Registrar ventas · fiados", self.abrir_ventas, 1, 0),
            ("💰 Caja", "Movimientos · cierres · reportes", self.abrir_caja, 1, 1),
            ("📒 Kardex", "Trazabilidad por producto", self.abrir_kardex, 1, 2),
        ]
        for title, desc, slot, r, c in tiles:
            t = self._make_tile(title, desc, slot)
            grid.addWidget(t, r, c)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        main.addLayout(grid, 1)

        # ── FOOTER ─────────────────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("sep")
        main.addWidget(sep2)
        footer = QHBoxLayout()
        self.lbl_footer = QLabel(
            f"Versión {APP_VERSION}   ·   Base de datos local   ·   Backups automáticos al cerrar"
        )
        self.lbl_footer.setObjectName("footer")
        footer.addWidget(self.lbl_footer, 1)
        self.lbl_last_refresh = QLabel("")
        self.lbl_last_refresh.setObjectName("footer")
        footer.addWidget(self.lbl_last_refresh)
        main.addLayout(footer)

    # ── MÉTRICAS ─────────────────────────────────────────
    def _refresh_metrics(self):
        try:
            self._load_ventas_hoy()
        except Exception:
            self.card_ventas_hoy.set_value("—", "Error")
            self.card_ingresos_hoy.set_value("—", "Error")

        try:
            self._load_caja()
        except Exception:
            self.card_saldo_caja.set_value("—", "Error")

        try:
            self._load_fiados()
        except Exception:
            self.card_fiados.set_value("—", "Error")

        try:
            self._load_stock()
        except Exception:
            self.card_stock_bajo.set_value("—", "Error")
            self.card_productos.set_value("—", "Error")

        try:
            self._load_chart()
        except Exception:
            pass

        now = datetime.now().strftime("%H:%M")
        self.lbl_last_refresh.setText(f"Actualizado: {now}")

    def _load_ventas_hoy(self):
        from app.db.database import SessionLocal
        from app.db.models import Sale
        from datetime import datetime, time

        hoy = date.today()
        start = datetime.combine(hoy, time.min)
        end = datetime.combine(hoy, time.max)

        with SessionLocal() as db:
            ventas_hoy = (
                db.query(Sale)
                .filter(
                    Sale.fecha >= start,
                    Sale.fecha <= end,
                    Sale.anulada.is_(False),
                )
                .all()
            )

        total_ventas = len(ventas_hoy)
        total_ingresos = sum(
            float(v.total or 0) for v in ventas_hoy if v.estado_pago == "PAGADO"
        )
        pendiente_hoy = sum(
            float(v.total or 0) for v in ventas_hoy if v.estado_pago == "PENDIENTE"
        )

        self.card_ventas_hoy.set_value(
            str(total_ventas),
            (
                f"{sum(1 for v in ventas_hoy if v.estado_pago=='PENDIENTE')} fiado(s)"
                if any(v.estado_pago == "PENDIENTE" for v in ventas_hoy)
                else "Al día ✓"
            ),
        )
        self.card_ingresos_hoy.set_value(
            _fmt_cop(total_ingresos),
            (
                f"+ {_fmt_cop(pendiente_hoy)} por cobrar"
                if pendiente_hoy > 0
                else "Todo cobrado ✓"
            ),
        )

    def _load_caja(self):
        from app.db.cash_repo import obtener_saldo, resumen_del_dia

        saldo = obtener_saldo()
        res = resumen_del_dia(date.today())
        self.card_saldo_caja.set_value(
            _fmt_cop(saldo),
            f"↑ {_fmt_cop(res['ingresos'])}  ↓ {_fmt_cop(res['egresos'])}",
        )

    def _load_fiados(self):
        from app.db.sales_repo import listar_ventas_pendientes

        pendientes = listar_ventas_pendientes()
        total_deuda = sum(float(v.total or 0) for v in pendientes)
        self.card_fiados.set_value(
            str(len(pendientes)),
            _fmt_cop(total_deuda) if pendientes else "Sin fiados ✓",
        )

    def _load_stock(self):
        from app.db.products_repo import listar_productos, es_stock_bajo

        todos = listar_productos("", incluir_inactivos=False)
        bajo = [p for p in todos if es_stock_bajo(p)]
        inactivos_count = len(listar_productos("", incluir_inactivos=True)) - len(todos)

        self.card_stock_bajo.set_value(
            str(len(bajo)),
            (
                bajo[0].nombre[:22] + "…"
                if len(bajo) == 1
                else (f"Ej: {bajo[0].nombre[:18]}…" if bajo else "Todo en orden ✓")
            ),
        )
        self.card_productos.set_value(
            str(len(todos)),
            f"{inactivos_count} inactivo(s)" if inactivos_count else "Todos activos ✓",
        )

    def _load_chart(self):
        from app.db.database import SessionLocal
        from app.db.models import Sale
        from datetime import timedelta, time

        hoy = date.today()
        data = []
        dias_es = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

        for i in range(6, -1, -1):
            dia = hoy - timedelta(days=i)
            start = datetime.combine(dia, time.min)
            end = datetime.combine(dia, time.max)
            with SessionLocal() as db:
                ventas = (
                    db.query(Sale)
                    .filter(
                        Sale.fecha >= start,
                        Sale.fecha <= end,
                        Sale.anulada.is_(False),
                    )
                    .all()
                )
            total = sum(
                float(v.total or 0) for v in ventas if v.estado_pago == "PAGADO"
            )
            label = "Hoy" if i == 0 else dias_es[dia.weekday()]
            data.append((label, total))

        self.sales_chart.set_data(data)

    # ── HELPERS ──────────────────────────────────────────
    def _update_datetime(self):
        now = datetime.now()
        dias = [
            "Lunes",
            "Martes",
            "Miércoles",
            "Jueves",
            "Viernes",
            "Sábado",
            "Domingo",
        ]
        meses = [
            "ene",
            "feb",
            "mar",
            "abr",
            "may",
            "jun",
            "jul",
            "ago",
            "sep",
            "oct",
            "nov",
            "dic",
        ]
        txt = f"{dias[now.weekday()]} {now.day} {meses[now.month-1]} {now.year}  ·  {now.strftime('%H:%M')}"
        self.lbl_datetime.setText(txt)

    def _make_tile(self, title: str, desc: str, slot) -> DashboardTile:
        t = DashboardTile(title, desc)
        t.clicked.connect(slot)
        return t

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

    # ── NAVEGACIÓN ───────────────────────────────────────
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

    # ── BACKUP ───────────────────────────────────────────
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

    def keyPressEvent(self, event):
        from PySide6.QtCore import Qt

        key = event.key()
        mod = event.modifiers()
        if key == Qt.Key_F5:
            self._refresh_metrics()
        elif key == Qt.Key_B and mod == Qt.ControlModifier:
            self.hacer_backup()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        try:
            ruta_db = get_app_data_dir() / "inventario.db"
            crear_backup(str(ruta_db))
        except Exception:
            pass
        event.accept()

    # ── ESTILOS ──────────────────────────────────────────
    def _styles(self) -> str:
        return """
        QMainWindow, QWidget#root, QWidget#innerRoot {
            background: #080f1e;
        }
        QScrollArea#mainScroll {
            background: #080f1e;
            border: none;
        }
        QScrollArea#mainScroll > QWidget > QWidget {
            background: #080f1e;
        }
        QScrollBar:vertical {
            background: #0b1120; width: 6px; border-radius: 3px;
        }
        QScrollBar::handle:vertical { background: #1e3a5f; border-radius: 3px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

        * {
            font-family: "Segoe UI", Arial, sans-serif;
            color: #e2e8f0;
        }

        /* ── Header ── */
        #title {
            font-size: 22px; font-weight: 800;
            color: #f1f5f9; letter-spacing: -0.5px;
        }
        #subtitle { font-size: 12px; color: #475569; }
        #datetimeLabel { font-size: 11px; color: #334155; margin-top: 2px; }

        /* ── Logo ── */
        #card {
            background: #0f1a2e;
            border: 1px solid #1e293b;
            border-radius: 10px;
        }
        #logoBox {
            background: #111c33;
            border: 2px dashed #1e3a5f;
            border-radius: 8px;
            color: #334155;
            font-size: 12px;
        }

        /* ── Sección ── */
        #sectionTitle {
            font-size: 13px; font-weight: 700;
            color: #64748b; letter-spacing: 0.5px;
        }
        #sep { border: none; border-top: 1px solid #131f35; }

        /* ── Metric Cards ── */
        #metricCard {
            background: #0d1829;
            border: 1px solid #1a2a45;
            border-radius: 12px;
            min-height: 90px;
        }
        #metricCard:hover { border-color: #2d4a7a; background: #0f1e36; }

        #metricIcon { font-size: 16px; }
        #metricLabel {
            font-size: 10px; font-weight: 700;
            color: #475569; letter-spacing: 1px;
            text-transform: uppercase;
        }
        #metricValue {
            font-size: 22px; font-weight: 900;
            letter-spacing: -0.5px;
        }
        #metricSub { font-size: 10px; color: #334155; }

        /* ── Module Tiles ── */
        #tile {
            background: #0d1829;
            border: 1px solid #1a2a45;
            border-radius: 12px;
            min-height: 95px;
        }
        #tile:hover { background: #111f38; border-color: #2563eb; }

        #tileTitle {
            font-size: 14px; font-weight: 700; color: #e2e8f0;
        }
        #tileDesc { font-size: 11px; color: #475569; }
        #tileHint { font-size: 11px; color: #1e3a5f; font-weight: 600; }
        #tile:hover #tileHint { color: #3b82f6; }

        /* ── Botones ── */
        #btnPrimary {
            background: #2563eb; border: none; border-radius: 8px;
            padding: 7px 18px; font-weight: 700; color: white;
            font-size: 12px; min-width: 100px;
        }
        #btnPrimary:hover { background: #1d4ed8; }

        #btnSecondary {
            background: #0d1829; border: 1px solid #1e3a5f;
            border-radius: 8px; padding: 7px 14px;
            font-weight: 600; color: #64748b;
            font-size: 12px; min-width: 100px;
        }
        #btnSecondary:hover { border-color: #3b82f6; color: #e2e8f0; }

        /* ── Chart ── */
        #chartCard {
            background: #0d1829;
            border: 1px solid #1a2a45;
            border-radius: 12px;
            min-height: 180px;
        }

        /* ── Footer ── */
        #footer { font-size: 10px; color: #1e293b; }
        """
