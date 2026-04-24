"""
app/ui/customer_pdf.py
──────────────────────────────────────────────────────────────────────────────
Exportación a PDF del historial de compras de un cliente.
Extraído de customers_window.py para mantener archivos manejables.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
)

from app.utils.formatters import fmt_cop as _fmt_cop, fmt_qty as _qty


def mostrar_factura_compacta(parent, sale_id: int) -> None:
    """Muestra diálogo con factura compacta de la venta y permite exportar a PDF."""
    from app.ui.sale_receipt import exportar_recibo_pdf

    exportar_recibo_pdf(parent, sale_id)


def exportar_historial_cliente_pdf(
    parent, customer, ventas: list, desde: date, hasta: date
) -> None:
    try:
        from reportlab.lib.pagesizes import A4  # noqa: F401
    except ImportError:
        QMessageBox.critical(
            parent,
            "Dependencia faltante",
            "Instala reportlab:\n\n  pip install reportlab",
        )
        return

    if not ventas:
        QMessageBox.information(
            parent, "Sin datos", "No hay compras en el período seleccionado."
        )
        return

    # ── Elegir color o blanco y negro ────────────────────────────────────────
    dlg_modo = QDialog(parent)
    dlg_modo.setWindowTitle("Estilo del PDF")
    dlg_modo.setFixedWidth(320)
    dlg_modo.setStyleSheet("background:#0b1120; color:#e2e8f0; font-family:'Segoe UI';")
    lay_m = QVBoxLayout(dlg_modo)
    lay_m.setSpacing(12)
    lay_m.setContentsMargins(20, 20, 20, 20)
    lbl_m = QLabel("¿Cómo deseas imprimir el historial?")
    lbl_m.setStyleSheet("font-size:13px; font-weight:600;")
    lay_m.addWidget(lbl_m)
    row_m = QHBoxLayout()
    btn_color = QPushButton("🎨  A color")
    btn_color.setStyleSheet(
        "background:#1e3a5f; border:1px solid #3b82f6; border-radius:8px;"
        " padding:10px; font-weight:700; color:#93c5fd;"
    )
    btn_bw = QPushButton("🖨  Blanco y negro")
    btn_bw.setStyleSheet(
        "background:#1a1a1a; border:1px solid #475569; border-radius:8px;"
        " padding:10px; font-weight:700; color:#e2e8f0;"
    )
    row_m.addWidget(btn_color)
    row_m.addWidget(btn_bw)
    lay_m.addLayout(row_m)
    _modo = ["color"]
    btn_color.clicked.connect(
        lambda: (_modo.__setitem__(0, "color"), dlg_modo.accept())
    )
    btn_bw.clicked.connect(lambda: (_modo.__setitem__(0, "bw"), dlg_modo.accept()))
    if dlg_modo.exec() != QDialog.Accepted:
        return
    modo_bw = _modo[0] == "bw"

    nombre_slug = customer.nombre.replace(" ", "_")[:20]
    default = (
        f"historial_{nombre_slug}_"
        f"{desde.strftime('%Y%m%d')}_al_{hasta.strftime('%Y%m%d')}.pdf"
    )
    path, _ = QFileDialog.getSaveFileName(
        parent, "Guardar historial PDF", default, "PDF (*.pdf)"
    )
    if not path:
        return

    try:
        _build_historial_pdf(path, customer, ventas, desde, hasta, modo_bw=modo_bw)
        QMessageBox.information(
            parent, "✅ Exportado", f"Historial guardado en:\n{path}"
        )
    except Exception as e:
        QMessageBox.critical(parent, "Error al generar PDF", str(e))


def _build_historial_pdf(
    path: str, customer, ventas: list, desde: date, hasta: date, modo_bw: bool = False
) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as rl_canvas
    from app.utils.config_manager import cargar_config
    from app.db.database import get_app_data_dir

    cfg = cargar_config()
    empresa = cfg.get("empresa_nombre") or "Inventario JH"
    empresa_tel = cfg.get("empresa_telefono", "")

    PAGE_W, PAGE_H = A4
    c = rl_canvas.Canvas(path, pagesize=A4)
    W, H = PAGE_W, PAGE_H

    if modo_bw:
        COL_BG = colors.white
        COL_HEADER = colors.HexColor("#f0f0f0")
        COL_ACCENT = colors.HexColor("#333333")
        COL_TEXT = colors.black
        COL_MUTED = colors.HexColor("#555555")
        COL_GREEN = colors.black
        COL_YELLOW = colors.HexColor("#333333")
        COL_ROW_ALT = colors.HexColor("#eeeeee")
        COL_ROW_NORM = colors.white
        COL_LINE = colors.HexColor("#cccccc")
        COL_CAB_BG = colors.HexColor("#dddddd")
        COL_CAB_TXT = colors.HexColor("#333333")
    else:
        COL_BG = colors.HexColor("#0b1120")
        COL_HEADER = colors.HexColor("#0d1829")
        COL_ACCENT = colors.HexColor("#2563eb")
        COL_TEXT = colors.HexColor("#e2e8f0")
        COL_MUTED = colors.HexColor("#475569")
        COL_GREEN = colors.HexColor("#4ade80")
        COL_YELLOW = colors.HexColor("#fbbf24")
        COL_ROW_ALT = colors.HexColor("#0f1a2e")
        COL_ROW_NORM = colors.HexColor("#0b1120")
        COL_LINE = colors.HexColor("#1e293b")
        COL_CAB_BG = colors.HexColor("#1e3a5f")
        COL_CAB_TXT = colors.HexColor("#94a3b8")

    MARGIN = 14 * mm
    COL_W = W - 2 * MARGIN
    logo_path = get_app_data_dir() / "logo.png"

    def new_page():
        c.setFillColor(COL_BG)
        c.rect(0, 0, W, H, fill=1, stroke=0)

    def hline(y, color=None):
        c.setStrokeColor(color or COL_LINE)
        c.setLineWidth(0.4)
        c.line(MARGIN, y, W - MARGIN, y)

    page_num = [0]

    def draw_header(y_start):
        page_num[0] += 1
        new_page()
        y = y_start

        c.setFillColor(COL_ACCENT)
        c.rect(0, H - 16 * mm, W, 16 * mm, fill=1, stroke=0)

        if logo_path.exists():
            try:
                c.drawImage(
                    str(logo_path),
                    MARGIN,
                    H - 14 * mm,
                    width=30 * mm,
                    height=12 * mm,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(W / 2, H - 10 * mm, empresa.upper())
        if empresa_tel:
            c.setFont("Helvetica", 7)
            c.drawCentredString(W / 2, H - 13.5 * mm, f"Tel: {empresa_tel}")

        y = H - 22 * mm
        c.setFillColor(COL_TEXT)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(MARGIN, y, "HISTORIAL DE COMPRAS — CLIENTE")
        y -= 7 * mm

        c.setFillColor(COL_MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(MARGIN, y, "CLIENTE")
        c.setFillColor(COL_TEXT)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN + 18 * mm, y, customer.nombre)
        y -= 5 * mm

        if customer.documento:
            c.setFillColor(COL_MUTED)
            c.setFont("Helvetica", 7.5)
            c.drawString(MARGIN, y, f"Doc: {customer.documento}")
            y -= 4 * mm
        if customer.telefono:
            c.setFillColor(COL_MUTED)
            c.setFont("Helvetica", 7.5)
            c.drawString(MARGIN, y, f"Tel: {customer.telefono}")
            y -= 4 * mm

        c.setFillColor(COL_MUTED)
        c.setFont("Helvetica", 8)
        periodo = (
            f"Período: {desde.strftime('%d/%m/%Y')} — {hasta.strftime('%d/%m/%Y')}"
        )
        c.drawString(MARGIN, y, periodo)
        c.drawRightString(W - MARGIN, y, f"Página {page_num[0]}")
        y -= 3 * mm

        hline(y)
        y -= 3 * mm
        return y

    total_pagado = sum(
        float(s.total or 0)
        for s in ventas
        if getattr(s, "estado_pago", "PAGADO") == "PAGADO"
    )
    total_pendiente = sum(
        float(s.total or 0)
        for s in ventas
        if getattr(s, "estado_pago", "PAGADO") == "PENDIENTE"
    )

    y = draw_header(H)

    kpi_y = y - 2 * mm
    c.setFillColor(COL_HEADER)
    c.roundRect(MARGIN, kpi_y - 14 * mm, COL_W, 14 * mm, 3 * mm, fill=1, stroke=0)
    kpi_items = [
        ("COMPRAS", str(len(ventas))),
        ("TOTAL PAGADO", _fmt_cop(total_pagado)),
        ("PENDIENTE", _fmt_cop(total_pendiente)),
    ]
    kpi_col_w = COL_W / len(kpi_items)
    for i, (label, val) in enumerate(kpi_items):
        kx = MARGIN + i * kpi_col_w + kpi_col_w / 2
        c.setFillColor(COL_MUTED)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(kx, kpi_y - 5 * mm, label)
        col_val = COL_GREEN if i == 1 else (COL_YELLOW if i == 2 else COL_TEXT)
        c.setFillColor(col_val)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(kx, kpi_y - 11 * mm, val)
    y = kpi_y - 17 * mm

    hline(y)
    y -= 4 * mm

    COL_POSITIONS = {
        "factura": (MARGIN, 28 * mm),
        "fecha": (MARGIN + 30 * mm, 30 * mm),
        "productos": (MARGIN + 62 * mm, 68 * mm),
        "total": (MARGIN + 132 * mm, 28 * mm),
        "estado": (MARGIN + 162 * mm, 22 * mm),
    }

    def draw_table_header(y):
        c.setFillColor(COL_CAB_BG)
        c.rect(MARGIN, y - 6 * mm, COL_W, 7 * mm, fill=1, stroke=0)
        c.setFillColor(COL_CAB_TXT)
        c.setFont("Helvetica-Bold", 6.5)
        for xpos, txt in [
            (COL_POSITIONS["factura"][0], "N° FACTURA"),
            (COL_POSITIONS["fecha"][0], "FECHA"),
            (COL_POSITIONS["productos"][0], "PRODUCTOS"),
            (COL_POSITIONS["total"][0], "TOTAL"),
            (COL_POSITIONS["estado"][0], "ESTADO"),
        ]:
            c.drawString(xpos + 1 * mm, y - 4 * mm, txt)
        return y - 8 * mm

    y = draw_table_header(y)

    PROD_COL_X = COL_POSITIONS["productos"][0] + 1 * mm
    PROD_COL_W = COL_POSITIONS["productos"][1] - 2 * mm
    LINE_H = 4.2 * mm
    PAD_V = 2.0 * mm

    def wrap_productos(items: list[str], max_w: float, font_size: float) -> list[str]:
        c.setFont("Helvetica", font_size)
        lines, current = [], ""
        for item in items:
            probe = (current + " · " + item) if current else item
            if c.stringWidth(probe, "Helvetica", font_size) <= max_w:
                current = probe
            else:
                if current:
                    lines.append(current)
                while c.stringWidth(item, "Helvetica", font_size) > max_w:
                    cut = item
                    while (
                        cut and c.stringWidth(cut + "…", "Helvetica", font_size) > max_w
                    ):
                        cut = cut[:-1]
                    lines.append(cut + "…")
                    item = ""
                    break
                current = item
        if current:
            lines.append(current)
        return lines or ["—"]

    for idx, s in enumerate(ventas):
        es_pendiente = getattr(s, "estado_pago", "PAGADO") == "PENDIENTE"

        prods = []
        for d in s.details or []:
            nombre = d.product.nombre if d.product else f"#{d.product_id}"
            prods.append(f"{nombre} ({_qty(d.cantidad)})")
        prod_lines = wrap_productos(prods, PROD_COL_W, 6.5)

        row_h = max(7 * mm, len(prod_lines) * LINE_H + PAD_V * 2)

        if y - row_h < 25 * mm:
            c.showPage()
            y = draw_header(H)
            y = draw_table_header(y)

        bg = COL_ROW_ALT if idx % 2 == 0 else COL_ROW_NORM
        c.setFillColor(bg)
        c.rect(MARGIN, y - row_h, COL_W, row_h, fill=1, stroke=0)

        ty = y - PAD_V - LINE_H * 0.75
        mid_y = y - row_h / 2 - 1.5 * mm

        c.setFillColor(COL_TEXT)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(
            COL_POSITIONS["factura"][0] + 1 * mm, mid_y, s.numero_factura or f"#{s.id}"
        )

        c.setFillColor(COL_MUTED)
        c.setFont("Helvetica", 7)
        try:
            fecha_txt = s.fecha.strftime("%d/%m/%Y")
        except Exception:
            fecha_txt = str(s.fecha)
        c.drawString(COL_POSITIONS["fecha"][0] + 1 * mm, mid_y, fecha_txt)

        c.setFillColor(COL_TEXT)
        c.setFont("Helvetica", 6.5)
        for li, line_txt in enumerate(prod_lines):
            c.drawString(PROD_COL_X, ty - li * LINE_H, line_txt)

        col_total = COL_YELLOW if es_pendiente else COL_GREEN
        c.setFillColor(col_total)
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(
            COL_POSITIONS["total"][0] + COL_POSITIONS["total"][1] - 1 * mm,
            mid_y,
            _fmt_cop(float(s.total or 0)),
        )

        c.setFillColor(COL_YELLOW if es_pendiente else COL_GREEN)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(
            COL_POSITIONS["estado"][0] + 1 * mm,
            mid_y,
            "PENDIENTE" if es_pendiente else "PAGADO",
        )

        c.setStrokeColor(COL_LINE)
        c.setLineWidth(0.3)
        c.line(MARGIN, y - row_h, W - MARGIN, y - row_h)

        y -= row_h

    y -= 3 * mm
    hline(y)
    y -= 6 * mm
    c.setFillColor(COL_MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN, y, "TOTAL PAGADO")
    c.setFillColor(COL_GREEN)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(W - MARGIN, y, _fmt_cop(total_pagado))
    if total_pendiente > 0:
        y -= 7 * mm
        c.setFillColor(COL_MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(MARGIN, y, "TOTAL PENDIENTE")
        c.setFillColor(COL_YELLOW)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(W - MARGIN, y, _fmt_cop(total_pendiente))

    y -= 10 * mm
    c.setFillColor(COL_MUTED)
    c.setFont("Helvetica", 6)
    c.drawCentredString(
        W / 2,
        y,
        f"Generado por {empresa} — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )
    c.save()
