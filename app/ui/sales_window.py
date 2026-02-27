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

from app.db.products_repo import listar_productos  # ← repo, no SessionLocal directo
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

        # --- Tabla de items ---
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(
            ["ID", "Producto", "Cant", "Precio", "Subtotal"]
        )
        self.tbl.setColumnHidden(0, True)
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

        self.btn_anular = QPushButton("Anular venta seleccionada")
        bottom.addWidget(self.btn_anular)

        # Eventos
        self.btn_agregar.clicked.connect(self.agregar_item)
        self.btn_quitar.clicked.connect(self.quitar_item)
        self.btn_guardar.clicked.connect(self.guardar_venta)
        self.btn_anular.clicked.connect(self.anular_seleccionada)

        # Al cambiar producto, rellena el precio de venta automáticamente
        self.cbo_producto.currentIndexChanged.connect(self._rellenar_precio)

        self._productos: dict[int, object] = {}  # id -> producto
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
    # Productos  ← usa products_repo, sin SessionLocal en la UI
    # -----------------------
    def cargar_productos(self) -> None:
        lista = listar_productos(texto="", incluir_inactivos=False)

        self._productos = {p.id: p for p in lista}

        self.cbo_producto.blockSignals(True)
        self.cbo_producto.clear()
        for p in lista:
            stock_txt = (
                f"{int(p.stock_actual)}"
                if float(p.stock_actual or 0).is_integer()
                else f"{p.stock_actual:g}"
            )
            self.cbo_producto.addItem(f"{p.nombre}  (Stock: {stock_txt})", p.id)
        self.cbo_producto.blockSignals(False)

        self._rellenar_precio()

    def _rellenar_precio(self) -> None:
        """Rellena el spinbox de precio con el precio_venta del producto seleccionado."""
        product_id = self.cbo_producto.currentData()
        if not product_id:
            return
        p = self._productos.get(int(product_id))
        if p:
            self.sp_precio.setValue(float(p.precio_venta or 0.0))

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

        sale = obtener_venta_con_detalle(int(sale_id_item.text()))
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

        # Validar stock disponible antes de agregar a la lista
        p = self._productos.get(product_id)
        if p:
            stock = float(getattr(p, "stock_actual", 0.0) or 0.0)
            ya_en_lista = sum(
                float(i["cantidad"])
                for i in self.items
                if int(i["product_id"]) == product_id
            )
            if (ya_en_lista + cantidad) > stock:
                QMessageBox.warning(
                    self,
                    "Stock insuficiente",
                    f"Stock disponible para '{p.nombre}': {stock:g}\n"
                    f"Ya en lista: {ya_en_lista:g}  +  Nuevo: {cantidad:g} = {ya_en_lista + cantidad:g}",
                )
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
        total = sum(float(i["cantidad"]) * float(i["precio_venta"]) for i in self.items)
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
            f"Venta #{sale.id} guardada.\n"
            f"Total: {self._fmt_money(float(sale.total))}\n"
            f"Método: {metodo}",
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
        metodo = self.cbo_metodo.currentText()

        confirm = QMessageBox.question(
            self,
            "Confirmar anulación",
            f"¿Anular la venta #{sale_id}?\n"
            f"Esto devolverá el stock y registrará EGRESO en caja.",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            anular_venta(sale_id, motivo="Anulada desde UI", metodo_pago=metodo)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        QMessageBox.information(
            self,
            "OK",
            f"Venta #{sale_id} anulada. Stock devuelto y caja actualizada.",
        )
        self.cargar_historial()
        self.cargar_productos()
        self.tbl_det.setRowCount(0)
