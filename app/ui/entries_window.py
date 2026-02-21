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
)
from PySide6.QtCore import Qt

from app.db.entries_repo import crear_entrada
from app.db.products_repo import listar_productos
from app.db.suppliers_repo import listar_proveedores
from app.db.cash_repo import registrar_movimiento


class EntriesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Entradas (Compras)")
        self.resize(950, 600)

        layout = QVBoxLayout(self)

        # --- Proveedor ---
        top = QHBoxLayout()
        top.addWidget(QLabel("Proveedor:"))

        self.cbo_supplier = QComboBox()
        top.addWidget(self.cbo_supplier)

        btn_add_row = QPushButton("Agregar producto")
        btn_add_row.clicked.connect(self.agregar_fila)
        top.addWidget(btn_add_row)

        btn_remove_row = QPushButton("Quitar fila")
        btn_remove_row.clicked.connect(self.quitar_fila)
        top.addWidget(btn_remove_row)

        top.addStretch()
        layout.addLayout(top)

        # --- Pagado + Método ---
        pago = QHBoxLayout()

        self.chk_pagado = QCheckBox("Pagado (sale de caja)")
        self.chk_pagado.setChecked(True)  # por defecto, compras pagadas
        pago.addWidget(self.chk_pagado)

        pago.addWidget(QLabel("Método:"))
        self.cbo_metodo = QComboBox()
        self.cbo_metodo.addItems(
            ["Efectivo", "Transferencia", "Nequi", "Débito", "Crédito"]
        )
        pago.addWidget(self.cbo_metodo)

        pago.addStretch()
        layout.addLayout(pago)

        # --- Tabla detalle ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Producto", "Cantidad", "Precio compra", "Subtotal"]
        )
        layout.addWidget(self.table)

        # --- Total + Guardar ---
        bottom = QHBoxLayout()
        self.lbl_total = QLabel("Total: $0,00")
        bottom.addWidget(self.lbl_total)

        bottom.addStretch()

        btn_guardar = QPushButton("Guardar Entrada")
        btn_guardar.clicked.connect(self.guardar)
        bottom.addWidget(btn_guardar)

        layout.addLayout(bottom)

        # Data cache
        self._productos = []
        self._proveedores = []

        self.cargar_data()
        self.agregar_fila()

        self.table.cellChanged.connect(self.recalcular_totales)

    def cargar_data(self):
        # Solo activos para entradas
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

        cbo_prod = QComboBox()
        for p in self._productos:
            cbo_prod.addItem(f"{p.codigo} - {p.nombre}", p.id)
        cbo_prod.currentIndexChanged.connect(self.recalcular_totales)
        self.table.setCellWidget(row, 0, cbo_prod)

        self.table.setItem(row, 1, QTableWidgetItem("1"))
        self.table.setItem(row, 2, QTableWidgetItem("0"))

        item_sub = QTableWidgetItem("0.00")
        item_sub.setFlags(item_sub.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 3, item_sub)

        self.table.blockSignals(False)
        self.recalcular_totales()

    def quitar_fila(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.recalcular_totales()

    def _parse_float(self, s: str) -> float:
        """
        Permite entradas como:
        - 5000
        - 5000.5
        - 5.000
        - 5.000,50
        - $5.000,50
        """
        try:
            raw = (s or "0").strip()
            raw = raw.replace("$", "").replace(" ", "")
            raw = raw.replace(".", "")  # miles
            raw = raw.replace(",", ".")  # decimal
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
            cantidad = self._parse_float(
                self.table.item(row, 1).text() if self.table.item(row, 1) else "0"
            )
            precio = self._parse_float(
                self.table.item(row, 2).text() if self.table.item(row, 2) else "0"
            )
            total += max(cantidad, 0.0) * max(precio, 0.0)
        return total

    def recalcular_totales(self):
        self.table.blockSignals(True)  # ✅ evita el loop

        total = 0.0
        for row in range(self.table.rowCount()):
            cantidad = self._parse_float(
                self.table.item(row, 1).text() if self.table.item(row, 1) else "0"
            )
            precio = self._parse_float(
                self.table.item(row, 2).text() if self.table.item(row, 2) else "0"
            )

            subtotal = max(cantidad, 0.0) * max(precio, 0.0)
            total += subtotal

            item = QTableWidgetItem(f"{subtotal:.2f}")
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, item)

        self.lbl_total.setText(f"Total: {self._fmt_money(total)}")
        self.table.blockSignals(False)  # ✅ reactivar señales

    def guardar(self):
        supplier_id = self.cbo_supplier.currentData()
        if not supplier_id:
            QMessageBox.warning(
                self, "Falta proveedor", "Selecciona un proveedor activo."
            )
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
                    self, "Falta producto", f"Fila {row+1}: selecciona producto."
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
            QMessageBox.warning(self, "Sin items", "Agrega al menos un producto.")
            return

        total = self._total_actual()
        if total <= 0:
            QMessageBox.warning(self, "Total inválido", "El total debe ser mayor a 0.")
            return

        try:
            # 1) Crear entrada (esto suma stock y guarda detalles)
            entry = crear_entrada(
                supplier_id=supplier_id,
                items=items,
                pagado=self.chk_pagado.isChecked(),
                metodo_pago=self.cbo_metodo.currentText(),
            )

            # 2) Si está pagado, registra EGRESO en Caja
            if self.chk_pagado.isChecked():
                metodo = self.cbo_metodo.currentText()
                proveedor_txt = self.cbo_supplier.currentText()

                concepto = f"Compra (Entrada #{entry.id})"
                if proveedor_txt:
                    concepto += f" - {proveedor_txt}"

                registrar_movimiento(
                    tipo="EGRESO",
                    concepto=concepto,
                    monto=float(entry.total or total),
                    referencia=f"Entrada {entry.id}",
                    observacion=f"Método: {metodo}",
                )

            # 3) UX
            msg = f"Entrada #{entry.id} guardada. Stock actualizado."
            if self.chk_pagado.isChecked():
                msg += " Caja actualizada (EGRESO)."
            else:
                msg += " (Compra a crédito: no afecta caja)."

            QMessageBox.information(self, "OK", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la entrada:\n{e}")
            return

        # Reset
        self.table.setRowCount(0)
        self.agregar_fila()
        self.recalcular_totales()
