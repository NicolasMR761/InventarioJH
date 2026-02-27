from __future__ import annotations

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
    QDateEdit,
    QTextEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
)
from PySide6.QtCore import Qt, QDate

from app.db.cash_repo import (
    listar_movimientos,
    obtener_saldo,
    cerrar_dia,
    esta_cerrado,
    resumen_del_dia,
    resumen_rango,
    contar_movimientos,
)
from app.ui.cash_form import CashForm
from app.utils.formatters import fmt_fecha, fmt_cop  # ← centralizado


class CashWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Caja")
        self.resize(1050, 600)

        self.page_size = 50
        self.offset = 0
        self.total_count = 0

        layout = QVBoxLayout(self)

        # --- Filtros ---
        filters = QHBoxLayout()

        filters.addWidget(QLabel("Desde:"))
        self.dt_desde = QDateEdit()
        self.dt_desde.setCalendarPopup(True)
        # Por defecto: primer día del mes actual
        self.dt_desde.setDate(
            QDate.currentDate().addDays(-(QDate.currentDate().day() - 1))
        )
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
        btn_aplicar.clicked.connect(lambda: self.cargar(reset_offset=True))
        filters.addWidget(btn_aplicar)

        btn_refrescar = QPushButton("Refrescar")
        btn_refrescar.clicked.connect(lambda: self.cargar(reset_offset=False))
        filters.addWidget(btn_refrescar)

        layout.addLayout(filters)

        # --- Barra acciones ---
        top = QHBoxLayout()

        self.lbl_saldo = QLabel("Saldo: $0")
        f = self.lbl_saldo.font()
        f.setPointSize(12)
        f.setBold(True)
        self.lbl_saldo.setFont(f)
        top.addWidget(self.lbl_saldo)

        self.lbl_estado = QLabel("")
        top.addWidget(self.lbl_estado)

        self.lbl_resumen = QLabel("Balance: $0 | Ingresos: $0 | Egresos: $0")
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

        # --- Acciones manuales ---
        actions = QHBoxLayout()
        self.btn_ingreso = QPushButton("Nuevo Ingreso")
        self.btn_egreso = QPushButton("Nuevo Egreso")
        self.btn_ingreso.clicked.connect(self.abrir_ingreso)
        self.btn_egreso.clicked.connect(self.abrir_egreso)
        actions.addWidget(self.btn_ingreso)
        actions.addWidget(self.btn_egreso)
        actions.addStretch()
        layout.addLayout(actions)

        # --- Tabla ---
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Fecha", "Tipo", "Concepto", "Monto", "Referencia", "Detalle"]
        )
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # --- Paginación ---
        pager = QHBoxLayout()
        self.btn_prev = QPushButton("« Anterior")
        self.btn_prev.clicked.connect(self.pagina_anterior)
        pager.addWidget(self.btn_prev)

        self.lbl_pager = QLabel("Mostrando 0–0 de 0")
        pager.addWidget(self.lbl_pager)

        self.btn_next = QPushButton("Siguiente »")
        self.btn_next.clicked.connect(self.pagina_siguiente)
        pager.addWidget(self.btn_next)

        pager.addStretch()
        layout.addLayout(pager)

        self._movs = []
        self.cargar(reset_offset=True)

    # ---------------- helpers ----------------

    def _get_filters(self):
        d1 = self.dt_desde.date().toPython()
        d2 = self.dt_hasta.date().toPython()
        tipo = self.cbo_tipo.currentText()
        if tipo == "TODOS":
            tipo = None
        q = (self.txt_buscar.text() or "").strip() or None
        return d1, d2, tipo, q

    def _mov_by_id(self, mov_id: int):
        for m in self._movs:
            if int(getattr(m, "id", 0)) == int(mov_id):
                return m
        return None

    def ver_detalle_por_id(self, mov_id: int) -> None:
        m = self._mov_by_id(mov_id)
        if not m:
            QMessageBox.information(self, "Detalle", "No se encontró el movimiento.")
            return

        fecha_txt = fmt_fecha(getattr(m, "fecha", None))

        detalle = (
            f"ID: {m.id}\n"
            f"Fecha: {fecha_txt}\n"
            f"Tipo: {m.tipo or ''}\n"
            f"Concepto: {m.concepto or ''}\n"
            f"Monto: {fmt_cop(m.monto or 0.0, decimales=True)}\n"
            f"Referencia: {m.referencia or ''}\n"
            f"Observación:\n{m.observacion or ''}"
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Detalle del movimiento")
        dlg.resize(520, 360)
        lay = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(detalle)
        lay.addWidget(txt)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)
        dlg.exec()

    def abrir_ingreso(self):
        form = CashForm(tipo="INGRESO", parent=self)
        if form.exec():
            self.cargar(reset_offset=False)

    def abrir_egreso(self):
        form = CashForm(tipo="EGRESO", parent=self)
        if form.exec():
            self.cargar(reset_offset=False)

    def pagina_anterior(self):
        self.offset = max(0, self.offset - self.page_size)
        self.cargar(reset_offset=False)

    def pagina_siguiente(self):
        if self.offset + self.page_size < self.total_count:
            self.offset += self.page_size
        self.cargar(reset_offset=False)

    def _update_pager_ui(self):
        shown = len(self._movs)
        start = 0 if self.total_count == 0 else self.offset + 1
        end = self.offset + shown
        self.lbl_pager.setText(f"Mostrando {start}–{end} de {self.total_count}")
        self.btn_prev.setEnabled(self.offset > 0)
        self.btn_next.setEnabled(self.offset + self.page_size < self.total_count)

    def cargar(self, reset_offset: bool = False):
        try:
            if reset_offset:
                self.offset = 0

            d1, d2, tipo, q = self._get_filters()

            if d1 == d2 and esta_cerrado(d1):
                self.lbl_estado.setText(f"🧾 Día {d1} CERRADO")
            else:
                self.lbl_estado.setText("")

            saldo = obtener_saldo()
            self.lbl_saldo.setText(f"Saldo: {fmt_cop(saldo)}")

            if d1 == d2:
                data = resumen_del_dia(d1)
            else:
                data = resumen_rango(d1, d2)

            ingresos = float(data["ingresos"] or 0.0)
            egresos = float(data["egresos"] or 0.0)
            balance = ingresos - egresos

            self.lbl_resumen.setText(
                f"Balance: {fmt_cop(balance)}  |  "
                f"Ingresos: {fmt_cop(ingresos)}  |  "
                f"Egresos: {fmt_cop(egresos)}"
            )

            self.total_count = contar_movimientos(
                fecha_desde=d1,
                fecha_hasta=d2,
                tipo=tipo,
                q=q,
            )
            self._movs = listar_movimientos(
                limit=self.page_size,
                offset=self.offset,
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
                self.table.setItem(row, 0, QTableWidgetItem(str(m.id)))
                self.table.setItem(row, 1, QTableWidgetItem(fmt_fecha(m.fecha)))
                self.table.setItem(row, 2, QTableWidgetItem(m.tipo or ""))
                self.table.setItem(row, 3, QTableWidgetItem(m.concepto or ""))

                it_m = QTableWidgetItem(fmt_cop(m.monto or 0.0))
                it_m.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 4, it_m)

                self.table.setItem(row, 5, QTableWidgetItem(m.referencia or ""))

                mov_id = int(m.id)
                btn = QPushButton("Ver detalle")
                btn.clicked.connect(
                    lambda _=False, mid=mov_id: self.ver_detalle_por_id(mid)
                )
                self.table.setCellWidget(row, 6, btn)

            self.table.blockSignals(False)
            self.table.setSortingEnabled(was_sort)
            self._update_pager_ui()

        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    # --- Exportar ---

    def _movs_para_exportar(self):
        d1, d2, tipo, q = self._get_filters()
        return listar_movimientos(
            limit=200000,
            offset=0,
            fecha_desde=d1,
            fecha_hasta=d2,
            tipo=tipo,
            q=q,
        )

    def exportar_pdf(self):
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm

            d1, d2, tipo, q = self._get_filters()

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar PDF",
                f"caja_{d1}_a_{d2}.pdf",
                "PDF (*.pdf)",
            )
            if not path:
                return

            movs = self._movs_para_exportar()
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
            c.drawString(2 * cm, y, self.lbl_saldo.text())
            y -= 0.8 * cm

            if d1 == d2:
                data = resumen_del_dia(d1)
                estado = "CERRADO" if esta_cerrado(d1) else "ABIERTO"
                c.setFont("Helvetica-Bold", 11)
                c.drawString(2 * cm, y, f"Resumen del día ({d1}) - Estado: {estado}")
                y -= 0.55 * cm
                c.setFont("Helvetica", 10)
                for label, key in [
                    ("Saldo inicial", "saldo_inicial"),
                    ("Ingresos", "ingresos"),
                    ("Egresos", "egresos"),
                    ("Saldo final", "saldo_final"),
                ]:
                    c.drawString(2 * cm, y, f"{label}: {fmt_cop(data[key])}")
                    y -= 0.45 * cm
            else:
                data = resumen_rango(d1, d2)
                c.setFont("Helvetica-Bold", 11)
                c.drawString(2 * cm, y, f"Resumen del rango ({d1} a {d2})")
                y -= 0.55 * cm
                c.setFont("Helvetica", 10)
                for label, key in [
                    ("Saldo inicial", "saldo_inicial"),
                    ("Ingresos", "ingresos"),
                    ("Egresos", "egresos"),
                    ("Saldo final", "saldo_final"),
                ]:
                    c.drawString(2 * cm, y, f"{label}: {fmt_cop(data[key])}")
                    y -= 0.45 * cm

            y -= 0.35 * cm
            c.setFont("Helvetica-Bold", 9)
            c.drawString(2 * cm, y, "Fecha")
            c.drawString(6.2 * cm, y, "Tipo")
            c.drawString(8.2 * cm, y, "Monto")
            c.drawString(11.2 * cm, y, "Concepto / Ref")
            y -= 0.4 * cm
            c.setFont("Helvetica", 9)

            for m in movs:
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

                line = (m.concepto or "").strip()
                ref = (m.referencia or "").strip()
                if ref:
                    line += f" ({ref})"

                c.drawString(2 * cm, y, str(fmt_fecha(m.fecha))[:16])
                c.drawString(6.2 * cm, y, (m.tipo or "")[:10])
                c.drawRightString(10.8 * cm, y, fmt_cop(m.monto or 0.0))
                c.drawString(11.2 * cm, y, line[:60])
                y -= 0.38 * cm

            c.save()
            QMessageBox.information(self, "OK", "PDF exportado correctamente.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def exportar_excel(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font
            from openpyxl.utils import get_column_letter

            d1, d2, tipo, q = self._get_filters()

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Excel",
                f"caja_{d1}_a_{d2}.xlsx",
                "Excel (*.xlsx)",
            )
            if not path:
                return

            movs = self._movs_para_exportar()
            wb = Workbook()
            ws = wb.active
            ws.title = "Caja"

            ws["A1"] = "Reporte de Caja"
            ws["A1"].font = Font(bold=True, size=14)
            ws["A2"] = f"Rango: {d1} a {d2}"
            ws["A3"] = f"Tipo: {tipo or 'TODOS'}"
            ws["A4"] = f"Buscar: {q or '-'}"
            ws["A5"] = self.lbl_saldo.text()

            row_ptr = 7

            if d1 == d2:
                data = resumen_del_dia(d1)
                estado = "CERRADO" if esta_cerrado(d1) else "ABIERTO"
                ws[f"A{row_ptr}"] = f"Resumen del día ({d1}) - Estado: {estado}"
                ws[f"A{row_ptr}"].font = Font(bold=True)
                row_ptr += 1
            else:
                data = resumen_rango(d1, d2)
                ws[f"A{row_ptr}"] = f"Resumen del rango ({d1} a {d2})"
                ws[f"A{row_ptr}"].font = Font(bold=True)
                row_ptr += 1

            for label, key in [
                ("Saldo inicial:", "saldo_inicial"),
                ("Ingresos:", "ingresos"),
                ("Egresos:", "egresos"),
                ("Saldo final:", "saldo_final"),
            ]:
                ws[f"A{row_ptr}"] = label
                ws[f"B{row_ptr}"] = float(data[key])
                ws[f"B{row_ptr}"].number_format = "#,##0.00"
                row_ptr += 1

            row_ptr += 1

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

            for m in movs:
                ws.cell(row_ptr, 1, int(m.id))
                ws.cell(row_ptr, 2, fmt_fecha(m.fecha))
                ws.cell(row_ptr, 3, m.tipo)
                ws.cell(row_ptr, 4, m.concepto)
                ws.cell(row_ptr, 5, float(m.monto or 0.0)).number_format = "#,##0.00"
                ws.cell(row_ptr, 6, m.referencia or "")
                ws.cell(row_ptr, 7, m.observacion or "")
                row_ptr += 1

            widths = [10, 20, 12, 30, 14, 18, 30]
            for i, w in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = w

            wb.save(path)
            QMessageBox.information(self, "OK", "Excel exportado correctamente.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

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

            data = resumen_del_dia(d)
            msg = (
                f"Cierre del día: {d}\n\n"
                f"Saldo inicial: {fmt_cop(data['saldo_inicial'])}\n"
                f"Ingresos:      {fmt_cop(data['ingresos'])}\n"
                f"Egresos:       {fmt_cop(data['egresos'])}\n"
                f"Saldo final:   {fmt_cop(data['saldo_final'])}\n\n"
                f"¿Confirmas cerrar el día?"
            )
            if QMessageBox.question(self, "Confirmar cierre", msg) != QMessageBox.Yes:
                return

            cerrar_dia(d, cerrado_por=None)
            QMessageBox.information(self, "OK", f"Día {d} cerrado.")
            self.cargar(reset_offset=False)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
