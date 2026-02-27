from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.db.database import SessionLocal
from app.db.models import Entry, EntryDetail, Sale, SaleDetail, Supplier


@dataclass
class KardexRow:
    fecha: datetime
    tipo: str  # ENTRADA | VENTA | ANULACION
    referencia: str
    cantidad: float  # + entra, - sale
    precio: float
    subtotal: float
    saldo: float = 0.0


def obtener_kardex(
    product_id: int,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> dict:
    """
    Retorna:
      {
        "saldo_inicial": float,
        "rows": list[KardexRow],
        "advertencias": list[str]   ← ✅ FIX #3: avisa ventas con anulación fuera del rango
      }

    Regla para ventas anuladas:
      - registra la VENTA en sale.fecha (cantidad negativa)
      - registra la ANULACION en sale.anulada_en (cantidad positiva)
      - Si la VENTA está dentro del rango pero la ANULACION cae fuera (o viceversa),
        se genera una advertencia para que la UI informe al usuario.
    """
    pid = int(product_id)

    with SessionLocal() as db:
        compras = (
            db.query(
                Entry.fecha,
                Entry.id,
                Supplier.nombre,
                EntryDetail.cantidad,
                EntryDetail.precio_compra,
                EntryDetail.subtotal,
            )
            .join(EntryDetail, EntryDetail.entry_id == Entry.id)
            .join(Supplier, Supplier.id == Entry.supplier_id)
            .filter(EntryDetail.product_id == pid)
            .all()
        )

        ventas = (
            db.query(
                Sale.fecha,
                Sale.id,
                Sale.anulada,
                Sale.anulada_en,
                SaleDetail.cantidad,
                SaleDetail.precio_venta,
                SaleDetail.subtotal,
            )
            .join(SaleDetail, SaleDetail.sale_id == Sale.id)
            .filter(SaleDetail.product_id == pid)
            .all()
        )

    movimientos: list[KardexRow] = []
    advertencias: list[str] = []

    # Compras -> ENTRADA (+)
    for fecha, entry_id, proveedor, cant, precio, sub in compras:
        movimientos.append(
            KardexRow(
                fecha=fecha,
                tipo="ENTRADA",
                referencia=f"Compra #{entry_id} ({proveedor})",
                cantidad=float(cant or 0.0),
                precio=float(precio or 0.0),
                subtotal=float(sub or 0.0),
            )
        )

    # Ventas -> VENTA (-) y si anulada -> ANULACION (+)
    for fecha, sale_id, anulada, anulada_en, cant, precio, sub in ventas:
        cant = float(cant or 0.0)
        precio = float(precio or 0.0)
        sub = float(sub or 0.0)

        movimientos.append(
            KardexRow(
                fecha=fecha,
                tipo="VENTA",
                referencia=f"Venta #{sale_id}",
                cantidad=-cant,
                precio=precio,
                subtotal=-sub,
            )
        )

        if bool(anulada) and anulada_en:
            movimientos.append(
                KardexRow(
                    fecha=anulada_en,
                    tipo="ANULACION",
                    referencia=f"Anulación Venta #{sale_id}",
                    cantidad=+cant,
                    precio=precio,
                    subtotal=+sub,
                )
            )

            # ✅ FIX #3: Detectar si VENTA y ANULACION quedan en lados opuestos del rango
            if desde or hasta:
                venta_en_rango = True
                anulacion_en_rango = True

                if desde:
                    venta_en_rango = venta_en_rango and (fecha >= desde)
                    anulacion_en_rango = anulacion_en_rango and (anulada_en >= desde)
                if hasta:
                    venta_en_rango = venta_en_rango and (fecha <= hasta)
                    anulacion_en_rango = anulacion_en_rango and (anulada_en <= hasta)

                if venta_en_rango and not anulacion_en_rango:
                    advertencias.append(
                        f"⚠️ Venta #{sale_id} aparece en el rango pero su anulación "
                        f"({anulada_en.strftime('%d/%m/%Y')}) cae fuera. "
                        f"El saldo puede aparecer más bajo de lo real."
                    )
                elif anulacion_en_rango and not venta_en_rango:
                    advertencias.append(
                        f"⚠️ Anulación de Venta #{sale_id} aparece en el rango pero la venta original "
                        f"({fecha.strftime('%d/%m/%Y')}) cae fuera. "
                        f"El saldo puede aparecer más alto de lo real."
                    )

    # Orden cronológico
    movimientos.sort(key=lambda r: (r.fecha or datetime.min, r.tipo))

    # Saldo inicial = movimientos antes de "desde"
    saldo_inicial = 0.0
    if desde:
        for r in movimientos:
            if r.fecha and r.fecha < desde:
                saldo_inicial += float(r.cantidad or 0.0)

    # Filtrar rango
    rows: list[KardexRow] = []
    for r in movimientos:
        if desde and r.fecha and r.fecha < desde:
            continue
        if hasta and r.fecha and r.fecha > hasta:
            continue
        rows.append(r)

    # Calcular saldo acumulado
    saldo = saldo_inicial
    for r in rows:
        saldo += float(r.cantidad or 0.0)
        r.saldo = saldo

    return {
        "saldo_inicial": saldo_inicial,
        "rows": rows,
        "advertencias": advertencias,
    }
