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
from app.utils.formatters import fmt_fecha, fmt_qty as _qty, fmt_cop as _fmt_cop
from app.ui.customer_form import ClienteFormDialog
from app.ui.customer_pdf import exportar_historial_cliente_pdf, mostrar_factura_compacta


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────


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
            self.tbl.setItem(row, 1, cell((s.numero_factura or "—").upper()))
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
