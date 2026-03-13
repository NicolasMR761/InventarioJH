from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
    QCompleter,
    QDialog,
    QTextEdit,
    QHeaderView,
    QFrame,
    QScrollArea,
    QAbstractScrollArea,
)
from PySide6.QtGui import QColor, QBrush, QWheelEvent

from app.db.products_repo import listar_productos
from app.db.customers_repo import listar_clientes, crear_cliente
from app.db.sales_repo import (
    crear_venta,
    listar_ventas,
    listar_ventas_pendientes,
    obtener_venta_con_detalle,
    anular_venta,
    registrar_pago_pendiente,
)
from app.utils.formatters import fmt_fecha
from app.ui.widgets import CommaDoubleSpinBox


class CopSpinBox(QSpinBox):
    """
    SpinBox para precios en COP:
    - Muestra separador de miles con punto  (ej: $6.000)
    - Sube/baja de 50 en 50 con las flechas
    - Acepta entrada con o sin puntos
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(0)
        self.setMaximum(99_999_999)
        self.setSingleStep(50)
        self.setPrefix("$")

    def textFromValue(self, value: int) -> str:
        s = ""
        digits = str(abs(value))
        for i, ch in enumerate(reversed(digits)):
            if i > 0 and i % 3 == 0:
                s = "." + s
            s = ch + s
        return s

    def valueFromText(self, text: str) -> int:
        clean = text.replace("$", "").replace(".", "").replace(",", "").strip()
        try:
            return int(clean)
        except ValueError:
            return 0

    def validate(self, text: str, pos: int):
        from PySide6.QtGui import QValidator

        clean = text.replace("$", "").replace(".", "").replace(",", "").strip()
        if clean == "" or clean.isdigit():
            return (QValidator.Acceptable, text, pos)
        return (QValidator.Invalid, text, pos)


class _FixedTable(QTableWidget):
    """
    Tabla con altura fija y scroll interno propio.
    La rueda del mouse scrollea DENTRO de la tabla.
    NO propaga el evento al QScrollArea padre, evitando
    que la página entera se mueva al scrollear sobre la tabla.
    """

    def wheelEvent(self, event: QWheelEvent):
        super().wheelEvent(event)
        event.accept()


class SalesWindow(QWidget):
    def __init__(self):
        super().__init__()
        try:
            from app.main import get_icon

            if get_icon():
                self.setWindowIcon(get_icon())
        except Exception:
            pass
        self.setWindowTitle("Ventas")
        self.resize(1020, 760)
        self.setStyleSheet(self._styles())

        self.items: list[dict] = []
        self._productos_cache: list[dict] = []
        self._clientes_cache: list[dict] = []

        self._page_size = 50
        self._offset = 0
        self._total_ventas = 0
        self._ventas_cache: list = []

        # ── Layout raíz ────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._page_scroll = QScrollArea()
        self._page_scroll.setWidgetResizable(True)
        self._page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._page_scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(self._page_scroll)

        content = QWidget()
        self._page_scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        # ── HEADER ────────────────────────────────────────
        lbl_title = QLabel("🛒 Ventas")
        lbl_title.setObjectName("pageTitle")
        lbl_sub = QLabel("Registra ventas · Gestiona fiados · Consulta historial")
        lbl_sub.setObjectName("pageSub")
        root.addWidget(lbl_title)
        root.addWidget(lbl_sub)

        sep0 = QFrame()
        sep0.setFrameShape(QFrame.HLine)
        sep0.setObjectName("separator")
        root.addWidget(sep0)

        # ── FILA 1: Producto + Cant + Precio ─────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        lbl_p = QLabel("Producto:")
        lbl_p.setObjectName("fieldLabel")
        row1.addWidget(lbl_p)
        self.cbo_producto = QComboBox()
        self.cbo_producto.setObjectName("combo")
        self.cbo_producto.setMinimumWidth(240)
        self.cbo_producto.setCursor(Qt.ArrowCursor)
        row1.addWidget(self.cbo_producto, 3)

        lbl_c = QLabel("Cant:")
        lbl_c.setObjectName("fieldLabel")
        row1.addWidget(lbl_c)
        self.sp_cant = CommaDoubleSpinBox()
        self.sp_cant.setObjectName("spinBox")
        self.sp_cant.setMinimum(0.01)
        self.sp_cant.setMaximum(999999.99)
        self.sp_cant.setValue(1.0)
        self.sp_cant.setDecimals(2)
        self.sp_cant.setSingleStep(0.5)
        self.sp_cant.setFixedWidth(100)
        row1.addWidget(self.sp_cant)

        lbl_pr = QLabel("Precio:")
        lbl_pr.setObjectName("fieldLabel")
        row1.addWidget(lbl_pr)
        self.sp_precio = CopSpinBox()
        self.sp_precio.setObjectName("spinBox")
        self.sp_precio.setFixedWidth(130)
        row1.addWidget(self.sp_precio)

        self.btn_agregar = QPushButton("＋  Agregar")
        self.btn_agregar.setObjectName("btnPrimary")
        row1.addWidget(self.btn_agregar)
        root.addLayout(row1)

        # ── FILA 2: Factura + Cliente + Estado + Método ──
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        lbl_f = QLabel("Factura:")
        lbl_f.setObjectName("fieldLabel")
        row2.addWidget(lbl_f)
        self.txt_factura = QLineEdit()
        self.txt_factura.setObjectName("inputField")
        self.txt_factura.setPlaceholderText("Nro. factura…")
        self.txt_factura.setFixedWidth(120)
        row2.addWidget(self.txt_factura)

        lbl_cl = QLabel("Cliente:")
        lbl_cl.setObjectName("fieldLabel")
        row2.addWidget(lbl_cl)
        self.txt_cliente = QLineEdit()
        self.txt_cliente.setObjectName("inputField")
        self.txt_cliente.setPlaceholderText("Nombre cliente…")
        row2.addWidget(self.txt_cliente, 2)

        self.btn_nuevo_cliente = QPushButton("＋ Cliente")
        self.btn_nuevo_cliente.setObjectName("btnSecondary")
        row2.addWidget(self.btn_nuevo_cliente)

        lbl_ep = QLabel("Estado:")
        lbl_ep.setObjectName("fieldLabel")
        row2.addWidget(lbl_ep)
        self.cbo_estado_pago = QComboBox()
        self.cbo_estado_pago.setObjectName("combo")
        self.cbo_estado_pago.addItems(["✅ PAGADO", "⏳ PENDIENTE (fiado)"])
        self.cbo_estado_pago.setCursor(Qt.ArrowCursor)
        row2.addWidget(self.cbo_estado_pago)

        lbl_mt = QLabel("Método:")
        lbl_mt.setObjectName("fieldLabel")
        row2.addWidget(lbl_mt)
        self.cbo_metodo = QComboBox()
        self.cbo_metodo.setObjectName("combo")
        self.cbo_metodo.addItems(
            ["Efectivo", "Transferencia", "Nequi", "Débito", "Crédito"]
        )
        self.cbo_metodo.setCursor(Qt.ArrowCursor)
        row2.addWidget(self.cbo_metodo)
        root.addLayout(row2)

        # ── TABLA ITEMS VENTA ACTUAL ──────────────────────
        self.tbl = QTableWidget(0, 5)
        self.tbl.setObjectName("innerTable")
        self.tbl.setHorizontalHeaderLabels(
            ["ID", "Producto", "Cant", "Precio", "Subtotal"]
        )
        self.tbl.setColumnHidden(0, True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setShowGrid(True)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.viewport().setCursor(Qt.ArrowCursor)
        self.tbl.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        self.tbl.setColumnWidth(2, 80)
        self.tbl.setColumnWidth(3, 120)
        self.tbl.setColumnWidth(4, 130)
        self.tbl.setFixedHeight(130)
        root.addWidget(self.tbl)

        # Footer venta actual
        foot_new = QHBoxLayout()
        self.lbl_total = QLabel("Total: $0,00")
        self.lbl_total.setObjectName("totalLabel")
        foot_new.addWidget(self.lbl_total, 1)
        self.btn_quitar = QPushButton("✕  Quitar")
        self.btn_quitar.setObjectName("btnDanger")
        self.btn_guardar = QPushButton("💾  Guardar venta")
        self.btn_guardar.setObjectName("btnSuccess")
        foot_new.addWidget(self.btn_quitar)
        foot_new.addWidget(self.btn_guardar)
        root.addLayout(foot_new)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setObjectName("separator")
        root.addWidget(sep1)

        # ── FIADOS PENDIENTES ─────────────────────────────
        lbl_fiado = QLabel("⏳  Ventas pendientes de cobro (fiado)")
        lbl_fiado.setObjectName("sectionTitle")
        root.addWidget(lbl_fiado)

        self.tbl_pendientes = _FixedTable(0, 6)
        self.tbl_pendientes.setObjectName("innerTable")
        self.tbl_pendientes.setHorizontalHeaderLabels(
            ["ID", "Factura", "Fecha", "Cliente", "Total", ""]
        )
        self.tbl_pendientes.verticalHeader().setVisible(False)
        self.tbl_pendientes.setShowGrid(True)
        self.tbl_pendientes.setAlternatingRowColors(True)
        self.tbl_pendientes.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_pendientes.viewport().setCursor(Qt.ArrowCursor)
        self.tbl_pendientes.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        hh2 = self.tbl_pendientes.horizontalHeader()
        hh2.setSectionResizeMode(0, QHeaderView.Fixed)
        hh2.setSectionResizeMode(1, QHeaderView.Fixed)
        hh2.setSectionResizeMode(2, QHeaderView.Fixed)
        hh2.setSectionResizeMode(3, QHeaderView.Stretch)
        hh2.setSectionResizeMode(4, QHeaderView.Fixed)
        hh2.setSectionResizeMode(5, QHeaderView.Fixed)
        self.tbl_pendientes.setColumnWidth(0, 50)
        self.tbl_pendientes.setColumnWidth(1, 100)
        self.tbl_pendientes.setColumnWidth(2, 140)
        self.tbl_pendientes.setColumnWidth(4, 120)
        self.tbl_pendientes.setColumnWidth(5, 100)
        self.tbl_pendientes.setFixedHeight(140)
        root.addWidget(self.tbl_pendientes)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("separator")
        root.addWidget(sep2)

        # ── HISTORIAL ─────────────────────────────────────
        hdr_hist = QHBoxLayout()
        lbl_hist = QLabel("📋  Historial de ventas")
        lbl_hist.setObjectName("sectionTitle")
        hdr_hist.addWidget(lbl_hist)
        hdr_hist.addStretch()
        self.btn_refrescar = QPushButton("↺  Refrescar")
        self.btn_refrescar.setObjectName("btnSecondary")
        hdr_hist.addWidget(self.btn_refrescar)
        self.btn_anular = QPushButton("✕  Anular seleccionada")
        self.btn_anular.setObjectName("btnDanger")
        hdr_hist.addWidget(self.btn_anular)
        root.addLayout(hdr_hist)

        # Tabla historial — 7 columnas (agrega col PDF)
        self.tbl_hist = _FixedTable(0, 7)
        self.tbl_hist.setObjectName("innerTable")
        self.tbl_hist.setHorizontalHeaderLabels(
            ["ID", "Factura", "Fecha", "Cliente", "Total", "Acciones", ""]
        )
        self.tbl_hist.verticalHeader().setVisible(False)
        self.tbl_hist.setShowGrid(True)
        self.tbl_hist.setAlternatingRowColors(True)
        self.tbl_hist.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_hist.viewport().setCursor(Qt.ArrowCursor)
        self.tbl_hist.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.tbl_hist.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        hh3 = self.tbl_hist.horizontalHeader()
        hh3.setSectionResizeMode(0, QHeaderView.Fixed)
        hh3.setSectionResizeMode(1, QHeaderView.Fixed)
        hh3.setSectionResizeMode(2, QHeaderView.Fixed)
        hh3.setSectionResizeMode(3, QHeaderView.Stretch)
        hh3.setSectionResizeMode(4, QHeaderView.Fixed)
        hh3.setSectionResizeMode(5, QHeaderView.Fixed)
        hh3.setSectionResizeMode(6, QHeaderView.Fixed)
        self.tbl_hist.setColumnWidth(0, 45)
        self.tbl_hist.setColumnWidth(1, 100)
        self.tbl_hist.setColumnWidth(2, 135)
        self.tbl_hist.setColumnWidth(4, 120)
        self.tbl_hist.setColumnWidth(5, 80)
        self.tbl_hist.setColumnWidth(6, 80)
        self.tbl_hist.setFixedHeight(520)
        root.addWidget(self.tbl_hist)

        # Paginación historial
        pager = QHBoxLayout()
        self.btn_prev = QPushButton("« Anterior")
        self.btn_prev.setObjectName("btnSecondary")
        self.btn_prev.setFixedWidth(100)
        self.lbl_pager = QLabel("—")
        self.lbl_pager.setObjectName("pagerLabel")
        self.lbl_pager.setAlignment(Qt.AlignCenter)
        self.btn_next = QPushButton("Siguiente »")
        self.btn_next.setObjectName("btnSecondary")
        self.btn_next.setFixedWidth(100)
        pager.addWidget(self.btn_prev)
        pager.addWidget(self.lbl_pager, 1)
        pager.addWidget(self.btn_next)
        root.addLayout(pager)

        # ── SEÑALES ───────────────────────────────────────
        self.btn_agregar.clicked.connect(self.agregar_item)
        self.btn_quitar.clicked.connect(self.quitar_item)
        self.btn_guardar.clicked.connect(self.guardar_venta)
        self.btn_anular.clicked.connect(self.anular_seleccionada)
        self.btn_nuevo_cliente.clicked.connect(self.crear_cliente_rapido)
        self.btn_refrescar.clicked.connect(self.refrescar_todo)
        self.cbo_producto.currentIndexChanged.connect(self._autocompletar_precio)
        self.cbo_estado_pago.currentIndexChanged.connect(self._toggle_metodo)
        self.btn_prev.clicked.connect(self._pag_anterior)
        self.btn_next.clicked.connect(self._pag_siguiente)

        self.refrescar_todo()

    # ── ESTILOS ───────────────────────────────────────────
    def _styles(self) -> str:
        return """
        QWidget {
            background: #0b1120;
            color: #e2e8f0;
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 13px;
        }
        QScrollArea { border: none; background: #0b1120; }

        #pageTitle {
            font-size: 20px; font-weight: 800;
            color: #f1f5f9; letter-spacing: -0.3px;
        }
        #pageSub { font-size: 12px; color: #475569; }
        #sectionTitle { font-size: 13px; font-weight: 700; color: #94a3b8; }
        #fieldLabel { color: #64748b; font-size: 12px; font-weight: 600; }
        #pagerLabel { font-size: 11px; color: #475569; }

        #separator { border: none; border-top: 1px solid #1e293b; }

        #inputField {
            background: #111c33; border: 1px solid #1e3a5f;
            border-radius: 8px; padding: 6px 10px;
            color: #e2e8f0; min-height: 28px;
        }
        #inputField:focus { border-color: #3b82f6; }

        #combo {
            background: #111c33; border: 1px solid #1e3a5f;
            border-radius: 8px; padding: 4px 8px;
            color: #e2e8f0; min-height: 28px;
        }
        QComboBox::drop-down { border: none; width: 18px; }
        QComboBox QAbstractItemView {
            background: #111c33; border: 1px solid #1e3a5f;
            color: #e2e8f0; selection-background-color: #1e3a5f;
        }

        #spinBox {
            background: #111c33; border: 1px solid #1e3a5f;
            border-radius: 8px; padding: 4px 8px;
            color: #e2e8f0; min-height: 28px;
        }
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            cursor: default; width: 18px;
        }

        #btnPrimary {
            background: #2563eb; border: none; border-radius: 8px;
            padding: 6px 16px; font-weight: 700; color: white; min-height: 30px;
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
            border-radius: 8px; padding: 6px 16px;
            font-weight: 700; color: #4ade80; min-height: 30px;
        }
        #btnSuccess:hover { background: #15803d; color: #fff; }

        #btnDanger {
            background: #1a0a0a; border: 1px solid #7f1d1d;
            border-radius: 8px; padding: 6px 12px;
            font-weight: 600; color: #f87171; min-height: 30px;
        }
        #btnDanger:hover { background: #7f1d1d; color: #fff; }

        #totalLabel {
            font-size: 16px; font-weight: 800; color: #4ade80;
        }

        #innerTable {
            background: #0b1120;
            alternate-background-color: #0f1a2e;
            border: 1px solid #1e293b;
            border-radius: 8px;
            gridline-color: #1e293b;
            selection-background-color: #1e3a5f;
            selection-color: #f1f5f9;
            outline: none;
        }
        #innerTable QHeaderView::section {
            background: #111c33; color: #475569;
            font-size: 10px; font-weight: 700;
            letter-spacing: 1px; text-transform: uppercase;
            padding: 6px 10px;
            border: none; border-bottom: 2px solid #1e293b;
        }
        #innerTable::item { padding: 5px 10px; border: none; }
        #innerTable::item:selected { background: #1e3a5f; }

        QScrollBar:vertical {
            background: #0b1120; width: 6px; border-radius: 3px;
        }
        QScrollBar::handle:vertical { background: #1e3a5f; border-radius: 3px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """

    # ── HELPERS ──────────────────────────────────────────
    def _fmt_money(self, value: float) -> str:
        try:
            n = int(round(float(value or 0)))
            s = "${:,}".format(n).replace(",", "X").replace(".", ",").replace("X", ".")
            return s
        except Exception:
            return "$0"

    def _toggle_metodo(self):
        self.cbo_metodo.setEnabled(
            "PENDIENTE" not in self.cbo_estado_pago.currentText()
        )

    def _autocompletar_precio(self, index: int):
        if 0 <= index < len(self._productos_cache):
            precio = self._productos_cache[index]["precio_venta"]
            if precio > 0:
                self.sp_precio.setValue(int(precio))

    def _customer_id_por_nombre(self) -> int | None:
        nombre = self.txt_cliente.text().strip()
        if not nombre:
            return None
        for c in self._clientes_cache:
            if c["nombre"].lower() == nombre.lower():
                return c["id"]
        return None

    # ── PAGINACIÓN ────────────────────────────────────────
    def _pag_anterior(self):
        if self._offset > 0:
            self._offset = max(0, self._offset - self._page_size)
            self._pintar_historial()

    def _pag_siguiente(self):
        if self._offset + self._page_size < self._total_ventas:
            self._offset += self._page_size
            self._pintar_historial()

    def _pintar_historial(self):
        ventas_pagina = self._ventas_cache[
            self._offset : self._offset + self._page_size
        ]

        self.tbl_hist.blockSignals(True)
        self.tbl_hist.setRowCount(0)

        for s in ventas_pagina:
            row = self.tbl_hist.rowCount()
            self.tbl_hist.insertRow(row)
            self.tbl_hist.setRowHeight(row, 34)

            cliente_nombre = s.customer.nombre if getattr(s, "customer", None) else "—"
            es_anulada = getattr(s, "anulada", False)
            es_pendiente = getattr(s, "estado_pago", "PAGADO") == "PENDIENTE"

            if es_anulada:
                estado_icon = " ❌"
                color_fila = QColor(120, 30, 30, 60)
            elif es_pendiente:
                estado_icon = " ⏳"
                color_fila = QColor(120, 90, 10, 60)
            else:
                estado_icon = ""
                color_fila = None

            def cell(txt, align=Qt.AlignLeft | Qt.AlignVCenter):
                it = QTableWidgetItem(str(txt))
                it.setTextAlignment(int(align))
                return it

            self.tbl_hist.setItem(
                row, 0, cell(str(s.id), Qt.AlignCenter | Qt.AlignVCenter)
            )
            self.tbl_hist.setItem(row, 1, cell(s.numero_factura or "—"))
            self.tbl_hist.setItem(row, 2, cell(fmt_fecha(s.fecha)))
            self.tbl_hist.setItem(row, 3, cell(cliente_nombre))

            it_total = cell(
                f"{self._fmt_money(float(s.total or 0))}{estado_icon}",
                Qt.AlignRight | Qt.AlignVCenter,
            )
            if es_anulada:
                it_total.setForeground(QBrush(QColor("#f87171")))
            elif es_pendiente:
                it_total.setForeground(QBrush(QColor("#fbbf24")))
            else:
                it_total.setForeground(QBrush(QColor("#4ade80")))
            self.tbl_hist.setItem(row, 4, it_total)

            if color_fila:
                for col in range(5):
                    it = self.tbl_hist.item(row, col)
                    if it:
                        it.setBackground(QBrush(color_fila))

            sale_id = int(s.id)

            # ── Botón Ver ─────────────────────────────────
            btn_ver = QPushButton(" Ver ")
            btn_ver.setCursor(Qt.ArrowCursor)
            btn_ver.setStyleSheet(
                """
                QPushButton {
                    background: #111c33; border: 1px solid #1e3a5f;
                    border-radius: 5px; padding: 3px 10px;
                    color: #93c5fd; font-size: 11px; font-weight: 600;
                }
                QPushButton:hover { background: #1e3a5f; color: #fff; }
            """
            )
            btn_ver.clicked.connect(lambda _, sid=sale_id: self.ver_detalle_venta(sid))
            self.tbl_hist.setCellWidget(row, 5, btn_ver)

            # ── Botón PDF ─────────────────────────────────
            btn_pdf = QPushButton("🖨 PDF")
            btn_pdf.setCursor(Qt.ArrowCursor)
            btn_pdf.setStyleSheet(
                """
                QPushButton {
                    background: #0f2d1a; border: 1px solid #15803d;
                    border-radius: 5px; padding: 3px 10px;
                    color: #4ade80; font-size: 11px; font-weight: 600;
                }
                QPushButton:hover { background: #15803d; color: #fff; }
            """
            )
            btn_pdf.clicked.connect(lambda _, sid=sale_id: self.recibo_pdf(sid))
            self.tbl_hist.setCellWidget(row, 6, btn_pdf)

        self.tbl_hist.blockSignals(False)

        start = self._offset + 1 if self._total_ventas else 0
        end = min(self._offset + self._page_size, self._total_ventas)
        self.lbl_pager.setText(f"{start}–{end} de {self._total_ventas} ventas")
        self.btn_prev.setEnabled(self._offset > 0)
        self.btn_next.setEnabled(self._offset + self._page_size < self._total_ventas)

    # ── CARGA DE DATOS ────────────────────────────────────
    def keyPressEvent(self, event):
        from PySide6.QtCore import Qt

        key = event.key()
        mod = event.modifiers()
        if key in (Qt.Key_Return, Qt.Key_Enter) and mod == Qt.NoModifier:
            # Solo agregar si el foco está en los campos del formulario
            focus = self.focusWidget()
            form_widgets = (
                self.cbo_producto,
                self.sp_cant,
                self.sp_precio,
                self.txt_cliente,
                self.txt_factura,
            )
            if focus in form_widgets:
                self.agregar_item()
        elif key == Qt.Key_S and mod == Qt.ControlModifier:
            self.guardar_venta()
        elif key == Qt.Key_F5:
            self.refrescar_todo()
        elif key == Qt.Key_Escape:
            # Limpiar formulario actual
            self.items.clear()
            self.tbl.setRowCount(0)
            self.txt_cliente.clear()
            self.txt_factura.clear()
            self.actualizar_total()
        else:
            super().keyPressEvent(event)

    def refrescar_todo(self):
        self.cargar_productos()
        self.cargar_clientes()
        self.cargar_historial()
        self.cargar_pendientes()

    def cargar_productos(self):
        self._productos_cache = []
        self.cbo_producto.blockSignals(True)
        self.cbo_producto.clear()
        for p in listar_productos("", incluir_inactivos=False):
            self._productos_cache.append(
                {
                    "id": p.id,
                    "nombre": p.nombre,
                    "stock_actual": float(p.stock_actual or 0.0),
                    "precio_venta": float(p.precio_venta or 0.0),
                }
            )
            stock = float(p.stock_actual or 0)
            stock_txt = (
                str(int(stock))
                if stock == int(stock)
                else f"{stock:.2f}".replace(".", ",")
            )
            self.cbo_producto.addItem(f"{p.nombre}  (Stock: {stock_txt})", p.id)
        self.cbo_producto.blockSignals(False)
        self._autocompletar_precio(self.cbo_producto.currentIndex())

    def cargar_clientes(self):
        self._clientes_cache = []
        nombres = []
        for c in listar_clientes("", incluir_inactivos=False):
            self._clientes_cache.append({"id": c.id, "nombre": c.nombre})
            nombres.append(c.nombre)
        completer = QCompleter(nombres)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.txt_cliente.setCompleter(completer)

    def cargar_historial(self):
        self._ventas_cache = listar_ventas(5000)
        self._total_ventas = len(self._ventas_cache)
        self._offset = 0
        self._pintar_historial()

    def cargar_pendientes(self):
        pendientes = listar_ventas_pendientes()
        self.tbl_pendientes.blockSignals(True)
        self.tbl_pendientes.setRowCount(0)
        for s in pendientes:
            row = self.tbl_pendientes.rowCount()
            self.tbl_pendientes.insertRow(row)
            self.tbl_pendientes.setRowHeight(row, 32)
            cliente_nombre = s.customer.nombre if getattr(s, "customer", None) else "—"
            self.tbl_pendientes.setItem(row, 0, QTableWidgetItem(str(s.id)))
            self.tbl_pendientes.setItem(
                row, 1, QTableWidgetItem(s.numero_factura or "—")
            )
            self.tbl_pendientes.setItem(row, 2, QTableWidgetItem(fmt_fecha(s.fecha)))
            self.tbl_pendientes.setItem(row, 3, QTableWidgetItem(cliente_nombre))
            it_t = QTableWidgetItem(self._fmt_money(float(s.total or 0)))
            it_t.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_t.setForeground(QBrush(QColor("#fbbf24")))
            self.tbl_pendientes.setItem(row, 4, it_t)
            sale_id = int(s.id)
            btn = QPushButton("💵 Cobrar")
            btn.setObjectName("cobrarBtn")
            btn.setCursor(Qt.ArrowCursor)
            btn.setStyleSheet(
                """
                QPushButton {
                    background: #052e16; border: 1px solid #15803d;
                    border-radius: 6px; padding: 3px 10px;
                    color: #4ade80; font-weight: 700; font-size: 12px;
                }
                QPushButton:hover { background: #15803d; color: #fff; }
            """
            )
            btn.clicked.connect(lambda _, sid=sale_id: self.cobrar_pendiente(sid))
            self.tbl_pendientes.setCellWidget(row, 5, btn)
        self.tbl_pendientes.blockSignals(False)

    # ── ACCIONES ─────────────────────────────────────────
    def crear_cliente_rapido(self):
        nombre = self.txt_cliente.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Cliente", "Escribe un nombre primero.")
            return
        for c in self._clientes_cache:
            if c["nombre"].lower() == nombre.lower():
                QMessageBox.information(self, "Cliente", f"'{nombre}' ya existe.")
                return
        try:
            nuevo = crear_cliente(nombre)
            self._clientes_cache.append({"id": nuevo.id, "nombre": nuevo.nombre})
            self.cargar_clientes()
            QMessageBox.information(self, "Cliente", f"Cliente '{nombre}' creado.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def agregar_item(self):
        if self.cbo_producto.count() == 0:
            QMessageBox.warning(self, "Ventas", "No hay productos activos.")
            return
        product_id = int(self.cbo_producto.currentData())
        nombre = self.cbo_producto.currentText()
        cantidad = float(self.sp_cant.value())
        precio = float(self.sp_precio.value())
        if cantidad <= 0:
            QMessageBox.warning(self, "Ventas", "La cantidad debe ser mayor que 0.")
            return
        if precio < 0:
            QMessageBox.warning(self, "Ventas", "El precio no puede ser negativo.")
            return

        # ── Validar stock disponible ──────────────────
        idx = self.cbo_producto.currentIndex()
        if 0 <= idx < len(self._productos_cache):
            stock_disp = self._productos_cache[idx]["stock_actual"]
            # Restar lo que ya está en el formulario para este mismo producto
            ya_en_form = sum(
                i["cantidad"] for i in self.items if i["product_id"] == product_id
            )
            stock_real = stock_disp - ya_en_form
            nombre_simple = nombre.split("  (")[0]
            if cantidad > stock_real:
                stock_disp_txt = (
                    str(int(stock_real))
                    if stock_real == int(stock_real)
                    else f"{stock_real:.2f}".replace(".", ",")
                )
                ya_disp_txt = (
                    str(int(ya_en_form))
                    if ya_en_form == int(ya_en_form)
                    else f"{ya_en_form:.2f}".replace(".", ",")
                )
                QMessageBox.warning(
                    self,
                    "Stock insuficiente",
                    f"'{nombre_simple}' solo tiene {stock_disp_txt} unidad(es) disponible(s).\n"
                    f"Ya tienes {ya_disp_txt} en este pedido.",
                )
                return

        subtotal = cantidad * precio
        self.items.append(
            {"product_id": product_id, "cantidad": cantidad, "precio_venta": precio}
        )
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        self.tbl.setRowHeight(row, 30)
        self.tbl.setItem(row, 0, QTableWidgetItem(str(product_id)))
        self.tbl.setItem(row, 1, QTableWidgetItem(nombre))
        cant_txt = (
            str(int(cantidad))
            if cantidad == int(cantidad)
            else f"{cantidad:.2f}".replace(".", ",")
        )
        it_c = QTableWidgetItem(cant_txt)
        it_c.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tbl.setItem(row, 2, it_c)
        it_p = QTableWidgetItem(self._fmt_money(precio))
        it_p.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tbl.setItem(row, 3, it_p)
        it_s = QTableWidgetItem(self._fmt_money(subtotal))
        it_s.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        it_s.setForeground(QBrush(QColor("#4ade80")))
        self.tbl.setItem(row, 4, it_s)
        self.actualizar_total()

    def quitar_item(self):
        row = self.tbl.currentRow()
        if row < 0:
            return
        try:
            self.items.pop(row)
        except Exception:
            pass
        self.tbl.removeRow(row)
        self.actualizar_total()

    def actualizar_total(self):
        total = sum(float(i["cantidad"]) * float(i["precio_venta"]) for i in self.items)
        self.lbl_total.setText(f"Total: {self._fmt_money(total)}")

    def guardar_venta(self):
        if not self.items:
            QMessageBox.warning(self, "Ventas", "Agrega al menos 1 producto.")
            return
        numero_factura = self.txt_factura.text().strip()
        if not numero_factura:
            QMessageBox.warning(
                self, "Obligatorio", "El número de factura es obligatorio."
            )
            self.txt_factura.setFocus()
            return
        nombre_txt = self.txt_cliente.text().strip()
        if not nombre_txt:
            QMessageBox.warning(self, "Obligatorio", "El cliente es obligatorio.")
            self.txt_cliente.setFocus()
            return
        metodo = self.cbo_metodo.currentText()
        es_pendiente = "PENDIENTE" in self.cbo_estado_pago.currentText()
        estado_pago = "PENDIENTE" if es_pendiente else "PAGADO"
        customer_id = self._customer_id_por_nombre()
        if not customer_id:
            resp = QMessageBox.question(
                self,
                "Cliente nuevo",
                f"'{nombre_txt}' no existe.\n¿Crear cliente nuevo?",
            )
            if resp == QMessageBox.Yes:
                try:
                    nuevo = crear_cliente(nombre_txt)
                    self._clientes_cache.append(
                        {"id": nuevo.id, "nombre": nuevo.nombre}
                    )
                    customer_id = nuevo.id
                    self.cargar_clientes()
                except Exception as e:
                    QMessageBox.critical(self, "Error", str(e))
                    return
        try:
            sale = crear_venta(
                self.items,
                metodo_pago=metodo,
                customer_id=customer_id,
                estado_pago=estado_pago,
                numero_factura=numero_factura,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))
            return

        estado_txt = "⏳ Pendiente de cobro" if es_pendiente else "✅ Pagado"

        # Ofrecer imprimir recibo inmediatamente
        resp_pdf = QMessageBox.question(
            self,
            "Venta guardada ✅",
            f"Venta {sale.numero_factura or f'#{sale.id}'} guardada.\n"
            f"Total: {self._fmt_money(float(sale.total))}\n"
            f"Estado: {estado_txt}\n\n"
            f"¿Exportar recibo PDF ahora?",
        )
        if resp_pdf == QMessageBox.Yes:
            self.recibo_pdf(sale.id)

        self.items.clear()
        self.tbl.setRowCount(0)
        self.txt_cliente.clear()
        self.txt_factura.clear()
        self.actualizar_total()
        self.refrescar_todo()

    def cobrar_pendiente(self, sale_id: int):
        metodo = self.cbo_metodo.currentText()
        confirm = QMessageBox.question(
            self,
            "Cobrar fiado",
            f"¿Registrar cobro de la venta #{sale_id}?\nMétodo: {metodo}",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            registrar_pago_pendiente(sale_id, metodo_pago=metodo)
            QMessageBox.information(self, "OK", "Pago registrado y caja actualizada.")
            self.refrescar_todo()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def anular_seleccionada(self):
        row = self.tbl_hist.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ventas", "Selecciona una venta del historial.")
            return
        item = self.tbl_hist.item(row, 0)
        if not item:
            return
        sale_id = int(item.text())
        factura = (
            self.tbl_hist.item(row, 1).text()
            if self.tbl_hist.item(row, 1)
            else f"#{sale_id}"
        )
        confirm = QMessageBox.question(
            self,
            "Confirmar anulación",
            f"¿Anular la venta {factura}?\n"
            f"Esto devolverá el stock y (si estaba pagada) afectará la caja.",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            anular_venta(
                sale_id,
                motivo="Anulada desde UI",
                metodo_pago=self.cbo_metodo.currentText(),
            )
            QMessageBox.information(self, "OK", f"Venta {factura} anulada.")
            self.refrescar_todo()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def ver_detalle_venta(self, sale_id: int) -> None:
        sale = obtener_venta_con_detalle(sale_id)
        if not sale:
            QMessageBox.information(self, "Detalle", "No se encontró la venta.")
            return
        try:
            fecha_txt = sale.fecha.strftime("%d/%m/%Y  %H:%M")
        except Exception:
            fecha_txt = str(getattr(sale, "fecha", ""))

        es_anulada = getattr(sale, "anulada", False)
        es_pendiente = getattr(sale, "estado_pago", "PAGADO") == "PENDIENTE"

        if es_anulada:
            color, label_estado, emoji = "#ef4444", "ANULADA", "✕"
        elif es_pendiente:
            color, label_estado, emoji = "#f59e0b", "PENDIENTE", "⏳"
        else:
            color, label_estado, emoji = "#22c55e", "PAGADO", "✓"

        cliente_nombre = (
            sale.customer.nombre if getattr(sale, "customer", None) else "—"
        )
        factura_txt = sale.numero_factura or f"#{sale.id}"

        items_html = ""
        for d in sale.details:
            nombre = d.product.nombre if d.product else f"Producto #{d.product_id}"
            cant = float(d.cantidad or 0)
            cant_txt = (
                str(int(cant)) if cant == int(cant) else f"{cant:.2f}".replace(".", ",")
            )
            items_html += f"""
            <tr>
                <td style='padding:7px 0;color:#cbd5e1;font-size:13px;
                           border-bottom:1px solid #1e293b;'>{nombre}</td>
                <td style='padding:7px 0;color:#94a3b8;font-size:12px;
                           border-bottom:1px solid #1e293b;text-align:center;'>{cant_txt}</td>
                <td style='padding:7px 0;color:#94a3b8;font-size:12px;
                           border-bottom:1px solid #1e293b;text-align:right;'>
                    {self._fmt_money(float(d.precio_venta or 0))}</td>
                <td style='padding:7px 0;color:#4ade80;font-size:13px;font-weight:600;
                           border-bottom:1px solid #1e293b;text-align:right;'>
                    {self._fmt_money(float(d.subtotal or 0))}</td>
            </tr>"""

        metodo_pago_txt = getattr(sale, "metodo_pago", None) or "—"
        if es_anulada and getattr(sale, "anulada_en", None):
            anulada_row_html = (
                "<tr><td style='padding:6px 0;color:#475569;font-size:11px;"
                "text-transform:uppercase;letter-spacing:1px;'>Anulada el</td>"
                "<td style='padding:6px 0;color:#f87171;font-size:13px;font-weight:600;'>"
                + sale.anulada_en.strftime("%d/%m/%Y %H:%M")
                + "</td></tr>"
            )
        else:
            anulada_row_html = ""

        html = f"""
        <html><body style='margin:0;padding:0;background:#0a0f1e;
                           font-family:"Segoe UI",Arial,sans-serif;'>
        <div style='background:#0a0f1e;'>
            <div style='background:linear-gradient(135deg,{color}cc,{color}66);
                        padding:20px 28px 16px 28px;'>
                <div style='font-size:10px;color:rgba(255,255,255,0.65);letter-spacing:3px;
                            text-transform:uppercase;margin-bottom:6px;'>
                    INVENTARIO JH &nbsp;·&nbsp; Comprobante de Venta</div>
                <div style='font-size:24px;font-weight:800;color:#ffffff;'>{factura_txt}</div>
                <div style='margin-top:10px;'>
                    <span style='background:rgba(0,0,0,0.3);color:#fff;padding:3px 12px;
                                 border-radius:20px;font-size:11px;font-weight:700;
                                 letter-spacing:1.5px;'>{emoji} {label_estado}</span>
                    <span style='color:rgba(255,255,255,0.55);font-size:11px;margin-left:8px;'>
                        Cliente: {cliente_nombre}</span>
                </div>
            </div>
            <div style='background:#0f172a;padding:20px 28px;border-bottom:1px solid #1e293b;'>
                <div style='font-size:10px;color:#475569;letter-spacing:3px;
                            margin-bottom:4px;text-transform:uppercase;'>Total venta</div>
                <div style='font-size:36px;font-weight:900;color:{color};letter-spacing:-1px;'>
                    {self._fmt_money(float(sale.total or 0))}</div>
            </div>
            <div style='padding:16px 28px;border-bottom:1px solid #1e293b;'>
                <table width='100%' cellspacing='0' cellpadding='0'>
                    <tr><td style='padding:6px 0;color:#475569;font-size:11px;
                                   text-transform:uppercase;letter-spacing:1px;width:38%;'>
                            N° Factura</td>
                        <td style='padding:6px 0;color:#e2e8f0;font-size:13px;font-weight:600;'>
                            {factura_txt}</td></tr>
                    <tr><td style='padding:6px 0;color:#475569;font-size:11px;
                                   text-transform:uppercase;letter-spacing:1px;'>Fecha</td>
                        <td style='padding:6px 0;color:#e2e8f0;font-size:13px;font-weight:600;'>
                            {fecha_txt}</td></tr>
                    <tr><td style='padding:6px 0;color:#475569;font-size:11px;
                                   text-transform:uppercase;letter-spacing:1px;'>Cliente</td>
                        <td style='padding:6px 0;color:#e2e8f0;font-size:13px;font-weight:600;'>
                            {cliente_nombre}</td></tr>
                    <tr><td style='padding:6px 0;color:#475569;font-size:11px;
                                   text-transform:uppercase;letter-spacing:1px;'>M&eacute;todo pago</td>
                        <td style='padding:6px 0;color:#e2e8f0;font-size:13px;font-weight:600;'>
                            {metodo_pago_txt}</td></tr>
                    {anulada_row_html}
                </table>
            </div>
            <div style='padding:14px 28px 8px 28px;'>
                <div style='font-size:10px;color:#475569;letter-spacing:2px;
                            text-transform:uppercase;margin-bottom:10px;'>Productos</div>
                <table width='100%' cellspacing='0' cellpadding='0'>
                    <tr>
                        <th style='text-align:left;font-size:10px;color:#334155;
                                   padding-bottom:6px;border-bottom:1px solid #1e293b;'>Descripción</th>
                        <th style='text-align:center;font-size:10px;color:#334155;
                                   padding-bottom:6px;border-bottom:1px solid #1e293b;'>Cant</th>
                        <th style='text-align:right;font-size:10px;color:#334155;
                                   padding-bottom:6px;border-bottom:1px solid #1e293b;'>Precio</th>
                        <th style='text-align:right;font-size:10px;color:#334155;
                                   padding-bottom:6px;border-bottom:1px solid #1e293b;'>Subtotal</th>
                    </tr>
                    {items_html}
                </table>
            </div>
        </div></body></html>"""

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Venta {factura_txt}")
        dlg.setFixedWidth(520)
        dlg.setStyleSheet("background:#0a0f1e;")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 12)
        lay.setSpacing(0)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setHtml(html)
        txt.setStyleSheet(
            """
            QTextEdit { background:#0a0f1e; border:none; color:#e2e8f0; }
            QScrollBar:vertical { background:#0a0f1e; width:6px; }
            QScrollBar::handle:vertical { background:#334155; border-radius:3px; }
        """
        )
        txt.setMinimumHeight(480)
        lay.addWidget(txt)

        # Botones del diálogo: Cerrar + PDF
        row_btn = QHBoxLayout()
        row_btn.setContentsMargins(12, 0, 12, 0)
        row_btn.setSpacing(8)

        btn_pdf_dlg = QPushButton("🖨  Exportar PDF")
        btn_pdf_dlg.setCursor(Qt.ArrowCursor)
        btn_pdf_dlg.setStyleSheet(
            """
            QPushButton { background:#052e16; color:#4ade80; border:1px solid #15803d;
                          border-radius:6px; padding:7px 16px; font-weight:700; }
            QPushButton:hover { background:#15803d; color:#fff; }
        """
        )
        btn_pdf_dlg.clicked.connect(lambda: self.recibo_pdf(sale_id))

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedWidth(100)
        btn_cerrar.setCursor(Qt.ArrowCursor)
        btn_cerrar.setStyleSheet(
            """
            QPushButton { background:#1e3a5f; color:#e2e8f0; border:1px solid #2563eb;
                          border-radius:6px; padding:7px 0; font-weight:700; }
            QPushButton:hover { background:#2563eb; }
        """
        )
        btn_cerrar.clicked.connect(dlg.accept)

        row_btn.addWidget(btn_pdf_dlg)
        row_btn.addStretch()
        row_btn.addWidget(btn_cerrar)
        lay.addLayout(row_btn)
        dlg.exec()

    # ── RECIBO PDF ────────────────────────────────────────
    def recibo_pdf(self, sale_id: int) -> None:
        from app.ui.sale_receipt import exportar_recibo_pdf

        exportar_recibo_pdf(self, sale_id)
