from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QMessageBox,
    QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QValidator


class CopSpinBox(QSpinBox):
    """SpinBox COP: muestra $1.000, sube de 50 en 50."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(1)
        self.setMaximum(999_999_999)
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


from app.db.cash_repo import registrar_movimiento


class CashForm(QDialog):
    """
    Formulario para registrar un movimiento de caja manual.
    tipo: "INGRESO" o "EGRESO"
    """

    def __init__(self, parent=None, tipo: str = "INGRESO"):
        super().__init__(parent)
        self.setWindowTitle("Registrar movimiento de Caja")
        self.resize(520, 320)

        self.tipo = (tipo or "INGRESO").upper().strip()

        layout = QVBoxLayout(self)

        # Tipo (solo lectura)
        row_tipo = QHBoxLayout()
        row_tipo.addWidget(QLabel("Tipo:"))
        self.txt_tipo = QLineEdit(self.tipo)
        self.txt_tipo.setReadOnly(True)
        row_tipo.addWidget(self.txt_tipo)
        layout.addLayout(row_tipo)

        # Concepto
        row_concepto = QHBoxLayout()
        lbl_concepto = QLabel("Concepto: *")  # ✅ asterisco indica obligatorio
        lbl_concepto.setFixedWidth(120)
        row_concepto.addWidget(lbl_concepto)
        self.txt_concepto = QLineEdit()
        self.txt_concepto.setPlaceholderText(
            "Ej: Pago arriendo, Venta mostrador…  (obligatorio)"
        )
        row_concepto.addWidget(self.txt_concepto)
        layout.addLayout(row_concepto)

        # Monto
        row_monto = QHBoxLayout()
        lbl_monto = QLabel("Monto: *")
        lbl_monto.setFixedWidth(120)
        row_monto.addWidget(lbl_monto)
        self.sp_monto = CopSpinBox()
        row_monto.addWidget(self.sp_monto)
        layout.addLayout(row_monto)

        # Referencia
        row_ref = QHBoxLayout()
        lbl_ref = QLabel("Referencia:")
        lbl_ref.setFixedWidth(120)
        row_ref.addWidget(lbl_ref)
        self.txt_referencia = QLineEdit()
        self.txt_referencia.setPlaceholderText(
            "Ej: Factura 123 / Venta #10  (opcional)"
        )
        self.txt_referencia.textEdited.connect(
            lambda t: self.txt_referencia.setText(t.upper())
        )
        row_ref.addWidget(self.txt_referencia)
        layout.addLayout(row_ref)

        # Observación
        layout.addWidget(QLabel("Observación (opcional):"))
        self.txt_obs = QTextEdit()
        self.txt_obs.setPlaceholderText("Notas adicionales…")
        self.txt_obs.setFixedHeight(70)
        layout.addWidget(self.txt_obs)

        # Botones
        buttons = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_guardar = QPushButton("Guardar")
        btn_guardar.clicked.connect(self.guardar)
        btn_guardar.setDefault(True)
        buttons.addStretch()
        buttons.addWidget(btn_cancelar)
        buttons.addWidget(btn_guardar)
        layout.addLayout(buttons)

    def _parse_monto(self) -> float:
        monto = float(self.sp_monto.value())
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a 0.")
        return monto

    def guardar(self):
        # ✅ FIX #3: Validar concepto en el formulario antes de llamar al repo
        concepto = (self.txt_concepto.text() or "").strip()
        if not concepto:
            QMessageBox.warning(
                self,
                "Campo obligatorio",
                "El concepto no puede estar vacío.\nEjemplo: 'Pago arriendo', 'Venta mostrador'…",
            )
            self.txt_concepto.setFocus()
            return

        try:
            monto = self._parse_monto()
        except ValueError as e:
            QMessageBox.warning(self, "Monto inválido", str(e))
            return

        referencia = (self.txt_referencia.text() or "").strip().upper() or None
        obs = (self.txt_obs.toPlainText() or "").strip() or None

        try:
            registrar_movimiento(
                tipo=self.tipo,
                concepto=concepto,
                monto=monto,
                referencia=referencia,
                observacion=obs,
            )
            QMessageBox.information(self, "OK", "Movimiento registrado.")
            self.accept()

        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
