from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QSpinBox,
    QDialogButtonBox,
    QMessageBox,
    QCheckBox,
    QHBoxLayout,
)
from PySide6.QtGui import QValidator
from PySide6.QtCore import QLocale

from app.ui.widgets import CommaDoubleSpinBox


class CopSpinBox(QSpinBox):
    """SpinBox COP: muestra $1.000, sube de 50 en 50."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(0)
        self.setMaximum(99_999_999)
        self.setSingleStep(50)
        self.setPrefix("$")

    def textFromValue(self, value: int) -> str:
        s = ""
        digits = str(abs(value))
        for i, ch in enumerate(reversed(digits)):
            if i > 0 and i % 3 == 0:
                s = "." + s
            s = ch + s
        return s

    def valueFromText(self, text: str) -> int:
        clean = text.replace("$", "").replace(".", "").replace(",", "").strip()
        try:
            return int(clean)
        except ValueError:
            return 0

    def validate(self, text: str, pos: int):
        clean = text.replace("$", "").replace(".", "").replace(",", "").strip()
        if clean == "" or clean.isdigit():
            return (QValidator.Acceptable, text, pos)
        return (QValidator.Invalid, text, pos)


from app.db.products_repo import crear_producto, actualizar_producto


class ProductForm(QDialog):
    def __init__(self, parent=None, product=None):
        super().__init__(parent)
        self.product = product

        self.setWindowTitle("Editar Producto" if self.product else "Nuevo Producto")
        self.resize(420, 280)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_codigo = QLineEdit()
        self.txt_nombre = QLineEdit()

        # ── Unidad con checkbox KG ──────────────────────────
        unidad_row = QHBoxLayout()
        self.txt_unidad = QLineEdit("und")
        self.txt_unidad.setMaximumWidth(80)
        unidad_row.addWidget(self.txt_unidad)

        self.chk_kg = QCheckBox("Kilogramo (kg)")
        self.chk_kg.setToolTip("Activa para fijar la unidad en kg y vender por peso")
        self.chk_kg.toggled.connect(self._toggle_kg)
        unidad_row.addWidget(self.chk_kg)
        unidad_row.addStretch()
        # ────────────────────────────────────────────────────

        self.sp_precio = CopSpinBox()

        self.sp_minimo = CommaDoubleSpinBox()
        self.sp_minimo.setMaximum(1_000_000)
        self.sp_minimo.setDecimals(2)

        form.addRow("Código:", self.txt_codigo)
        form.addRow("Nombre:", self.txt_nombre)
        form.addRow("Unidad:", unidad_row)
        form.addRow("Precio venta:", self.sp_precio)
        form.addRow("Stock mínimo:", self.sp_minimo)

        layout.addLayout(form)

        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.guardar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        if self.product:
            self._cargar_producto()

    def _toggle_kg(self, checked: bool):
        if checked:
            self.txt_unidad.setText("kg")
            self.txt_unidad.setEnabled(False)
        else:
            self.txt_unidad.setEnabled(True)
            if self.txt_unidad.text().strip().lower() == "kg":
                self.txt_unidad.setText("und")

    def _cargar_producto(self):
        self.txt_codigo.setText(self.product.codigo)
        self.txt_nombre.setText(self.product.nombre)
        unidad = (self.product.unidad or "und").strip().lower()
        if unidad == "kg":
            self.chk_kg.setChecked(True)  # _toggle_kg se dispara automáticamente
        else:
            self.txt_unidad.setText(self.product.unidad or "und")
        self.sp_precio.setValue(int(self.product.precio_venta or 0))
        self.sp_minimo.setValue(float(self.product.stock_minimo or 0.0))

    def guardar(self):
        codigo = self.txt_codigo.text().strip()
        nombre = self.txt_nombre.text().strip()

        if not codigo or not nombre:
            QMessageBox.warning(
                self, "Faltan datos", "Código y Nombre son obligatorios."
            )
            return

        unidad = (
            "kg"
            if self.chk_kg.isChecked()
            else (self.txt_unidad.text().strip() or "und")
        )

        try:
            if self.product:
                actualizar_producto(
                    product_id=self.product.id,
                    codigo=codigo,
                    nombre=nombre,
                    unidad=unidad,
                    precio_venta=float(self.sp_precio.value()),
                    stock_minimo=self.sp_minimo.value(),
                )
            else:
                crear_producto(
                    codigo=codigo,
                    nombre=nombre,
                    unidad=unidad,
                    precio_venta=float(self.sp_precio.value()),
                    stock_minimo=self.sp_minimo.value(),
                )
        except ValueError as e:
            QMessageBox.warning(self, "No se pudo guardar", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error inesperado:\n{e}")
            return

        self.accept()
