from datetime import datetime, date


def fmt_fecha(dt) -> str:
    """
    Formatea fecha o datetime como DD/MM/AAAA HH:MM
    """
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
