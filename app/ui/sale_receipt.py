"""
app/ui/sale_receipt.py
──────────────────────────────────────────────────────────────────────────────
Generación de recibo PDF de venta — formato ticket vertical (80 mm de ancho)
y guardado en ruta elegida por el usuario.

Uso:
    from app.ui.sale_receipt import exportar_recibo_pdf
    exportar_recibo_pdf(parent_widget, sale_id)
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox


# ── helpers de formato ────────────────────────────────────────────────────────
def _cop(value) -> str:
    """Formato COP sin depender del locale del sistema."""
    try:
        n = int(round(float(value or 0)))
        # Formatear manualmente para evitar problemas de locale
        s = ""
        neg = n < 0
        n = abs(n)
        digits = str(n)
        # Agregar puntos cada 3 dígitos desde la derecha
        for i, ch in enumerate(reversed(digits)):
            if i > 0 and i % 3 == 0:
                s = "." + s
            s = ch + s
        return ("$-" if neg else "$") + s
    except Exception:
        return "$0"


def _qty(value) -> str:
    try:
        v = float(value or 0)
        s = f"{v:.3f}".rstrip("0").rstrip(".")
        return s.replace(".", ",")
    except Exception:
        return "0"


# ── función pública ───────────────────────────────────────────────────────────
def exportar_recibo_pdf(parent, sale_id: int) -> None:
    """
    Genera y guarda el recibo PDF de la venta `sale_id`.
    Muestra diálogo de guardado y mensajes de éxito/error al usuario.
    """
    # 1. Importar reportlab (opcional en el proyecto)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm, cm
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.platypus import Table, TableStyle
    except ImportError:
        QMessageBox.critical(
            parent,
            "Dependencia faltante",
            "Instala reportlab:\n\n  pip install reportlab",
        )
        return

    # 2. Cargar la venta
    try:
        from app.db.sales_repo import obtener_venta_con_detalle

        sale = obtener_venta_con_detalle(sale_id)
    except Exception as e:
        QMessageBox.critical(parent, "Error", f"No se pudo cargar la venta:\n{e}")
        return

    if not sale:
        QMessageBox.information(parent, "Recibo", "Venta no encontrada.")
        return

    # 3. Elegir destino
    factura_slug = (
        (sale.numero_factura or str(sale.id)).replace("/", "-").replace(" ", "_")
    )
    default_name = f"recibo_{factura_slug}.pdf"
    path, _ = QFileDialog.getSaveFileName(
        parent, "Guardar recibo PDF", default_name, "PDF (*.pdf)"
    )
    if not path:
        return

    # 4. Construir PDF
    try:
        _build_pdf(path, sale)
        QMessageBox.information(
            parent, "✅ Recibo exportado", f"Recibo guardado en:\n{path}"
        )
    except Exception as e:
        QMessageBox.critical(parent, "Error al generar PDF", str(e))


# ── construcción del PDF ──────────────────────────────────────────────────────
def _build_pdf(path: str, sale) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

    # ── Datos de la venta ────────────────────────────────────────────────────
    try:
        fecha_txt = sale.fecha.strftime("%d/%m/%Y  %H:%M")
    except Exception:
        fecha_txt = str(getattr(sale, "fecha", ""))

    factura_txt = sale.numero_factura or f"#{sale.id}"
    cliente_nombre = sale.customer.nombre if getattr(sale, "customer", None) else "—"
    es_anulada = getattr(sale, "anulada", False)
    es_pendiente = getattr(sale, "estado_pago", "PAGADO") == "PENDIENTE"

    if es_anulada:
        estado_label = "ANULADA"
        estado_color = colors.HexColor("#ef4444")
    elif es_pendiente:
        estado_label = "PENDIENTE DE COBRO"
        estado_color = colors.HexColor("#f59e0b")
    else:
        estado_label = "PAGADO"
        estado_color = colors.HexColor("#22c55e")

    # ── Logo ─────────────────────────────────────────────────────────────────
    from app.db.database import get_app_data_dir

    logo_path = get_app_data_dir() / "logo.png"
    has_logo = logo_path.exists()

    # ── Página: ticket vertical 80 mm ancho ──────────────────────────────────
    PAGE_W = 80 * mm
    # Altura dinámica según cantidad de productos
    n_items = len(sale.details) if sale.details else 0
    PAGE_H = max(180 * mm, (120 + n_items * 14 + 60) * mm / 3.7)

    c = rl_canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H))
    W, H = PAGE_W, PAGE_H

    # ── Fondo oscuro ─────────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#0b1120"))
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Banda superior de color según estado ─────────────────────────────────
    c.setFillColor(estado_color)
    c.rect(0, H - 6 * mm, W, 6 * mm, fill=1, stroke=0)

    y = H - 6 * mm  # cursor vertical, baja desde arriba

    # ── Logo (si existe) ──────────────────────────────────────────────────────
    if has_logo:
        logo_h = 28 * mm
        logo_w = 60 * mm
        y -= logo_h + 3 * mm
        c.drawImage(
            str(logo_path),
            (W - logo_w) / 2,
            y,
            width=logo_w,
            height=logo_h,
            preserveAspectRatio=True,
            mask="auto",
        )
        y -= 3 * mm
    else:
        y -= 6 * mm

    # ── Encabezado empresa ────────────────────────────────────────────────────
    from app.utils.config_manager import cargar_config

    cfg = cargar_config()
    empresa_nombre = cfg.get("empresa_nombre") or "Inventario JH"
    empresa_tel = cfg.get("empresa_telefono", "")
    empresa_dir = cfg.get("empresa_direccion", "")

    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W / 2, y, empresa_nombre.upper())
    y -= 5 * mm

    if empresa_tel:
        c.setFillColor(colors.HexColor("#475569"))
        c.setFont("Helvetica", 7)
        c.drawCentredString(W / 2, y, f"Tel: {empresa_tel}")
        y -= 4 * mm

    if empresa_dir:
        c.setFillColor(colors.HexColor("#475569"))
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(W / 2, y, empresa_dir[:40])
        y -= 4 * mm

    y -= 3 * mm

    # ── Línea divisora ────────────────────────────────────────────────────────
    def hline(ypos, color="#1e3a5f", dash=None):
        c.setStrokeColor(colors.HexColor(color))
        c.setLineWidth(0.5)
        if dash:
            c.setDash(dash)
        c.line(4 * mm, ypos, W - 4 * mm, ypos)
        c.setDash([])

    hline(y)
    y -= 5 * mm

    # ── N° Factura + estado ───────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#e2e8f0"))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W / 2, y, f"FACTURA  {factura_txt}")
    y -= 5 * mm

    # Badge estado
    badge_w = 32 * mm
    badge_x = (W - badge_w) / 2
    c.setFillColor(estado_color)
    c.roundRect(badge_x, y - 1 * mm, badge_w, 5 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(W / 2, y + 0.8 * mm, estado_label)
    y -= 8 * mm

    hline(y, dash=[2, 2])
    y -= 4 * mm

    # ── Info cliente / fecha ──────────────────────────────────────────────────
    def row_info(label: str, value: str, ypos: float) -> float:
        c.setFillColor(colors.HexColor("#475569"))
        c.setFont("Helvetica", 6.5)
        c.drawString(4 * mm, ypos, label.upper())
        c.setFillColor(colors.HexColor("#e2e8f0"))
        c.setFont("Helvetica-Bold", 7.5)
        c.drawRightString(W - 4 * mm, ypos, value)
        return ypos - 5 * mm

    y = row_info("Cliente", cliente_nombre[:28], y)
    y = row_info("Fecha", fecha_txt, y)
    y -= 2 * mm

    hline(y)
    y -= 5 * mm

    # ── Cabecera tabla productos ──────────────────────────────────────────────
    # 3 columnas: PRODUCTO | CANT x PRECIO | SUBTOTAL
    col_sub = W - 4 * mm
    col_mid = W * 0.60

    c.setFillColor(colors.HexColor("#1e3a5f"))
    c.rect(4 * mm, y - 1 * mm, W - 8 * mm, 6 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(5 * mm, y + 1 * mm, "PRODUCTO")
    c.drawCentredString(col_mid, y + 1 * mm, "CANT x PRECIO")
    c.drawRightString(col_sub, y + 1 * mm, "SUBTOTAL")
    y -= 7 * mm

    # ── Filas productos ───────────────────────────────────────────────────────
    for i, d in enumerate(sale.details or []):
        nombre = (d.product.nombre if d.product else f"Prod #{d.product_id}")[:20]
        cant = _qty(d.cantidad)
        precio = _cop(d.precio_venta)
        subtot = _cop(d.subtotal)
        cant_x_precio = f"{cant} x {precio}"

        row_h = 5.5 * mm

        # Fila alterna
        if i % 2 == 0:
            c.setFillColor(colors.HexColor("#0d1829"))
            c.rect(4 * mm, y - 1 * mm, W - 8 * mm, row_h, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#cbd5e1"))
        c.setFont("Helvetica", 7)
        c.drawString(5 * mm, y + 1 * mm, nombre)

        c.setFillColor(colors.HexColor("#94a3b8"))
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(col_mid, y + 1 * mm, cant_x_precio)

        c.setFillColor(colors.HexColor("#4ade80"))
        c.setFont("Helvetica-Bold", 7)
        c.drawRightString(col_sub, y + 1 * mm, subtot)

        y -= row_h

    y -= 2 * mm
    hline(y)
    y -= 5 * mm

    # ── Total ─────────────────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 8)
    c.drawString(4 * mm, y, "TOTAL")
    c.setFillColor(estado_color)
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(W - 4 * mm, y - 1 * mm, _cop(sale.total))
    y -= 10 * mm

    hline(y, dash=[1, 3])
    y -= 5 * mm

    # ── Pie ───────────────────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#1e293b"))
    c.setFont("Helvetica", 6)
    c.drawCentredString(W / 2, y, "Gracias por su compra")
    y -= 4 * mm
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(W / 2, y, f"Generado por {empresa_nombre}")

    c.save()
