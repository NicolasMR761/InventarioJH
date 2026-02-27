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
        self.txt_monto = QLineEdit()
        self.txt_monto.setPlaceholderText("Ej: 5000 o 5.000 o 5000,50  (sin $)")
        self.txt_monto.setAlignment(Qt.AlignRight)
        row_monto.addWidget(self.txt_monto)
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
        """
        Acepta formatos: 5000 / 5.000 / 5000,50 / 5.000,50 / $5.000
        """
        raw = (self.txt_monto.text() or "").strip()
        if not raw:
            raise ValueError("El monto es obligatorio.")

        raw = raw.replace("$", "").replace(" ", "")

        has_dot = "." in raw
        has_comma = "," in raw

        if has_dot and has_comma:
            last_dot = raw.rfind(".")
            last_comma = raw.rfind(",")
            if last_comma > last_dot:
                raw = raw.replace(".", "").replace(",", ".")
            else:
                raw = raw.replace(",", "")
        elif has_comma and not has_dot:
            raw = raw.replace(",", ".")
        elif has_dot and not has_comma:
            parts = raw.split(".")
            if (
                len(parts) == 2
                and len(parts[1]) == 3
                and parts[0].isdigit()
                and parts[1].isdigit()
            ):
                raw = raw.replace(".", "")

        monto = float(raw)
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
            self.txt_monto.setFocus()
            return

        referencia = (self.txt_referencia.text() or "").strip() or None
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
