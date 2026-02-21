from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont

from app.db.products_repo import listar_productos, cambiar_estado_producto


class ProductsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Productos")
        self.resize(900, 520)

        layout = QVBoxLayout(self)

        # Barra superior
        top = QHBoxLayout()

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar por código o nombre...")
        self.txt_buscar.textChanged.connect(self.cargar_productos)
        top.addWidget(self.txt_buscar)

        btn_refrescar = QPushButton("Refrescar")
        btn_refrescar.clicked.connect(self.cargar_productos)
        top.addWidget(btn_refrescar)

        btn_nuevo = QPushButton("Nuevo")
        btn_nuevo.clicked.connect(self.abrir_form_nuevo)
        top.addWidget(btn_nuevo)

        btn_editar = QPushButton("Editar")
        btn_editar.clicked.connect(self.abrir_form_editar)
        top.addWidget(btn_editar)

        btn_estado = QPushButton("Activar / Desactivar")
        btn_estado.clicked.connect(self.cambiar_estado_seleccionado)
        top.addWidget(btn_estado)

        top.addStretch()
        layout.addLayout(top)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Código", "Nombre", "Unidad", "Stock", "Precio Venta", "Activo"]
        )
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self._dbl_click_editar)
        layout.addWidget(self.table)

        self._productos = []
        self.cargar_productos()

    def showEvent(self, event):
        super().showEvent(event)
        self.cargar_productos()

    def cargar_productos(self):
        texto = self.txt_buscar.text().strip()
        self._productos = listar_productos(texto=texto, incluir_inactivos=True)

        was_sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)

        self.table.setRowCount(len(self._productos))

        for row, p in enumerate(self._productos):
            stock = float(p.stock_actual or 0.0)
            minimo = float(p.stock_minimo or 0.0)

            es_bajo = minimo > 0 and stock <= minimo

            self.table.setItem(row, 0, QTableWidgetItem(str(p.id)))
            self.table.setItem(row, 1, QTableWidgetItem(p.codigo or ""))
            self.table.setItem(row, 2, QTableWidgetItem(p.nombre or ""))
            self.table.setItem(row, 3, QTableWidgetItem(p.unidad or ""))

            # Stock
            item_stock = QTableWidgetItem(f"{stock:.2f}")
            item_stock.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            if es_bajo:
                font = QFont()
                font.setBold(True)
                item_stock.setFont(font)

            self.table.setItem(row, 4, item_stock)

            # Precio
            precio_formateado = (
                "${:,.2f}".format(float(p.precio_venta or 0.0))
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            item_precio = QTableWidgetItem(precio_formateado)
            item_precio.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 5, item_precio)

            # Activo
            self.table.setItem(row, 6, QTableWidgetItem("Sí" if p.activo else "No"))

            # 🔴 Pintar fila si stock bajo
            if es_bajo:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QBrush(QColor(120, 40, 40)))
                        item.setForeground(QBrush(QColor(240, 240, 240)))

        self.table.blockSignals(False)
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(was_sorting)

    def _get_selected_product(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._productos):
            return None
        return self._productos[row]

    def abrir_form_nuevo(self):
        from app.ui.product_form import ProductForm

        dlg = ProductForm(self)
        if dlg.exec():
            self.cargar_productos()

    def abrir_form_editar(self):
        from app.ui.product_form import ProductForm

        p = self._get_selected_product()
        if not p:
            QMessageBox.information(
                self, "Selecciona", "Selecciona un producto primero."
            )
            return

        dlg = ProductForm(self, product=p)
        if dlg.exec():
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
            f"¿Cambiar estado del producto '{p.nombre}' (código {p.codigo})?\n\n"
            f"Estado actual: {'Activo' if p.activo else 'Inactivo'}",
        )
        if r != QMessageBox.Yes:
            return

        try:
            cambiar_estado_producto(p.id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cambiar estado:\n{e}")
            return

        self.cargar_productos()
