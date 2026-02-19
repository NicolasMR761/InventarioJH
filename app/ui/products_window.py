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

from app.db.products_repo import listar_productos, desactivar_producto


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

        btn_desactivar = QPushButton("Desactivar")
        btn_desactivar.clicked.connect(self.desactivar_seleccionado)
        top.addWidget(btn_desactivar)

        top.addStretch()
        layout.addLayout(top)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Código", "Nombre", "Unidad", "Precio Venta", "Activo"]
        )
        self.table.setSortingEnabled(True)  # opcional: ordenar columnas
        self.table.cellDoubleClicked.connect(self._dbl_click_editar)
        layout.addWidget(self.table)

        self._productos = []
        self.cargar_productos()

    def cargar_productos(self):
        texto = self.txt_buscar.text().strip()
        self._productos = listar_productos(texto=texto, incluir_inactivos=True)

        self.table.setRowCount(len(self._productos))

        for row, p in enumerate(self._productos):
            self.table.setItem(row, 0, QTableWidgetItem(str(p.id)))
            self.table.setItem(row, 1, QTableWidgetItem(p.codigo))
            self.table.setItem(row, 2, QTableWidgetItem(p.nombre))
            self.table.setItem(row, 3, QTableWidgetItem(p.unidad))
            self.table.setItem(row, 4, QTableWidgetItem(f"{p.precio_venta:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem("Sí" if p.activo else "No"))

        self.table.resizeColumnsToContents()

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

    def desactivar_seleccionado(self):
        p = self._get_selected_product()
        if not p:
            QMessageBox.information(
                self, "Selecciona", "Selecciona un producto primero."
            )
            return

        if not p.activo:
            QMessageBox.information(self, "Info", "Ese producto ya está desactivado.")
            return

        r = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Desactivar el producto '{p.nombre}' (código {p.codigo})?\n\n(No se borrará, solo quedará inactivo.)",
        )
        if r != QMessageBox.Yes:
            return

        try:
            desactivar_producto(p.id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo desactivar:\n{e}")
            return

        self.cargar_productos()
