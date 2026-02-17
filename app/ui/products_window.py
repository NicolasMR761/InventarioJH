from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from app.db.products_repo import listar_productos


class ProductsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Productos")
        self.resize(800, 500)

        layout = QVBoxLayout(self)

        # Barra superior (botones)
        top = QHBoxLayout()

        btn_refrescar = QPushButton("Refrescar")
        btn_refrescar.clicked.connect(self.cargar_productos)
        top.addWidget(btn_refrescar)

        btn_nuevo = QPushButton("Nuevo")
        btn_nuevo.clicked.connect(self.abrir_form_nuevo)
        top.addWidget(btn_nuevo)

        top.addStretch()
        layout.addLayout(top)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Código", "Nombre", "Unidad", "Precio Venta", "Activo"]
        )
        layout.addWidget(self.table)

        self.cargar_productos()

    def cargar_productos(self):
        productos = listar_productos()
        self.table.setRowCount(len(productos))

        for row, p in enumerate(productos):
            self.table.setItem(row, 0, QTableWidgetItem(str(p.id)))
            self.table.setItem(row, 1, QTableWidgetItem(p.codigo))
            self.table.setItem(row, 2, QTableWidgetItem(p.nombre))
            self.table.setItem(row, 3, QTableWidgetItem(p.unidad))
            self.table.setItem(row, 4, QTableWidgetItem(f"{p.precio_venta:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem("Sí" if p.activo else "No"))

        self.table.resizeColumnsToContents()

    def abrir_form_nuevo(self):
        from app.ui.product_form import ProductForm

        dlg = ProductForm(self)
        if dlg.exec():
            self.cargar_productos()
