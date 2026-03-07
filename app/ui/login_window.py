from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QMessageBox,
    QFrame,
    QStackedWidget,
    QComboBox,
)
from PySide6.QtGui import QFont


# ── Preguntas de seguridad predefinidas ──────────────────────
PREGUNTAS = [
    "¿Cuál es el nombre de tu primera mascota?",
    "¿En qué ciudad naciste?",
    "¿Cuál es el nombre de tu madre?",
    "¿Cuál es tu película favorita?",
    "¿Cuál fue el nombre de tu primer colegio?",
    "¿Cuál es el apodo de tu mejor amigo?",
]


class LoginWindow(QWidget):
    """
    Ventana de autenticación con 3 pantallas:
      0 → Login normal
      1 → Setup inicial (primera vez)
      2 → Recuperar contraseña
    """

    login_exitoso = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventario JH — Acceso")
        self.setFixedSize(480, 620)
        self.setStyleSheet(self._styles())

        from app.db.auth_repo import existe_admin
        from app.db.database import init_db

        init_db()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._stack.addWidget(self._build_login())  # 0
        self._stack.addWidget(self._build_setup())  # 1
        self._stack.addWidget(self._build_recovery())  # 2

        # Decidir pantalla inicial
        if existe_admin():
            self._stack.setCurrentIndex(0)
        else:
            self._stack.setCurrentIndex(1)

    # ── PANTALLA 0: LOGIN ────────────────────────────────────
    def _build_login(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(48, 40, 48, 40)
        lay.setSpacing(0)

        # Logo / título
        from app.db.database import get_app_data_dir
        from PySide6.QtGui import QPixmap

        logo_path = get_app_data_dir() / "logo.png"
        lbl_icon = QLabel()
        lbl_icon.setAlignment(Qt.AlignCenter)
        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                from PySide6.QtGui import QPainter, QBrush, QPainterPath

                scaled = pix.scaled(
                    180, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                rounded = QPixmap(scaled.size())
                rounded.fill(Qt.transparent)
                p = QPainter(rounded)
                p.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addRoundedRect(0, 0, scaled.width(), scaled.height(), 18, 18)
                p.setClipPath(path)
                p.drawPixmap(0, 0, scaled)
                p.end()
                lbl_icon.setPixmap(rounded)
            else:
                lbl_icon.setText("🔐")
                lbl_icon.setStyleSheet("font-size: 48px;")
        else:
            lbl_icon.setText("🔐")
            lbl_icon.setStyleSheet("font-size: 48px;")
        lbl_icon.setContentsMargins(0, 0, 0, 8)
        lay.addWidget(lbl_icon)

        lay.addSpacing(28)

        lbl_pass = QLabel("Contraseña")
        lbl_pass.setObjectName("fieldLabel")
        lay.addWidget(lbl_pass)

        lay.addSpacing(8)

        self.txt_password = QLineEdit()
        self.txt_password.setObjectName("inputField")
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Ingresa tu contraseña…")
        self.txt_password.returnPressed.connect(self._do_login)
        lay.addWidget(self.txt_password)

        lay.addSpacing(8)

        self.lbl_login_error = QLabel("")
        self.lbl_login_error.setObjectName("errorLabel")
        self.lbl_login_error.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_login_error)

        lay.addSpacing(16)

        btn_login = QPushButton("Ingresar")
        btn_login.setObjectName("btnPrimary")
        btn_login.clicked.connect(self._do_login)
        lay.addWidget(btn_login)

        lay.addSpacing(14)

        btn_forgot = QPushButton("¿Olvidaste tu contraseña?")
        btn_forgot.setObjectName("btnLink")
        btn_forgot.clicked.connect(lambda: self._ir_recovery())
        lay.addWidget(btn_forgot)

        lay.addStretch()

        lbl_version = QLabel("v1.4.0")
        lbl_version.setObjectName("versionLabel")
        lbl_version.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl_version)

        return w

    # ── PANTALLA 1: SETUP INICIAL ────────────────────────────
    def _build_setup(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(48, 28, 48, 28)
        lay.setSpacing(0)

        lbl_icon = QLabel("⚙️")
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 40px; margin-bottom: 6px;")
        lay.addWidget(lbl_icon)

        lbl_title = QLabel("Configuración inicial")
        lbl_title.setObjectName("mainTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl_title)

        lbl_sub = QLabel("Crea tu contraseña de acceso")
        lbl_sub.setObjectName("subTitle")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl_sub)

        lay.addSpacing(20)

        # Contraseña
        lay.addWidget(self._field_label("Nueva contraseña"))
        lay.addSpacing(8)
        self.txt_setup_pass1 = QLineEdit()
        self.txt_setup_pass1.setObjectName("inputField")
        self.txt_setup_pass1.setEchoMode(QLineEdit.Password)
        self.txt_setup_pass1.setPlaceholderText("Mínimo 4 caracteres…")
        lay.addWidget(self.txt_setup_pass1)

        lay.addSpacing(14)
        lay.addWidget(self._field_label("Confirmar contraseña"))
        lay.addSpacing(8)
        self.txt_setup_pass2 = QLineEdit()
        self.txt_setup_pass2.setObjectName("inputField")
        self.txt_setup_pass2.setEchoMode(QLineEdit.Password)
        self.txt_setup_pass2.setPlaceholderText("Repite la contraseña…")
        lay.addWidget(self.txt_setup_pass2)

        lay.addSpacing(14)
        lay.addWidget(self._field_label("Pregunta de seguridad"))
        lay.addSpacing(8)
        self.cbo_setup_pregunta = QComboBox()
        self.cbo_setup_pregunta.setObjectName("combo")
        self.cbo_setup_pregunta.addItems(PREGUNTAS)
        lay.addWidget(self.cbo_setup_pregunta)

        lay.addSpacing(14)
        lay.addWidget(self._field_label("Respuesta secreta"))
        lay.addSpacing(8)
        self.txt_setup_respuesta = QLineEdit()
        self.txt_setup_respuesta.setObjectName("inputField")
        self.txt_setup_respuesta.setPlaceholderText(
            "Tu respuesta (no distingue mayúsculas)…"
        )
        lay.addWidget(self.txt_setup_respuesta)

        lay.addSpacing(10)
        self.lbl_setup_error = QLabel("")
        self.lbl_setup_error.setObjectName("errorLabel")
        self.lbl_setup_error.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_setup_error)

        lay.addSpacing(14)
        btn_setup = QPushButton("Crear acceso")
        btn_setup.setObjectName("btnPrimary")
        btn_setup.clicked.connect(self._do_setup)
        lay.addWidget(btn_setup)

        lay.addStretch()

        return w

    # ── PANTALLA 2: RECUPERAR ────────────────────────────────
    def _build_recovery(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(48, 32, 48, 32)
        lay.setSpacing(0)

        lbl_icon = QLabel("🔑")
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 40px; margin-bottom: 6px;")
        lay.addWidget(lbl_icon)

        lbl_title = QLabel("Recuperar acceso")
        lbl_title.setObjectName("mainTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl_title)

        lay.addSpacing(16)

        # Mostrar la pregunta guardada
        self.lbl_recovery_pregunta = QLabel("")
        self.lbl_recovery_pregunta.setObjectName("preguntaLabel")
        self.lbl_recovery_pregunta.setWordWrap(True)
        self.lbl_recovery_pregunta.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_recovery_pregunta)

        lay.addSpacing(14)
        lay.addWidget(self._field_label("Tu respuesta"))
        lay.addSpacing(8)
        self.txt_recovery_respuesta = QLineEdit()
        self.txt_recovery_respuesta.setObjectName("inputField")
        self.txt_recovery_respuesta.setPlaceholderText("Respuesta secreta…")
        lay.addWidget(self.txt_recovery_respuesta)

        lay.addSpacing(14)
        lay.addWidget(self._field_label("Nueva contraseña"))
        lay.addSpacing(8)
        self.txt_recovery_pass1 = QLineEdit()
        self.txt_recovery_pass1.setObjectName("inputField")
        self.txt_recovery_pass1.setEchoMode(QLineEdit.Password)
        self.txt_recovery_pass1.setPlaceholderText("Nueva contraseña…")
        lay.addWidget(self.txt_recovery_pass1)

        lay.addSpacing(14)
        lay.addWidget(self._field_label("Confirmar contraseña"))
        lay.addSpacing(8)
        self.txt_recovery_pass2 = QLineEdit()
        self.txt_recovery_pass2.setObjectName("inputField")
        self.txt_recovery_pass2.setEchoMode(QLineEdit.Password)
        self.txt_recovery_pass2.setPlaceholderText("Repite la contraseña…")
        lay.addWidget(self.txt_recovery_pass2)

        lay.addSpacing(10)
        self.lbl_recovery_error = QLabel("")
        self.lbl_recovery_error.setObjectName("errorLabel")
        self.lbl_recovery_error.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_recovery_error)

        lay.addSpacing(14)
        btn_recovery = QPushButton("Cambiar contraseña")
        btn_recovery.setObjectName("btnPrimary")
        btn_recovery.clicked.connect(self._do_recovery)
        lay.addWidget(btn_recovery)

        lay.addSpacing(12)
        btn_back = QPushButton("← Volver al login")
        btn_back.setObjectName("btnLink")
        btn_back.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        lay.addWidget(btn_back)

        lay.addStretch()
        return w

    # ── ACCIONES ─────────────────────────────────────────────
    def _do_login(self):
        from app.db.auth_repo import verificar_password

        pwd = self.txt_password.text()
        if not pwd:
            self.lbl_login_error.setText("Ingresa tu contraseña.")
            return
        if verificar_password(pwd):
            self.lbl_login_error.setText("")
            self.txt_password.clear()
            self.login_exitoso.emit()
        else:
            self.lbl_login_error.setText("❌ Contraseña incorrecta.")
            self.txt_password.clear()
            self.txt_password.setFocus()

    def _do_setup(self):
        from app.db.auth_repo import crear_admin

        p1 = self.txt_setup_pass1.text()
        p2 = self.txt_setup_pass2.text()
        pregunta = self.cbo_setup_pregunta.currentText()
        respuesta = self.txt_setup_respuesta.text().strip().lower()

        if len(p1) < 4:
            self.lbl_setup_error.setText(
                "La contraseña debe tener al menos 4 caracteres."
            )
            return
        if p1 != p2:
            self.lbl_setup_error.setText("Las contraseñas no coinciden.")
            return
        if not respuesta:
            self.lbl_setup_error.setText("La respuesta secreta es obligatoria.")
            return

        try:
            crear_admin(p1, pregunta, respuesta)
            QMessageBox.information(
                self,
                "¡Listo!",
                "Acceso configurado correctamente.\nYa puedes ingresar al sistema.",
            )
            self.txt_setup_pass1.clear()
            self.txt_setup_pass2.clear()
            self.txt_setup_respuesta.clear()
            self.lbl_setup_error.setText("")
            self._stack.setCurrentIndex(0)
            self.txt_password.setFocus()
        except Exception as e:
            self.lbl_setup_error.setText(f"Error: {e}")

    def _do_recovery(self):
        from app.db.auth_repo import verificar_respuesta, cambiar_password

        respuesta = self.txt_recovery_respuesta.text().strip().lower()
        p1 = self.txt_recovery_pass1.text()
        p2 = self.txt_recovery_pass2.text()

        if not respuesta:
            self.lbl_recovery_error.setText("Ingresa tu respuesta secreta.")
            return
        if not verificar_respuesta(respuesta):
            self.lbl_recovery_error.setText("❌ Respuesta incorrecta.")
            return
        if len(p1) < 4:
            self.lbl_recovery_error.setText(
                "La contraseña debe tener al menos 4 caracteres."
            )
            return
        if p1 != p2:
            self.lbl_recovery_error.setText("Las contraseñas no coinciden.")
            return

        cambiar_password(p1)
        QMessageBox.information(self, "¡Listo!", "Contraseña cambiada correctamente.")
        self.txt_recovery_respuesta.clear()
        self.txt_recovery_pass1.clear()
        self.txt_recovery_pass2.clear()
        self.lbl_recovery_error.setText("")
        self._stack.setCurrentIndex(0)
        self.txt_password.setFocus()

    def _ir_recovery(self):
        from app.db.auth_repo import obtener_pregunta

        pregunta = obtener_pregunta()
        if pregunta:
            self.lbl_recovery_pregunta.setText(f"💬 {pregunta}")
        self.txt_recovery_respuesta.clear()
        self.txt_recovery_pass1.clear()
        self.txt_recovery_pass2.clear()
        self.lbl_recovery_error.setText("")
        self._stack.setCurrentIndex(2)

    # ── HELPERS ──────────────────────────────────────────────
    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        return lbl

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            pass  # No cerrar con Escape en el login
        else:
            super().keyPressEvent(event)

    # ── ESTILOS ──────────────────────────────────────────────
    def _styles(self) -> str:
        return """
        QWidget {
            background: #080f1e;
            color: #e2e8f0;
            font-family: "Segoe UI", Arial, sans-serif;
        }

        #mainTitle {
            font-size: 22px; font-weight: 800;
            color: #f1f5f9; letter-spacing: -0.5px;
            margin-top: 4px;
        }
        #subTitle {
            font-size: 12px; color: #475569;
            margin-bottom: 4px;
        }
        #fieldLabel {
            font-size: 12px; font-weight: 600; color: #64748b;
        }
        #preguntaLabel {
            font-size: 13px; color: #93c5fd;
            font-weight: 600; padding: 10px;
            background: #0d1829;
            border: 1px solid #1e3a5f;
            border-radius: 8px;
        }
        #errorLabel {
            font-size: 11px; color: #f87171;
            min-height: 16px;
        }
        #versionLabel {
            font-size: 10px; color: #1e293b;
        }

        #inputField {
            background: #111c33;
            border: 1px solid #1e3a5f;
            border-radius: 8px;
            padding: 9px 12px;
            color: #e2e8f0;
            font-size: 13px;
            min-height: 32px;
        }
        #inputField:focus { border-color: #3b82f6; }

        #combo {
            background: #111c33;
            border: 1px solid #1e3a5f;
            border-radius: 8px;
            padding: 6px 10px;
            color: #e2e8f0;
            font-size: 12px;
            min-height: 32px;
        }
        QComboBox::drop-down { border: none; width: 18px; }
        QComboBox QAbstractItemView {
            background: #111c33; border: 1px solid #1e3a5f;
            color: #e2e8f0; selection-background-color: #1e3a5f;
        }

        #btnPrimary {
            background: #2563eb;
            border: none;
            border-radius: 8px;
            padding: 10px 0;
            font-weight: 700;
            color: white;
            font-size: 14px;
            min-height: 40px;
        }
        #btnPrimary:hover { background: #1d4ed8; }

        #btnLink {
            background: transparent;
            border: none;
            color: #3b82f6;
            font-size: 12px;
            padding: 4px 0;
        }
        #btnLink:hover { color: #60a5fa; }
        """
