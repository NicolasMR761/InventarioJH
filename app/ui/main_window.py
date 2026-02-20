from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton
from app.db.database import init_db


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventario JH - Offline")
        self.resize(900, 500)

        init_db()

        root = QWidget()
        layout = QVBoxLayout(root)

        titulo = QLabel("Sistema de Inventario JH")
        layout.addWidget(titulo)

        # --- Botón Productos ---
        btn_productos = QPushButton("Gestionar Productos")
        btn_productos.clicked.connect(self.abrir_productos)
        layout.addWidget(btn_productos)

        # --- Botón Proveedores ---
        btn_proveedores = QPushButton("Gestionar Proveedores")
        btn_proveedores.clicked.connect(self.abrir_proveedores)
        layout.addWidget(btn_proveedores)

        # --- Botón Entradas ---
        btn_entradas = QPushButton("Entradas (Compras)")
        btn_entradas.clicked.connect(self.abrir_entradas)
        layout.addWidget(btn_entradas)

        # --- Botón Ventas ---
        btn_ventas = QPushButton("Ventas")
        btn_ventas.clicked.connect(self.abrir_ventas)
        layout.addWidget(btn_ventas)

        self.setCentralWidget(root)

    # ---------------- MÉTODOS ----------------

    def abrir_productos(self):
        from app.ui.products_window import ProductsWindow

        self.win_productos = ProductsWindow()
        self.win_productos.show()

    def abrir_proveedores(self):
        from app.ui.suppliers_window import SuppliersWindow

        self.win_suppliers = SuppliersWindow()
        self.win_suppliers.show()

    def abrir_entradas(self):
        from app.ui.entries_window import EntriesWindow

        self.win_entries = EntriesWindow()
        self.win_entries.show()

    def abrir_ventas(self):
        from app.ui.sales_window import SalesWindow

        self.win_sales = SalesWindow()
        self.win_sales.show()
