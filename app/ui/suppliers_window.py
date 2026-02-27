from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QMessageBox,
)

from app.db.suppliers_repo import listar_proveedores, cambiar_estado_proveedor


class SuppliersWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proveedores")
        self.resize(900, 520)

        layout = QVBoxLayout(self)

        top = QHBoxLayout()

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar por nombre o NIT...")
        self.txt_buscar.textChanged.connect(self.cargar_proveedores)
        top.addWidget(self.txt_buscar)

        btn_refrescar = QPushButton("Refrescar")
        btn_refrescar.clicked.connect(self.cargar_proveedores)
        top.addWidget(btn_refrescar)

        btn_nuevo = QPushButton("Nuevo")
        btn_nuevo.clicked.connect(self.abrir_form_nuevo)
        top.addWidget(btn_nuevo)

        btn_editar = QPushButton("Editar")
        btn_editar.clicked.connect(self.abrir_form_editar)
        top.addWidget(btn_editar)

        btn_estado = QPushButton("Activar / Desactivar")
        btn_estado.clicked.connect(self.cambiar_estado_seleccionado)
        top.addWidget(btn_estado)

        top.addStretch()
        layout.addLayout(top)

        # Col 0 = ID oculto, el resto visible
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "NIT", "Teléfono", "Dirección", "Activo"]
        )
        self.table.setColumnHidden(0, True)  # ← ID oculto, usado para lookup
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self._dbl_click_editar)
        layout.addWidget(self.table)

        self._proveedores: dict[int, object] = {}  # id -> proveedor
        self.cargar_proveedores()

    def cargar_proveedores(self):
        texto = self.txt_buscar.text().strip()
        lista = listar_proveedores(texto=texto, incluir_inactivos=True)

        # Guardar como dict id->proveedor para lookup seguro
        self._proveedores = {p.id: p for p in lista}

        self.table.setRowCount(len(lista))

        for row, p in enumerate(lista):
            # Col 0: ID oculto — clave para lookup al seleccionar
            self.table.setItem(row, 0, QTableWidgetItem(str(p.id)))

            self.table.setItem(row, 1, QTableWidgetItem(p.nombre or ""))
            self.table.setItem(row, 2, QTableWidgetItem(p.nit or ""))
            self.table.setItem(row, 3, QTableWidgetItem(p.telefono or ""))
            self.table.setItem(row, 4, QTableWidgetItem(p.direccion or ""))
            self.table.setItem(row, 5, QTableWidgetItem("Sí" if p.activo else "No"))

        self.table.resizeColumnsToContents()

    def _get_selected(self):
        """
        Obtiene el proveedor seleccionado usando el ID de la col 0 (oculta).
        Funciona correctamente aunque la tabla esté ordenada por cualquier columna.
        """
        row = self.table.currentRow()
        if row < 0:
            return None
        id_item = self.table.item(row, 0)
        if not id_item:
            return None
        return self._proveedores.get(int(id_item.text()))

    def abrir_form_nuevo(self):
        from app.ui.supplier_form import SupplierForm

        dlg = SupplierForm(self)
        if dlg.exec():
            self.cargar_proveedores()

    def abrir_form_editar(self):
        from app.ui.supplier_form import SupplierForm

        p = self._get_selected()
        if not p:
            QMessageBox.information(
                self, "Selecciona", "Selecciona un proveedor primero."
            )
            return

        dlg = SupplierForm(self, supplier=p)
        if dlg.exec():
            self.cargar_proveedores()

    def _dbl_click_editar(self, row, col):
        self.abrir_form_editar()

    def cambiar_estado_seleccionado(self):
        p = self._get_selected()
        if not p:
            QMessageBox.information(
                self, "Selecciona", "Selecciona un proveedor primero."
            )
            return

        r = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Cambiar estado del proveedor '{p.nombre}'?\n\n"
            f"Estado actual: {'Activo' if p.activo else 'Inactivo'}",
        )
        if r != QMessageBox.Yes:
            return

        try:
            cambiar_estado_proveedor(p.id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cambiar estado:\n{e}")
            return

        self.cargar_proveedores()
