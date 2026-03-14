"""
app/ui/widgets.py
──────────────────────────────────────────────────────────────────────────────
Widgets reutilizables compartidos entre ventanas:

  · CommaDoubleSpinBox  — QDoubleSpinBox que acepta punto, muestra coma
  · CommaDelegate       — delegado para tablas: celdas numéricas con coma
  · CopSpinBox          — QSpinBox para precios COP con separador de miles
  · _FixedTable         — QTableWidget con scroll interno (no propaga rueda)
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QStyledItemDelegate,
    QLineEdit,
    QSpinBox,
    QTableWidget,
)
from PySide6.QtCore import Qt, QLocale
from PySide6.QtGui import QValidator, QWheelEvent


# ─────────────────────────────────────────────────────────────────────────────
#  CommaDoubleSpinBox
#  Úsalo donde antes usabas QDoubleSpinBox.
#  · El usuario escribe  1512.25  (punto del teclado numérico)
#  · Se muestra en pantalla  1512,250  (coma como separador decimal)
#  · getValue() devuelve float 1512.25  sin cambios
# ─────────────────────────────────────────────────────────────────────────────
class CommaDoubleSpinBox(QDoubleSpinBox):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLocale(QLocale(QLocale.Spanish, QLocale.Colombia))

    # Mostrar siempre con coma
    def textFromValue(self, value: float) -> str:
        decimals = self.decimals()
        return f"{value:.{decimals}f}".replace(".", ",")

    # Aceptar tanto coma como punto al leer
    def valueFromText(self, text: str) -> float:
        clean = text.strip().replace(",", ".")
        try:
            return float(clean)
        except ValueError:
            return 0.0

    # Validar: dígitos + una sola coma o punto
    def validate(self, text: str, pos: int):
        clean = text.strip()
        if clean == "" or clean == "-":
            return (QValidator.Intermediate, text, pos)
        normalized = clean.replace(",", ".")
        if normalized.count(".") > 1:
            return (QValidator.Invalid, text, pos)
        try:
            float(normalized)
            return (QValidator.Acceptable, text, pos)
        except ValueError:
            if normalized.endswith("."):
                try:
                    float(normalized[:-1])
                    return (QValidator.Intermediate, text, pos)
                except ValueError:
                    pass
            return (QValidator.Invalid, text, pos)

    # Punto del teclado → insertar coma
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Period, Qt.Key_Comma):
            le = self.lineEdit()
            current = le.text()
            # Solo insertar si no hay ya separador decimal
            if "," not in current and "." not in current:
                pos = le.cursorPosition()
                le.setText(current[:pos] + "," + current[pos:])
                le.setCursorPosition(pos + 1)
            return
        super().keyPressEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
#  _CommaLineEdit  (interno, usado por el delegado)
#  QLineEdit que intercepta el punto y lo convierte en coma
# ─────────────────────────────────────────────────────────────────────────────
class _CommaLineEdit(QLineEdit):

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Period, Qt.Key_Comma):
            current = self.text()
            if "," not in current and "." not in current:
                pos = self.cursorPosition()
                self.setText(current[:pos] + "," + current[pos:])
                self.setCursorPosition(pos + 1)
            return
        super().keyPressEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
#  CommaDelegate
#  Delegado para QTableWidget / QTableView.
#  Aplica en las columnas numéricas (cantidad, precio, etc.) de Entradas.
#
#  Uso:
#      from app.ui.widgets import CommaDelegate
#      delegate = CommaDelegate(columns=[1, 2])   # cols de cantidad y precio
#      self.table.setItemDelegate(delegate)
# ─────────────────────────────────────────────────────────────────────────────
class CommaDelegate(QStyledItemDelegate):
    """
    Delegado que:
    · Usa _CommaLineEdit como editor → punto → coma en tiempo real
    · Al mostrar el valor almacenado, reemplaza punto por coma
    · Solo actúa en las columnas indicadas en `columns`
    """

    def __init__(self, parent=None, columns: list[int] | None = None):
        super().__init__(parent)
        # None = aplica en todas las columnas; lista = solo en esas
        self._columns = columns

    def _aplica(self, index) -> bool:
        if self._columns is None:
            return True
        return index.column() in self._columns

    # Editor personalizado: _CommaLineEdit
    def createEditor(self, parent, option, index):
        if not self._aplica(index):
            return super().createEditor(parent, option, index)
        editor = _CommaLineEdit(parent)
        editor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        editor.setStyleSheet(
            "background: #111c33; border: 1px solid #3b82f6; "
            "border-radius: 4px; color: #e2e8f0; padding: 2px 6px; font-size: 13px;"
        )
        return editor

    # Llenar el editor con el valor de la celda (punto → coma)
    def setEditorData(self, editor, index):
        if not self._aplica(index) or not isinstance(editor, _CommaLineEdit):
            return super().setEditorData(editor, index)
        text = index.model().data(index, Qt.EditRole) or ""
        editor.setText(str(text).replace(".", ","))
        editor.selectAll()

    # Guardar lo que escribió el usuario (coma → punto para almacenar como float)
    def setModelData(self, editor, model, index):
        if not self._aplica(index) or not isinstance(editor, _CommaLineEdit):
            return super().setModelData(editor, model, index)
        text = editor.text().strip().replace(",", ".")
        try:
            value = float(text)
            # Guardar en la celda con coma para que siempre se muestre con coma
            display = f"{value:g}".replace(".", ",")
            model.setData(index, display, Qt.EditRole)
        except ValueError:
            model.setData(index, "0", Qt.EditRole)

    # Al mostrar (sin editar), convertir punto a coma por si acaso
    def displayText(self, value, locale):
        if not value:
            return value
        text = str(value)
        # Si es número con punto decimal → mostrar con coma
        try:
            f = float(text.replace(",", "."))
            # Mostrar sin ceros finales pero con coma
            formatted = f"{f:g}".replace(".", ",")
            return formatted
        except ValueError:
            return text


# ─────────────────────────────────────────────────────────────────────────────
#  CopSpinBox


class CopSpinBox(QSpinBox):

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


# ─────────────────────────────────────────────────────────────────────────────
#  _FixedTable


class _FixedTable(QTableWidget):
    """Tabla con scroll interno — no propaga rueda al padre."""

    def wheelEvent(self, event: QWheelEvent):
        super().wheelEvent(event)
        event.accept()
