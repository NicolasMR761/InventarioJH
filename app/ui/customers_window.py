"""
app/ui/customers_window.py
──────────────────────────────────────────────────────────────────────────────
Módulo de Clientes:
  · Lista todos los clientes con búsqueda
  · Detalle con historial completo de compras filtrable por fecha
  · Exportar historial a PDF (factura de historial)
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
    QHeaderView,
    QFrame,
    QDialog,
    QScrollArea,
    QDateEdit,
    QDialogButtonBox,
    QAbstractItemView,
)
from PySide6.QtCore import QDate
from PySide6.QtGui import QColor, QBrush

from app.db.customers_repo import (
    listar_clientes,
    crear_cliente,
    actualizar_cliente,
    cambiar_estado_cliente,
)
from app.utils.formatters import fmt_fecha


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _fmt_cop(value) -> str:
    try:
        n = int(round(float(value or 0)))
        s = ""
        neg = n < 0
        n = abs(n)
        digits = str(n)
        for i, ch in enumerate(reversed(digits)):
            if i > 0 and i % 3 == 0:
                s = "." + s
            s = ch + s
        return ("$-" if neg else "$") + s
    except Exception:
        return "$0"


def _qty(value) -> str:
    try:
        v = float(value or 0)
        s = f"{v:.3f}".rstrip("0").rstrip(".")
        return s.replace(".", ",")
    except Exception:
        return "0"


# ─────────────────────────────────────────────────────────────────────────────
#  Diálogo: editar/crear cliente
# ─────────────────────────────────────────────────────────────────────────────
class ClienteFormDialog(QDialog):
    def __init__(self, parent=None, customer=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle("Editar Cliente" if customer else "Nuevo Cliente")
        self.setFixedWidth(380)
        self.setStyleSheet(
            """
            QDialog { background: #0b1120; color: #e2e8f0; font-family: 'Segoe UI', Arial; }
            QLabel { color: #94a3b8; font-size: 12px; }
            QLineEdit {
                background: #111c33; border: 1px solid #1e3a5f;
                border-radius: 8px; padding: 7px 10px; color: #e2e8f0;
            }
            QLineEdit:focus { border-color: #3b82f6; }
            QPushButton {
                background: #2563eb; border: none; border-radius: 8px;
                padding: 8px 20px; font-weight: 700; color: white;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton[flat="true"] {
                background: #111c33; border: 1px solid #1e3a5f; color: #94a3b8;
            }
        """
        )

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        lay.addWidget(QLabel("Nombre *"))
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre completo…")
        lay.addWidget(self.txt_nombre)

        lay.addWidget(QLabel("Teléfono"))
        self.txt_telefono = QLineEdit()
        self.txt_telefono.setPlaceholderText("Teléfono (opcional)…")
        lay.addWidget(self.txt_telefono)

        lay.addWidget(QLabel("Documento / NIT"))
        self.txt_documento = QLineEdit()
        self.txt_documento.setPlaceholderText("Cédula o NIT (opcional)…")
        lay.addWidget(self.txt_documento)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("flat", True)
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("💾  Guardar")
        btn_save.clicked.connect(self._guardar)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        lay.addLayout(btns)

        if customer:
            self.txt_nombre.setText(customer.nombre or "")
            self.txt_telefono.setText(customer.telefono or "")
            self.txt_documento.setText(customer.documento or "")

    def _guardar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Campo obligatorio", "El nombre es obligatorio.")
            return
        try:
            if self.customer:
                actualizar_cliente(
                    self.customer.id,
                    nombre,
                    self.txt_telefono.text().strip() or None,
                    self.txt_documento.text().strip() or None,
                )
            else:
                crear_cliente(
                    nombre,
                    self.txt_telefono.text().strip() or None,
                    self.txt_documento.text().strip() or None,
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# ─────────────────────────────────────────────────────────────────────────────
#  Diálogo: historial del cliente
# ─────────────────────────────────────────────────────────────────────────────
class HistorialClienteDialog(QDialog):
    def __init__(self, parent, customer):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle(f"Historial — {customer.nombre}")
        self.resize(820, 620)
        self.setStyleSheet(_STYLES_DIALOG)

        try:
            from app.main import get_icon

            if get_icon():
                self.setWindowIcon(get_icon())
        except Exception:
            pass

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 12)
        lay.setSpacing(10)

        # ── Header ───────────────────────────────────────────
        lbl_title = QLabel(f"👤  {customer.nombre}")
        lbl_title.setObjectName("pageTitle")
        lay.addWidget(lbl_title)

        info_row = QHBoxLayout()
        tel = customer.telefono or "—"
        doc = customer.documento or "—"
        lbl_info = QLabel(f"Tel: {tel}   ·   Doc: {doc}")
        lbl_info.setObjectName("pageSub")
        info_row.addWidget(lbl_info, 1)
        lay.addLayout(info_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        # ── Filtro por fecha ─────────────────────────────────
        filtro_row = QHBoxLayout()
        filtro_row.setSpacing(8)
        lbl_desde = QLabel("Desde:")
        lbl_desde.setObjectName("fieldLabel")
        filtro_row.addWidget(lbl_desde)
        self.dt_desde = QDateEdit()
        self.dt_desde.setCalendarPopup(True)
        self.dt_desde.setDate(QDate(date.today().year, 1, 1))
        self.dt_desde.setObjectName("dateEdit")
        filtro_row.addWidget(self.dt_desde)

        lbl_hasta = QLabel("Hasta:")
        lbl_hasta.setObjectName("fieldLabel")
        filtro_row.addWidget(lbl_hasta)
        self.dt_hasta = QDateEdit()
        self.dt_hasta.setCalendarPopup(True)
        self.dt_hasta.setDate(QDate.currentDate())
        self.dt_hasta.setObjectName("dateEdit")
        filtro_row.addWidget(self.dt_hasta)

        btn_filtrar = QPushButton("🔍  Filtrar")
        btn_filtrar.setObjectName("btnSecondary")
        btn_filtrar.clicked.connect(self._cargar_historial)
        filtro_row.addWidget(btn_filtrar)

        btn_todo = QPushButton("Ver todo")
        btn_todo.setObjectName("btnSecondary")
        btn_todo.clicked.connect(self._ver_todo)
        filtro_row.addWidget(btn_todo)

        filtro_row.addStretch()

        btn_factura = QPushButton("🧾  Factura")
        btn_factura.setObjectName("btnSecondary")
        btn_factura.clicked.connect(self._ver_factura_seleccionada)
        filtro_row.addWidget(btn_factura)

        btn_pdf = QPushButton("🖨  Exportar PDF")
        btn_pdf.setObjectName("btnSuccess")
        btn_pdf.clicked.connect(self._exportar_pdf)
        filtro_row.addWidget(btn_pdf)
        lay.addLayout(filtro_row)

        # ── Resumen KPI ──────────────────────────────────────
        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setObjectName("kpiLabel")
        lay.addWidget(self.lbl_resumen)

        # ── Tabla historial ──────────────────────────────────
        self.tbl = QTableWidget(0, 6)
        self.tbl.setObjectName("innerTable")
        self.tbl.setHorizontalHeaderLabels(
            ["ID", "N° Factura", "Fecha", "Productos", "Total", "Estado"]
        )
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setShowGrid(True)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.viewport().setCursor(Qt.ArrowCursor)
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        hh.setSectionResizeMode(5, QHeaderView.Fixed)
        self.tbl.setColumnWidth(0, 45)
        self.tbl.setColumnWidth(1, 110)
        self.tbl.setColumnWidth(2, 140)
        self.tbl.setColumnWidth(4, 120)
        self.tbl.setColumnWidth(5, 100)
        lay.addWidget(self.tbl, 1)

        # ── Botones cierre ───────────────────────────────────
        row_btn = QHBoxLayout()
        row_btn.addStretch()
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("btnSecondary")
        btn_cerrar.setFixedWidth(100)
        btn_cerrar.clicked.connect(self.accept)
        row_btn.addWidget(btn_cerrar)
        lay.addLayout(row_btn)

        self._cargar_historial()

    def _ver_todo(self):
        self.dt_desde.setDate(QDate(2000, 1, 1))
        self.dt_hasta.setDate(QDate.currentDate())
        self._cargar_historial()

    def _cargar_historial(self):
        from app.db.database import SessionLocal
        from app.db.models import Sale, SaleDetail, Product
        from sqlalchemy.orm import joinedload
        from datetime import time as dt_time

        desde = self.dt_desde.date().toPython()
        hasta = self.dt_hasta.date().toPython()
        start = datetime.combine(desde, dt_time.min)
        end = datetime.combine(hasta, dt_time.max)

        with SessionLocal() as db:
            ventas = (
                db.query(Sale)
                .options(
                    joinedload(Sale.details).joinedload(SaleDetail.product),
                    joinedload(Sale.customer),
                )
                .filter(
                    Sale.customer_id == self.customer.id,
                    Sale.fecha >= start,
                    Sale.fecha <= end,
                    Sale.anulada.is_(False),
                )
                .order_by(Sale.fecha.desc())
                .all()
            )

        self._ventas = ventas
        self.tbl.setRowCount(0)

        total_acum = 0.0
        for s in ventas:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self.tbl.setRowHeight(row, 32)

            es_pendiente = getattr(s, "estado_pago", "PAGADO") == "PENDIENTE"

            # Resumen de productos
            prods = []
            for d in s.details or []:
                nombre = d.product.nombre if d.product else f"#{d.product_id}"
                qty = _qty(d.cantidad)
                prods.append(f"{nombre} x{qty}")
            prods_txt = "  ·  ".join(prods) if prods else "—"

            def cell(txt, align=Qt.AlignLeft | Qt.AlignVCenter):
                it = QTableWidgetItem(str(txt))
                it.setTextAlignment(int(align))
                return it

            self.tbl.setItem(row, 0, cell(str(s.id), Qt.AlignCenter | Qt.AlignVCenter))
            self.tbl.setItem(row, 1, cell(s.numero_factura or "—"))
            self.tbl.setItem(row, 2, cell(fmt_fecha(s.fecha)))
            self.tbl.setItem(row, 3, cell(prods_txt))

            it_total = cell(
                _fmt_cop(float(s.total or 0)), Qt.AlignRight | Qt.AlignVCenter
            )
            if es_pendiente:
                it_total.setForeground(QBrush(QColor("#fbbf24")))
            else:
                it_total.setForeground(QBrush(QColor("#4ade80")))
                total_acum += float(s.total or 0)
            self.tbl.setItem(row, 4, it_total)

            estado_txt = "⏳ PENDIENTE" if es_pendiente else "✅ PAGADO"
            it_est = cell(estado_txt, Qt.AlignCenter | Qt.AlignVCenter)
            if es_pendiente:
                it_est.setForeground(QBrush(QColor("#fbbf24")))
            else:
                it_est.setForeground(QBrush(QColor("#4ade80")))
            self.tbl.setItem(row, 5, it_est)

        # KPI resumen
        n = len(ventas)
        pendientes = sum(
            1 for s in ventas if getattr(s, "estado_pago", "PAGADO") == "PENDIENTE"
        )
        total_pendiente = sum(
            float(s.total or 0)
            for s in ventas
            if getattr(s, "estado_pago", "PAGADO") == "PENDIENTE"
        )
        resumen = (
            f"  📋 {n} compra(s)   ·   " f"💰 Total pagado: {_fmt_cop(total_acum)}"
        )
        if pendientes:
            resumen += (
                f"   ·   ⏳ {pendientes} pendiente(s): {_fmt_cop(total_pendiente)}"
            )
        self.lbl_resumen.setText(resumen)

    def _exportar_pdf(self):
        desde = self.dt_desde.date().toPython()
        hasta = self.dt_hasta.date().toPython()
        exportar_historial_cliente_pdf(self, self.customer, self._ventas, desde, hasta)

    def _ver_factura_seleccionada(self):
        """Abre la factura compacta de la venta seleccionada en la tabla."""
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.warning(
                self, "Factura", "Selecciona una compra de la tabla primero."
            )
            return
        sale_id = int(self.tbl.item(row, 0).text())
        mostrar_factura_compacta(self, sale_id)


# ─────────────────────────────────────────────────────────────────────────────
#  Ventana principal de Clientes
# ─────────────────────────────────────────────────────────────────────────────
class CustomersWindow(QWidget):
    def __init__(self):
        super().__init__()
        try:
            from app.main import get_icon

            if get_icon():
                self.setWindowIcon(get_icon())
        except Exception:
            pass
        self.setWindowTitle("Clientes")
        self.resize(860, 560)
        self.setStyleSheet(_STYLES_MAIN)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)

        # ── Header ───────────────────────────────────────────
        lbl_title = QLabel("👥  Clientes")
        lbl_title.setObjectName("pageTitle")
        lbl_sub = QLabel("Gestiona clientes · historial de compras · exporta a PDF")
        lbl_sub.setObjectName("pageSub")
        lay.addWidget(lbl_title)
        lay.addWidget(lbl_sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        # ── Barra de acciones ────────────────────────────────
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍  Buscar por nombre o documento…")
        self.txt_buscar.setObjectName("searchBox")
        self.txt_buscar.textChanged.connect(self._cargar)
        bar.addWidget(self.txt_buscar, 1)

        for label, obj, slot in [
            ("↺  Refrescar", "btnSecondary", self._cargar),
            ("＋  Nuevo", "btnPrimary", self._nuevo),
            ("✎  Editar", "btnSecondary", self._editar),
            ("📋  Historial", "btnSuccess", self._ver_historial),
            ("⏺  Activar/Desact.", "btnWarning", self._toggle_estado),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj)
            btn.clicked.connect(slot)
            bar.addWidget(btn)

        lay.addLayout(bar)

        # ── Tabla ─────────────────────────────────────────────
        self.tbl = QTableWidget(0, 6)
        self.tbl.setObjectName("productTable")
        self.tbl.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Teléfono", "Documento", "Compras", "Estado"]
        )
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setShowGrid(True)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSortingEnabled(True)
        self.tbl.cellDoubleClicked.connect(lambda r, c: self._ver_historial())
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        hh.setSectionResizeMode(5, QHeaderView.Fixed)
        self.tbl.setColumnWidth(0, 45)
        self.tbl.setColumnWidth(2, 130)
        self.tbl.setColumnWidth(3, 130)
        self.tbl.setColumnWidth(4, 90)
        self.tbl.setColumnWidth(5, 100)
        lay.addWidget(self.tbl, 1)

        self.lbl_footer = QLabel("")
        self.lbl_footer.setObjectName("footer")
        lay.addWidget(self.lbl_footer)

        self._cargar()

    # ── Carga ─────────────────────────────────────────────────
    def _cargar(self):
        texto = self.txt_buscar.text().strip()
        clientes = listar_clientes(texto, incluir_inactivos=True)

        # Contar compras por cliente (rápido desde BD)
        from app.db.database import SessionLocal
        from app.db.models import Sale
        from sqlalchemy import func

        with SessionLocal() as db:
            conteo = dict(
                db.query(Sale.customer_id, func.count(Sale.id))
                .filter(Sale.anulada.is_(False))
                .group_by(Sale.customer_id)
                .all()
            )

        self.tbl.setSortingEnabled(False)
        self.tbl.setRowCount(0)
        for c in clientes:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self.tbl.setRowHeight(row, 32)

            activo = getattr(c, "activo", True)
            num_compras = conteo.get(c.id, 0)

            def cell(txt, align=Qt.AlignLeft | Qt.AlignVCenter):
                it = QTableWidgetItem(str(txt))
                it.setTextAlignment(int(align))
                return it

            self.tbl.setItem(row, 0, cell(str(c.id), Qt.AlignCenter | Qt.AlignVCenter))
            self.tbl.setItem(row, 1, cell(c.nombre))
            self.tbl.setItem(row, 2, cell(c.telefono or "—"))
            self.tbl.setItem(row, 3, cell(c.documento or "—"))
            it_comp = cell(str(num_compras), Qt.AlignCenter | Qt.AlignVCenter)
            if num_compras > 0:
                it_comp.setForeground(QBrush(QColor("#4ade80")))
            self.tbl.setItem(row, 4, it_comp)

            estado_txt = "✅ Activo" if activo else "⛔ Inactivo"
            it_est = cell(estado_txt, Qt.AlignCenter | Qt.AlignVCenter)
            if not activo:
                it_est.setForeground(QBrush(QColor("#f87171")))
                for col in range(5):
                    it = self.tbl.item(row, col)
                    if it:
                        it.setForeground(QBrush(QColor("#475569")))
            self.tbl.setItem(row, 5, it_est)

        self.tbl.setSortingEnabled(True)
        activos = sum(1 for c in clientes if getattr(c, "activo", True))
        self.lbl_footer.setText(f"{len(clientes)} cliente(s) · {activos} activo(s)")

    def _selected_customer(self):
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Clientes", "Selecciona un cliente primero.")
            return None
        cid = int(self.tbl.item(row, 0).text())
        from app.db.customers_repo import obtener_cliente

        return obtener_cliente(cid)

    def _nuevo(self):
        dlg = ClienteFormDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._cargar()

    def _editar(self):
        c = self._selected_customer()
        if not c:
            return
        dlg = ClienteFormDialog(self, c)
        if dlg.exec() == QDialog.Accepted:
            self._cargar()

    def _toggle_estado(self):
        c = self._selected_customer()
        if not c:
            return
        accion = "desactivar" if c.activo else "activar"
        resp = QMessageBox.question(
            self, "Confirmar", f"¿{accion.capitalize()} al cliente '{c.nombre}'?"
        )
        if resp == QMessageBox.Yes:
            try:
                cambiar_estado_cliente(c.id)
                self._cargar()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _ver_historial(self):
        c = self._selected_customer()
        if not c:
            return
        dlg = HistorialClienteDialog(self, c)
        dlg.exec()


# ─────────────────────────────────────────────────────────────────────────────
#  Factura compacta (ticket) de una venta individual
# ─────────────────────────────────────────────────────────────────────────────
def mostrar_factura_compacta(parent, sale_id: int) -> None:
    """Muestra diálogo con factura compacta de la venta y permite exportar a PDF."""
    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        QMessageBox.critical(
            parent,
            "Dependencia faltante",
            "Instala reportlab:\n\n  pip install reportlab",
        )
        return

    from app.db.sales_repo import obtener_venta_con_detalle

    sale = obtener_venta_con_detalle(sale_id)
    if not sale:
        QMessageBox.information(parent, "Factura", "Venta no encontrada.")
        return

    from app.ui.sale_receipt import exportar_recibo_pdf

    exportar_recibo_pdf(parent, sale_id)


# ─────────────────────────────────────────────────────────────────────────────
#  Exportar historial a PDF
# ─────────────────────────────────────────────────────────────────────────────
def exportar_historial_cliente_pdf(
    parent, customer, ventas: list, desde: date, hasta: date
) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as rl_canvas
    except ImportError:
        QMessageBox.critical(
            parent,
            "Dependencia faltante",
            "Instala reportlab:\n\n  pip install reportlab",
        )
        return

    if not ventas:
        QMessageBox.information(
            parent, "Sin datos", "No hay compras en el período seleccionado."
        )
        return

    # ── Elegir color o blanco y negro ────────────────────────
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

    dlg_modo = QDialog(parent)
    dlg_modo.setWindowTitle("Estilo del PDF")
    dlg_modo.setFixedWidth(320)
    dlg_modo.setStyleSheet("background:#0b1120; color:#e2e8f0; font-family:'Segoe UI';")
    lay_m = QVBoxLayout(dlg_modo)
    lay_m.setSpacing(12)
    lay_m.setContentsMargins(20, 20, 20, 20)
    lbl_m = QLabel("¿Cómo deseas imprimir el historial?")
    lbl_m.setStyleSheet("font-size:13px; font-weight:600;")
    lay_m.addWidget(lbl_m)
    row_m = QHBoxLayout()
    btn_color = QPushButton("🎨  A color")
    btn_color.setStyleSheet(
        "background:#1e3a5f; border:1px solid #3b82f6; border-radius:8px; padding:10px; font-weight:700; color:#93c5fd;"
    )
    btn_bw = QPushButton("🖨  Blanco y negro")
    btn_bw.setStyleSheet(
        "background:#1a1a1a; border:1px solid #475569; border-radius:8px; padding:10px; font-weight:700; color:#e2e8f0;"
    )
    row_m.addWidget(btn_color)
    row_m.addWidget(btn_bw)
    lay_m.addLayout(row_m)
    _modo = ["color"]
    btn_color.clicked.connect(
        lambda: (_modo.__setitem__(0, "color"), dlg_modo.accept())
    )
    btn_bw.clicked.connect(lambda: (_modo.__setitem__(0, "bw"), dlg_modo.accept()))
    if dlg_modo.exec() != QDialog.Accepted:
        return
    modo_bw = _modo[0] == "bw"

    from PySide6.QtWidgets import QFileDialog

    nombre_slug = customer.nombre.replace(" ", "_")[:20]
    default = f"historial_{nombre_slug}_{desde.strftime('%Y%m%d')}_al_{hasta.strftime('%Y%m%d')}.pdf"
    path, _ = QFileDialog.getSaveFileName(
        parent, "Guardar historial PDF", default, "PDF (*.pdf)"
    )
    if not path:
        return

    try:
        _build_historial_pdf(path, customer, ventas, desde, hasta, modo_bw=modo_bw)
        QMessageBox.information(
            parent, "✅ Exportado", f"Historial guardado en:\n{path}"
        )
    except Exception as e:
        QMessageBox.critical(parent, "Error al generar PDF", str(e))


def _build_historial_pdf(
    path: str, customer, ventas: list, desde: date, hasta: date, modo_bw: bool = False
) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as rl_canvas
    from app.utils.config_manager import cargar_config
    from app.db.database import get_app_data_dir

    cfg = cargar_config()
    empresa = cfg.get("empresa_nombre") or "Inventario JH"
    empresa_tel = cfg.get("empresa_telefono", "")
    empresa_dir = cfg.get("empresa_direccion", "")

    PAGE_W, PAGE_H = A4
    c = rl_canvas.Canvas(path, pagesize=A4)
    W, H = PAGE_W, PAGE_H

    # Paleta según modo
    if modo_bw:
        COL_BG = colors.white
        COL_HEADER = colors.HexColor("#f0f0f0")
        COL_ACCENT = colors.HexColor("#333333")
        COL_TEXT = colors.black
        COL_MUTED = colors.HexColor("#555555")
        COL_GREEN = colors.black
        COL_YELLOW = colors.HexColor("#333333")
        COL_ROW_ALT = colors.HexColor("#eeeeee")
        COL_ROW_NORM = colors.white
        COL_LINE = colors.HexColor("#cccccc")
        COL_CAB_BG = colors.HexColor("#dddddd")
        COL_CAB_TXT = colors.HexColor("#333333")
    else:
        COL_BG = colors.HexColor("#0b1120")
        COL_HEADER = colors.HexColor("#0d1829")
        COL_ACCENT = colors.HexColor("#2563eb")
        COL_TEXT = colors.HexColor("#e2e8f0")
        COL_MUTED = colors.HexColor("#475569")
        COL_GREEN = colors.HexColor("#4ade80")
        COL_YELLOW = colors.HexColor("#fbbf24")
        COL_ROW_ALT = colors.HexColor("#0f1a2e")
        COL_ROW_NORM = colors.HexColor("#0b1120")
        COL_LINE = colors.HexColor("#1e293b")
        COL_CAB_BG = colors.HexColor("#1e3a5f")
        COL_CAB_TXT = colors.HexColor("#94a3b8")

    MARGIN = 14 * mm
    COL_W = W - 2 * MARGIN

    logo_path = get_app_data_dir() / "logo.png"

    def new_page():
        c.setFillColor(COL_BG)
        c.rect(0, 0, W, H, fill=1, stroke=0)

    def hline(y, color=None):
        c.setStrokeColor(color or COL_LINE)
        c.setLineWidth(0.4)
        c.line(MARGIN, y, W - MARGIN, y)

    page_num = [0]

    def draw_header(y_start):
        page_num[0] += 1
        new_page()
        y = y_start

        # Banda azul superior
        c.setFillColor(COL_ACCENT)
        c.rect(0, H - 16 * mm, W, 16 * mm, fill=1, stroke=0)

        # Logo
        if logo_path.exists():
            try:
                logo_h, logo_w = 12 * mm, 30 * mm
                c.drawImage(
                    str(logo_path),
                    MARGIN,
                    H - 14 * mm,
                    width=logo_w,
                    height=logo_h,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(W / 2, H - 10 * mm, empresa.upper())
        if empresa_tel:
            c.setFont("Helvetica", 7)
            c.drawCentredString(W / 2, H - 13.5 * mm, f"Tel: {empresa_tel}")

        # Título documento
        y = H - 22 * mm
        c.setFillColor(COL_TEXT)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(MARGIN, y, "HISTORIAL DE COMPRAS — CLIENTE")
        y -= 7 * mm

        # Info cliente
        c.setFillColor(COL_MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(MARGIN, y, "CLIENTE")
        c.setFillColor(COL_TEXT)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN + 18 * mm, y, customer.nombre)
        y -= 5 * mm

        if customer.documento:
            c.setFillColor(COL_MUTED)
            c.setFont("Helvetica", 7.5)
            c.drawString(MARGIN, y, f"Doc: {customer.documento}")
            y -= 4 * mm
        if customer.telefono:
            c.setFillColor(COL_MUTED)
            c.setFont("Helvetica", 7.5)
            c.drawString(MARGIN, y, f"Tel: {customer.telefono}")
            y -= 4 * mm

        # Período
        c.setFillColor(COL_MUTED)
        c.setFont("Helvetica", 8)
        periodo = (
            f"Período: {desde.strftime('%d/%m/%Y')} — {hasta.strftime('%d/%m/%Y')}"
        )
        c.drawString(MARGIN, y, periodo)
        c.drawRightString(W - MARGIN, y, f"Página {page_num[0]}")
        y -= 3 * mm

        hline(y)
        y -= 3 * mm
        return y

    # ── Calcular totales ────────────────────────────────────────────────────
    total_pagado = sum(
        float(s.total or 0)
        for s in ventas
        if getattr(s, "estado_pago", "PAGADO") == "PAGADO"
    )
    total_pendiente = sum(
        float(s.total or 0)
        for s in ventas
        if getattr(s, "estado_pago", "PAGADO") == "PENDIENTE"
    )

    # ── Primera página ──────────────────────────────────────────────────────
    y = draw_header(H)

    # KPI resumen
    kpi_y = y - 2 * mm
    c.setFillColor(COL_HEADER)
    c.roundRect(MARGIN, kpi_y - 14 * mm, COL_W, 14 * mm, 3 * mm, fill=1, stroke=0)
    kpi_items = [
        ("COMPRAS", str(len(ventas))),
        ("TOTAL PAGADO", _fmt_cop(total_pagado)),
        ("PENDIENTE", _fmt_cop(total_pendiente)),
    ]
    kpi_col_w = COL_W / len(kpi_items)
    for i, (label, val) in enumerate(kpi_items):
        kx = MARGIN + i * kpi_col_w + kpi_col_w / 2
        c.setFillColor(COL_MUTED)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(kx, kpi_y - 5 * mm, label)
        col_val = COL_GREEN if i == 1 else (COL_YELLOW if i == 2 else COL_TEXT)
        c.setFillColor(col_val)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(kx, kpi_y - 11 * mm, val)
    y = kpi_y - 17 * mm

    hline(y)
    y -= 4 * mm

    # ── Encabezado tabla ────────────────────────────────────────────────────
    COL_POSITIONS = {
        "factura": (MARGIN, 28 * mm),
        "fecha": (MARGIN + 30 * mm, 30 * mm),
        "productos": (MARGIN + 62 * mm, 68 * mm),
        "total": (MARGIN + 132 * mm, 28 * mm),
        "estado": (MARGIN + 162 * mm, 22 * mm),
    }

    def draw_table_header(y):
        c.setFillColor(COL_CAB_BG)
        c.rect(MARGIN, y - 6 * mm, COL_W, 7 * mm, fill=1, stroke=0)
        c.setFillColor(COL_CAB_TXT)
        c.setFont("Helvetica-Bold", 6.5)
        headers = [
            (COL_POSITIONS["factura"][0], "N° FACTURA"),
            (COL_POSITIONS["fecha"][0], "FECHA"),
            (COL_POSITIONS["productos"][0], "PRODUCTOS"),
            (COL_POSITIONS["total"][0], "TOTAL"),
            (COL_POSITIONS["estado"][0], "ESTADO"),
        ]
        for xpos, txt in headers:
            c.drawString(xpos + 1 * mm, y - 4 * mm, txt)
        return y - 8 * mm

    y = draw_table_header(y)

    # ── Filas de ventas ──────────────────────────────────────────────────────
    PROD_COL_X = COL_POSITIONS["productos"][0] + 1 * mm
    PROD_COL_W = COL_POSITIONS["productos"][1] - 2 * mm  # ancho útil productos
    LINE_H = 4.2 * mm  # altura por línea de texto
    PAD_V = 2.0 * mm  # padding vertical por fila

    def wrap_productos(items: list[str], max_w: float, font_size: float) -> list[str]:
        """Parte la lista de productos en líneas que caben en max_w."""
        c.setFont("Helvetica", font_size)
        lines, current = [], ""
        for item in items:
            probe = (current + " · " + item) if current else item
            if c.stringWidth(probe, "Helvetica", font_size) <= max_w:
                current = probe
            else:
                if current:
                    lines.append(current)
                # Si el item solo ya es más ancho, lo cortamos con …
                while c.stringWidth(item, "Helvetica", font_size) > max_w:
                    # recortar carácter a carácter
                    cut = item
                    while (
                        cut and c.stringWidth(cut + "…", "Helvetica", font_size) > max_w
                    ):
                        cut = cut[:-1]
                    lines.append(cut + "…")
                    item = ""
                    break
                current = item
        if current:
            lines.append(current)
        return lines or ["—"]

    for idx, s in enumerate(ventas):
        es_pendiente = getattr(s, "estado_pago", "PAGADO") == "PENDIENTE"

        # Construir lista de ítems
        prods = []
        for d in s.details or []:
            nombre = d.product.nombre if d.product else f"#{d.product_id}"
            qty = _qty(d.cantidad)
            prods.append(f"{nombre} ({qty})")
        prod_lines = wrap_productos(prods, PROD_COL_W, 6.5)

        # Altura dinámica según cantidad de líneas
        row_h = max(7 * mm, len(prod_lines) * LINE_H + PAD_V * 2)

        # Necesita nueva página?
        if y - row_h < 25 * mm:
            c.showPage()
            y = draw_header(H)
            y = draw_table_header(y)

        # Fondo fila alterna
        bg = COL_ROW_ALT if idx % 2 == 0 else COL_ROW_NORM
        c.setFillColor(bg)
        c.rect(MARGIN, y - row_h, COL_W, row_h, fill=1, stroke=0)

        # Baseline primera línea (desde arriba con padding)
        ty = y - PAD_V - LINE_H * 0.75

        # N° Factura (centrado verticalmente)
        mid_y = y - row_h / 2 - 1.5 * mm
        c.setFillColor(COL_TEXT)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(
            COL_POSITIONS["factura"][0] + 1 * mm, mid_y, s.numero_factura or f"#{s.id}"
        )

        # Fecha (centrada verticalmente)
        c.setFillColor(COL_MUTED)
        c.setFont("Helvetica", 7)
        try:
            fecha_txt = s.fecha.strftime("%d/%m/%Y %H:%M")
        except Exception:
            fecha_txt = str(s.fecha)
        c.drawString(COL_POSITIONS["fecha"][0] + 1 * mm, mid_y, fecha_txt)

        # Productos — multi-línea
        c.setFillColor(COL_TEXT)
        c.setFont("Helvetica", 6.5)
        for li, line_txt in enumerate(prod_lines):
            c.drawString(PROD_COL_X, ty - li * LINE_H, line_txt)

        # Total (centrado verticalmente)
        col_total = COL_YELLOW if es_pendiente else COL_GREEN
        c.setFillColor(col_total)
        c.setFont("Helvetica-Bold", 8)
        total_txt = _fmt_cop(float(s.total or 0))
        c.drawRightString(
            COL_POSITIONS["total"][0] + COL_POSITIONS["total"][1] - 1 * mm,
            mid_y,
            total_txt,
        )

        # Estado (centrado verticalmente)
        estado_txt = "PENDIENTE" if es_pendiente else "PAGADO"
        c.setFillColor(COL_YELLOW if es_pendiente else COL_GREEN)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(COL_POSITIONS["estado"][0] + 1 * mm, mid_y, estado_txt)

        # Línea separadora fina entre filas
        c.setStrokeColor(COL_LINE)
        c.setLineWidth(0.3)
        c.line(MARGIN, y - row_h, W - MARGIN, y - row_h)

        y -= row_h

    # ── Línea total final ────────────────────────────────────────────────────
    y -= 3 * mm
    hline(y)
    y -= 6 * mm
    c.setFillColor(COL_MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN, y, "TOTAL PAGADO")
    c.setFillColor(COL_GREEN)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(W - MARGIN, y, _fmt_cop(total_pagado))
    if total_pendiente > 0:
        y -= 7 * mm
        c.setFillColor(COL_MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(MARGIN, y, "TOTAL PENDIENTE")
        c.setFillColor(COL_YELLOW)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(W - MARGIN, y, _fmt_cop(total_pendiente))

    y -= 10 * mm
    c.setFillColor(COL_MUTED)
    c.setFont("Helvetica", 6)
    c.drawCentredString(
        W / 2,
        y,
        f"Generado por {empresa} — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )

    c.save()


# ─────────────────────────────────────────────────────────────────────────────
#  Estilos
# ─────────────────────────────────────────────────────────────────────────────
_STYLES_MAIN = """
QWidget {
    background: #0b1120; color: #e2e8f0;
    font-family: "Segoe UI", Arial, sans-serif; font-size: 13px;
}
#pageTitle { font-size: 20px; font-weight: 800; color: #f1f5f9; }
#pageSub   { font-size: 12px; color: #475569; }
#footer    { font-size: 10px; color: #334155; }
#separator { border: none; border-top: 1px solid #1e293b; }
#searchBox {
    background: #111c33; border: 1px solid #1e3a5f;
    border-radius: 8px; padding: 6px 12px; color: #e2e8f0; min-height: 30px;
}
#searchBox:focus { border-color: #3b82f6; }
#btnPrimary {
    background: #2563eb; border: none; border-radius: 8px;
    padding: 6px 14px; font-weight: 700; color: white; min-height: 30px;
}
#btnPrimary:hover { background: #1d4ed8; }
#btnSecondary {
    background: #111c33; border: 1px solid #1e3a5f;
    border-radius: 8px; padding: 6px 12px;
    font-weight: 600; color: #94a3b8; min-height: 30px;
}
#btnSecondary:hover { border-color: #3b82f6; color: #e2e8f0; }
#btnSuccess {
    background: #052e16; border: 1px solid #15803d;
    border-radius: 8px; padding: 6px 14px;
    font-weight: 700; color: #4ade80; min-height: 30px;
}
#btnSuccess:hover { background: #15803d; color: #fff; }
#btnWarning {
    background: #1a1200; border: 1px solid #92400e;
    border-radius: 8px; padding: 6px 12px;
    font-weight: 600; color: #fbbf24; min-height: 30px;
}
#btnWarning:hover { background: #92400e; color: #fff; }
#productTable {
    background: #0b1120; alternate-background-color: #0f1a2e;
    border: 1px solid #1e293b; border-radius: 8px;
    gridline-color: #1e293b;
    selection-background-color: #1e3a5f; selection-color: #f1f5f9; outline: none;
}
#productTable QHeaderView::section {
    background: #111c33; color: #475569;
    font-size: 10px; font-weight: 700; letter-spacing: 1px;
    padding: 6px 10px; border: none; border-bottom: 2px solid #1e293b;
}
#productTable::item { padding: 4px 10px; border: none; }
QScrollBar:vertical { background: #0b1120; width: 6px; border-radius: 3px; }
QScrollBar::handle:vertical { background: #1e3a5f; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

_STYLES_DIALOG = (
    _STYLES_MAIN
    + """
QDialog { background: #0b1120; }
#kpiLabel { font-size: 12px; color: #64748b; padding: 4px 0; }
#dateEdit {
    background: #111c33; border: 1px solid #1e3a5f;
    border-radius: 8px; padding: 4px 8px; color: #e2e8f0; min-height: 28px;
}
#fieldLabel { color: #64748b; font-size: 12px; font-weight: 600; }
#innerTable {
    background: #0b1120; alternate-background-color: #0f1a2e;
    border: 1px solid #1e293b; border-radius: 8px;
    gridline-color: #1e293b;
    selection-background-color: #1e3a5f; selection-color: #f1f5f9; outline: none;
}
#innerTable QHeaderView::section {
    background: #111c33; color: #475569;
    font-size: 10px; font-weight: 700; letter-spacing: 1px;
    padding: 6px 10px; border: none; border-bottom: 2px solid #1e293b;
}
#innerTable::item { padding: 4px 10px; border: none; }
"""
)
