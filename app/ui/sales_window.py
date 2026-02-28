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
    QLineEdit,
    QCompleter,
    QDialog,
    QTextEdit,
    QHeaderView,
)

from app.db.products_repo import listar_productos
from app.db.customers_repo import listar_clientes, crear_cliente
from app.db.sales_repo import (
    crear_venta,
    listar_ventas,
    listar_ventas_pendientes,
    obtener_venta_con_detalle,
    anular_venta,
    registrar_pago_pendiente,
)
from app.utils.formatters import fmt_fecha


class SalesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ventas")
        self.resize(980, 660)

        self.items: list[dict] = []
        self._productos_cache: list[dict] = []
        self._clientes_cache: list[dict] = []

        root = QVBoxLayout(self)

        # ─────────────────────────────────────────
        # Fila 1: Producto + Cant + Precio + Agregar
        # ─────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Producto:"))
        self.cbo_producto = QComboBox()
        self.cbo_producto.setMinimumWidth(220)
        row1.addWidget(self.cbo_producto, 3)

        row1.addWidget(QLabel("Cant:"))
        self.sp_cant = QDoubleSpinBox()
        self.sp_cant.setDecimals(2)
        self.sp_cant.setRange(0.01, 9999999)
        self.sp_cant.setValue(1)
        row1.addWidget(self.sp_cant, 1)

        row1.addWidget(QLabel("Precio:"))
        self.sp_precio = QDoubleSpinBox()
        self.sp_precio.setDecimals(2)
        self.sp_precio.setRange(0, 999999999)
        self.sp_precio.setValue(0)
        row1.addWidget(self.sp_precio, 1)

        self.btn_agregar = QPushButton("Agregar")
        row1.addWidget(self.btn_agregar)
        root.addLayout(row1)

        # ─────────────────────────────────────────
        # Fila 2: Cliente + Factura + Pago + Método
        # ─────────────────────────────────────────
        row2 = QHBoxLayout()

        row2.addWidget(QLabel("Cliente:"))
        self.txt_cliente = QLineEdit()
        self.txt_cliente.setPlaceholderText("Nombre (opcional)")
        self.txt_cliente.setMinimumWidth(160)
        row2.addWidget(self.txt_cliente, 2)

        self.btn_nuevo_cliente = QPushButton("+ Cliente")
        self.btn_nuevo_cliente.setToolTip("Crear cliente con el nombre escrito")
        row2.addWidget(self.btn_nuevo_cliente)

        row2.addWidget(QLabel("N° Factura:"))
        self.txt_factura = QLineEdit()
        self.txt_factura.setPlaceholderText("Ej: 001, FAC-123…")
        self.txt_factura.setMaximumWidth(120)
        row2.addWidget(self.txt_factura)

        row2.addWidget(QLabel("Pago:"))
        self.cbo_estado_pago = QComboBox()
        self.cbo_estado_pago.addItems(["PAGADO", "PENDIENTE (Fiado)"])
        row2.addWidget(self.cbo_estado_pago)

        row2.addWidget(QLabel("Método:"))
        self.cbo_metodo = QComboBox()
        self.cbo_metodo.addItems(
            ["Efectivo", "Transferencia", "Nequi", "Débito", "Crédito"]
        )
        row2.addWidget(self.cbo_metodo)

        root.addLayout(row2)

        # ─────────────────────────────────────────
        # Tabla items venta actual
        # ─────────────────────────────────────────
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(
            ["ID", "Producto", "Cant", "Precio", "Subtotal"]
        )
        self.tbl.setColumnHidden(0, True)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setMaximumHeight(150)
        root.addWidget(self.tbl)

        # Footer nueva venta
        foot_new = QHBoxLayout()
        self.lbl_total = QLabel("Total: $0,00")
        self.lbl_total.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        foot_new.addWidget(self.lbl_total, 1)
        self.btn_quitar = QPushButton("Quitar seleccionado")
        self.btn_guardar = QPushButton("💾 Guardar venta")
        foot_new.addWidget(self.btn_quitar)
        foot_new.addWidget(self.btn_guardar)
        root.addLayout(foot_new)

        # ─────────────────────────────────────────
        # Fiados pendientes
        # ─────────────────────────────────────────
        root.addWidget(QLabel("💳 Ventas pendientes (fiado):"))
        self.tbl_pendientes = QTableWidget(0, 6)
        self.tbl_pendientes.setHorizontalHeaderLabels(
            ["ID", "Factura", "Fecha", "Cliente", "Total", "Cobrar"]
        )
        self.tbl_pendientes.horizontalHeader().setStretchLastSection(True)
        self.tbl_pendientes.setMaximumHeight(130)
        root.addWidget(self.tbl_pendientes)

        # ─────────────────────────────────────────
        # Historial
        # ─────────────────────────────────────────
        hdr_hist = QHBoxLayout()
        hdr_hist.addWidget(QLabel("📋 Historial de ventas:"))
        hdr_hist.addStretch()
        self.btn_refrescar = QPushButton("🔄 Refrescar")  # ← UN solo botón
        hdr_hist.addWidget(self.btn_refrescar)
        root.addLayout(hdr_hist)

        self.tbl_hist = QTableWidget(0, 6)
        self.tbl_hist.setHorizontalHeaderLabels(
            ["ID", "Factura", "Fecha", "Cliente", "Total", ""]
        )
        self.tbl_hist.horizontalHeader().setStretchLastSection(False)
        self.tbl_hist.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        root.addWidget(self.tbl_hist, 1)

        root.addWidget(QLabel("Detalle:"))
        self.tbl_det = QTableWidget(0, 4)
        self.tbl_det.setHorizontalHeaderLabels(
            ["Producto", "Cant", "Precio", "Subtotal"]
        )
        self.tbl_det.horizontalHeader().setStretchLastSection(True)
        self.tbl_det.setMaximumHeight(110)
        root.addWidget(self.tbl_det)

        foot_hist = QHBoxLayout()
        foot_hist.addStretch()
        self.btn_anular = QPushButton("❌ Anular venta seleccionada")
        foot_hist.addWidget(self.btn_anular)
        root.addLayout(foot_hist)

        # ─────────────────────────────────────────
        # Señales
        # ─────────────────────────────────────────
        self.btn_agregar.clicked.connect(self.agregar_item)
        self.btn_quitar.clicked.connect(self.quitar_item)
        self.btn_guardar.clicked.connect(self.guardar_venta)
        self.btn_anular.clicked.connect(self.anular_seleccionada)
        self.btn_nuevo_cliente.clicked.connect(self.crear_cliente_rapido)
        self.btn_refrescar.clicked.connect(self.refrescar_todo)
        self.tbl_hist.itemSelectionChanged.connect(self.cargar_detalle_seleccionado)
        self.cbo_producto.currentIndexChanged.connect(self._autocompletar_precio)
        self.cbo_estado_pago.currentIndexChanged.connect(self._toggle_metodo)

        self.refrescar_todo()

    # ─────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────
    def _fmt_money(self, value: float) -> str:
        return (
            "${:,.2f}".format(float(value or 0.0))
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    def _toggle_metodo(self):
        es_pendiente = "PENDIENTE" in self.cbo_estado_pago.currentText()
        self.cbo_metodo.setEnabled(not es_pendiente)

    def _autocompletar_precio(self, index: int):
        if 0 <= index < len(self._productos_cache):
            precio = self._productos_cache[index]["precio_venta"]
            if precio > 0:
                self.sp_precio.setValue(precio)

    def _customer_id_por_nombre(self) -> int | None:
        nombre = self.txt_cliente.text().strip()
        if not nombre:
            return None
        for c in self._clientes_cache:
            if c["nombre"].lower() == nombre.lower():
                return c["id"]
        return None

    # ─────────────────────────────────────────
    # Refrescar todo de una vez
    # ─────────────────────────────────────────
    def refrescar_todo(self):
        self.cargar_productos()
        self.cargar_clientes()
        self.cargar_historial()
        self.cargar_pendientes()

    # ─────────────────────────────────────────
    # Carga de datos
    # ─────────────────────────────────────────
    def cargar_productos(self):
        self._productos_cache = []
        self.cbo_producto.clear()
        for p in listar_productos("", incluir_inactivos=False):
            self._productos_cache.append(
                {
                    "id": p.id,
                    "nombre": p.nombre,
                    "stock_actual": float(p.stock_actual or 0.0),
                    "precio_venta": float(p.precio_venta or 0.0),
                }
            )
            self.cbo_producto.addItem(
                f"{p.nombre}  (Stock: {float(p.stock_actual or 0):.0f})", p.id
            )
        self._autocompletar_precio(self.cbo_producto.currentIndex())

    def cargar_clientes(self):
        self._clientes_cache = []
        nombres = []
        for c in listar_clientes("", incluir_inactivos=False):
            self._clientes_cache.append({"id": c.id, "nombre": c.nombre})
            nombres.append(c.nombre)
        completer = QCompleter(nombres)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.txt_cliente.setCompleter(completer)

    def cargar_historial(self):
        ventas = listar_ventas(200)
        self.tbl_hist.setRowCount(0)
        for s in ventas:
            row = self.tbl_hist.rowCount()
            self.tbl_hist.insertRow(row)
            cliente_nombre = s.customer.nombre if getattr(s, "customer", None) else "—"
            estado = ""
            if getattr(s, "anulada", False):
                estado = " ❌"
            elif getattr(s, "estado_pago", "PAGADO") == "PENDIENTE":
                estado = " ⏳"
            self.tbl_hist.setItem(row, 0, QTableWidgetItem(str(s.id)))
            self.tbl_hist.setItem(row, 1, QTableWidgetItem(s.numero_factura or "—"))
            self.tbl_hist.setItem(row, 2, QTableWidgetItem(fmt_fecha(s.fecha)))
            self.tbl_hist.setItem(row, 3, QTableWidgetItem(cliente_nombre))
            self.tbl_hist.setItem(
                row,
                4,
                QTableWidgetItem(f"{self._fmt_money(float(s.total or 0))}{estado}"),
            )
            sale_id = int(s.id)
            btn = QPushButton("Ver detalle")
            btn.clicked.connect(lambda _, sid=sale_id: self.ver_detalle_venta(sid))
            self.tbl_hist.setCellWidget(row, 5, btn)
        self.tbl_det.setRowCount(0)

    def cargar_pendientes(self):
        pendientes = listar_ventas_pendientes()
        self.tbl_pendientes.setRowCount(0)
        for s in pendientes:
            row = self.tbl_pendientes.rowCount()
            self.tbl_pendientes.insertRow(row)
            cliente_nombre = (
                s.customer.nombre if getattr(s, "customer", None) else "Sin cliente"
            )
            self.tbl_pendientes.setItem(row, 0, QTableWidgetItem(str(s.id)))
            self.tbl_pendientes.setItem(
                row, 1, QTableWidgetItem(s.numero_factura or "—")
            )
            self.tbl_pendientes.setItem(row, 2, QTableWidgetItem(fmt_fecha(s.fecha)))
            self.tbl_pendientes.setItem(row, 3, QTableWidgetItem(cliente_nombre))
            self.tbl_pendientes.setItem(
                row, 4, QTableWidgetItem(self._fmt_money(float(s.total or 0)))
            )
            sale_id = int(s.id)
            btn = QPushButton("💵 Cobrar")
            btn.clicked.connect(lambda _, sid=sale_id: self.cobrar_pendiente(sid))
            self.tbl_pendientes.setCellWidget(row, 5, btn)

    def cargar_detalle_seleccionado(self):
        row = self.tbl_hist.currentRow()
        if row < 0:
            return
        item = self.tbl_hist.item(row, 0)
        if not item:
            return
        sale = obtener_venta_con_detalle(int(item.text()))
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

    # ─────────────────────────────────────────
    # Acciones
    # ─────────────────────────────────────────
    def crear_cliente_rapido(self):
        nombre = self.txt_cliente.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Cliente", "Escribe un nombre primero.")
            return
        for c in self._clientes_cache:
            if c["nombre"].lower() == nombre.lower():
                QMessageBox.information(self, "Cliente", f"'{nombre}' ya existe.")
                return
        try:
            nuevo = crear_cliente(nombre)
            self._clientes_cache.append({"id": nuevo.id, "nombre": nuevo.nombre})
            self.cargar_clientes()
            QMessageBox.information(self, "Cliente", f"Cliente '{nombre}' creado.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def ver_detalle_venta(self, sale_id: int) -> None:
        sale = obtener_venta_con_detalle(sale_id)
        if not sale:
            QMessageBox.information(self, "Detalle", "No se encontró la venta.")
            return

        fecha_txt = ""
        if getattr(sale, "fecha", None):
            try:
                fecha_txt = sale.fecha.strftime("%d/%m/%Y  %H:%M")
            except Exception:
                fecha_txt = str(sale.fecha)

        es_anulada = getattr(sale, "anulada", False)
        es_pendiente = getattr(sale, "estado_pago", "PAGADO") == "PENDIENTE"

        if es_anulada:
            color = "#ef4444"
            label_estado = "ANULADA"
            emoji = "✕"
        elif es_pendiente:
            color = "#f59e0b"
            label_estado = "PENDIENTE"
            emoji = "⏳"
        else:
            color = "#22c55e"
            label_estado = "PAGADO"
            emoji = "✓"

        cliente_nombre = (
            sale.customer.nombre if getattr(sale, "customer", None) else "—"
        )
        factura_txt = sale.numero_factura or f"#{sale.id}"

        # Filas de productos
        items_html = ""
        for d in sale.details:
            nombre = d.product.nombre if d.product else f"Producto #{d.product_id}"
            cant = float(d.cantidad or 0)
            cant_txt = f"{int(cant)}" if cant == int(cant) else f"{cant:g}"
            items_html += f"""
            <tr>
                <td style='padding:7px 0;color:#cbd5e1;font-size:13px;
                           border-bottom:1px solid #1e293b;'>{nombre}</td>
                <td style='padding:7px 0;color:#94a3b8;font-size:12px;
                           border-bottom:1px solid #1e293b;text-align:center;'>{cant_txt}</td>
                <td style='padding:7px 0;color:#94a3b8;font-size:12px;
                           border-bottom:1px solid #1e293b;text-align:right;'>
                    {self._fmt_money(float(d.precio_venta or 0))}</td>
                <td style='padding:7px 0;color:#e2e8f0;font-size:13px;font-weight:600;
                           border-bottom:1px solid #1e293b;text-align:right;'>
                    {self._fmt_money(float(d.subtotal or 0))}</td>
            </tr>"""

        html = f"""
        <html><body style='margin:0;padding:0;background:#0a0f1e;
                           font-family:"Segoe UI",Arial,sans-serif;'>
        <div style='background:#0a0f1e;padding:0 0 8px 0;'>

            <!-- BANDA SUPERIOR -->
            <div style='background:linear-gradient(135deg,{color}cc,{color}66);
                        padding:20px 28px 16px 28px;'>
                <div style='font-size:10px;color:rgba(255,255,255,0.65);letter-spacing:3px;
                            text-transform:uppercase;margin-bottom:6px;'>
                    INVENTARIO JH &nbsp;·&nbsp; Comprobante de Venta
                </div>
                <div style='font-size:24px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;'>
                    {factura_txt}
                </div>
                <div style='margin-top:10px;'>
                    <span style='background:rgba(0,0,0,0.3);color:#fff;
                                 padding:3px 12px;border-radius:20px;font-size:11px;
                                 font-weight:700;letter-spacing:1.5px;'>
                        {emoji} {label_estado}
                    </span>
                    <span style='color:rgba(255,255,255,0.55);font-size:11px;margin-left:8px;'>
                        Cliente: {cliente_nombre}
                    </span>
                </div>
            </div>

            <!-- MONTO -->
            <div style='background:#0f172a;padding:20px 28px;border-bottom:1px solid #1e293b;'>
                <div style='font-size:10px;color:#475569;letter-spacing:3px;
                            margin-bottom:4px;text-transform:uppercase;'>Total venta</div>
                <div style='font-size:36px;font-weight:900;color:{color};letter-spacing:-1px;'>
                    {self._fmt_money(float(sale.total or 0))}
                </div>
            </div>

            <!-- DATOS -->
            <div style='padding:16px 28px;border-bottom:1px solid #1e293b;'>
                <table width='100%' cellspacing='0' cellpadding='0'>
                    <tr>
                        <td style='padding:6px 0;color:#475569;font-size:11px;
                                   text-transform:uppercase;letter-spacing:1px;width:38%;'>
                            N° Factura</td>
                        <td style='padding:6px 0;color:#e2e8f0;font-size:13px;
                                   font-weight:600;'>{factura_txt}</td>
                    </tr>
                    <tr>
                        <td style='padding:6px 0;color:#475569;font-size:11px;
                                   text-transform:uppercase;letter-spacing:1px;'>Fecha</td>
                        <td style='padding:6px 0;color:#e2e8f0;font-size:13px;
                                   font-weight:600;'>{fecha_txt}</td>
                    </tr>
                    <tr>
                        <td style='padding:6px 0;color:#475569;font-size:11px;
                                   text-transform:uppercase;letter-spacing:1px;'>Cliente</td>
                        <td style='padding:6px 0;color:#e2e8f0;font-size:13px;
                                   font-weight:600;'>{cliente_nombre}</td>
                    </tr>
                </table>
            </div>

            <!-- PRODUCTOS -->
            <div style='padding:14px 28px 8px 28px;'>
                <div style='font-size:10px;color:#475569;letter-spacing:2px;
                            text-transform:uppercase;margin-bottom:10px;'>Productos</div>
                <table width='100%' cellspacing='0' cellpadding='0'>
                    <tr>
                        <th style='text-align:left;font-size:10px;color:#334155;
                                   padding-bottom:6px;font-weight:600;
                                   border-bottom:1px solid #1e293b;'>Descripción</th>
                        <th style='text-align:center;font-size:10px;color:#334155;
                                   padding-bottom:6px;font-weight:600;
                                   border-bottom:1px solid #1e293b;'>Cant</th>
                        <th style='text-align:right;font-size:10px;color:#334155;
                                   padding-bottom:6px;font-weight:600;
                                   border-bottom:1px solid #1e293b;'>Precio</th>
                        <th style='text-align:right;font-size:10px;color:#334155;
                                   padding-bottom:6px;font-weight:600;
                                   border-bottom:1px solid #1e293b;'>Subtotal</th>
                    </tr>
                    {items_html}
                </table>
            </div>

        </div>
        </body></html>
        """

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Venta {factura_txt}")
        dlg.setFixedWidth(520)
        dlg.setStyleSheet("background: #0a0f1e;")

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 12)
        lay.setSpacing(0)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setHtml(html)
        txt.setStyleSheet(
            """
            QTextEdit {
                background: #0a0f1e;
                border: none;
                color: #e2e8f0;
            }
            QScrollBar:vertical {
                background: #0a0f1e;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 3px;
            }
        """
        )
        txt.setMinimumHeight(500)
        lay.addWidget(txt)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedWidth(120)
        btn_cerrar.setStyleSheet(
            """
            QPushButton {
                background: #1e3a5f;
                color: #e2e8f0;
                border: 1px solid #2563eb;
                border-radius: 6px;
                padding: 7px 0;
                font-weight: 700;
            }
            QPushButton:hover { background: #2563eb; }
        """
        )
        btn_cerrar.clicked.connect(dlg.accept)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn_cerrar)
        row.addStretch()
        lay.addLayout(row)

        dlg.exec()

    def agregar_item(self):
        if self.cbo_producto.count() == 0:
            QMessageBox.warning(self, "Ventas", "No hay productos activos.")
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

    def quitar_item(self):
        row = self.tbl.currentRow()
        if row < 0:
            return
        try:
            self.items.pop(row)
        except Exception:
            pass
        self.tbl.removeRow(row)
        self.actualizar_total()

    def actualizar_total(self):
        total = sum(float(i["cantidad"]) * float(i["precio_venta"]) for i in self.items)
        self.lbl_total.setText(f"Total: {self._fmt_money(total)}")

    def guardar_venta(self):
        if not self.items:
            QMessageBox.warning(self, "Ventas", "Agrega al menos 1 producto.")
            return

        # ✅ Factura obligatoria
        numero_factura = self.txt_factura.text().strip()
        if not numero_factura:
            QMessageBox.warning(
                self, "Campo obligatorio", "El número de factura es obligatorio."
            )
            self.txt_factura.setFocus()
            return

        # ✅ Cliente obligatorio
        nombre_txt = self.txt_cliente.text().strip()
        if not nombre_txt:
            QMessageBox.warning(self, "Campo obligatorio", "El cliente es obligatorio.")
            self.txt_cliente.setFocus()
            return

        metodo = self.cbo_metodo.currentText()
        es_pendiente = "PENDIENTE" in self.cbo_estado_pago.currentText()
        estado_pago = "PENDIENTE" if es_pendiente else "PAGADO"
        customer_id = self._customer_id_por_nombre()

        # Si el nombre no está en cache, ofrecer crear
        if not customer_id:
            resp = QMessageBox.question(
                self,
                "Cliente nuevo",
                f"'{nombre_txt}' no existe.\n¿Crear cliente nuevo?",
            )
            if resp == QMessageBox.Yes:
                try:
                    nuevo = crear_cliente(nombre_txt)
                    self._clientes_cache.append(
                        {"id": nuevo.id, "nombre": nuevo.nombre}
                    )
                    customer_id = nuevo.id
                    self.cargar_clientes()
                except Exception as e:
                    QMessageBox.critical(self, "Error", str(e))
                    return

        try:
            sale = crear_venta(
                self.items,
                metodo_pago=metodo,
                customer_id=customer_id,
                estado_pago=estado_pago,
                numero_factura=numero_factura,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))
            return

        estado_txt = "⏳ Pendiente de cobro (fiado)" if es_pendiente else "✅ Pagado"
        factura_txt = sale.numero_factura or f"#{sale.id}"
        QMessageBox.information(
            self,
            "Venta guardada",
            f"Venta {factura_txt} guardada.\n"
            f"Total: {self._fmt_money(float(sale.total))}\n"
            f"Estado: {estado_txt}",
        )
        self.items.clear()
        self.tbl.setRowCount(0)
        self.txt_cliente.clear()
        self.txt_factura.clear()
        self.actualizar_total()
        self.refrescar_todo()

    def cobrar_pendiente(self, sale_id: int):
        metodo = self.cbo_metodo.currentText()
        confirm = QMessageBox.question(
            self,
            "Cobrar fiado",
            f"¿Registrar cobro de la venta #{sale_id}?\nMétodo: {metodo}",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            registrar_pago_pendiente(sale_id, metodo_pago=metodo)
            QMessageBox.information(self, "OK", "Pago registrado y caja actualizada.")
            self.refrescar_todo()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def anular_seleccionada(self):
        row = self.tbl_hist.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ventas", "Selecciona una venta del historial.")
            return
        item = self.tbl_hist.item(row, 0)
        if not item:
            return
        sale_id = int(item.text())
        factura = (
            self.tbl_hist.item(row, 1).text()
            if self.tbl_hist.item(row, 1)
            else f"#{sale_id}"
        )
        confirm = QMessageBox.question(
            self,
            "Confirmar anulación",
            f"¿Anular la venta {factura}?\n"
            f"Esto devolverá el stock y (si estaba pagada) afectará la caja.",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            anular_venta(
                sale_id,
                motivo="Anulada desde UI",
                metodo_pago=self.cbo_metodo.currentText(),
            )
            QMessageBox.information(self, "OK", f"Venta {factura} anulada.")
            self.refrescar_todo()
            self.tbl_det.setRowCount(0)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
