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
from app.utils.formatters import fmt_fecha


def _fmt_qty(x: float) -> str:
    """
    Cantidades: sin separador de miles, con hasta 3 decimales,
    y sin ceros a la derecha.
    5.0   -> "5"
    5.5   -> "5,5"
    5.250 -> "5,25"
    """
    try:
        v = float(x or 0.0)
        s = f"{v:.3f}".rstrip("0").rstrip(".")
        return s.replace(".", ",")
    except Exception:
        return "0"


def _fmt_cop(value: float) -> str:
    try:
        s = "${:,.2f}".format(float(value or 0.0))
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "$0,00"


def _item(
    text: str, align: Qt.AlignmentFlag | Qt.Alignment = Qt.AlignLeft | Qt.AlignVCenter
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

        # -------------------
        # Filtros
        # -------------------
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

        # -------------------
        # Info saldo inicial
        # -------------------
        self.lbl_info = QLabel("Saldo inicial: 0")
        self.lbl_info.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.lbl_info)

        # -------------------
        # Tabla
        # -------------------
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
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Fecha
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Tipo
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Referencia
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Cantidad
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Precio
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Subtotal
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Saldo

        layout.addWidget(self.table, 1)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # -------------------
        # Resumen inferior (pro)
        # -------------------
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

        # Cache: product_id -> unidad
        self._prod_unidad: dict[int, str] = {}

        self._cargar_productos()
        self.cargar()

    def _cargar_productos(self):
        self.cbo_producto.clear()
        self._prod_unidad.clear()

        productos = listar_productos("", incluir_inactivos=False)
        for p in productos:
            unidad = (getattr(p, "unidad", "") or "").strip() or "und"
            self._prod_unidad[p.id] = unidad
            self.cbo_producto.addItem(f"{p.codigo} - {p.nombre} ({unidad})", p.id)

    def _row_brush(self, tipo: str) -> QBrush | None:
        """
        Fondo MUY suave para diferenciar visualmente (sin parecer dinero).
        """
        t = (tipo or "").upper().strip()
        if t == "ENTRADA":
            return QBrush(QColor(30, 120, 60, 35))  # verde tenue
        if t == "VENTA":
            return QBrush(QColor(200, 60, 60, 35))  # rojo tenue
        if t == "ANULACION":
            return QBrush(QColor(200, 140, 30, 35))  # naranja tenue
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
                tot_ventas += abs(c)  # en kardex viene negativo
            elif t == "ANULACION":
                tot_anul += c

        neto = tot_entradas - tot_ventas + tot_anul
        saldo_final = float(rows[-1].saldo) if rows else 0.0

        self.lbl_tot_entradas.setText(f"Entradas: {_fmt_qty(tot_entradas)} {unidad}")
        self.lbl_tot_ventas.setText(f"Ventas: {_fmt_qty(tot_ventas)} {unidad}")
        self.lbl_tot_anul.setText(f"Anulaciones: {_fmt_qty(tot_anul)} {unidad}")
        self.lbl_neto.setText(f"Neto: {_fmt_qty(neto)} {unidad}")
        self.lbl_saldo_final.setText(f"Saldo final: {_fmt_qty(saldo_final)} {unidad}")

    def cargar(self):
        if self.cbo_producto.count() == 0:
            self.table.setRowCount(0)
            self.lbl_info.setText("Saldo inicial: 0")
            self._set_resumen("und", [])
            return

        product_id = int(self.cbo_producto.currentData())
        unidad = self._prod_unidad.get(product_id, "und")

        # Encabezados dinámicos con unidad
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
            f"Saldo inicial (antes del rango): {_fmt_qty(saldo_inicial)} {unidad}"
        )

        self.table.setRowCount(len(rows))

        font_tipo = QFont()
        font_tipo.setBold(True)

        for i, r in enumerate(rows):
            fecha_txt = fmt_fecha(r.fecha)
            tipo_txt = (r.tipo or "").upper().strip()
            ref_txt = r.referencia or ""

            it_fecha = _item(fecha_txt, Qt.AlignLeft | Qt.AlignVCenter)
            it_tipo = _item(tipo_txt, Qt.AlignLeft | Qt.AlignVCenter)
            it_ref = _item(ref_txt, Qt.AlignLeft | Qt.AlignVCenter)

            it_cant = _item(_fmt_qty(r.cantidad), Qt.AlignRight | Qt.AlignVCenter)
            it_precio = _item(_fmt_cop(r.precio), Qt.AlignRight | Qt.AlignVCenter)
            it_sub = _item(_fmt_cop(r.subtotal), Qt.AlignRight | Qt.AlignVCenter)
            it_saldo = _item(_fmt_qty(r.saldo), Qt.AlignRight | Qt.AlignVCenter)

            it_tipo.setFont(font_tipo)
            it_ref.setToolTip(ref_txt)

            self.table.setItem(i, 0, it_fecha)
            self.table.setItem(i, 1, it_tipo)
            self.table.setItem(i, 2, it_ref)
            self.table.setItem(i, 3, it_cant)
            self.table.setItem(i, 4, it_precio)
            self.table.setItem(i, 5, it_sub)
            self.table.setItem(i, 6, it_saldo)

            brush = self._row_brush(tipo_txt)
            if brush is not None:
                for col in range(7):
                    cell = self.table.item(i, col)
                    if cell is not None:
                        cell.setBackground(brush)

        self.table.resizeRowsToContents()
        self._set_resumen(unidad, rows)

    # -------------------
    # Exportar (PDF / Excel)
    # -------------------

    def _kardex_para_exportar(self):
        """
        Trae el kardex completo del rango actual (sin depender de lo que esté pintado en tabla).
        """
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

        # Totales
        tot_entradas = 0.0
        tot_ventas = 0.0
        tot_anul = 0.0
        for r in rows:
            t = (r.tipo or "").upper().strip()
            c = float(r.cantidad or 0.0)
            if t == "ENTRADA":
                tot_entradas += c
            elif t == "VENTA":
                tot_ventas += abs(c)  # viene negativo
            elif t == "ANULACION":
                tot_anul += c

        neto = tot_entradas - tot_ventas + tot_anul
        saldo_final = float(rows[-1].saldo) if rows else 0.0

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
            "neto": neto,
            "saldo_final": saldo_final,
        }

    def exportar_pdf(self):
        """
        PDF compacto, pero con la Referencia COMPLETA (se ajusta a varias líneas).
        """
        try:
            payload = self._kardex_para_exportar()
            if not payload:
                QMessageBox.information(self, "Kardex", "No hay datos para exportar.")
                return

            producto = payload["producto_text"]
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
                c.drawString(2 * cm, y, f"Producto: {producto}")
                y -= 0.5 * cm
                c.drawString(2 * cm, y, f"Rango: {d1} a {d2}")
                y -= 0.5 * cm
                c.drawString(
                    2 * cm,
                    y,
                    f"Saldo inicial (antes del rango): {_fmt_qty(saldo_inicial)} {unidad}",
                )
                y -= 0.8 * cm

                # Resumen
                c.setFont("Helvetica-Bold", 11)
                c.drawString(2 * cm, y, "Resumen")
                y -= 0.55 * cm

                c.setFont("Helvetica", 10)
                c.drawString(
                    2 * cm, y, f"Entradas: {_fmt_qty(payload['tot_entradas'])} {unidad}"
                )
                y -= 0.45 * cm
                c.drawString(
                    2 * cm, y, f"Ventas: {_fmt_qty(payload['tot_ventas'])} {unidad}"
                )
                y -= 0.45 * cm
                c.drawString(
                    2 * cm, y, f"Anulaciones: {_fmt_qty(payload['tot_anul'])} {unidad}"
                )
                y -= 0.45 * cm
                c.drawString(2 * cm, y, f"Neto: {_fmt_qty(payload['neto'])} {unidad}")
                y -= 0.45 * cm
                c.drawString(
                    2 * cm,
                    y,
                    f"Saldo final: {_fmt_qty(payload['saldo_final'])} {unidad}",
                )
                y -= 0.85 * cm

                # Encabezados tabla
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

            def ensure_space(min_y=2 * cm):
                nonlocal y
                if y < min_y:
                    c.showPage()
                    y = h - 2 * cm
                    header_page()

            def wrap_text(text: str, max_width: float) -> list[str]:
                """
                Wrap simple basado en ancho en puntos.
                """
                words = (text or "").split()
                if not words:
                    return [""]
                lines = []
                line = words[0]
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

            # Layout columnas
            x_fecha = 2 * cm
            x_tipo = 5.2 * cm
            x_ref = 7.3 * cm
            x_cant_r = 14.2 * cm
            x_prec_r = 16.7 * cm
            x_sub_r = 19.5 * cm

            ref_col_width = (
                x_cant_r - x_ref - 0.3 * cm
            )  # ancho disponible para referencia

            for r in rows:
                fecha_txt = str(fmt_fecha(r.fecha) or "")[:16]
                tipo_txt = (r.tipo or "").upper().strip()
                ref_txt = r.referencia or ""

                cant_txt = _fmt_qty(r.cantidad)
                precio_txt = _fmt_cop(r.precio)
                sub_txt = _fmt_cop(r.subtotal)

                ref_lines = wrap_text(ref_txt, ref_col_width)
                needed_height = max(1, len(ref_lines)) * 0.42 * cm + 0.05 * cm

                ensure_space(min_y=2 * cm + needed_height)

                # Dibujo fila (fecha/tipo solo en primera línea)
                c.drawString(x_fecha, y, fecha_txt)
                c.drawString(x_tipo, y, tipo_txt[:10])

                # referencia (multi línea)
                yy = y
                for li, line in enumerate(ref_lines):
                    c.drawString(x_ref, yy, line)
                    yy -= 0.42 * cm

                # números (alineados a la derecha en la primera línea)
                c.drawRightString(x_cant_r, y, cant_txt)
                c.drawRightString(x_prec_r, y, precio_txt)
                c.drawRightString(x_sub_r, y, sub_txt)

                y -= needed_height

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

            producto = payload["producto_text"]
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

            wb = Workbook()
            ws = wb.active
            ws.title = "Kardex"

            # Encabezado
            ws["A1"] = "Kardex por Producto"
            ws["A1"].font = Font(bold=True, size=14)

            ws["A2"] = "Producto:"
            ws["B2"] = producto
            ws["A3"] = "Rango:"
            ws["B3"] = f"{d1} a {d2}"
            ws["A4"] = "Saldo inicial:"
            ws["B4"] = f"{_fmt_qty(saldo_inicial)} {unidad}"

            # Resumen
            ws["A6"] = "Resumen"
            ws["A6"].font = Font(bold=True)

            ws["A7"] = "Entradas"
            ws["B7"] = f"{_fmt_qty(payload['tot_entradas'])} {unidad}"
            ws["A8"] = "Ventas"
            ws["B8"] = f"{_fmt_qty(payload['tot_ventas'])} {unidad}"
            ws["A9"] = "Anulaciones"
            ws["B9"] = f"{_fmt_qty(payload['tot_anul'])} {unidad}"
            ws["A10"] = "Neto"
            ws["B10"] = f"{_fmt_qty(payload['neto'])} {unidad}"
            ws["A11"] = "Saldo final"
            ws["B11"] = f"{_fmt_qty(payload['saldo_final'])} {unidad}"
            ws["A11"].font = Font(bold=True)
            ws["B11"].font = Font(bold=True)

            # Tabla (desde fila 13)
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
            for col, htxt in enumerate(headers, start=1):
                cell = ws.cell(row=start_row, column=col, value=htxt)
                cell.font = Font(bold=True)

            # Datos
            align_right = Alignment(horizontal="right")
            for i, r in enumerate(rows, start=start_row + 1):
                ws.cell(i, 1, fmt_fecha(r.fecha))
                ws.cell(i, 2, (r.tipo or "").upper().strip())
                ws.cell(i, 3, r.referencia or "")

                c4 = ws.cell(i, 4, _fmt_qty(r.cantidad))
                c4.alignment = align_right

                c5 = ws.cell(i, 5, _fmt_cop(r.precio))
                c5.alignment = align_right

                c6 = ws.cell(i, 6, _fmt_cop(r.subtotal))
                c6.alignment = align_right

                # Saldo (si necesitas saldo en excel, debe venir en rows)
                c7 = ws.cell(i, 7, _fmt_qty(r.saldo))
                c7.alignment = align_right

            # Ajuste de columnas
            for col in range(1, 8):
                ws.column_dimensions[get_column_letter(col)].width = 18
            ws.column_dimensions["C"].width = 55  # Referencia más amplia

            wb.save(path)
            QMessageBox.information(self, "OK", "Excel exportado correctamente.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
