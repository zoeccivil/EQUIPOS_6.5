"""
Diálogo de Configuración completo para EQUIPOS
Pestañas: Empresa, Aplicación, Firebase, Backup, WhatsApp
"""

import os
import copy
import logging
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTabWidget, QWidget, QFormLayout, QFileDialog, QMessageBox,
    QCheckBox, QSpinBox, QGroupBox, QStyle, QTimeEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, QTime, QSize
from PyQt6.QtGui import QPixmap, QIcon

from config_manager import guardar_configuracion

logger = logging.getLogger(__name__)


class ConfiguracionDialog(QDialog):
    """Diálogo de configuración completo del sistema."""

    def __init__(self, firebase_manager, config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.config = config
        self.config_original = copy.deepcopy(config)
        self.config_modificada = False

        self.setWindowTitle("⚙️ Configuración del Sistema")
        self.setMinimumSize(580, 520)
        self.resize(620, 560)

        self._init_ui()
        self._cargar_valores()

    # ------------------------------------------------------------------ UI
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._crear_tab_empresa(), "🏢 Empresa")
        self.tabs.addTab(self._crear_tab_aplicacion(), "🎨 Aplicación")
        self.tabs.addTab(self._crear_tab_firebase(), "🔥 Firebase")
        self.tabs.addTab(self._crear_tab_backup(), "💾 Backup")
        self.tabs.addTab(self._crear_tab_whatsapp(), "📱 WhatsApp")
        layout.addWidget(self.tabs)

        # Botones inferiores
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_guardar = QPushButton("Guardar")
        btn_guardar.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        btn_guardar.setMinimumWidth(120)
        btn_guardar.clicked.connect(self._guardar)
        btn_layout.addWidget(btn_guardar)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        btn_cancelar.setMinimumWidth(120)
        btn_cancelar.clicked.connect(self._cancelar)
        btn_layout.addWidget(btn_cancelar)

        layout.addLayout(btn_layout)

    # ========================== TAB EMPRESA ==========================
    def _crear_tab_empresa(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(6)

        self.txt_empresa_nombre = QLineEdit()
        self.txt_empresa_nombre.setPlaceholderText("Nombre de la empresa")
        form.addRow("Nombre:", self.txt_empresa_nombre)

        self.txt_empresa_rnc = QLineEdit()
        self.txt_empresa_rnc.setPlaceholderText("RNC o cédula fiscal")
        form.addRow("RNC:", self.txt_empresa_rnc)

        self.txt_empresa_direccion = QLineEdit()
        self.txt_empresa_direccion.setPlaceholderText("Dirección física")
        form.addRow("Dirección:", self.txt_empresa_direccion)

        self.txt_empresa_telefono = QLineEdit()
        self.txt_empresa_telefono.setPlaceholderText("+1 (809) 555-1234")
        form.addRow("Teléfono:", self.txt_empresa_telefono)

        self.txt_empresa_email = QLineEdit()
        self.txt_empresa_email.setPlaceholderText("info@empresa.com")
        form.addRow("Email:", self.txt_empresa_email)

        # Logo
        logo_layout = QHBoxLayout()
        self.txt_logo_path = QLineEdit()
        self.txt_logo_path.setPlaceholderText("Ruta al logo de la empresa")
        self.txt_logo_path.setReadOnly(True)
        logo_layout.addWidget(self.txt_logo_path)

        btn_logo = QPushButton("Explorar")
        btn_logo.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        btn_logo.clicked.connect(self._seleccionar_logo)
        logo_layout.addWidget(btn_logo)
        form.addRow("Logo:", logo_layout)

        self.lbl_logo_preview = QLabel("Sin logo")
        self.lbl_logo_preview.setFixedSize(120, 60)
        self.lbl_logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo_preview.setStyleSheet("border: 1px dashed gray; border-radius: 4px;")
        form.addRow("", self.lbl_logo_preview)

        return tab

    # ========================== TAB APLICACIÓN ==========================
    def _crear_tab_aplicacion(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(6)

        self.combo_tema = QComboBox()
        self.combo_tema.addItems(["Claro", "Oscuro", "Azul Corporativo", "Morado Moderno"])
        form.addRow("Tema:", self.combo_tema)

        self.combo_moneda = QComboBox()
        self.combo_moneda.setEditable(True)
        self.combo_moneda.addItems(["RD$", "US$", "€", "L", "Q", "C$", "B/."])
        form.addRow("Moneda:", self.combo_moneda)

        self.combo_formato_fecha = QComboBox()
        self.combo_formato_fecha.addItems(["yyyy-MM-dd", "dd/MM/yyyy", "MM/dd/yyyy", "dd-MM-yyyy"])
        form.addRow("Formato fecha:", self.combo_formato_fecha)

        self.chk_maximizada = QCheckBox("Iniciar con ventana maximizada")
        form.addRow("", self.chk_maximizada)

        # Separador visual
        form.addRow(QLabel(""))

        info = QLabel(
            "ℹ️ El cambio de tema se aplicará al reiniciar la aplicación."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-style: italic;")
        form.addRow(info)

        return tab

    # ========================== TAB FIREBASE ==========================
    def _crear_tab_firebase(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(6)

        # Credenciales
        cred_layout = QHBoxLayout()
        self.txt_firebase_cred = QLineEdit()
        self.txt_firebase_cred.setPlaceholderText("Ruta al archivo JSON de credenciales")
        self.txt_firebase_cred.setReadOnly(True)
        cred_layout.addWidget(self.txt_firebase_cred)

        btn_cred = QPushButton("Explorar")
        btn_cred.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        btn_cred.clicked.connect(self._seleccionar_credenciales)
        cred_layout.addWidget(btn_cred)
        form.addRow("Credenciales:", cred_layout)

        self.txt_firebase_project = QLineEdit()
        self.txt_firebase_project.setPlaceholderText("mi-proyecto-firebase")
        form.addRow("Project ID:", self.txt_firebase_project)

        self.txt_firebase_bucket = QLineEdit()
        self.txt_firebase_bucket.setPlaceholderText("mi-proyecto.appspot.com")
        form.addRow("Storage Bucket:", self.txt_firebase_bucket)

        # Estado de conexión
        self.lbl_firebase_estado = QLabel("⚪ Sin verificar")
        form.addRow("Estado:", self.lbl_firebase_estado)

        btn_test = QPushButton("Probar Conexión")
        btn_test.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        btn_test.clicked.connect(self._probar_conexion_firebase)
        form.addRow("", btn_test)

        # Advertencia
        warn = QLabel(
            "⚠️ Cambiar las credenciales de Firebase requiere reiniciar la aplicación."
        )
        warn.setWordWrap(True)
        warn.setStyleSheet("color: #D97706; font-style: italic;")
        form.addRow(warn)

        return tab

    # ========================== TAB BACKUP ==========================
    def _crear_tab_backup(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(6)

        # Ruta de backup
        ruta_layout = QHBoxLayout()
        self.txt_backup_ruta = QLineEdit()
        self.txt_backup_ruta.setPlaceholderText("./backups/equipos_backup.db")
        ruta_layout.addWidget(self.txt_backup_ruta)

        btn_ruta = QPushButton("Explorar")
        btn_ruta.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        btn_ruta.clicked.connect(self._seleccionar_ruta_backup)
        ruta_layout.addWidget(btn_ruta)
        form.addRow("Ruta backup:", ruta_layout)

        self.combo_frecuencia = QComboBox()
        self.combo_frecuencia.addItems(["diario", "semanal", "mensual", "manual"])
        form.addRow("Frecuencia:", self.combo_frecuencia)

        self.time_backup = QTimeEdit()
        self.time_backup.setDisplayFormat("HH:mm")
        self.time_backup.setTime(QTime(2, 0))
        form.addRow("Hora ejecución:", self.time_backup)

        self.lbl_ultimo_backup = QLabel("Nunca")
        form.addRow("Último backup:", self.lbl_ultimo_backup)

        # Botón backup manual
        form.addRow(QLabel(""))
        btn_backup_ahora = QPushButton("Crear Backup Ahora")
        btn_backup_ahora.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        btn_backup_ahora.clicked.connect(self._crear_backup_ahora)
        form.addRow("", btn_backup_ahora)

        return tab

    # ========================== TAB WHATSAPP ==========================
    def _crear_tab_whatsapp(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # ── Green-API ────────────────────────────────────────────────────────
        group_green = QGroupBox("Green-API  (Bot WhatsApp)")
        green_form = QFormLayout(group_green)
        green_form.setSpacing(8)

        self.txt_greenapi_instance = QLineEdit()
        self.txt_greenapi_instance.setPlaceholderText("ej. 1101234567")
        green_form.addRow("Instance ID:", self.txt_greenapi_instance)

        self.txt_greenapi_token = QLineEdit()
        self.txt_greenapi_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_greenapi_token.setPlaceholderText("Token de la instancia")
        green_form.addRow("API Token:", self.txt_greenapi_token)

        layout.addWidget(group_green)

        # ── Teléfono personal contable ────────────────────────────────────────
        group_contable = QGroupBox("Notificaciones Internas")
        contable_form = QFormLayout(group_contable)
        contable_form.setSpacing(8)

        lbl_info = QLabel(
            "Este número recibirá recordatorios automáticos de pagos pendientes."
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #6B7280; font-size: 9pt;")
        contable_form.addRow(lbl_info)

        self.txt_telefono_contable = QLineEdit()
        self.txt_telefono_contable.setPlaceholderText("+18291234567  (código de país incluido)")
        contable_form.addRow("Tel. Contabilidad:", self.txt_telefono_contable)

        layout.addWidget(group_contable)

        # ── Recordatorios automáticos ─────────────────────────────────────────
        group_rec = QGroupBox("Recordatorios Automáticos a Clientes")
        rec_form = QFormLayout(group_rec)
        rec_form.setSpacing(6)

        self.chk_recordatorios = QCheckBox("Activar recordatorios automáticos")
        rec_form.addRow(self.chk_recordatorios)

        self.spin_dias_antes = QSpinBox()
        self.spin_dias_antes.setRange(1, 30)
        self.spin_dias_antes.setValue(3)
        rec_form.addRow("Días antes del vencimiento:", self.spin_dias_antes)

        self.time_recordatorio = QTimeEdit()
        self.time_recordatorio.setDisplayFormat("HH:mm")
        self.time_recordatorio.setTime(QTime(9, 0))
        rec_form.addRow("Hora de envío:", self.time_recordatorio)

        layout.addWidget(group_rec)
        layout.addStretch()

        return tab

    # ---------------------------------------------------------- Cargar valores
    def _cargar_valores(self):
        """Carga los valores actuales del config en los widgets."""
        cfg = self.config

        # --- Empresa ---
        reportes = cfg.get("reportes", {})
        self.txt_empresa_nombre.setText(reportes.get("empresa", ""))
        self.txt_empresa_rnc.setText(reportes.get("rnc", ""))
        self.txt_empresa_direccion.setText(reportes.get("direccion", ""))
        self.txt_empresa_telefono.setText(reportes.get("telefono", ""))
        self.txt_empresa_email.setText(reportes.get("email", ""))
        logo = reportes.get("logo_path", "")
        self.txt_logo_path.setText(logo)
        self._actualizar_preview_logo(logo)

        # --- Aplicación ---
        app_cfg = cfg.get("app", {})
        tema = app_cfg.get("tema", "Oscuro")
        idx = self.combo_tema.findText(tema)
        if idx >= 0:
            self.combo_tema.setCurrentIndex(idx)

        moneda = app_cfg.get("moneda", "RD$")
        idx = self.combo_moneda.findText(moneda)
        if idx >= 0:
            self.combo_moneda.setCurrentIndex(idx)
        else:
            self.combo_moneda.setEditText(moneda)

        formato = app_cfg.get("formato_fecha", "yyyy-MM-dd")
        idx = self.combo_formato_fecha.findText(formato)
        if idx >= 0:
            self.combo_formato_fecha.setCurrentIndex(idx)

        self.chk_maximizada.setChecked(app_cfg.get("ventana_maximizada", False))

        # --- Firebase ---
        fb = cfg.get("firebase", {})
        self.txt_firebase_cred.setText(fb.get("credentials_path", ""))
        self.txt_firebase_project.setText(fb.get("project_id", ""))
        self.txt_firebase_bucket.setText(fb.get("storage_bucket", ""))

        # --- Backup ---
        bk = cfg.get("backup", {})
        self.txt_backup_ruta.setText(bk.get("ruta_backup_sqlite", "./backups/equipos_backup.db"))
        idx = self.combo_frecuencia.findText(bk.get("frecuencia", "diario"))
        if idx >= 0:
            self.combo_frecuencia.setCurrentIndex(idx)

        hora_str = bk.get("hora_ejecucion", "02:00")
        try:
            h, m = hora_str.split(":")
            self.time_backup.setTime(QTime(int(h), int(m)))
        except (ValueError, AttributeError):
            pass

        ultimo = bk.get("ultimo_backup")
        self.lbl_ultimo_backup.setText(ultimo if ultimo else "Nunca")

        # --- WhatsApp ---
        wa = cfg.get("whatsapp", {})
        self.txt_greenapi_instance.setText(wa.get("greenapi_instance_id", ""))
        self.txt_greenapi_token.setText(wa.get("greenapi_token", ""))
        self.txt_telefono_contable.setText(wa.get("telefono_contable", ""))

        rec = wa.get("recordatorios_auto", {})
        self.chk_recordatorios.setChecked(rec.get("activo", False))
        self.spin_dias_antes.setValue(rec.get("dias_antes", 3))
        hora_rec = rec.get("hora", "09:00")
        try:
            h, m = hora_rec.split(":")
            self.time_recordatorio.setTime(QTime(int(h), int(m)))
        except (ValueError, AttributeError):
            pass

    # ---------------------------------------------------------- Acciones
    def _seleccionar_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Logo", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.svg)"
        )
        if path:
            self.txt_logo_path.setText(path)
            self._actualizar_preview_logo(path)

    def _actualizar_preview_logo(self, path: str):
        if path and os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                self.lbl_logo_preview.setPixmap(
                    pix.scaled(
                        self.lbl_logo_preview.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        self.lbl_logo_preview.setText("Sin logo")

    def _seleccionar_credenciales(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Credenciales Firebase", "",
            "JSON (*.json)"
        )
        if path:
            self.txt_firebase_cred.setText(path)

    def _seleccionar_ruta_backup(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Seleccionar Ruta de Backup", "",
            "SQLite (*.db)"
        )
        if path:
            self.txt_backup_ruta.setText(path)

    def _probar_conexion_firebase(self):
        """Prueba la conexión con Firebase usando el manager actual."""
        try:
            if self.fm and self.fm.db:
                # Intentar leer una colección pequeña
                self.fm.db.collection("equipos").limit(1).get()
                self.lbl_firebase_estado.setText("🟢 Conexión exitosa")
                self.lbl_firebase_estado.setStyleSheet("color: #10B981; font-weight: bold;")
            else:
                self.lbl_firebase_estado.setText("🔴 Firebase no inicializado")
                self.lbl_firebase_estado.setStyleSheet("color: #EF4444; font-weight: bold;")
        except Exception as e:
            self.lbl_firebase_estado.setText(f"🔴 Error: {e}")
            self.lbl_firebase_estado.setStyleSheet("color: #EF4444;")
            logger.error(f"Error al probar conexión Firebase: {e}")

    def _crear_backup_ahora(self):
        """Crea un backup inmediato."""
        try:
            from backup_manager import BackupManager
            ruta = self.txt_backup_ruta.text().strip() or "./backups/equipos_backup.db"

            bm = BackupManager(ruta_backup=ruta, firebase_manager=self.fm)
            if bm.crear_backup():
                from datetime import datetime
                ahora = datetime.now().isoformat()
                self.lbl_ultimo_backup.setText(ahora)
                QMessageBox.information(self, "Backup", "Backup creado exitosamente.")
            else:
                QMessageBox.warning(self, "Backup", "No se pudo crear el backup.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al crear backup:\n{e}")
            logger.error(f"Error al crear backup manual: {e}", exc_info=True)

    # ---------------------------------------------------------- Guardar
    def _recopilar_config(self) -> Dict[str, Any]:
        """Recopila todos los valores de los widgets al diccionario config."""
        cfg = copy.deepcopy(self.config)

        # Empresa / Reportes
        if "reportes" not in cfg:
            cfg["reportes"] = {}
        cfg["reportes"]["empresa"] = self.txt_empresa_nombre.text().strip()
        cfg["reportes"]["rnc"] = self.txt_empresa_rnc.text().strip()
        cfg["reportes"]["direccion"] = self.txt_empresa_direccion.text().strip()
        cfg["reportes"]["telefono"] = self.txt_empresa_telefono.text().strip()
        cfg["reportes"]["email"] = self.txt_empresa_email.text().strip()
        cfg["reportes"]["logo_path"] = self.txt_logo_path.text().strip()

        # Aplicación
        if "app" not in cfg:
            cfg["app"] = {}
        cfg["app"]["tema"] = self.combo_tema.currentText()
        cfg["app"]["moneda"] = self.combo_moneda.currentText().strip()
        cfg["app"]["formato_fecha"] = self.combo_formato_fecha.currentText()
        cfg["app"]["ventana_maximizada"] = self.chk_maximizada.isChecked()

        # Firebase
        if "firebase" not in cfg:
            cfg["firebase"] = {}
        cfg["firebase"]["credentials_path"] = self.txt_firebase_cred.text().strip()
        cfg["firebase"]["project_id"] = self.txt_firebase_project.text().strip()
        cfg["firebase"]["storage_bucket"] = self.txt_firebase_bucket.text().strip()

        # Backup
        if "backup" not in cfg:
            cfg["backup"] = {}
        cfg["backup"]["ruta_backup_sqlite"] = self.txt_backup_ruta.text().strip()
        cfg["backup"]["frecuencia"] = self.combo_frecuencia.currentText()
        cfg["backup"]["hora_ejecucion"] = self.time_backup.time().toString("HH:mm")
        # Preservar ultimo_backup del label si se cambió
        ultimo = self.lbl_ultimo_backup.text()
        if ultimo != "Nunca":
            cfg["backup"]["ultimo_backup"] = ultimo

        # WhatsApp
        if "whatsapp" not in cfg:
            cfg["whatsapp"] = {}
        cfg["whatsapp"]["greenapi_instance_id"] = self.txt_greenapi_instance.text().strip()
        cfg["whatsapp"]["greenapi_token"]       = self.txt_greenapi_token.text().strip()
        cfg["whatsapp"]["telefono_contable"]    = self.txt_telefono_contable.text().strip()
        cfg["whatsapp"]["recordatorios_auto"] = {
            "activo":     self.chk_recordatorios.isChecked(),
            "dias_antes": self.spin_dias_antes.value(),
            "hora":       self.time_recordatorio.time().toString("HH:mm"),
        }

        return cfg

    def _guardar(self):
        """Guarda la configuración en disco y cierra el diálogo."""
        nueva_config = self._recopilar_config()

        if guardar_configuracion(nueva_config):
            # Actualizar el config en memoria (ref compartida)
            self.config.clear()
            self.config.update(nueva_config)
            self.config_modificada = True
            logger.info("Configuración guardada exitosamente")
            QMessageBox.information(self, "Configuración", "Configuración guardada correctamente.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "No se pudo guardar la configuración.")

    def _cancelar(self):
        """Cierra sin guardar."""
        self.reject()