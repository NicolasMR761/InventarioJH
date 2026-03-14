"""
app/ui/customer_form.py
──────────────────────────────────────────────────────────────────────────────
Formulario de creación y edición de clientes.
Extraído de customers_window.py para mantener archivos manejables.
──────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)

from app.db.customers_repo import crear_cliente, actualizar_cliente


class ClienteFormDialog(QDialog):
    def __init__(self, parent=None, customer=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle("Editar Cliente" if customer else "Nuevo Cliente")
        self.setFixedWidth(380)
        self.setStyleSheet("""
            QDialog { background: #0b1120; color: #e2e8f0; font-family: 'Segoe UI', Arial; }
            QLabel { color: #94a3b8; font-size: 12px; }
            QLineEdit {
                background: #111c33; border: 1px solid #1e3a5f;
                border-radius: 8px; padding: 7px 10px; color: #e2e8f0;
            }
            QLineEdit:focus { border-color: #3b82f6; }
            QPushButton {
                background: #2563eb; border: none; border-radius: 8px;
                padding: 8px 20px; font-weight: 700; color: white;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton[flat="true"] {
                background: #111c33; border: 1px solid #1e3a5f; color: #94a3b8;
            }
        """)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        lay.addWidget(QLabel("Nombre *"))
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre completo…")
        lay.addWidget(self.txt_nombre)

        lay.addWidget(QLabel("Teléfono"))
        self.txt_telefono = QLineEdit()
        self.txt_telefono.setPlaceholderText("Teléfono (opcional)…")
        lay.addWidget(self.txt_telefono)

        lay.addWidget(QLabel("Documento / NIT"))
        self.txt_documento = QLineEdit()
        self.txt_documento.setPlaceholderText("Cédula o NIT (opcional)…")
        lay.addWidget(self.txt_documento)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("flat", True)
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("💾  Guardar")
        btn_save.clicked.connect(self._guardar)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        lay.addLayout(btns)

        if customer:
            self.txt_nombre.setText(customer.nombre or "")
            self.txt_telefono.setText(customer.telefono or "")
            self.txt_documento.setText(customer.documento or "")

    def _guardar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Campo obligatorio", "El nombre es obligatorio.")
            return
        try:
            if self.customer:
                actualizar_cliente(
                    self.customer.id, nombre,
                    self.txt_telefono.text().strip() or None,
                    self.txt_documento.text().strip() or None,
                )
            else:
                crear_cliente(
                    nombre,
                    self.txt_telefono.text().strip() or None,
                    self.txt_documento.text().strip() or None,
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
