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

        self.page_size = 50
        self.offset = 0
        self.total_count = 0

        layout = QVBoxLayout(self)

        # -------------------
        # Filtros
        # ✅ FIX #5: rango default = últimos 30 días (no solo hoy)
        # -------------------
        filters = QHBoxLayout()

        filters.addWidget(QLabel("Desde:"))
        self.dt_desde = QDateEdit()
        self.dt_desde.setCalendarPopup(True)
        self.dt_desde.setDate(QDate.currentDate().addDays(-30))  # ← últimos 30 días
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

        btn_hoy = QPushButton("Hoy")
        btn_hoy.clicked.connect(self._filtro_hoy)
        filters.addWidget(btn_hoy)

        btn_aplicar = QPushButton("Aplicar")
        btn_aplicar.clicked.connect(lambda: self.cargar(reset_offset=True))
        filters.addWidget(btn_aplicar)

        btn_refrescar = QPushButton("Refrescar")
        btn_refrescar.clicked.connect(lambda: self.cargar(reset_offset=False))
        filters.addWidget(btn_refrescar)

        layout.addLayout(filters)

        # -------------------
        # Barra acciones
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

        # -------------------
        # Acciones manuales
        # -------------------
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
            ["ID", "Fecha", "Tipo", "Concepto", "Monto", "Referencia", "Detalle"]
        )
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # -------------------
        # Paginación
        # -------------------
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

    # ---------------- Filtros rápidos ----------------

    def _filtro_hoy(self):
        """Botón rápido para ver solo el día de hoy."""
        hoy = QDate.currentDate()
        self.dt_desde.setDate(hoy)
        self.dt_hasta.setDate(hoy)
        self.cargar(reset_offset=True)

    # ---------------- Helpers ----------------

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

        fecha_txt = ""
        if getattr(m, "fecha", None):
            try:
                fecha_txt = m.fecha.strftime("%d/%m/%Y  %H:%M")
            except Exception:
                fecha_txt = str(m.fecha)

        es_ingreso = (m.tipo or "").upper() == "INGRESO"
        color_tipo = "#22c55e" if es_ingreso else "#ef4444"
        label_tipo = "INGRESO" if es_ingreso else "EGRESO"
        emoji_tipo = "↑" if es_ingreso else "↓"

        # Observación: cada línea como ítem
        obs_raw = (m.observacion or "").strip()
        obs_lines = obs_raw.split("\n") if obs_raw else []
        obs_html = (
            "".join(
                f"<tr><td style='padding:5px 0;color:#cbd5e1;font-size:13px;border-bottom:1px solid #1e293b;'>{ln}</td></tr>"
                for ln in obs_lines
            )
            if obs_lines
            else "<tr><td style='color:#475569;font-size:12px;'>Sin detalle</td></tr>"
        )

        ref_txt = (m.referencia or "—").strip()

        html = f"""
        <html><body style='margin:0;padding:0;background:#0a0f1e;font-family:"Segoe UI",Arial,sans-serif;'>
        <div style='background:#0a0f1e;padding:0 0 8px 0;'>

            <!-- BANDA SUPERIOR DE COLOR -->
            <div style='background:linear-gradient(135deg,{color_tipo}cc,{color_tipo}66);
                        padding:20px 28px 16px 28px;margin-bottom:0;'>
                <div style='font-size:10px;color:rgba(255,255,255,0.65);letter-spacing:3px;
                            text-transform:uppercase;margin-bottom:6px;'>
                    INVENTARIO JH &nbsp;·&nbsp; Comprobante Interno
                </div>
                <div style='font-size:24px;font-weight:800;color:#ffffff;
                            letter-spacing:-0.5px;line-height:1.2;'>
                    {m.concepto or "Sin concepto"}
                </div>
                <div style='margin-top:10px;display:flex;align-items:center;gap:8px;'>
                    <span style='background:rgba(0,0,0,0.3);color:#fff;
                                 padding:3px 12px;border-radius:20px;font-size:11px;
                                 font-weight:700;letter-spacing:1.5px;'>
                        {emoji_tipo} {label_tipo}
                    </span>
                    <span style='color:rgba(255,255,255,0.55);font-size:11px;'>
                        Ref: {ref_txt}
                    </span>
                </div>
            </div>

            <!-- MONTO -->
            <div style='background:#0f172a;padding:20px 28px;
                        border-bottom:1px solid #1e293b;'>
                <div style='font-size:10px;color:#475569;letter-spacing:3px;
                            margin-bottom:4px;text-transform:uppercase;'>Monto total</div>
                <div style='font-size:36px;font-weight:900;color:{color_tipo};
                            letter-spacing:-1px;'>
                    {_fmt_cop(m.monto or 0.0)}
                </div>
            </div>

            <!-- DATOS -->
            <div style='padding:16px 28px;border-bottom:1px solid #1e293b;'>
                <table width='100%' cellspacing='0' cellpadding='0'>
                    <tr>
                        <td style='padding:6px 0;color:#475569;font-size:11px;
                                   text-transform:uppercase;letter-spacing:1px;width:38%;'>
                            N° Registro</td>
                        <td style='padding:6px 0;color:#e2e8f0;font-size:13px;
                                   font-weight:600;'>#{m.id}</td>
                    </tr>
                    <tr>
                        <td style='padding:6px 0;color:#475569;font-size:11px;
                                   text-transform:uppercase;letter-spacing:1px;'>Fecha</td>
                        <td style='padding:6px 0;color:#e2e8f0;font-size:13px;
                                   font-weight:600;'>{fecha_txt}</td>
                    </tr>
                    <tr>
                        <td style='padding:6px 0;color:#475569;font-size:11px;
                                   text-transform:uppercase;letter-spacing:1px;'>Referencia</td>
                        <td style='padding:6px 0;color:#e2e8f0;font-size:13px;
                                   font-weight:600;'>{ref_txt}</td>
                    </tr>
                </table>
            </div>

            <!-- DETALLE -->
            <div style='padding:14px 28px 8px 28px;'>
                <div style='font-size:10px;color:#475569;letter-spacing:2px;
                            text-transform:uppercase;margin-bottom:10px;'>Detalle</div>
                <table width='100%' cellspacing='0' cellpadding='0'>
                    {obs_html}
                </table>
            </div>

        </div>
        </body></html>
        """

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Comprobante #{m.id}")
        dlg.setFixedWidth(480)
        dlg.setStyleSheet("background: #0f172a;")

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 12)
        lay.setSpacing(0)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setHtml(html)
        txt.setStyleSheet(
            """
            QTextEdit {
                background: #0f172a;
                border: none;
                color: #e2e8f0;
            }
            QScrollBar:vertical {
                background: #0f172a;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 3px;
            }
        """
        )
        txt.setMinimumHeight(460)
        lay.addWidget(txt)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedWidth(120)
        btn_cerrar.setStyleSheet(
            """
            QPushButton {
                background: #1e3a5f;
                color: #e2e8f0;
                border: 1px solid #2563eb;
                border-radius: 6px;
                padding: 7px 0;
                font-weight: 700;
            }
            QPushButton:hover { background: #2563eb; }
        """
        )
        btn_cerrar.clicked.connect(dlg.accept)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn_cerrar)
        row.addStretch()
        lay.addLayout(row)

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

            if d1 == d2:
                data = resumen_del_dia(d1)
            else:
                data = resumen_rango(d1, d2)

            ingresos = float(data["ingresos"] or 0.0)
            egresos = float(data["egresos"] or 0.0)
            balance = ingresos - egresos

            # Saldo = balance del período filtrado
            self.lbl_saldo.setText(f"Saldo: {_fmt_cop(balance)}")
            self.lbl_resumen.setText(
                f"Ingresos: {_fmt_cop(ingresos)}  |  Egresos: {_fmt_cop(egresos)}"
            )

            self.total_count = contar_movimientos(
                fecha_desde=d1, fecha_hasta=d2, tipo=tipo, q=q
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
                fecha_txt = fmt_fecha(m.fecha) if getattr(m, "fecha", None) else ""

                self.table.setItem(row, 0, QTableWidgetItem(str(m.id)))
                self.table.setItem(row, 1, QTableWidgetItem(fecha_txt))
                self.table.setItem(row, 2, QTableWidgetItem(m.tipo or ""))
                self.table.setItem(row, 3, QTableWidgetItem(m.concepto or ""))

                it_m = QTableWidgetItem(_fmt_cop(m.monto or 0.0))
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

    # -------------------
    # Exportar
    # -------------------
    def _movs_para_exportar(self):
        d1, d2, tipo, q = self._get_filters()
        return listar_movimientos(
            limit=200000, offset=0, fecha_desde=d1, fecha_hasta=d2, tipo=tipo, q=q
        )

    def exportar_pdf(self):
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm
        except ImportError:
            QMessageBox.critical(
                self,
                "Dependencia faltante",
                "Instala reportlab para exportar PDF:\n\npip install reportlab",
            )
            return

        try:
            d1, d2, tipo, q = self._get_filters()
            path, _ = QFileDialog.getSaveFileName(
                self, "Guardar PDF", f"caja_{d1}_a_{d2}.pdf", "PDF (*.pdf)"
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
                c.drawString(2 * cm, y, f"{label}: {_fmt_cop(data[key])}")
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

                fecha_txt = fmt_fecha(m.fecha) if getattr(m, "fecha", None) else ""
                line = (m.concepto or "").strip()
                ref = (m.referencia or "").strip()
                if ref:
                    line += f" ({ref})"

                c.drawString(2 * cm, y, str(fecha_txt)[:16])
                c.drawString(6.2 * cm, y, (m.tipo or "")[:10])
                c.drawRightString(10.8 * cm, y, _fmt_cop(m.monto or 0.0))
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
        except ImportError:
            QMessageBox.critical(
                self,
                "Dependencia faltante",
                "Instala openpyxl para exportar Excel:\n\npip install openpyxl",
            )
            return

        try:
            d1, d2, tipo, q = self._get_filters()
            path, _ = QFileDialog.getSaveFileName(
                self, "Guardar Excel", f"caja_{d1}_a_{d2}.xlsx", "Excel (*.xlsx)"
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
            else:
                data = resumen_rango(d1, d2)
                ws[f"A{row_ptr}"] = f"Resumen del rango ({d1} a {d2})"

            ws[f"A{row_ptr}"].font = Font(bold=True)
            row_ptr += 1

            for label, key in [
                ("Saldo inicial", "saldo_inicial"),
                ("Ingresos", "ingresos"),
                ("Egresos", "egresos"),
                ("Saldo final", "saldo_final"),
            ]:
                ws[f"A{row_ptr}"] = f"{label}:"
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
                ws.cell(row=row_ptr, column=1, value=int(m.id))
                ws.cell(row=row_ptr, column=2, value=fmt_fecha(m.fecha))
                ws.cell(row=row_ptr, column=3, value=m.tipo)
                ws.cell(row=row_ptr, column=4, value=m.concepto)
                ws.cell(row=row_ptr, column=5, value=float(m.monto or 0.0))
                ws.cell(row=row_ptr, column=5).number_format = "#,##0.00"
                ws.cell(row=row_ptr, column=6, value=m.referencia or "")
                ws.cell(row=row_ptr, column=7, value=m.observacion or "")
                row_ptr += 1

            for i, w in enumerate([10, 20, 12, 30, 14, 18, 30], 1):
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
                f"Saldo inicial: {_fmt_cop(data['saldo_inicial'])}\n"
                f"Ingresos: {_fmt_cop(data['ingresos'])}\n"
                f"Egresos: {_fmt_cop(data['egresos'])}\n"
                f"Saldo final: {_fmt_cop(data['saldo_final'])}\n\n"
                f"¿Confirmas cerrar el día?"
            )
            if QMessageBox.question(self, "Confirmar cierre", msg) != QMessageBox.Yes:
                return

            cerrar_dia(d, cerrado_por=None)
            QMessageBox.information(self, "OK", f"Día {d} cerrado.")
            self.cargar(reset_offset=False)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
