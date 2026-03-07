from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QFrame,
    QFileDialog,
    QMessageBox,
    QScrollArea,
)
from PySide6.QtGui import QPixmap, QPainter, QPainterPath

from app.utils.config_manager import cargar_config, guardar_config
from app.db.database import get_app_data_dir


class SettingsWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            from app.main import get_icon

            if get_icon():
                self.setWindowIcon(get_icon())
        except Exception:
            pass
        self.setWindowTitle("⚙️  Configuración")
        self.resize(520, 680)
        self.setMinimumSize(460, 580)
        self._config = cargar_config()
        self._build_ui()
        self.setStyleSheet(self._styles())

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        # Título
        lbl_title = QLabel("⚙️  Configuración")
        lbl_title.setObjectName("pageTitle")
        root.addWidget(lbl_title)

        # ══ EMPRESA ══════════════════════════════════════════
        root.addWidget(self._sep("🏢  Datos de la empresa"))

        # Logo
        logo_row = QHBoxLayout()
        logo_row.setSpacing(16)
        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(120, 80)
        self.lbl_logo.setObjectName("logoBox")
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        self._refresh_logo_preview()
        logo_row.addWidget(self.lbl_logo)

        logo_btns = QVBoxLayout()
        logo_btns.setSpacing(8)
        btn_logo = QPushButton("📁  Cargar logo")
        btn_logo.setObjectName("btnSecondary")
        btn_logo.clicked.connect(self._cargar_logo)
        btn_logo_del = QPushButton("🗑  Quitar logo")
        btn_logo_del.setObjectName("btnDanger")
        btn_logo_del.clicked.connect(self._quitar_logo)
        logo_btns.addWidget(btn_logo)
        logo_btns.addWidget(btn_logo_del)
        logo_btns.addStretch()
        logo_row.addLayout(logo_btns)
        logo_row.addStretch()
        root.addLayout(logo_row)

        root.addWidget(self._lbl("Nombre del negocio"))
        self.txt_nombre = QLineEdit(self._config.get("empresa_nombre", ""))
        self.txt_nombre.setObjectName("inputField")
        self.txt_nombre.setPlaceholderText("Ej: Distribuidora JH")
        root.addWidget(self.txt_nombre)

        root.addWidget(self._lbl("Teléfono"))
        self.txt_tel = QLineEdit(self._config.get("empresa_telefono", ""))
        self.txt_tel.setObjectName("inputField")
        self.txt_tel.setPlaceholderText("Ej: 310 123 4567")
        root.addWidget(self.txt_tel)

        root.addWidget(self._lbl("Dirección"))
        self.txt_dir = QLineEdit(self._config.get("empresa_direccion", ""))
        self.txt_dir.setObjectName("inputField")
        self.txt_dir.setPlaceholderText("Ej: Calle 10 # 5-20, Bogotá")
        root.addWidget(self.txt_dir)

        # ══ SEGURIDAD ═════════════════════════════════════════
        root.addWidget(self._sep("🔐  Seguridad"))

        root.addWidget(self._lbl("Contraseña actual"))
        self.txt_pass_actual = QLineEdit()
        self.txt_pass_actual.setObjectName("inputField")
        self.txt_pass_actual.setEchoMode(QLineEdit.Password)
        self.txt_pass_actual.setPlaceholderText("Contraseña actual…")
        root.addWidget(self.txt_pass_actual)

        root.addWidget(self._lbl("Nueva contraseña"))
        self.txt_pass_nueva = QLineEdit()
        self.txt_pass_nueva.setObjectName("inputField")
        self.txt_pass_nueva.setEchoMode(QLineEdit.Password)
        self.txt_pass_nueva.setPlaceholderText("Mínimo 4 caracteres…")
        root.addWidget(self.txt_pass_nueva)

        root.addWidget(self._lbl("Confirmar nueva contraseña"))
        self.txt_pass_conf = QLineEdit()
        self.txt_pass_conf.setObjectName("inputField")
        self.txt_pass_conf.setEchoMode(QLineEdit.Password)
        self.txt_pass_conf.setPlaceholderText("Repite la nueva contraseña…")
        root.addWidget(self.txt_pass_conf)

        btn_pass = QPushButton("🔒  Cambiar contraseña")
        btn_pass.setObjectName("btnSecondary")
        btn_pass.clicked.connect(self._cambiar_password)
        root.addWidget(btn_pass)

        root.addSpacing(4)

        from app.db.auth_repo import obtener_pregunta
        from app.ui.login_window import PREGUNTAS

        pregunta_actual = obtener_pregunta() or "No configurada"
        lbl_preg = QLabel(f"Pregunta actual: {pregunta_actual}")
        lbl_preg.setObjectName("fieldLabel")
        lbl_preg.setWordWrap(True)
        root.addWidget(lbl_preg)

        root.addWidget(self._lbl("Nueva pregunta de seguridad"))
        self.cbo_pregunta = QComboBox()
        self.cbo_pregunta.setObjectName("combo")
        self.cbo_pregunta.addItems(PREGUNTAS)
        root.addWidget(self.cbo_pregunta)

        root.addWidget(self._lbl("Nueva respuesta secreta"))
        self.txt_respuesta = QLineEdit()
        self.txt_respuesta.setObjectName("inputField")
        self.txt_respuesta.setPlaceholderText("Tu respuesta…")
        root.addWidget(self.txt_respuesta)

        btn_preg = QPushButton("💬  Actualizar pregunta de seguridad")
        btn_preg.setObjectName("btnSecondary")
        btn_preg.clicked.connect(self._cambiar_pregunta)
        root.addWidget(btn_preg)

        # ══ DATOS ══════════════════════════════════════════════
        root.addWidget(self._sep("🗄️  Datos y respaldo"))

        lbl_db = QLabel(f"📂  BD: {get_app_data_dir() / 'inventario.db'}")
        lbl_db.setObjectName("fieldLabel")
        lbl_db.setWordWrap(True)
        root.addWidget(lbl_db)

        btn_backup = QPushButton("💾  Crear backup ahora")
        btn_backup.setObjectName("btnSecondary")
        btn_backup.clicked.connect(self._hacer_backup)
        root.addWidget(btn_backup)

        # ══ BOTONES FINALES ════════════════════════════════════
        root.addSpacing(4)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("sep")
        root.addWidget(sep)

        btns = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecondary")
        btn_cancelar.clicked.connect(self.close)
        btn_guardar = QPushButton("💾  Guardar cambios")
        btn_guardar.setObjectName("btnPrimary")
        btn_guardar.clicked.connect(self._guardar)
        btns.addWidget(btn_cancelar)
        btns.addStretch()
        btns.addWidget(btn_guardar)
        root.addLayout(btns)

    # ── HELPERS UI ───────────────────────────────────────────
    def _sep(self, titulo: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 6, 0, 0)
        lay.setSpacing(10)
        lbl = QLabel(titulo)
        lbl.setObjectName("sectionTitle")
        lay.addWidget(lbl)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("sep")
        lay.addWidget(line, 1)
        return w

    def _lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setObjectName("fieldLabel")
        return l

    # ── LOGO ─────────────────────────────────────────────────
    def _logo_path(self) -> Path:
        return get_app_data_dir() / "logo.png"

    def _refresh_logo_preview(self):
        path = self._logo_path()
        if path.exists():
            pix = QPixmap(str(path))
            if not pix.isNull():
                scaled = pix.scaled(
                    120, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                rounded = QPixmap(scaled.size())
                rounded.fill(Qt.transparent)
                p = QPainter(rounded)
                p.setRenderHint(QPainter.Antialiasing)
                pp = QPainterPath()
                pp.addRoundedRect(0, 0, scaled.width(), scaled.height(), 12, 12)
                p.setClipPath(pp)
                p.drawPixmap(0, 0, scaled)
                p.end()
                self.lbl_logo.setPixmap(rounded)
                self.lbl_logo.setText("")
                return
        self.lbl_logo.setPixmap(QPixmap())
        self.lbl_logo.setText("＋  Logo")

    def _cargar_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar logo", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        dest = self._logo_path()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(path).read_bytes())
        self._refresh_logo_preview()

    def _quitar_logo(self):
        p = self._logo_path()
        if p.exists():
            p.unlink()
        self._refresh_logo_preview()

    # ── SEGURIDAD ────────────────────────────────────────────
    def _cambiar_password(self):
        from app.db.auth_repo import verificar_password, cambiar_password

        actual = self.txt_pass_actual.text()
        nueva = self.txt_pass_nueva.text()
        conf = self.txt_pass_conf.text()
        if not verificar_password(actual):
            QMessageBox.warning(self, "Error", "La contraseña actual es incorrecta.")
            return
        if len(nueva) < 4:
            QMessageBox.warning(self, "Error", "Mínimo 4 caracteres.")
            return
        if nueva != conf:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
            return
        cambiar_password(nueva)
        self.txt_pass_actual.clear()
        self.txt_pass_nueva.clear()
        self.txt_pass_conf.clear()
        QMessageBox.information(self, "✓", "Contraseña actualizada.")

    def _cambiar_pregunta(self):
        from app.db.auth_repo import cambiar_pregunta_respuesta

        pregunta = self.cbo_pregunta.currentText()
        respuesta = self.txt_respuesta.text().strip().lower()
        if not respuesta:
            QMessageBox.warning(self, "Error", "La respuesta no puede estar vacía.")
            return
        cambiar_pregunta_respuesta(pregunta, respuesta)
        self.txt_respuesta.clear()
        QMessageBox.information(self, "✓", "Pregunta de seguridad actualizada.")

    # ── BACKUP ───────────────────────────────────────────────
    def _hacer_backup(self):
        from app.utils.backup import crear_backup

        try:
            ruta = crear_backup(str(get_app_data_dir() / "inventario.db"))
            QMessageBox.information(self, "Backup", f"Guardado en:\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ── GUARDAR ──────────────────────────────────────────────
    def _guardar(self):
        config = cargar_config()
        config["empresa_nombre"] = self.txt_nombre.text().strip() or "Inventario JH"
        config["empresa_telefono"] = self.txt_tel.text().strip()
        config["empresa_direccion"] = self.txt_dir.text().strip()
        guardar_config(config)
        QMessageBox.information(self, "✓", "Configuración guardada correctamente.")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def _styles(self) -> str:
        return """
        QWidget { background: #0b1120; color: #e2e8f0;
                  font-family: "Segoe UI", Arial, sans-serif; font-size: 13px; }
        QScrollArea { border: none; background: #0b1120; }
        #pageTitle { font-size: 20px; font-weight: 800; color: #f1f5f9; }
        #sectionTitle { font-size: 12px; font-weight: 700; color: #64748b; letter-spacing: 0.5px; }
        #fieldLabel { color: #64748b; font-size: 12px; font-weight: 600; }
        #sep { border: none; border-top: 1px solid #1e293b; }
        #logoBox { background: #111c33; border: 2px dashed #1e3a5f;
                   border-radius: 10px; color: #334155; font-size: 12px; }
        #inputField { background: #111c33; border: 1px solid #1e3a5f;
                      border-radius: 8px; padding: 7px 10px; color: #e2e8f0; min-height: 28px; }
        #inputField:focus { border-color: #3b82f6; }
        #combo { background: #111c33; border: 1px solid #1e3a5f;
                 border-radius: 8px; padding: 5px 8px; color: #e2e8f0; min-height: 28px; }
        QComboBox::drop-down { border: none; width: 18px; }
        QComboBox QAbstractItemView { background: #111c33; border: 1px solid #1e3a5f;
                                      color: #e2e8f0; selection-background-color: #1e3a5f; }
        #btnPrimary { background: #2563eb; border: none; border-radius: 8px;
                      padding: 8px 20px; font-weight: 700; color: white; min-height: 34px; }
        #btnPrimary:hover { background: #1d4ed8; }
        #btnSecondary { background: #111c33; border: 1px solid #1e3a5f; border-radius: 8px;
                        padding: 8px 14px; font-weight: 600; color: #94a3b8; min-height: 34px; }
        #btnSecondary:hover { border-color: #3b82f6; color: #e2e8f0; }
        #btnDanger { background: #1a0a0a; border: 1px solid #7f1d1d; border-radius: 8px;
                     padding: 8px 14px; font-weight: 600; color: #f87171; min-height: 34px; }
        #btnDanger:hover { background: #7f1d1d; color: #fff; }
        QScrollBar:vertical { background: #0b1120; width: 6px; border-radius: 3px; }
        QScrollBar::handle:vertical { background: #1e3a5f; border-radius: 3px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """
