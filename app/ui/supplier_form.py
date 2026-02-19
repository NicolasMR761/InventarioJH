from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QMessageBox,
)

from app.db.suppliers_repo import crear_proveedor, actualizar_proveedor


class SupplierForm(QDialog):
    def __init__(self, parent=None, supplier=None):
        super().__init__(parent)
        self.supplier = supplier

        self.setWindowTitle("Editar Proveedor" if self.supplier else "Nuevo Proveedor")
        self.resize(420, 260)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_nombre = QLineEdit()
        self.txt_nit = QLineEdit()
        self.txt_telefono = QLineEdit()
        self.txt_direccion = QLineEdit()

        form.addRow("Nombre:", self.txt_nombre)
        form.addRow("NIT:", self.txt_nit)
        form.addRow("Teléfono:", self.txt_telefono)
        form.addRow("Dirección:", self.txt_direccion)

        layout.addLayout(form)

        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.guardar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        if self.supplier:
            self._cargar()

    def _cargar(self):
        self.txt_nombre.setText(self.supplier.nombre or "")
        self.txt_nit.setText(self.supplier.nit or "")
        self.txt_telefono.setText(self.supplier.telefono or "")
        self.txt_direccion.setText(self.supplier.direccion or "")

    def guardar(self):
        nombre = self.txt_nombre.text().strip()
        nit = self.txt_nit.text().strip() or None
        telefono = self.txt_telefono.text().strip() or None
        direccion = self.txt_direccion.text().strip() or None

        if not nombre:
            QMessageBox.warning(self, "Faltan datos", "Nombre es obligatorio.")
            return

        try:
            if self.supplier:
                actualizar_proveedor(
                    supplier_id=self.supplier.id,
                    nombre=nombre,
                    nit=nit,
                    telefono=telefono,
                    direccion=direccion,
                )
            else:
                crear_proveedor(
                    nombre=nombre,
                    nit=nit,
                    telefono=telefono,
                    direccion=direccion,
                )
        except ValueError as e:
            QMessageBox.warning(self, "No se pudo guardar", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error inesperado:\n{e}")
            return

        self.accept()
