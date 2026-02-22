from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
    QComboBox,
    QFileDialog,
    QDateEdit,
)
from PySide6.QtCore import Qt, QDate

from app.db.cash_repo import (
    listar_movimientos,
    obtener_saldo,
    cerrar_dia,
    esta_cerrado,
    resumen_del_dia,
    resumen_rango,
)
from app.ui.cash_form import CashForm
from app.utils.formatters import fmt_fecha


def _fmt_cop(value: float) -> str:
    try:
        s = "${:,.2f}".format(float(value or 0.0))
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "$0,00"


class CashWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Caja")
        self.resize(1050, 600)

        layout = QVBoxLayout(self)

        # -------------------
        # Filtros (fecha, tipo, buscar)
        # -------------------
        filters = QHBoxLayout()

        filters.addWidget(QLabel("Desde:"))
        self.dt_desde = QDateEdit()
        self.dt_desde.setCalendarPopup(True)
        self.dt_desde.setDate(QDate.currentDate())
        filters.addWidget(self.dt_desde)

        filters.addWidget(QLabel("Hasta:"))
        self.dt_hasta = QDateEdit()
        self.dt_hasta.setCalendarPopup(True)
        self.dt_hasta.setDate(QDate.currentDate())
        filters.addWidget(self.dt_hasta)

        filters.addWidget(QLabel("Tipo:"))
        self.cbo_tipo = QComboBox()
        self.cbo_tipo.addItems(["TODOS", "INGRESO", "EGRESO"])
        filters.addWidget(self.cbo_tipo)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText(
            "Buscar (concepto, referencia, observación)..."
        )
        filters.addWidget(self.txt_buscar, 2)

        btn_aplicar = QPushButton("Aplicar")
        btn_aplicar.clicked.connect(self.cargar)
        filters.addWidget(btn_aplicar)

        btn_refrescar = QPushButton("Refrescar")
        btn_refrescar.clicked.connect(self.cargar)
        filters.addWidget(btn_refrescar)

        layout.addLayout(filters)

        # -------------------
        # Barra acciones (saldo + export + cierre)
        # -------------------
        top = QHBoxLayout()

        self.lbl_saldo = QLabel("Saldo: $0,00")
        f = self.lbl_saldo.font()
        f.setPointSize(12)
        f.setBold(True)
        self.lbl_saldo.setFont(f)
        top.addWidget(self.lbl_saldo)

        self.lbl_estado = QLabel("")
        top.addWidget(self.lbl_estado)

        self.lbl_resumen = QLabel("Balance: $0,00 | Ingresos: $0,00 | Egresos: $0,00")
        self.lbl_resumen.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top.addWidget(self.lbl_resumen, 1)

        top.addStretch()

        self.btn_export = QPushButton("Exportar PDF")
        self.btn_export.clicked.connect(self.exportar_pdf)
        top.addWidget(self.btn_export)

        self.btn_excel = QPushButton("Exportar Excel")
        self.btn_excel.clicked.connect(self.exportar_excel)
        top.addWidget(self.btn_excel)

        self.btn_cierre = QPushButton("Cierre del día")
        self.btn_cierre.clicked.connect(self.cerrar_dia_ui)
        top.addWidget(self.btn_cierre)

        layout.addLayout(top)

        # Barra superior de acciones (debajo del título o arriba de la tabla)
        actions = QHBoxLayout()

        self.btn_ingreso = QPushButton("Nuevo Ingreso")
        self.btn_egreso = QPushButton("Nuevo Egreso")

        self.btn_ingreso.clicked.connect(self.abrir_ingreso)
        self.btn_egreso.clicked.connect(self.abrir_egreso)

        actions.addWidget(self.btn_ingreso)
        actions.addWidget(self.btn_egreso)
        actions.addStretch()

        layout.addLayout(actions)

        # -------------------
        # Tabla
        # -------------------
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Fecha", "Tipo", "Concepto", "Monto", "Referencia", "Observación"]
        )
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self._movs = []
        self.cargar()

    # ---------------- MÉTODOS DE VENTANA ----------------

    def abrir_ingreso(self):
        form = CashForm(tipo="INGRESO", parent=self)
        # Si CashForm es QDialog, esto funciona perfecto:
        if hasattr(form, "exec"):
            if form.exec():
                self.cargar()
        else:
            # Si CashForm fuera QWidget (raro), lo mostramos y recargamos al cerrar manualmente después
            form.show()

    def abrir_egreso(self):
        form = CashForm(tipo="EGRESO", parent=self)
        if hasattr(form, "exec"):
            if form.exec():
                self.cargar()
        else:
            form.show()

    def _get_filters(self):
        d1 = self.dt_desde.date().toPython()
        d2 = self.dt_hasta.date().toPython()

        tipo = self.cbo_tipo.currentText()
        if tipo == "TODOS":
            tipo = None

        q = (self.txt_buscar.text() or "").strip() or None
        return d1, d2, tipo, q

    def cargar(self):
        try:
            d1, d2, tipo, q = self._get_filters()

            # Estado cierre del día (solo informativo)
            if d1 == d2 and esta_cerrado(d1):
                self.lbl_estado.setText(f"🧾 Día {d1} CERRADO")
            else:
                self.lbl_estado.setText("")

            # saldo total (global)
            saldo = obtener_saldo()
            self.lbl_saldo.setText(f"Saldo: {_fmt_cop(saldo)}")

            # Resumen del rango (o día) según filtros
            if d1 == d2:
                data = resumen_del_dia(d1)
                ingresos = float(data["ingresos"] or 0.0)
                egresos = float(data["egresos"] or 0.0)
            else:
                data = resumen_rango(d1, d2)
                ingresos = float(data["ingresos"] or 0.0)
                egresos = float(data["egresos"] or 0.0)

            balance = ingresos - egresos

            self.lbl_resumen.setText(
                f"Balance: {_fmt_cop(balance)}  |  Ingresos: {_fmt_cop(ingresos)}  |  Egresos: {_fmt_cop(egresos)}"
            )

            self._movs = listar_movimientos(
                limit=1000,
                fecha_desde=d1,
                fecha_hasta=d2,
                tipo=tipo,
                q=q,
            )

            was_sort = self.table.isSortingEnabled()
            self.table.setSortingEnabled(False)
            self.table.blockSignals(True)

            self.table.setRowCount(len(self._movs))

            for row, m in enumerate(self._movs):
                fecha_txt = ""
                if getattr(m, "fecha", None):
                    try:
                        fecha_txt = fmt_fecha(m.fecha)
                    except Exception:
                        fecha_txt = str(m.fecha)

                self.table.setItem(row, 0, QTableWidgetItem(str(m.id)))
                self.table.setItem(row, 1, QTableWidgetItem(fecha_txt))
                self.table.setItem(row, 2, QTableWidgetItem(m.tipo or ""))
                self.table.setItem(row, 3, QTableWidgetItem(m.concepto or ""))

                it_m = QTableWidgetItem(_fmt_cop(m.monto or 0.0))
                it_m.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 4, it_m)

                self.table.setItem(row, 5, QTableWidgetItem(m.referencia or ""))
                self.table.setItem(row, 6, QTableWidgetItem(m.observacion or ""))

            self.table.blockSignals(False)
            self.table.setSortingEnabled(was_sort)

        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    # -------------------
    # Export PDF
    # -------------------

    def exportar_pdf(self):
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm
            from PySide6.QtWidgets import QFileDialog

            d1, d2, tipo, q = self._get_filters()

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar PDF",
                f"caja_{d1}_a_{d2}.pdf",
                "PDF (*.pdf)",
            )
            if not path:
                return

            c = canvas.Canvas(path, pagesize=letter)
            w, h = letter

            y = h - 2 * cm
            c.setFont("Helvetica-Bold", 14)
            c.drawString(2 * cm, y, "Reporte de Caja")
            y -= 0.7 * cm

            c.setFont("Helvetica", 10)
            c.drawString(2 * cm, y, f"Rango: {d1} a {d2}")
            y -= 0.5 * cm
            c.drawString(2 * cm, y, f"Tipo: {tipo or 'TODOS'}   Buscar: {q or '-'}")
            y -= 0.5 * cm

            # Saldo global (tal como se muestra en UI)
            c.drawString(2 * cm, y, f"{self.lbl_saldo.text()}")
            y -= 0.8 * cm

            # --------- Resumen diario (PRO) solo si es un día ---------
            # --------- Resumen PRO ---------
            if d1 == d2:
                data = resumen_del_dia(d1)
                estado = "CERRADO" if esta_cerrado(d1) else "ABIERTO"

                c.setFont("Helvetica-Bold", 11)
                c.drawString(2 * cm, y, f"Resumen del día ({d1}) - Estado: {estado}")
                y -= 0.55 * cm

                c.setFont("Helvetica", 10)
                c.drawString(
                    2 * cm, y, f"Saldo inicial: {_fmt_cop(data['saldo_inicial'])}"
                )
                y -= 0.45 * cm
                c.drawString(2 * cm, y, f"Ingresos: {_fmt_cop(data['ingresos'])}")
                y -= 0.45 * cm
                c.drawString(2 * cm, y, f"Egresos: {_fmt_cop(data['egresos'])}")
                y -= 0.45 * cm
                c.drawString(2 * cm, y, f"Saldo final: {_fmt_cop(data['saldo_final'])}")
                y -= 0.8 * cm
            else:
                data = resumen_rango(d1, d2)

                c.setFont("Helvetica-Bold", 11)
                c.drawString(2 * cm, y, f"Resumen del rango ({d1} a {d2})")
                y -= 0.55 * cm

                c.setFont("Helvetica", 10)
                c.drawString(
                    2 * cm, y, f"Saldo inicial: {_fmt_cop(data['saldo_inicial'])}"
                )
                y -= 0.45 * cm
                c.drawString(2 * cm, y, f"Ingresos: {_fmt_cop(data['ingresos'])}")
                y -= 0.45 * cm
                c.drawString(2 * cm, y, f"Egresos: {_fmt_cop(data['egresos'])}")
                y -= 0.45 * cm
                c.drawString(2 * cm, y, f"Saldo final: {_fmt_cop(data['saldo_final'])}")
                y -= 0.8 * cm

            # Encabezados tabla
            c.setFont("Helvetica-Bold", 9)
            c.drawString(2 * cm, y, "Fecha")
            c.drawString(6.2 * cm, y, "Tipo")
            c.drawString(8.2 * cm, y, "Monto")
            c.drawString(11.2 * cm, y, "Concepto / Ref")
            y -= 0.4 * cm

            c.setFont("Helvetica", 9)

            for m in self._movs:
                if y < 2 * cm:
                    c.showPage()
                    y = h - 2 * cm
                    c.setFont("Helvetica-Bold", 9)
                    c.drawString(2 * cm, y, "Fecha")
                    c.drawString(6.2 * cm, y, "Tipo")
                    c.drawString(8.2 * cm, y, "Monto")
                    c.drawString(11.2 * cm, y, "Concepto / Ref")
                    y -= 0.4 * cm
                    c.setFont("Helvetica", 9)

                fecha_txt = ""
                if getattr(m, "fecha", None):
                    try:
                        fecha_txt = fmt_fecha(m.fecha)
                    except Exception:
                        fecha_txt = str(m.fecha)

                concepto = (m.concepto or "").strip()
                ref = (m.referencia or "").strip()
                line = concepto
                if ref:
                    line += f" ({ref})"

                c.drawString(2 * cm, y, fecha_txt[:16])
                c.drawString(6.2 * cm, y, (m.tipo or "")[:10])
                c.drawRightString(10.8 * cm, y, _fmt_cop(m.monto or 0.0))
                c.drawString(11.2 * cm, y, line[:60])

                y -= 0.38 * cm

            c.save()

            QMessageBox.information(self, "OK", "PDF exportado correctamente.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # -------------------
    # EXPORTAR EXCEL
    # -------------------

    def exportar_excel(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font
            from openpyxl.utils import get_column_letter
            from PySide6.QtWidgets import QFileDialog

            d1, d2, tipo, q = self._get_filters()

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Excel",
                f"caja_{d1}_a_{d2}.xlsx",
                "Excel (*.xlsx)",
            )
            if not path:
                return

            wb = Workbook()
            ws = wb.active
            ws.title = "Caja"

            # Encabezado general
            ws["A1"] = "Reporte de Caja"
            ws["A1"].font = Font(bold=True, size=14)

            ws["A2"] = f"Rango: {d1} a {d2}"
            ws["A3"] = f"Tipo: {tipo or 'TODOS'}"
            ws["A4"] = f"Buscar: {q or '-'}"
            ws["A5"] = self.lbl_saldo.text()

            row_ptr = 7  # donde empezamos a escribir

            # --------- Resumen diario (PRO) solo si es un día ---------
            # --------- Resumen PRO ---------
            if d1 == d2:
                data = resumen_del_dia(d1)
                estado = "CERRADO" if esta_cerrado(d1) else "ABIERTO"

                ws[f"A{row_ptr}"] = f"Resumen del día ({d1}) - Estado: {estado}"
                ws[f"A{row_ptr}"].font = Font(bold=True)
                row_ptr += 1

                ws[f"A{row_ptr}"] = "Saldo inicial:"
                ws[f"B{row_ptr}"] = float(data["saldo_inicial"])
                ws[f"B{row_ptr}"].number_format = "#,##0.00"
                row_ptr += 1

                ws[f"A{row_ptr}"] = "Ingresos:"
                ws[f"B{row_ptr}"] = float(data["ingresos"])
                ws[f"B{row_ptr}"].number_format = "#,##0.00"
                row_ptr += 1

                ws[f"A{row_ptr}"] = "Egresos:"
                ws[f"B{row_ptr}"] = float(data["egresos"])
                ws[f"B{row_ptr}"].number_format = "#,##0.00"
                row_ptr += 1

                ws[f"A{row_ptr}"] = "Saldo final:"
                ws[f"B{row_ptr}"] = float(data["saldo_final"])
                ws[f"B{row_ptr}"].number_format = "#,##0.00"
                row_ptr += 2
            else:
                data = resumen_rango(d1, d2)

                ws[f"A{row_ptr}"] = f"Resumen del rango ({d1} a {d2})"
                ws[f"A{row_ptr}"].font = Font(bold=True)
                row_ptr += 1

                ws[f"A{row_ptr}"] = "Saldo inicial:"
                ws[f"B{row_ptr}"] = float(data["saldo_inicial"])
                row_ptr += 1

                ws[f"A{row_ptr}"] = "Ingresos:"
                ws[f"B{row_ptr}"] = float(data["ingresos"])
                row_ptr += 1

                ws[f"A{row_ptr}"] = "Egresos:"
                ws[f"B{row_ptr}"] = float(data["egresos"])
                row_ptr += 1

                ws[f"A{row_ptr}"] = "Saldo final:"
                ws[f"B{row_ptr}"] = float(data["saldo_final"])
                row_ptr += 2

            # Encabezados tabla
            headers = [
                "ID",
                "Fecha",
                "Tipo",
                "Concepto",
                "Monto",
                "Referencia",
                "Observación",
            ]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=row_ptr, column=col, value=header)
                cell.font = Font(bold=True)
            row_ptr += 1

            # Datos
            for m in self._movs:
                ws.cell(row=row_ptr, column=1, value=int(m.id))
                ws.cell(row=row_ptr, column=2, value=fmt_fecha(m.fecha))
                ws.cell(row=row_ptr, column=3, value=m.tipo)
                ws.cell(row=row_ptr, column=4, value=m.concepto)
                ws.cell(row=row_ptr, column=5, value=float(m.monto or 0.0))
                ws.cell(row=row_ptr, column=5).number_format = "#,##0.00"
                ws.cell(row=row_ptr, column=6, value=m.referencia or "")
                ws.cell(row=row_ptr, column=7, value=m.observacion or "")
                row_ptr += 1

            # Ajustes de ancho columnas
            widths = [10, 20, 12, 30, 14, 18, 30]
            for i, w in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = w

            wb.save(path)
            QMessageBox.information(self, "OK", "Excel exportado correctamente.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # -------------------
    # Cierre diario
    # -------------------
    def cerrar_dia_ui(self):
        try:
            d = self.dt_desde.date().toPython()
            d2 = self.dt_hasta.date().toPython()
            if d != d2:
                QMessageBox.warning(
                    self,
                    "Cierre",
                    "Para cierre diario, selecciona un solo día (Desde = Hasta).",
                )
                return

            if esta_cerrado(d):
                QMessageBox.information(self, "Cierre", f"El día {d} ya está cerrado.")
                return

            # Mostrar resumen antes de cerrar
            data = resumen_del_dia(d)
            msg = (
                f"Cierre del día: {d}\n\n"
                f"Saldo inicial: {_fmt_cop(data['saldo_inicial'])}\n"
                f"Ingresos: {_fmt_cop(data['ingresos'])}\n"
                f"Egresos: {_fmt_cop(data['egresos'])}\n"
                f"Saldo final: {_fmt_cop(data['saldo_final'])}\n\n"
                f"¿Confirmas cerrar el día?"
            )
            confirm = QMessageBox.question(self, "Confirmar cierre", msg)
            if confirm != QMessageBox.Yes:
                return

            cerrar_dia(d, cerrado_por=None)
            QMessageBox.information(self, "OK", f"Día {d} cerrado.")
            self.cargar()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
