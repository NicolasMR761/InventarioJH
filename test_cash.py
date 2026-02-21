from app.db.database import init_db
from app.db.cash_repo import registrar_movimiento, listar_movimientos, obtener_saldo

init_db()

registrar_movimiento("INGRESO", "Apertura de caja", 50000, referencia="Inicial")
registrar_movimiento("EGRESO", "Pago transporte", 8000)

print("Saldo:", obtener_saldo())
print("Últimos movimientos:")
for m in listar_movimientos(10):
    print(m.id, m.fecha, m.tipo, m.concepto, m.monto, m.referencia)
