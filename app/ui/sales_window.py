from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
)

from app.db.database import SessionLocal
from app.db.models import Product
from app.db.sales_repo import (
    crear_venta,
    listar_ventas,
    obtener_venta_con_detalle,
    anular_venta,
)


class SalesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ventas")
        self.resize(900, 560)

        self.items: list[dict] = []

        root = QVBoxLayout(self)

        # --- Controles de agregar item ---
        top = QHBoxLayout()
        root.addLayout(top)

        top.addWidget(QLabel("Producto:"))
        self.cbo_producto = QComboBox()
        top.addWidget(self.cbo_producto, 3)

        top.addWidget(QLabel("Cant:"))
        self.sp_cant = QDoubleSpinBox()
        self.sp_cant.setDecimals(2)
        self.sp_cant.setRange(0.01, 9999999)
        self.sp_cant.setValue(1)
        top.addWidget(self.sp_cant, 1)

        top.addWidget(QLabel("Precio:"))
        self.sp_precio = QDoubleSpinBox()
        self.sp_precio.setDecimals(2)
        self.sp_precio.setRange(0, 999999999)
        self.sp_precio.setValue(0)
        top.addWidget(self.sp_precio, 1)

        self.btn_agregar = QPushButton("Agregar")
        top.addWidget(self.btn_agregar, 1)

        # --- Método de pago (FULL caja) ---
        pay = QHBoxLayout()
        root.addLayout(pay)

        pay.addWidget(QLabel("Método de pago:"))
        self.cbo_metodo = QComboBox()
        self.cbo_metodo.addItems(
            ["Efectivo", "Transferencia", "Nequi", "Débito", "Crédito"]
        )
        pay.addWidget(self.cbo_metodo, 1)
        pay.addStretch()

        # --- Tabla de items ---
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(
            ["ID", "Producto", "Cant", "Precio", "Subtotal"]
        )
        self.tbl.setColumnHidden(0, True)  # ocultar product_id
        self.tbl.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.tbl, 1)

        # --- Historial de ventas ---
        root.addWidget(QLabel("Historial (últimas ventas):"))

        self.tbl_hist = QTableWidget(0, 3)
        self.tbl_hist.setHorizontalHeaderLabels(["ID", "Fecha", "Total"])
        self.tbl_hist.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.tbl_hist, 1)

        root.addWidget(QLabel("Detalle de la venta seleccionada:"))

        self.tbl_det = QTableWidget(0, 4)
        self.tbl_det.setHorizontalHeaderLabels(
            ["Producto", "Cant", "Precio", "Subtotal"]
        )
        self.tbl_det.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.tbl_det, 1)

        self.tbl_hist.itemSelectionChanged.connect(self.cargar_detalle_seleccionado)

        # --- Footer ---
        bottom = QHBoxLayout()
        root.addLayout(bottom)

        self.lbl_total = QLabel("Total: $0,00")
        self.lbl_total.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        bottom.addWidget(self.lbl_total, 1)

        self.btn_quitar = QPushButton("Quitar seleccionado")
        bottom.addWidget(self.btn_quitar)

        self.btn_guardar = QPushButton("Guardar venta")
        bottom.addWidget(self.btn_guardar)

        # Anular venta
        self.btn_anular = QPushButton("Anular venta seleccionada")
        bottom.addWidget(self.btn_anular)

        # Eventos
        self.btn_agregar.clicked.connect(self.agregar_item)
        self.btn_quitar.clicked.connect(self.quitar_item)
        self.btn_guardar.clicked.connect(self.guardar_venta)
        self.btn_anular.clicked.connect(self.anular_seleccionada)

        self.cargar_productos()
        self.cargar_historial()

    # -----------------------
    # Utilidades formato $
    # -----------------------
    def _fmt_money(self, value: float) -> str:
        return (
            "${:,.2f}".format(float(value or 0.0))
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    # -----------------------
    # Historial / Detalle
    # -----------------------
    def cargar_historial(self) -> None:
        ventas = listar_ventas(200)
        self.tbl_hist.setRowCount(0)

        for s in ventas:
            row = self.tbl_hist.rowCount()
            self.tbl_hist.insertRow(row)

            self.tbl_hist.setItem(row, 0, QTableWidgetItem(str(s.id)))
            self.tbl_hist.setItem(row, 1, QTableWidgetItem(str(s.fecha)))

            estado = " (ANULADA)" if getattr(s, "anulada", False) else ""
            self.tbl_hist.setItem(
                row,
                2,
                QTableWidgetItem(f"{self._fmt_money(float(s.total or 0.0))}{estado}"),
            )

        self.tbl_det.setRowCount(0)

    def cargar_detalle_seleccionado(self) -> None:
        row = self.tbl_hist.currentRow()
        if row < 0:
            return

        sale_id_item = self.tbl_hist.item(row, 0)
        if not sale_id_item:
            return

        sale_id = int(sale_id_item.text())
        sale = obtener_venta_con_detalle(sale_id)
        if not sale:
            return

        self.tbl_det.setRowCount(0)
        for d in sale.details:
            row = self.tbl_det.rowCount()
            self.tbl_det.insertRow(row)

            nombre = d.product.nombre if d.product else f"ID {d.product_id}"
            self.tbl_det.setItem(row, 0, QTableWidgetItem(nombre))
            self.tbl_det.setItem(row, 1, QTableWidgetItem(f"{float(d.cantidad):.2f}"))
            self.tbl_det.setItem(
                row, 2, QTableWidgetItem(self._fmt_money(float(d.precio_venta)))
            )
            self.tbl_det.setItem(
                row, 3, QTableWidgetItem(self._fmt_money(float(d.subtotal)))
            )

    # -----------------------
    # Productos
    # -----------------------
    def cargar_productos(self) -> None:
        self.cbo_producto.clear()
        with SessionLocal() as db:
            products = (
                db.query(Product)
                .filter(Product.activo.is_(True))  # noqa: E712
                .order_by(Product.nombre.asc())
                .all()
            )

        for p in products:
            self.cbo_producto.addItem(f"{p.nombre} (Stock: {p.stock_actual})", p.id)

    # -----------------------
    # Items venta
    # -----------------------
    def agregar_item(self) -> None:
        if self.cbo_producto.count() == 0:
            QMessageBox.warning(self, "Ventas", "No hay productos activos para vender.")
            return

        product_id = int(self.cbo_producto.currentData())
        nombre = self.cbo_producto.currentText()
        cantidad = float(self.sp_cant.value())
        precio = float(self.sp_precio.value())

        if cantidad <= 0:
            QMessageBox.warning(self, "Ventas", "La cantidad debe ser mayor que 0.")
            return
        if precio < 0:
            QMessageBox.warning(self, "Ventas", "El precio no puede ser negativo.")
            return

        subtotal = cantidad * precio

        self.items.append(
            {"product_id": product_id, "cantidad": cantidad, "precio_venta": precio}
        )

        row = self.tbl.rowCount()
        self.tbl.insertRow(row)

        self.tbl.setItem(row, 0, QTableWidgetItem(str(product_id)))
        self.tbl.setItem(row, 1, QTableWidgetItem(nombre))
        self.tbl.setItem(row, 2, QTableWidgetItem(f"{cantidad:.2f}"))
        self.tbl.setItem(row, 3, QTableWidgetItem(self._fmt_money(precio)))
        self.tbl.setItem(row, 4, QTableWidgetItem(self._fmt_money(subtotal)))

        self.actualizar_total()

    def quitar_item(self) -> None:
        row = self.tbl.currentRow()
        if row < 0:
            return

        try:
            self.items.pop(row)
        except Exception:
            pass

        self.tbl.removeRow(row)
        self.actualizar_total()

    def actualizar_total(self) -> None:
        total = 0.0
        for it in self.items:
            total += float(it["cantidad"]) * float(it["precio_venta"])
        self.lbl_total.setText(f"Total: {self._fmt_money(total)}")

    # -----------------------
    # Guardar / Anular
    # -----------------------
    def guardar_venta(self) -> None:
        if not self.items:
            QMessageBox.warning(self, "Ventas", "Agrega al menos 1 producto.")
            return

        metodo = self.cbo_metodo.currentText()

        try:
            # ✅ FULL CAJA: pasamos metodo_pago al repo (queda en CashMovement.observacion)
            sale = crear_venta(self.items, metodo_pago=metodo)
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))
            return

        QMessageBox.information(
            self,
            "Venta guardada",
            f"Venta #{sale.id} guardada.\nTotal: {self._fmt_money(float(sale.total))}\nMétodo: {metodo}",
        )

        # limpiar para nueva venta
        self.items.clear()
        self.tbl.setRowCount(0)
        self.actualizar_total()
        self.cargar_productos()  # refresca stock mostrado
        self.cargar_historial()

    def anular_seleccionada(self) -> None:
        row = self.tbl_hist.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ventas", "Selecciona una venta del historial.")
            return

        sale_id_item = self.tbl_hist.item(row, 0)
        if not sale_id_item:
            return

        sale_id = int(sale_id_item.text())

        confirm = QMessageBox.question(
            self,
            "Confirmar anulación",
            f"¿Anular la venta #{sale_id}?\nEsto devolverá el stock y registrará EGRESO en caja.",
        )
        if confirm != QMessageBox.Yes:
            return

        metodo = self.cbo_metodo.currentText()

        try:
            # ✅ FULL CAJA: pasamos metodo y motivo para que quede trazabilidad en caja
            anular_venta(sale_id, motivo="Anulada desde UI", metodo_pago=metodo)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        QMessageBox.information(
            self, "OK", f"Venta #{sale_id} anulada. Stock devuelto y caja actualizada."
        )
        self.cargar_historial()
        self.cargar_productos()
        self.tbl_det.setRowCount(0)
