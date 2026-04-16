#!/usr/bin/env python3
"""
herramientas/organizar_categorias.py
─────────────────────────────────────
Script independiente para organizar categorías y subcategorías huérfanas.

Uso:
    python herramientas/organizar_categorias.py

No forma parte de la aplicación principal; ejecútalo solo cuando necesites
hacer una limpieza o reorganización de categorías / subcategorías en Firebase.

Requiere:
  - config_equipos.json en el directorio raíz del proyecto (un nivel arriba).
  - Las dependencias normales del proyecto (PyQt6, firebase-admin, etc.).
"""

import sys
import os
import logging

# ── Asegurar que el directorio raíz del proyecto esté en el path ─────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QHBoxLayout, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── Carga de configuración y Firebase ────────────────────────────────────────

def _conectar_firebase():
    """Lee config_equipos.json y devuelve un FirebaseManager listo."""
    from config_manager import cargar_configuracion
    from firebase_manager import FirebaseManager

    config = cargar_configuracion()
    fb = config.get("firebase", {})
    creds = fb.get("credentials_path", "")
    proj  = fb.get("project_id", "")

    if not creds or not proj:
        raise ValueError(
            "Faltan 'credentials_path' o 'project_id' en config_equipos.json.\n"
            f"Archivo buscado en: {os.path.join(ROOT, 'config_equipos.json')}"
        )

    return FirebaseManager(creds, proj)


# ── Ventana principal ─────────────────────────────────────────────────────────

class VentanaPrincipal(QMainWindow):
    def __init__(self, fm):
        super().__init__()
        self.fm = fm
        self.setWindowTitle("Organizador de Categorías y Subcategorías — EQUIPOS")
        self.setMinimumSize(460, 280)
        self.resize(520, 320)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        ly = QVBoxLayout(central)
        ly.setContentsMargins(28, 28, 28, 20)
        ly.setSpacing(16)

        # Título
        titulo = QLabel("Organizador de Categorías")
        titulo.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly.addWidget(titulo)

        subtitulo = QLabel(
            "Herramienta independiente para gestionar categorías,\n"
            "subcategorías y reparar referencias huérfanas en Firebase."
        )
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo.setStyleSheet("color: #6B7280; font-size: 10pt;")
        ly.addWidget(subtitulo)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #E5E7EB;")
        ly.addWidget(sep)

        # Botones
        btns = QHBoxLayout()
        btns.setSpacing(12)

        btn_gestionar = QPushButton("  Abrir Gestor  ")
        btn_gestionar.setFixedHeight(42)
        btn_gestionar.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn_gestionar.setStyleSheet(
            "QPushButton { background:#3B82F6; color:#fff; border:none; "
            "border-radius:7px; padding:0 24px; }"
            "QPushButton:hover { background:#2563EB; }"
        )
        btn_gestionar.clicked.connect(self._abrir_gestor)

        btn_auditoria = QPushButton("  Auditoría rápida  ")
        btn_auditoria.setFixedHeight(42)
        btn_auditoria.setFont(QFont("Segoe UI", 11))
        btn_auditoria.setStyleSheet(
            "QPushButton { background:#F59E0B; color:#fff; border:none; "
            "border-radius:7px; padding:0 24px; }"
            "QPushButton:hover { background:#D97706; }"
        )
        btn_auditoria.clicked.connect(self._abrir_gestor_tab_auditoria)

        btn_salir = QPushButton("Salir")
        btn_salir.setFixedHeight(42)
        btn_salir.setStyleSheet(
            "QPushButton { background:#6B7280; color:#fff; border:none; "
            "border-radius:7px; padding:0 18px; }"
            "QPushButton:hover { background:#4B5563; }"
        )
        btn_salir.clicked.connect(self.close)

        btns.addWidget(btn_gestionar, 2)
        btns.addWidget(btn_auditoria, 2)
        btns.addWidget(btn_salir, 1)
        ly.addLayout(btns)

        ly.addStretch()

        # Pie de estado
        self.lbl_estado = QLabel("Conectado a Firebase correctamente.")
        self.lbl_estado.setStyleSheet("color:#16A34A; font-size:9pt;")
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly.addWidget(self.lbl_estado)

    def _abrir_gestor(self, tab_index: int = 0):
        from dialogos.categorias_dialog import CategoriasDialog
        dlg = CategoriasDialog(self.fm, parent=self)
        dlg.tabs.setCurrentIndex(tab_index)
        dlg.exec()
        self.lbl_estado.setText("Gestor cerrado. Cambios guardados en Firebase.")

    def _abrir_gestor_tab_auditoria(self):
        self._abrir_gestor(tab_index=1)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Organizador Categorías — EQUIPOS")
    app.setStyle("Fusion")

    # Intentar conectar a Firebase antes de mostrar la ventana
    try:
        fm = _conectar_firebase()
        logger.info("Firebase conectado OK.")
    except Exception as exc:
        logger.error(f"No se pudo conectar a Firebase: {exc}", exc_info=True)
        err = QMessageBox()
        err.setIcon(QMessageBox.Icon.Critical)
        err.setWindowTitle("Error de conexión")
        err.setText("No se pudo conectar a Firebase.")
        err.setDetailedText(str(exc))
        err.exec()
        sys.exit(1)

    ventana = VentanaPrincipal(fm)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
