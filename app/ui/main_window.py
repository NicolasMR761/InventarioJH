from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from app.db.database import init_db

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventario JH - Offline")
        init_db()

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(QLabel("Proyecto cargado correctamente."))
        self.setCentralWidget(root)
        self.resize(900, 500)
