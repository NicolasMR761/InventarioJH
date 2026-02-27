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

from app.db.products_repo import listar_productos
from app.db.sales_repo import (
    crear_venta,
    listar_ventas,
    obtener_venta_con_detalle,
    anular_venta,
)
from app.utils.formatters import fmt_fecha


class SalesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ventas")
        self.resize(900, 560)

        self.items: list[dict] = []

        root = QVBoxLayout(self)

        # --- Controles agregar item ---
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

        # --- Método de pago ---
        pay = QHBoxLayout()
        root.addLayout(pay)

        pay.addWidget(QLabel("Método de pago:"))
        self.cbo_metodo = QComboBox()
        self.cbo_metodo.addItems(
            ["Efectivo", "Transferencia", "Nequi", "Débito", "Crédito"]
        )
        pay.addWidget(self.cbo_metodo, 1)
        pay.addStretch()

        # --- Tabla items venta actual ---
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(
            ["ID", "Producto", "Cant", "Precio", "Subtotal"]
        )
        self.tbl.setColumnHidden(0, True)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.tbl, 1)

        # --- Historial ---
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

        self.btn_anular = QPushButton("Anular venta seleccionada")
        bottom.addWidget(self.btn_anular)

        self.btn_agregar.clicked.connect(self.agregar_item)
        self.btn_quitar.clicked.connect(self.quitar_item)
        self.btn_guardar.clicked.connect(self.guardar_venta)
        self.btn_anular.clicked.connect(self.anular_seleccionada)

        # ✅ Cache de productos: lista de dicts para evitar DetachedInstanceError
        self._productos_cache: list[dict] = []

        self.cargar_productos()
        self.cargar_historial()

    # -----------------------
    # Formato $
    # -----------------------
    def _fmt_money(self, value: float) -> str:
        return (
            "${:,.2f}".format(float(value or 0.0))
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    # -----------------------
    # Productos
    # ✅ FIX #3: Carga atributos dentro de la sesión y guarda en cache de dicts
    # (evita DetachedInstanceError al acceder a product.nombre fuera de sesión)
    # -----------------------
    def cargar_productos(self) -> None:
        self._productos_cache = []
        self.cbo_producto.clear()

        productos = listar_productos("", incluir_inactivos=False)
        for p in productos:
            entry = {
                "id": p.id,
                "nombre": p.nombre,
                "stock_actual": float(p.stock_actual or 0.0),
                "precio_venta": float(p.precio_venta or 0.0),
            }
            self._productos_cache.append(entry)
            self.cbo_producto.addItem(
                f"{p.nombre}  (Stock: {entry['stock_actual']:.0f})", p.id
            )

        # Auto-completar precio con el precio_venta del producto seleccionado
        self.cbo_producto.currentIndexChanged.connect(self._autocompletar_precio)
        self._autocompletar_precio(self.cbo_producto.currentIndex())

    def _autocompletar_precio(self, index: int) -> None:
        """Rellena el spinbox de precio con el precio_venta del producto seleccionado."""
        if index < 0 or index >= len(self._productos_cache):
            return
        precio = self._productos_cache[index]["precio_venta"]
        if precio > 0:
            self.sp_precio.setValue(precio)

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
            self.tbl_hist.setItem(row, 1, QTableWidgetItem(fmt_fecha(s.fecha)))
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
            r = self.tbl_det.rowCount()
            self.tbl_det.insertRow(r)
            nombre = d.product.nombre if d.product else f"ID {d.product_id}"
            self.tbl_det.setItem(r, 0, QTableWidgetItem(nombre))
            self.tbl_det.setItem(r, 1, QTableWidgetItem(f"{float(d.cantidad):.2f}"))
            self.tbl_det.setItem(
                r, 2, QTableWidgetItem(self._fmt_money(float(d.precio_venta)))
            )
            self.tbl_det.setItem(
                r, 3, QTableWidgetItem(self._fmt_money(float(d.subtotal)))
            )

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
        total = sum(
            float(it["cantidad"]) * float(it["precio_venta"]) for it in self.items
        )
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
            sale = crear_venta(self.items, metodo_pago=metodo)
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))
            return

        QMessageBox.information(
            self,
            "Venta guardada",
            f"Venta #{sale.id} guardada.\nTotal: {self._fmt_money(float(sale.total))}\nMétodo: {metodo}",
        )

        self.items.clear()
        self.tbl.setRowCount(0)
        self.actualizar_total()
        self.cargar_productos()
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
