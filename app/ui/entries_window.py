from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QCheckBox,
    QLineEdit,
    QFrame,
    QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont

from app.db.entries_repo import crear_entrada
from app.db.products_repo import listar_productos
from app.db.suppliers_repo import listar_proveedores


class EntriesWindow(QWidget):
    def __init__(self):
        super().__init__()
        try:
            from app.main import get_icon

            if get_icon():
                self.setWindowIcon(get_icon())
        except Exception:
            pass
        self.setWindowTitle("Entradas (Compras)")
        self.resize(980, 640)
        self.setStyleSheet(self._styles())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # ── HEADER ──────────────────────────────────────────
        lbl_title = QLabel("🧾 Entradas (Compras)")
        lbl_title.setObjectName("pageTitle")
        lbl_sub = QLabel(
            "Registra compras a proveedores · Actualiza stock automáticamente"
        )
        lbl_sub.setObjectName("pageSub")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        sep0 = QFrame()
        sep0.setFrameShape(QFrame.HLine)
        sep0.setObjectName("separator")
        layout.addWidget(sep0)

        # ── FILA 1: Proveedor + botones ──────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        lbl_prov = QLabel("Proveedor:")
        lbl_prov.setObjectName("fieldLabel")
        row1.addWidget(lbl_prov)

        self.cbo_supplier = QComboBox()
        self.cbo_supplier.setObjectName("combo")
        self.cbo_supplier.setMinimumWidth(240)
        row1.addWidget(self.cbo_supplier)

        row1.addSpacing(16)

        btn_add = QPushButton("＋  Agregar fila")
        btn_add.setObjectName("btnPrimary")
        btn_add.clicked.connect(self.agregar_fila)
        row1.addWidget(btn_add)

        btn_del = QPushButton("✕  Quitar fila")
        btn_del.setObjectName("btnSecondary")
        btn_del.clicked.connect(self.quitar_fila)
        row1.addWidget(btn_del)

        row1.addStretch()
        layout.addLayout(row1)

        # ── FILA 2: N° Factura ──────────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        lbl_fac = QLabel("N° Factura:")
        lbl_fac.setObjectName("fieldLabel")
        row2.addWidget(lbl_fac)

        self.txt_factura = QLineEdit()
        self.txt_factura.setObjectName("inputField")
        self.txt_factura.setPlaceholderText(
            "Número de factura del proveedor (obligatorio)"
        )
        self.txt_factura.setMinimumWidth(280)
        self.txt_factura.setMaximumWidth(320)
        row2.addWidget(self.txt_factura)
        row2.addStretch()
        layout.addLayout(row2)

        # ── FILA 3: Pago + Método ───────────────────────────
        row3 = QHBoxLayout()
        row3.setSpacing(16)

        self.chk_pagado = QCheckBox("¿Registrar pago en caja?")
        self.chk_pagado.setObjectName("chkPagado")
        self.chk_pagado.setChecked(True)
        row3.addWidget(self.chk_pagado)

        self.lbl_pago_hint = QLabel("✅ Se descontará de caja al guardar")
        self.lbl_pago_hint.setObjectName("hintPago")
        row3.addWidget(self.lbl_pago_hint)

        lbl_met = QLabel("Método:")
        lbl_met.setObjectName("fieldLabel")
        row3.addWidget(lbl_met)

        self.cbo_metodo = QComboBox()
        self.cbo_metodo.setObjectName("combo")
        self.cbo_metodo.addItems(
            ["Efectivo", "Transferencia", "Nequi", "Débito", "Crédito"]
        )
        self.cbo_metodo.setMinimumWidth(140)
        row3.addWidget(self.cbo_metodo)

        row3.addStretch()
        layout.addLayout(row3)

        self.chk_pagado.toggled.connect(self._toggle_metodo_pago)
        self._toggle_metodo_pago(True)
        self.chk_pagado.toggled.connect(self._update_hint)

        # ── SEPARADOR ───────────────────────────────────────
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setObjectName("separator")
        layout.addWidget(sep1)

        # ── TABLA ───────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setObjectName("entryTable")
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Producto", "Cantidad", "Precio compra", "Subtotal"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 140)

        layout.addWidget(self.table, 1)

        # ── FOOTER: total + guardar ─────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("separator")
        layout.addWidget(sep2)

        footer = QHBoxLayout()
        footer.setSpacing(12)

        self.lbl_total = QLabel("Total: $0,00")
        self.lbl_total.setObjectName("totalLabel")
        footer.addWidget(self.lbl_total)

        footer.addStretch()

        btn_guardar = QPushButton("💾  Guardar Entrada")
        btn_guardar.setObjectName("btnSuccess")
        btn_guardar.clicked.connect(self.guardar)
        footer.addWidget(btn_guardar)

        layout.addLayout(footer)

        # ── DATA ────────────────────────────────────────────
        self._productos = []
        self._proveedores = []
        self.cargar_data()
        self.agregar_fila()
        self.table.cellChanged.connect(self.recalcular_totales)

    # ── ESTILOS ──────────────────────────────────────────────
    def _styles(self) -> str:
        return """
        QWidget {
            background: #0b1120;
            color: #e2e8f0;
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 13px;
        }
        #pageTitle {
            font-size: 20px; font-weight: 800;
            color: #f1f5f9; letter-spacing: -0.3px;
        }
        #pageSub { font-size: 12px; color: #475569; }

        #fieldLabel { color: #64748b; font-size: 12px; font-weight: 600; }

        #inputField {
            background: #111c33;
            border: 1px solid #1e3a5f;
            border-radius: 8px;
            padding: 7px 12px;
            color: #e2e8f0;
            min-height: 30px;
        }
        #inputField:focus { border-color: #3b82f6; }

        #combo {
            background: #111c33;
            border: 1px solid #1e3a5f;
            border-radius: 8px;
            padding: 5px 10px;
            color: #e2e8f0;
            min-height: 30px;
        }
        #combo:focus { border-color: #3b82f6; }
        QComboBox::drop-down { border: none; width: 20px; }
        QComboBox QAbstractItemView {
            background: #111c33;
            border: 1px solid #1e3a5f;
            color: #e2e8f0;
            selection-background-color: #1e3a5f;
        }



        #btnPrimary {
            background: #2563eb; border: none;
            border-radius: 8px; padding: 7px 16px;
            font-weight: 700; color: white; min-height: 32px;
        }
        #btnPrimary:hover { background: #1d4ed8; }

        #btnSecondary {
            background: #111c33; border: 1px solid #1e3a5f;
            border-radius: 8px; padding: 7px 14px;
            font-weight: 600; color: #94a3b8; min-height: 32px;
        }
        #btnSecondary:hover { border-color: #ef4444; color: #f87171; }

        #btnSuccess {
            background: #16a34a; border: none;
            border-radius: 8px; padding: 8px 22px;
            font-weight: 700; color: white; min-height: 34px;
            font-size: 14px;
        }
        #btnSuccess:hover { background: #15803d; }

        #separator { border: none; border-top: 1px solid #1e293b; }

        #entryTable {
            background: #0b1120;
            alternate-background-color: #0f1a2e;
            border: 1px solid #1e293b;
            border-radius: 10px;
            gridline-color: #1e293b;
            selection-background-color: #1e3a5f;
            selection-color: #f1f5f9;
            outline: none;
        }
        #entryTable QHeaderView::section {
            background: #111c33;
            color: #475569;
            font-size: 11px; font-weight: 700;
            letter-spacing: 1px; text-transform: uppercase;
            padding: 8px 12px;
            border: none; border-bottom: 2px solid #1e293b;
        }
        #entryTable::item { padding: 6px 12px; border: none; }
        #entryTable::item:selected { background: #1e3a5f; }

        QScrollBar:vertical {
            background: #0b1120; width: 6px; border-radius: 3px;
        }
        QScrollBar::handle:vertical { background: #1e3a5f; border-radius: 3px; }

        #totalLabel {
            font-size: 16px; font-weight: 800;
            color: #4ade80; letter-spacing: -0.3px;
        }

        #hintPago {
            font-size: 11px; color: #4ade80;
            background: #052e16;
            border: 1px solid #166534;
            border-radius: 6px;
            padding: 3px 10px;
        }
        #hintPagoOff {
            font-size: 11px; color: #fbbf24;
            background: #1c1408;
            border: 1px solid #854d0e;
            border-radius: 6px;
            padding: 3px 10px;
        }

        #chkPagado {
            color: #e2e8f0;
            font-weight: 600;
            font-size: 13px;
            spacing: 8px;
        }
        #chkPagado::indicator {
            width: 18px; height: 18px;
            border: 2px solid #334155;
            border-radius: 5px;
            background: #0b1120;
        }
        #chkPagado::indicator:hover {
            border-color: #3b82f6;
        }
        #chkPagado::indicator:checked {
            background: #2563eb;
            border-color: #2563eb;
            image: url(none);
        }
        """

    # ── LÓGICA ───────────────────────────────────────────────
    def _toggle_metodo_pago(self, checked: bool):
        self.cbo_metodo.setEnabled(bool(checked))

    def _update_hint(self, checked: bool):
        if checked:
            self.lbl_pago_hint.setText("✅ Se descontará de caja al guardar")
            self.lbl_pago_hint.setObjectName("hintPago")
        else:
            self.lbl_pago_hint.setText("⏳ Compra a crédito · no afecta caja")
            self.lbl_pago_hint.setObjectName("hintPagoOff")
        # Re-apply style
        self.lbl_pago_hint.style().unpolish(self.lbl_pago_hint)
        self.lbl_pago_hint.style().polish(self.lbl_pago_hint)

    def keyPressEvent(self, event):
        from PySide6.QtCore import Qt

        key = event.key()
        mod = event.modifiers()
        if key == Qt.Key_F5:
            self.cargar_data()
        elif key == Qt.Key_Escape:
            self.close()
        elif key == Qt.Key_S and mod == Qt.ControlModifier:
            self.guardar()
        else:
            super().keyPressEvent(event)

    def cargar_data(self):
        self._proveedores = [
            s for s in listar_proveedores("", incluir_inactivos=True) if s.activo
        ]
        self.cbo_supplier.clear()
        for s in self._proveedores:
            self.cbo_supplier.addItem(f"{s.nombre}  ({s.nit or 'sin NIT'})", s.id)

        self._productos = [
            p for p in listar_productos("", incluir_inactivos=True) if p.activo
        ]

    def agregar_fila(self):
        self.table.blockSignals(True)
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 36)

        cbo_prod = QComboBox()
        cbo_prod.setStyleSheet(
            """
            QComboBox {
                background: #0f1a2e; border: none;
                color: #e2e8f0; padding: 4px 8px;
                font-size: 13px;
            }
            QComboBox::drop-down { border: none; width: 18px; }
            QComboBox QAbstractItemView {
                background: #111c33; border: 1px solid #1e3a5f;
                color: #e2e8f0; selection-background-color: #1e3a5f;
            }
        """
        )
        for p in self._productos:
            unidad = (p.unidad or "und").strip()
            cbo_prod.addItem(f"{p.codigo} — {p.nombre}  [{unidad}]", p.id)
        cbo_prod.currentIndexChanged.connect(self.recalcular_totales)
        self.table.setCellWidget(row, 0, cbo_prod)

        for col, val in [(1, "1"), (2, "0")]:
            it = QTableWidgetItem(val)
            it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, col, it)

        item_sub = QTableWidgetItem("$0,00")
        item_sub.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item_sub.setFlags(item_sub.flags() & ~Qt.ItemIsEditable)
        item_sub.setForeground(QBrush(QColor("#4ade80")))
        self.table.setItem(row, 3, item_sub)

        self.table.blockSignals(False)
        self.recalcular_totales()

    def quitar_fila(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.recalcular_totales()

    def _parse_float(self, s: str) -> float:
        try:
            raw = (s or "0").strip().replace("$", "").replace(" ", "")
            if not raw:
                return 0.0
            has_dot = "." in raw
            has_comma = "," in raw
            if has_dot and has_comma:
                if raw.rfind(",") > raw.rfind("."):
                    raw = raw.replace(".", "").replace(",", ".")
                else:
                    raw = raw.replace(",", "")
            elif has_comma:
                raw = raw.replace(",", ".")
            elif has_dot:
                parts = raw.split(".")
                if (
                    len(parts) == 2
                    and len(parts[1]) == 3
                    and parts[0].isdigit()
                    and parts[1].isdigit()
                ):
                    raw = raw.replace(".", "")
            return float(raw)
        except Exception:
            return 0.0

    def _fmt_money(self, value: float) -> str:
        return (
            "${:,.2f}".format(value)
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    def _total_actual(self) -> float:
        total = 0.0
        for row in range(self.table.rowCount()):
            c = self._parse_float(
                self.table.item(row, 1).text() if self.table.item(row, 1) else "0"
            )
            p = self._parse_float(
                self.table.item(row, 2).text() if self.table.item(row, 2) else "0"
            )
            total += max(c, 0.0) * max(p, 0.0)
        return total

    def recalcular_totales(self):
        self.table.blockSignals(True)
        total = 0.0
        for row in range(self.table.rowCount()):
            c = self._parse_float(
                self.table.item(row, 1).text() if self.table.item(row, 1) else "0"
            )
            p = self._parse_float(
                self.table.item(row, 2).text() if self.table.item(row, 2) else "0"
            )
            subtotal = max(c, 0.0) * max(p, 0.0)
            total += subtotal

            item = QTableWidgetItem(self._fmt_money(subtotal))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setForeground(QBrush(QColor("#4ade80")))
            self.table.setItem(row, 3, item)

        self.lbl_total.setText(f"Total: {self._fmt_money(total)}")
        self.table.blockSignals(False)

    def guardar(self):
        supplier_id = self.cbo_supplier.currentData()
        if not supplier_id:
            QMessageBox.warning(
                self, "Falta proveedor", "Selecciona un proveedor activo."
            )
            return

        numero_factura = self.txt_factura.text().strip()
        if not numero_factura:
            QMessageBox.warning(
                self, "Campo obligatorio", "El número de factura es obligatorio."
            )
            self.txt_factura.setFocus()
            return

        items = []
        for row in range(self.table.rowCount()):
            cbo = self.table.cellWidget(row, 0)
            if not cbo:
                continue
            product_id = cbo.currentData()
            cantidad = self._parse_float(
                self.table.item(row, 1).text() if self.table.item(row, 1) else "0"
            )
            precio = self._parse_float(
                self.table.item(row, 2).text() if self.table.item(row, 2) else "0"
            )

            if not product_id:
                QMessageBox.warning(
                    self, "Falta producto", f"Fila {row+1}: selecciona un producto."
                )
                return
            if cantidad <= 0:
                QMessageBox.warning(
                    self, "Cantidad inválida", f"Fila {row+1}: cantidad debe ser > 0."
                )
                return
            if precio < 0:
                QMessageBox.warning(
                    self,
                    "Precio inválido",
                    f"Fila {row+1}: precio no puede ser negativo.",
                )
                return

            items.append(
                {
                    "product_id": product_id,
                    "cantidad": cantidad,
                    "precio_compra": precio,
                }
            )

        if not items:
            QMessageBox.warning(self, "Sin ítems", "Agrega al menos un producto.")
            return
        if self._total_actual() <= 0:
            QMessageBox.warning(self, "Total inválido", "El total debe ser mayor a $0.")
            return

        try:
            entry = crear_entrada(
                supplier_id=supplier_id,
                items=items,
                pagado=self.chk_pagado.isChecked(),
                metodo_pago=self.cbo_metodo.currentText(),
                numero_factura=numero_factura,
            )
            msg = f"✅ Entrada #{entry.id} guardada · Stock actualizado."
            if self.chk_pagado.isChecked():
                msg += "\nEGRESO registrado en caja."
            else:
                msg += "\nCompra a crédito · no afecta caja."
            QMessageBox.information(self, "Entrada guardada", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la entrada:\n{e}")
            return

        self.txt_factura.clear()
        self.table.setRowCount(0)
        self.agregar_fila()
        self.recalcular_totales()
