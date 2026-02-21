from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QTextEdit,
)
from PySide6.QtCore import Qt

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

        # Tipo (solo lectura, viene predefinido desde el botón)
        row_tipo = QHBoxLayout()
        row_tipo.addWidget(QLabel("Tipo:"))
        self.txt_tipo = QLineEdit(self.tipo)
        self.txt_tipo.setReadOnly(True)
        row_tipo.addWidget(self.txt_tipo)
        layout.addLayout(row_tipo)

        # Concepto
        row_concepto = QHBoxLayout()
        row_concepto.addWidget(QLabel("Concepto:"))
        self.txt_concepto = QLineEdit()
        self.txt_concepto.setPlaceholderText("Ej: Pago arriendo, Venta mostrador, etc.")
        row_concepto.addWidget(self.txt_concepto)
        layout.addLayout(row_concepto)

        # Monto
        row_monto = QHBoxLayout()
        row_monto.addWidget(QLabel("Monto:"))
        self.txt_monto = QLineEdit()
        self.txt_monto.setPlaceholderText("Ej: 5000 o 5000.50 (sin $ ni puntos)")
        self.txt_monto.setAlignment(Qt.AlignRight)
        row_monto.addWidget(self.txt_monto)
        layout.addLayout(row_monto)

        # Referencia
        row_ref = QHBoxLayout()
        row_ref.addWidget(QLabel("Referencia (opcional):"))
        self.txt_referencia = QLineEdit()
        self.txt_referencia.setPlaceholderText(
            "Ej: Factura 123 / Venta #10 / Compra #5"
        )
        row_ref.addWidget(self.txt_referencia)
        layout.addLayout(row_ref)

        # Observación
        layout.addWidget(QLabel("Observación (opcional):"))
        self.txt_obs = QTextEdit()
        self.txt_obs.setPlaceholderText("Notas adicionales...")
        layout.addWidget(self.txt_obs)

        # Botones
        buttons = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)

        btn_guardar = QPushButton("Guardar")
        btn_guardar.clicked.connect(self.guardar)

        buttons.addStretch()
        buttons.addWidget(btn_cancelar)
        buttons.addWidget(btn_guardar)
        layout.addLayout(buttons)

    def _parse_monto(self) -> float:
        raw = (self.txt_monto.text() or "").strip()
        if not raw:
            raise ValueError("El monto es obligatorio.")

        # Permitimos "5.000,50" o "$5.000" etc. (limpieza básica)
        raw = raw.replace("$", "").replace(" ", "")
        raw = raw.replace(".", "")  # quita separadores de miles
        raw = raw.replace(",", ".")  # coma decimal a punto

        monto = float(raw)
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a 0.")
        return monto

    def guardar(self):
        try:
            concepto = (self.txt_concepto.text() or "").strip()
            monto = self._parse_monto()
            referencia = (self.txt_referencia.text() or "").strip() or None
            obs = (self.txt_obs.toPlainText() or "").strip() or None

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
