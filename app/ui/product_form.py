from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QDialogButtonBox,
    QMessageBox,
)

from app.db.products_repo import crear_producto, actualizar_producto


class ProductForm(QDialog):
    def __init__(self, parent=None, product=None):
        super().__init__(parent)
        self.product = product

        self.setWindowTitle("Editar Producto" if self.product else "Nuevo Producto")
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

        if self.product:
            self._cargar_producto()

    def _cargar_producto(self):
        self.txt_codigo.setText(self.product.codigo)
        self.txt_nombre.setText(self.product.nombre)
        self.txt_unidad.setText(self.product.unidad or "und")
        self.sp_precio.setValue(float(self.product.precio_venta or 0.0))
        self.sp_minimo.setValue(float(self.product.stock_minimo or 0.0))

    def guardar(self):
        codigo = self.txt_codigo.text().strip()
        nombre = self.txt_nombre.text().strip()

        if not codigo or not nombre:
            QMessageBox.warning(
                self, "Faltan datos", "Código y Nombre son obligatorios."
            )
            return

        try:
            if self.product:
                actualizar_producto(
                    product_id=self.product.id,
                    codigo=codigo,
                    nombre=nombre,
                    unidad=self.txt_unidad.text().strip() or "und",
                    precio_venta=self.sp_precio.value(),
                    stock_minimo=self.sp_minimo.value(),
                )
            else:
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
