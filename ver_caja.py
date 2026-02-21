from app.db.database import init_db
from app.db.cash_repo import listar_movimientos, obtener_saldo

init_db()

print("Saldo:", obtener_saldo())
for m in listar_movimientos(20):
    print(m.id, m.fecha, m.tipo, m.concepto, m.monto, m.referencia)
