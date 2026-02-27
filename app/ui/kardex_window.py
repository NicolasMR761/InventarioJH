from __future__ import annotations

from datetime import datetime, time

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QDateEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QFileDialog,
    QMessageBox,
)

from app.db.products_repo import listar_productos
from app.db.kardex_repo import obtener_kardex
from app.utils.formatters import fmt_fecha, fmt_cop, fmt_qty  # ← centralizado


def _item(
    text: str,
    align: Qt.AlignmentFlag | Qt.Alignment = Qt.AlignLeft | Qt.AlignVCenter,
) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setTextAlignment(int(align))
    return it


class KardexWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kardex por Producto")
        self.resize(1120, 680)

        layout = QVBoxLayout(self)

        # --- Filtros ---
        top = QHBoxLayout()

        top.addWidget(QLabel("Producto:"))
        self.cbo_producto = QComboBox()
        top.addWidget(self.cbo_producto, 2)

        top.addWidget(QLabel("Desde:"))
        self.dt_desde = QDateEdit()
        self.dt_desde.setCalendarPopup(True)
        self.dt_desde.setDisplayFormat("dd/MM/yyyy")
        self.dt_desde.setDate(QDate.currentDate().addDays(-7))
        top.addWidget(self.dt_desde)

        top.addWidget(QLabel("Hasta:"))
        self.dt_hasta = QDateEdit()
        self.dt_hasta.setCalendarPopup(True)
        self.dt_hasta.setDisplayFormat("dd/MM/yyyy")
        self.dt_hasta.setDate(QDate.currentDate())
        top.addWidget(self.dt_hasta)

        self.btn_cargar = QPushButton("Cargar")
        top.addWidget(self.btn_cargar)

        self.btn_pdf = QPushButton("Exportar PDF")
        top.addWidget(self.btn_pdf)

        self.btn_excel = QPushButton("Exportar Excel")
        top.addWidget(self.btn_excel)

        layout.addLayout(top)

        # --- Info saldo inicial ---
        self.lbl_info = QLabel("Saldo inicial: 0")
        self.lbl_info.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.lbl_info)

        # --- Tabla ---
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Fecha", "Tipo", "Referencia", "Cantidad", "Precio", "Subtotal", "Saldo"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)
        self.table.setSortingEnabled(False)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        layout.addWidget(self.table, 1)

        # --- Separador ---
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # --- Resumen inferior ---
        bottom = QHBoxLayout()
        bottom.setSpacing(18)

        self.lbl_tot_entradas = QLabel("Entradas: 0")
        self.lbl_tot_ventas = QLabel("Ventas: 0")
        self.lbl_tot_anul = QLabel("Anulaciones: 0")
        self.lbl_neto = QLabel("Neto: 0")
        self.lbl_saldo_final = QLabel("Saldo final: 0")

        f_bold = QFont()
        f_bold.setBold(True)
        self.lbl_saldo_final.setFont(f_bold)

        bottom.addWidget(self.lbl_tot_entradas)
        bottom.addWidget(self.lbl_tot_ventas)
        bottom.addWidget(self.lbl_tot_anul)
        bottom.addStretch(1)
        bottom.addWidget(self.lbl_neto)
        bottom.addWidget(self.lbl_saldo_final)

        layout.addLayout(bottom)

        # Señales
        self.btn_cargar.clicked.connect(self.cargar)
        self.btn_pdf.clicked.connect(self.exportar_pdf)
        self.btn_excel.clicked.connect(self.exportar_excel)

        self._prod_unidad: dict[int, str] = {}
        self._cargar_productos()
        self.cargar()

    def _cargar_productos(self):
        self.cbo_producto.clear()
        self._prod_unidad.clear()
        for p in listar_productos("", incluir_inactivos=False):
            unidad = (getattr(p, "unidad", "") or "").strip() or "und"
            self._prod_unidad[p.id] = unidad
            self.cbo_producto.addItem(f"{p.codigo} - {p.nombre} ({unidad})", p.id)

    def _row_brush(self, tipo: str) -> QBrush | None:
        t = (tipo or "").upper().strip()
        if t == "ENTRADA":
            return QBrush(QColor(30, 120, 60, 35))
        if t == "VENTA":
            return QBrush(QColor(200, 60, 60, 35))
        if t == "ANULACION":
            return QBrush(QColor(200, 140, 30, 35))
        return None

    def _set_resumen(self, unidad: str, rows: list) -> None:
        tot_entradas = 0.0
        tot_ventas = 0.0
        tot_anul = 0.0

        for r in rows:
            t = (r.tipo or "").upper().strip()
            c = float(r.cantidad or 0.0)
            if t == "ENTRADA":
                tot_entradas += c
            elif t == "VENTA":
                tot_ventas += abs(c)
            elif t == "ANULACION":
                tot_anul += c

        neto = tot_entradas - tot_ventas + tot_anul
        saldo_final = float(rows[-1].saldo) if rows else 0.0

        self.lbl_tot_entradas.setText(f"Entradas: {fmt_qty(tot_entradas)} {unidad}")
        self.lbl_tot_ventas.setText(f"Ventas: {fmt_qty(tot_ventas)} {unidad}")
        self.lbl_tot_anul.setText(f"Anulaciones: {fmt_qty(tot_anul)} {unidad}")
        self.lbl_neto.setText(f"Neto: {fmt_qty(neto)} {unidad}")
        self.lbl_saldo_final.setText(f"Saldo final: {fmt_qty(saldo_final)} {unidad}")

    def cargar(self):
        if self.cbo_producto.count() == 0:
            self.table.setRowCount(0)
            self.lbl_info.setText("Saldo inicial: 0")
            self._set_resumen("und", [])
            return

        product_id = int(self.cbo_producto.currentData())
        unidad = self._prod_unidad.get(product_id, "und")

        self.table.setHorizontalHeaderLabels(
            [
                "Fecha",
                "Tipo",
                "Referencia",
                f"Cantidad ({unidad})",
                "Precio",
                "Subtotal",
                f"Saldo ({unidad})",
            ]
        )

        d1 = self.dt_desde.date().toPython()
        d2 = self.dt_hasta.date().toPython()
        desde = datetime.combine(d1, time(0, 0, 0))
        hasta = datetime.combine(d2, time(23, 59, 59))

        data = obtener_kardex(product_id=product_id, desde=desde, hasta=hasta)
        saldo_inicial = float(data["saldo_inicial"] or 0.0)
        rows = data["rows"]

        self.lbl_info.setText(
            f"Saldo inicial (antes del rango): {fmt_qty(saldo_inicial)} {unidad}"
        )
        self.table.setRowCount(len(rows))

        font_tipo = QFont()
        font_tipo.setBold(True)

        for i, r in enumerate(rows):
            tipo_txt = (r.tipo or "").upper().strip()

            it_tipo = _item(tipo_txt)
            it_tipo.setFont(font_tipo)

            it_ref = _item(r.referencia or "")
            it_ref.setToolTip(r.referencia or "")

            self.table.setItem(i, 0, _item(fmt_fecha(r.fecha)))
            self.table.setItem(i, 1, it_tipo)
            self.table.setItem(i, 2, it_ref)
            self.table.setItem(
                i, 3, _item(fmt_qty(r.cantidad), Qt.AlignRight | Qt.AlignVCenter)
            )
            self.table.setItem(
                i, 4, _item(fmt_cop(r.precio), Qt.AlignRight | Qt.AlignVCenter)
            )
            self.table.setItem(
                i, 5, _item(fmt_cop(r.subtotal), Qt.AlignRight | Qt.AlignVCenter)
            )
            self.table.setItem(
                i, 6, _item(fmt_qty(r.saldo), Qt.AlignRight | Qt.AlignVCenter)
            )

            brush = self._row_brush(tipo_txt)
            if brush is not None:
                for col in range(7):
                    cell = self.table.item(i, col)
                    if cell:
                        cell.setBackground(brush)

        self.table.resizeRowsToContents()
        self._set_resumen(unidad, rows)

    # --- Exportar ---

    def _kardex_para_exportar(self):
        if self.cbo_producto.count() == 0:
            return None

        product_id = int(self.cbo_producto.currentData())
        unidad = self._prod_unidad.get(product_id, "und")
        d1 = self.dt_desde.date().toPython()
        d2 = self.dt_hasta.date().toPython()
        desde = datetime.combine(d1, time(0, 0, 0))
        hasta = datetime.combine(d2, time(23, 59, 59))

        data = obtener_kardex(product_id=product_id, desde=desde, hasta=hasta)
        saldo_inicial = float(data["saldo_inicial"] or 0.0)
        rows = data["rows"]

        tot_entradas = tot_ventas = tot_anul = 0.0
        for r in rows:
            t = (r.tipo or "").upper().strip()
            c = float(r.cantidad or 0.0)
            if t == "ENTRADA":
                tot_entradas += c
            elif t == "VENTA":
                tot_ventas += abs(c)
            elif t == "ANULACION":
                tot_anul += c

        return {
            "product_id": product_id,
            "producto_text": self.cbo_producto.currentText(),
            "unidad": unidad,
            "desde": d1,
            "hasta": d2,
            "saldo_inicial": saldo_inicial,
            "rows": rows,
            "tot_entradas": tot_entradas,
            "tot_ventas": tot_ventas,
            "tot_anul": tot_anul,
            "neto": tot_entradas - tot_ventas + tot_anul,
            "saldo_final": float(rows[-1].saldo) if rows else 0.0,
        }

    def exportar_pdf(self):
        try:
            payload = self._kardex_para_exportar()
            if not payload:
                QMessageBox.information(self, "Kardex", "No hay datos para exportar.")
                return

            d1 = payload["desde"]
            d2 = payload["hasta"]

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar PDF",
                f"kardex_{d1}_a_{d2}.pdf",
                "PDF (*.pdf)",
            )
            if not path:
                return

            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm

            unidad = payload["unidad"]
            saldo_inicial = payload["saldo_inicial"]
            rows = payload["rows"]

            c = canvas.Canvas(path, pagesize=letter)
            w, h = letter

            def header_page():
                nonlocal y
                c.setFont("Helvetica-Bold", 14)
                c.drawString(2 * cm, y, "Kardex por Producto")
                y -= 0.7 * cm
                c.setFont("Helvetica", 10)
                c.drawString(2 * cm, y, f"Producto: {payload['producto_text']}")
                y -= 0.5 * cm
                c.drawString(2 * cm, y, f"Rango: {d1} a {d2}")
                y -= 0.5 * cm
                c.drawString(
                    2 * cm,
                    y,
                    f"Saldo inicial (antes del rango): {fmt_qty(saldo_inicial)} {unidad}",
                )
                y -= 0.8 * cm

                c.setFont("Helvetica-Bold", 11)
                c.drawString(2 * cm, y, "Resumen")
                y -= 0.55 * cm
                c.setFont("Helvetica", 10)
                for label, key in [
                    ("Entradas", "tot_entradas"),
                    ("Ventas", "tot_ventas"),
                    ("Anulaciones", "tot_anul"),
                    ("Neto", "neto"),
                    ("Saldo final", "saldo_final"),
                ]:
                    c.drawString(
                        2 * cm, y, f"{label}: {fmt_qty(payload[key])} {unidad}"
                    )
                    y -= 0.45 * cm
                y -= 0.4 * cm

                c.setFont("Helvetica-Bold", 9)
                c.drawString(2 * cm, y, "Fecha")
                c.drawString(5.2 * cm, y, "Tipo")
                c.drawString(7.3 * cm, y, "Referencia")
                c.drawRightString(14.2 * cm, y, f"Cantidad ({unidad})")
                c.drawRightString(16.7 * cm, y, "Precio")
                c.drawRightString(19.5 * cm, y, "Subtotal")
                y -= 0.35 * cm
                c.line(2 * cm, y, 19.5 * cm, y)
                y -= 0.35 * cm
                c.setFont("Helvetica", 9)

            def ensure_space(min_h=2 * cm):
                nonlocal y
                if y < min_h:
                    c.showPage()
                    y = h - 2 * cm
                    header_page()

            def wrap_text(text: str, max_width: float) -> list[str]:
                words = (text or "").split()
                if not words:
                    return [""]
                lines, line = [], words[0]
                for w2 in words[1:]:
                    test = f"{line} {w2}"
                    if c.stringWidth(test, "Helvetica", 9) <= max_width:
                        line = test
                    else:
                        lines.append(line)
                        line = w2
                lines.append(line)
                return lines

            y = h - 2 * cm
            header_page()

            ref_col_width = 14.2 * cm - 7.3 * cm - 0.3 * cm

            for r in rows:
                tipo_txt = (r.tipo or "").upper().strip()
                ref_lines = wrap_text(r.referencia or "", ref_col_width)
                needed = max(1, len(ref_lines)) * 0.42 * cm + 0.05 * cm
                ensure_space(2 * cm + needed)

                c.drawString(2 * cm, y, str(fmt_fecha(r.fecha))[:16])
                c.drawString(5.2 * cm, y, tipo_txt[:10])

                yy = y
                for line in ref_lines:
                    c.drawString(7.3 * cm, yy, line)
                    yy -= 0.42 * cm

                c.drawRightString(14.2 * cm, y, fmt_qty(r.cantidad))
                c.drawRightString(16.7 * cm, y, fmt_cop(r.precio))
                c.drawRightString(19.5 * cm, y, fmt_cop(r.subtotal))
                y -= needed

            c.save()
            QMessageBox.information(self, "OK", "PDF exportado correctamente.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def exportar_excel(self):
        try:
            payload = self._kardex_para_exportar()
            if not payload:
                QMessageBox.information(self, "Kardex", "No hay datos para exportar.")
                return

            d1 = payload["desde"]
            d2 = payload["hasta"]

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Excel",
                f"kardex_{d1}_a_{d2}.xlsx",
                "Excel (*.xlsx)",
            )
            if not path:
                return

            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment
            from openpyxl.utils import get_column_letter

            unidad = payload["unidad"]
            saldo_inicial = payload["saldo_inicial"]
            rows = payload["rows"]
            align_right = Alignment(horizontal="right")

            wb = Workbook()
            ws = wb.active
            ws.title = "Kardex"

            ws["A1"] = "Kardex por Producto"
            ws["A1"].font = Font(bold=True, size=14)
            ws["A2"] = "Producto:"
            ws["B2"] = payload["producto_text"]
            ws["A3"] = "Rango:"
            ws["B3"] = f"{d1} a {d2}"
            ws["A4"] = "Saldo inicial:"
            ws["B4"] = f"{fmt_qty(saldo_inicial)} {unidad}"

            ws["A6"] = "Resumen"
            ws["A6"].font = Font(bold=True)
            for i, (label, key) in enumerate(
                [
                    ("Entradas", "tot_entradas"),
                    ("Ventas", "tot_ventas"),
                    ("Anulaciones", "tot_anul"),
                    ("Neto", "neto"),
                    ("Saldo final", "saldo_final"),
                ],
                start=7,
            ):
                ws[f"A{i}"] = label
                ws[f"B{i}"] = f"{fmt_qty(payload[key])} {unidad}"

            ws["A11"].font = Font(bold=True)
            ws["B11"].font = Font(bold=True)

            start_row = 13
            headers = [
                "Fecha",
                "Tipo",
                "Referencia",
                f"Cantidad ({unidad})",
                "Precio",
                "Subtotal",
                f"Saldo ({unidad})",
            ]
            for col, htxt in enumerate(headers, 1):
                ws.cell(start_row, col, htxt).font = Font(bold=True)

            for i, r in enumerate(rows, start=start_row + 1):
                ws.cell(i, 1, fmt_fecha(r.fecha))
                ws.cell(i, 2, (r.tipo or "").upper().strip())
                ws.cell(i, 3, r.referencia or "")
                ws.cell(i, 4, fmt_qty(r.cantidad)).alignment = align_right
                ws.cell(i, 5, fmt_cop(r.precio)).alignment = align_right
                ws.cell(i, 6, fmt_cop(r.subtotal)).alignment = align_right
                ws.cell(i, 7, fmt_qty(r.saldo)).alignment = align_right

            for col in range(1, 8):
                ws.column_dimensions[get_column_letter(col)].width = 18
            ws.column_dimensions["C"].width = 55

            wb.save(path)
            QMessageBox.information(self, "OK", "Excel exportado correctamente.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
