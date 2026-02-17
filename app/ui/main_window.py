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

        btn_productos = QPushButton("Gestionar Productos")
        btn_productos.clicked.connect(self.abrir_productos)
        layout.addWidget(btn_productos)

        self.setCentralWidget(root)

    def abrir_productos(self):
        from app.ui.products_window import ProductsWindow

        self.win_productos = ProductsWindow()
        self.win_productos.show()
