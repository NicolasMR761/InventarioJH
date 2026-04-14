from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QMessageBox,
    QLabel,
    QHeaderView,
    QFrame,
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QBrush, QFont

from app.db.products_repo import (
    listar_productos,
    cambiar_estado_producto,
    eliminar_producto,
    desactivar_producto,
)
from app.utils.formatters import fmt_qty


class ProductsWindow(QWidget):
    def __init__(self):
        super().__init__()
        try:
            from app.main import get_icon

            if get_icon():
                self.setWindowIcon(get_icon())
        except Exception:
            pass
        self.setWindowTitle("Productos")
        self.resize(960, 580)
        self.setStyleSheet(self._styles())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # ── HEADER ──────────────────────────────────────────
        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        lbl_title = QLabel("📦 Productos")
        lbl_title.setObjectName("pageTitle")
        lbl_sub = QLabel("Catálogo de productos · Stock en tiempo real")
        lbl_sub.setObjectName("pageSub")
        title_block.addWidget(lbl_title)
        title_block.addWidget(lbl_sub)
        header.addLayout(title_block, 1)
        layout.addLayout(header)

        # ── BARRA DE ACCIONES ────────────────────────────────
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍  Buscar por código o nombre…")
        self.txt_buscar.setObjectName("searchBox")
        self.txt_buscar.textChanged.connect(self.cargar_productos)
        bar.addWidget(self.txt_buscar, 1)

        for label, obj_name, slot in [
            ("↺  Refrescar", "btnSecondary", self.cargar_productos),
            ("＋  Nuevo", "btnPrimary", self.abrir_form_nuevo),
            ("✎  Editar", "btnSecondary", self.abrir_form_editar),
            ("⏺  Activar/Desact.", "btnWarning", self.cambiar_estado_seleccionado),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj_name)
            btn.clicked.connect(slot)
            bar.addWidget(btn)

        btn_eliminar = QPushButton("🗑  Eliminar")
        btn_eliminar.setObjectName("btnDanger")
        btn_eliminar.clicked.connect(self.eliminar_seleccionado)
        bar.addWidget(btn_eliminar)

        layout.addLayout(bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        layout.addWidget(sep)

        # ── TABLA ───────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setObjectName("productTable")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Código", "Nombre", "Unidad", "Stock", "Estado"]
        )
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self._dbl_click_editar)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        hh.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 110)

        layout.addWidget(self.table, 1)

        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("footerLabel")
        layout.addWidget(self.lbl_count)

        self._productos = []
        self.cargar_productos()

    def _styles(self) -> str:
        return """
        QWidget { background: #0b1120; color: #e2e8f0; font-family: "Segoe UI", Arial, sans-serif; font-size: 13px; }
        #pageTitle { font-size: 20px; font-weight: 800; color: #f1f5f9; letter-spacing: -0.3px; }
        #pageSub { font-size: 12px; color: #475569; }
        #searchBox { background: #111c33; border: 1px solid #1e3a5f; border-radius: 8px; padding: 7px 12px; color: #e2e8f0; font-size: 13px; min-height: 32px; }
        #searchBox:focus { border: 1px solid #3b82f6; }
        #btnPrimary { background: #2563eb; border: none; border-radius: 8px; padding: 7px 16px; font-weight: 700; color: white; min-height: 32px; }
        #btnPrimary:hover { background: #1d4ed8; }
        #btnSecondary { background: #111c33; border: 1px solid #1e3a5f; border-radius: 8px; padding: 7px 14px; font-weight: 600; color: #94a3b8; min-height: 32px; }
        #btnSecondary:hover { border-color: #3b82f6; color: #e2e8f0; }
        #btnWarning { background: #111c33; border: 1px solid #854d0e; border-radius: 8px; padding: 7px 14px; font-weight: 600; color: #fbbf24; min-height: 32px; }
        #btnWarning:hover { background: #1c1408; border-color: #fbbf24; }
        #btnDanger { background: #2d0a0a; border: 1px solid #991b1b; border-radius: 8px; padding: 7px 14px; font-weight: 600; color: #f87171; min-height: 32px; }
        #btnDanger:hover { background: #991b1b; color: #fff; }
        #separator { border: none; border-top: 1px solid #1e293b; margin: 0; }
        #productTable { background: #0b1120; alternate-background-color: #0f1a2e; border: 1px solid #1e293b; border-radius: 10px; gridline-color: #1e293b; selection-background-color: #1e3a5f; selection-color: #f1f5f9; outline: none; }
        #productTable QHeaderView::section { background: #111c33; color: #475569; font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; padding: 8px 12px; border: none; border-bottom: 2px solid #1e293b; }
        #productTable::item { padding: 6px 12px; border: none; }
        #productTable::item:selected { background: #1e3a5f; color: #f1f5f9; }
        QScrollBar:vertical { background: #0b1120; width: 6px; border-radius: 3px; }
        QScrollBar::handle:vertical { background: #1e3a5f; border-radius: 3px; }
        #footerLabel { font-size: 11px; color: #334155; }
        """

    def keyPressEvent(self, event):
        key = event.key()
        mod = event.modifiers()
        if key == Qt.Key_F5:
            self.cargar_productos()
        elif key == Qt.Key_Escape:
            self.close()
        elif key == Qt.Key_N and mod == Qt.ControlModifier:
            self.abrir_form_nuevo()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.cargar_productos()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange and self.isActiveWindow():
            self.cargar_productos()

    def cargar_productos(self):
        texto = self.txt_buscar.text().strip()
        self._productos = listar_productos(texto=texto, incluir_inactivos=True)

        was_sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._productos))

        activos = stock_bajo = 0

        for row, p in enumerate(self._productos):
            stock = float(p.stock_actual or 0.0)
            minimo = float(p.stock_minimo or 0.0)
            es_bajo = minimo > 0 and stock <= minimo
            es_activo = bool(p.activo)

            if es_activo:
                activos += 1
            if es_bajo:
                stock_bajo += 1

            self.table.setRowHeight(row, 34)

            def cell(text, align=Qt.AlignLeft | Qt.AlignVCenter):
                it = QTableWidgetItem(str(text))
                it.setTextAlignment(int(align))
                return it

            self.table.setItem(
                row, 0, cell(str(p.id), Qt.AlignCenter | Qt.AlignVCenter)
            )
            self.table.setItem(row, 1, cell(p.codigo or ""))
            self.table.setItem(row, 2, cell(p.nombre or ""))

            unidad_txt = (p.unidad or "und").strip()
            it_unidad = cell(unidad_txt, Qt.AlignCenter | Qt.AlignVCenter)
            if unidad_txt.lower() == "kg":
                it_unidad.setForeground(QBrush(QColor("#38bdf8")))
                fu = QFont()
                fu.setBold(True)
                it_unidad.setFont(fu)
            self.table.setItem(row, 3, it_unidad)

            it_stock = cell(fmt_qty(stock), Qt.AlignRight | Qt.AlignVCenter)
            if es_bajo:
                it_stock.setForeground(QBrush(QColor("#f87171")))
                f2 = QFont()
                f2.setBold(True)
                it_stock.setFont(f2)
            else:
                it_stock.setForeground(QBrush(QColor("#4ade80")))
            self.table.setItem(row, 4, it_stock)

            it_estado = cell(
                "● Activo" if es_activo else "○ Inactivo",
                Qt.AlignCenter | Qt.AlignVCenter,
            )
            it_estado.setForeground(
                QBrush(QColor("#4ade80") if es_activo else QColor("#475569"))
            )
            self.table.setItem(row, 5, it_estado)

            if es_bajo:
                for col in range(self.table.columnCount()):
                    it = self.table.item(row, col)
                    if it:
                        it.setBackground(QBrush(QColor(120, 30, 30, 80)))

            if not es_activo:
                for col in range(self.table.columnCount()):
                    it = self.table.item(row, col)
                    if it and col != 5:
                        it.setForeground(QBrush(QColor("#334155")))

        self.table.blockSignals(False)
        self.table.setSortingEnabled(was_sorting)

        parts = [f"{len(self._productos)} productos"]
        if stock_bajo:
            parts.append(f"⚠ {stock_bajo} con stock bajo")
        self.lbl_count.setText("  ·  ".join(parts))

    def _get_selected_product(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._productos):
            return None
        return self._productos[row]

    def abrir_form_nuevo(self):
        from app.ui.product_form import ProductForm

        if ProductForm(self).exec():
            self.cargar_productos()

    def abrir_form_editar(self):
        from app.ui.product_form import ProductForm

        p = self._get_selected_product()
        if not p:
            QMessageBox.information(
                self, "Selecciona", "Selecciona un producto primero."
            )
            return
        if ProductForm(self, product=p).exec():
            self.cargar_productos()

    def _dbl_click_editar(self, row, col):
        self.abrir_form_editar()

    def cambiar_estado_seleccionado(self):
        p = self._get_selected_product()
        if not p:
            QMessageBox.information(
                self, "Selecciona", "Selecciona un producto primero."
            )
            return
        r = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Cambiar estado de '{p.nombre}'?\nEstado actual: {'Activo' if p.activo else 'Inactivo'}",
        )
        if r != QMessageBox.Yes:
            return
        try:
            cambiar_estado_producto(p.id)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.cargar_productos()

    def eliminar_seleccionado(self):
        p = self._get_selected_product()
        if not p:
            QMessageBox.information(
                self, "Selecciona", "Selecciona un producto primero."
            )
            return

        resp = QMessageBox.question(
            self,
            "Eliminar producto",
            f"¿Eliminar <b>{p.nombre}</b> del catálogo?<br><br>"
            f"El historial de ventas y entradas no se verá afectado.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        try:
            eliminar_producto(p.id, forzar=True)
            self.cargar_productos()
            QMessageBox.information(
                self, "Eliminado", f"'{p.nombre}' eliminado del catálogo."
            )
        except ValueError as e:
            msg = str(e)
            # Si el error es por dependencias, ofrecer desactivar como alternativa
            if "registros asociados" in msg:
                respuesta = QMessageBox.question(
                    self,
                    "No se puede eliminar",
                    f"{msg}\n\n¿Deseas desactivarlo en su lugar?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if respuesta == QMessageBox.Yes:
                    try:
                        desactivar_producto(p.id)
                        self.cargar_productos()
                        QMessageBox.information(
                            self,
                            "Desactivado",
                            f"'{p.nombre}' ha sido desactivado.",
                        )
                    except Exception as e2:
                        QMessageBox.critical(self, "Error", str(e2))
            else:
                QMessageBox.warning(self, "No se pudo eliminar", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
