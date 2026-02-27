from datetime import datetime, date


def fmt_fecha(dt) -> str:
    """Formatea fecha o datetime como DD/MM/AAAA HH:MM"""
    if not dt:
        return ""
    try:
        if isinstance(dt, datetime):
            return dt.strftime("%d/%m/%Y %H:%M")
        if isinstance(dt, date):
            return dt.strftime("%d/%m/%Y")
        return str(dt)
    except Exception:
        return str(dt)


def fmt_cop(value, decimales: bool = False) -> str:
    """
    Formatea un valor numérico como pesos colombianos (COP).

    Ejemplos:
        fmt_cop(5000)        → "$5.000"
        fmt_cop(5000.5)      → "$5.000"
        fmt_cop(5000.5, True)→ "$5.000,50"
        fmt_cop(0)           → "$0"
        fmt_cop(None)        → "$0"

    Reglas COP:
    - Separador de miles  : punto   ( . )
    - Separador decimal   : coma    ( , )
    - Sin decimales por defecto (los centavos son poco usados en COP)
    """
    try:
        v = float(value or 0.0)
    except Exception:
        v = 0.0

    if decimales:
        # Ej: $5.000,50
        s = "{:,.2f}".format(v)  # "5,000.50"  (formato inglés)
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # "5.000,50"
        return f"${s}"
    else:
        # Ej: $5.000
        n = int(round(v))
        return "$" + f"{n:,}".replace(",", ".")


def fmt_qty(value) -> str:
    """
    Formatea cantidades sin separador de miles.
    - Enteros : "6"
    - Decimales: "6,5"  (coma decimal, estilo COP/ES)

    Ejemplos:
        fmt_qty(6)    → "6"
        fmt_qty(6.5)  → "6,5"
        fmt_qty(6.25) → "6,25"
    """
    try:
        v = float(value or 0.0)
        s = f"{v:.3f}".rstrip("0").rstrip(".")
        return s.replace(".", ",")
    except Exception:
        return "0"
