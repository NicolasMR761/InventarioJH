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

from app.db.suppliers_repo import listar_proveedores, cambiar_estado_proveedor


class SuppliersWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proveedores")
        self.resize(960, 560)
        self.setStyleSheet(self._styles())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # ── HEADER ──────────────────────────────────────────
        lbl_title = QLabel("🏭 Proveedores")
        lbl_title.setObjectName("pageTitle")
        lbl_sub = QLabel("Gestión de proveedores activos e inactivos")
        lbl_sub.setObjectName("pageSub")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # ── BARRA DE ACCIONES ────────────────────────────────
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍  Buscar por nombre o NIT…")
        self.txt_buscar.setObjectName("searchBox")
        self.txt_buscar.textChanged.connect(self.cargar_proveedores)
        bar.addWidget(self.txt_buscar, 1)

        for label, obj_name, slot in [
            ("↺  Refrescar", "btnSecondary", self.cargar_proveedores),
            ("＋  Nuevo", "btnPrimary", self.abrir_form_nuevo),
            ("✎  Editar", "btnSecondary", self.abrir_form_editar),
            ("⏺  Activar/Desact.", "btnWarning", self.cambiar_estado_seleccionado),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj_name)
            btn.clicked.connect(slot)
            bar.addWidget(btn)

        layout.addLayout(bar)

        # ── SEPARADOR ───────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        layout.addWidget(sep)

        # ── TABLA ───────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setObjectName("mainTable")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "NIT", "Teléfono", "Dirección", "Estado"]
        )
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self._dbl_click_editar)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)  # ID
        hh.setSectionResizeMode(1, QHeaderView.Stretch)  # Nombre
        hh.setSectionResizeMode(2, QHeaderView.Fixed)  # NIT
        hh.setSectionResizeMode(3, QHeaderView.Fixed)  # Teléfono
        hh.setSectionResizeMode(4, QHeaderView.Fixed)  # Dirección
        hh.setSectionResizeMode(5, QHeaderView.Fixed)  # Estado
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 160)
        self.table.setColumnWidth(5, 110)

        layout.addWidget(self.table, 1)

        # ── FOOTER ──────────────────────────────────────────
        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("footerLabel")
        layout.addWidget(self.lbl_count)

        self._proveedores = []
        self.cargar_proveedores()

    def _styles(self) -> str:
        return """
        QWidget {
            background: #0b1120;
            color: #e2e8f0;
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 13px;
        }
        #pageTitle {
            font-size: 20px;
            font-weight: 800;
            color: #f1f5f9;
            letter-spacing: -0.3px;
        }
        #pageSub {
            font-size: 12px;
            color: #475569;
        }
        #searchBox {
            background: #111c33;
            border: 1px solid #1e3a5f;
            border-radius: 8px;
            padding: 7px 12px;
            color: #e2e8f0;
            font-size: 13px;
            min-height: 32px;
        }
        #searchBox:focus { border: 1px solid #3b82f6; }

        #btnPrimary {
            background: #2563eb;
            border: none;
            border-radius: 8px;
            padding: 7px 16px;
            font-weight: 700;
            color: white;
            min-height: 32px;
        }
        #btnPrimary:hover { background: #1d4ed8; }

        #btnSecondary {
            background: #111c33;
            border: 1px solid #1e3a5f;
            border-radius: 8px;
            padding: 7px 14px;
            font-weight: 600;
            color: #94a3b8;
            min-height: 32px;
        }
        #btnSecondary:hover { border-color: #3b82f6; color: #e2e8f0; }

        #btnWarning {
            background: #111c33;
            border: 1px solid #854d0e;
            border-radius: 8px;
            padding: 7px 14px;
            font-weight: 600;
            color: #fbbf24;
            min-height: 32px;
        }
        #btnWarning:hover { background: #1c1408; border-color: #fbbf24; }

        #separator {
            border: none;
            border-top: 1px solid #1e293b;
        }

        #mainTable {
            background: #0b1120;
            alternate-background-color: #0f1a2e;
            border: 1px solid #1e293b;
            border-radius: 10px;
            gridline-color: #1e293b;
            selection-background-color: #1e3a5f;
            selection-color: #f1f5f9;
            outline: none;
        }
        #mainTable QHeaderView::section {
            background: #111c33;
            color: #475569;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            padding: 8px 12px;
            border: none;
            border-bottom: 2px solid #1e293b;
        }
        #mainTable::item { padding: 6px 12px; border: none; }
        #mainTable::item:selected { background: #1e3a5f; color: #f1f5f9; }

        QScrollBar:vertical {
            background: #0b1120; width: 6px; border-radius: 3px;
        }
        QScrollBar::handle:vertical {
            background: #1e3a5f; border-radius: 3px;
        }
        #footerLabel { font-size: 11px; color: #334155; }
        """

    def keyPressEvent(self, event):
        from PySide6.QtCore import Qt

        key = event.key()
        mod = event.modifiers()
        if key == Qt.Key_F5:
            self.cargar_proveedores()
        elif key == Qt.Key_Escape:
            self.close()
        elif key == Qt.Key_N and mod == Qt.ControlModifier:
            self.abrir_form_nuevo()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.cargar_proveedores()

    def cargar_proveedores(self):
        texto = self.txt_buscar.text().strip()
        self._proveedores = listar_proveedores(texto=texto, incluir_inactivos=True)

        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._proveedores))

        activos = 0
        for row, p in enumerate(self._proveedores):
            self.table.setRowHeight(row, 34)
            es_activo = bool(p.activo)
            if es_activo:
                activos += 1

            def cell(text, align=Qt.AlignLeft | Qt.AlignVCenter):
                it = QTableWidgetItem(str(text or ""))
                it.setTextAlignment(int(align))
                return it

            self.table.setItem(
                row, 0, cell(str(p.id), Qt.AlignCenter | Qt.AlignVCenter)
            )
            self.table.setItem(row, 1, cell(p.nombre or ""))
            self.table.setItem(row, 2, cell(p.nit or "—"))
            self.table.setItem(row, 3, cell(p.telefono or "—"))
            self.table.setItem(row, 4, cell(p.direccion or "—"))

            it_estado = cell(
                "● Activo" if es_activo else "○ Inactivo",
                Qt.AlignCenter | Qt.AlignVCenter,
            )
            it_estado.setForeground(
                QBrush(QColor("#4ade80") if es_activo else QColor("#475569"))
            )
            self.table.setItem(row, 5, it_estado)

            # Inactivo → texto apagado
            if not es_activo:
                for col in range(self.table.columnCount()):
                    it = self.table.item(row, col)
                    if it and col != 5:
                        it.setForeground(QBrush(QColor("#334155")))

        self.table.blockSignals(False)
        self.table.setSortingEnabled(True)

        total = len(self._proveedores)
        inactivos = total - activos
        parts = [f"{total} proveedores", f"{activos} activos"]
        if inactivos:
            parts.append(f"{inactivos} inactivos")
        self.lbl_count.setText("  ·  ".join(parts))

    def _get_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._proveedores):
            return None
        return self._proveedores[row]

    def abrir_form_nuevo(self):
        from app.ui.supplier_form import SupplierForm

        if SupplierForm(self).exec():
            self.cargar_proveedores()

    def abrir_form_editar(self):
        from app.ui.supplier_form import SupplierForm

        p = self._get_selected()
        if not p:
            QMessageBox.information(
                self, "Selecciona", "Selecciona un proveedor primero."
            )
            return
        if SupplierForm(self, supplier=p).exec():
            self.cargar_proveedores()

    def _dbl_click_editar(self, row, col):
        self.abrir_form_editar()

    def cambiar_estado_seleccionado(self):
        p = self._get_selected()
        if not p:
            QMessageBox.information(
                self, "Selecciona", "Selecciona un proveedor primero."
            )
            return
        r = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Cambiar estado de '{p.nombre}'?\n"
            f"Estado actual: {'Activo' if p.activo else 'Inactivo'}",
        )
        if r != QMessageBox.Yes:
            return
        try:
            cambiar_estado_proveedor(p.id)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.cargar_proveedores()
