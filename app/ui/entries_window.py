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
)

from app.db.entries_repo import crear_entrada
from app.db.products_repo import listar_productos
from app.db.suppliers_repo import listar_proveedores
from PySide6.QtCore import Qt


class EntriesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Entradas (Compras)")
        self.resize(950, 550)

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
        try:
            return float((s or "0").replace(",", "."))
        except Exception:
            return 0.0

    def _fmt_money(self, value: float) -> str:
        return (
            "${:,.2f}".format(value)
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

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
            item.setFlags(
                item.flags() & ~Qt.ItemIsEditable
            )  # o puedes bloquear edición aquí si quieres
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

        print("DEBUG: supplier_id =", supplier_id)
        print("DEBUG: items =", items)

        try:
            crear_entrada(supplier_id=supplier_id, items=items)
            print("DEBUG: crear_entrada ejecutada OK")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la entrada:\n{e}")
            return

        QMessageBox.information(self, "OK", "Entrada guardada. Stock actualizado.")
        self.table.setRowCount(0)
        self.agregar_fila()
        self.recalcular_totales()
