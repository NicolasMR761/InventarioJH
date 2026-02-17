from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QDialogButtonBox,
    QMessageBox,
)

from app.db.products_repo import crear_producto


class ProductForm(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Producto")
        self.resize(400, 250)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_codigo = QLineEdit()
        self.txt_nombre = QLineEdit()
        self.txt_unidad = QLineEdit("und")

        self.sp_precio = QDoubleSpinBox()
        self.sp_precio.setMaximum(10_000_000)
        self.sp_precio.setDecimals(2)

        self.sp_minimo = QDoubleSpinBox()
        self.sp_minimo.setMaximum(1_000_000)
        self.sp_minimo.setDecimals(2)

        form.addRow("Código:", self.txt_codigo)
        form.addRow("Nombre:", self.txt_nombre)
        form.addRow("Unidad:", self.txt_unidad)
        form.addRow("Precio venta:", self.sp_precio)
        form.addRow("Stock mínimo:", self.sp_minimo)

        layout.addLayout(form)

        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.guardar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def guardar(self):
        codigo = self.txt_codigo.text().strip()
        nombre = self.txt_nombre.text().strip()

        if not codigo or not nombre:
            QMessageBox.warning(
                self, "Faltan datos", "Código y Nombre son obligatorios."
            )
            return

        try:
            crear_producto(
                codigo=codigo,
                nombre=nombre,
                unidad=self.txt_unidad.text().strip() or "und",
                precio_venta=self.sp_precio.value(),
                stock_minimo=self.sp_minimo.value(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "No se pudo guardar", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error inesperado:\n{e}")
            return

        self.accept()
