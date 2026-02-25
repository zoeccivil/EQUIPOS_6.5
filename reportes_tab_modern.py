"""
Vista Moderna de Reportes - EQUIPOS 6.0
Grid de tarjetas para generar reportes PDF/Excel con filtros integrados
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QFileDialog, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon
from datetime import datetime
from typing import Dict
import logging

from app_theme_modern import ModernTheme
from ui_components import ModernCard
from firebase_manager import FirebaseManager
from storage_manager import StorageManager

logger = logging.getLogger(__name__)


class ReporteCard(QFrame):
    """
    Tarjeta de reporte clicable con icono Material, título y descripción.
    """
    clicked = pyqtSignal()
    
    def __init__(self, icon_text: str, title: str, description: str, icon_color: str = None, icon_bg: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("reporteCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Colores del icono
        self.icon_color = icon_color or ModernTheme.COLORS['primary']
        self.icon_bg = icon_bg or "#FFF7ED"
        
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icono
        icon_container = QFrame()
        icon_container.setFixedSize(80, 80)
        icon_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.icon_bg};
                border-radius: 12px;
            }}
        """)
        
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel(icon_text)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            QLabel {{
                color: {self.icon_color};
                font-family: 'Material Icons Round', 'Segoe UI Emoji', sans-serif;
                font-size: 40px;
                background-color: transparent;
            }}
        """)
        icon_layout.addWidget(icon_label)
        
        icon_wrapper = QHBoxLayout()
        icon_wrapper.addStretch()
        icon_wrapper.addWidget(icon_container)
        icon_wrapper.addStretch()
        layout.addLayout(icon_wrapper)
        
        # Título
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_main']};
                font-size: 16px;
                font-weight: 700;
                background-color: transparent;
                margin-top: 8px;
            }}
        """)
        layout.addWidget(title_label)
        
        # Descripción
        desc_label = QLabel(description)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_muted']};
                font-size: 13px;
                background-color: transparent;
                line-height: 1.5;
            }}
        """)
        layout.addWidget(desc_label)
        
        layout.addStretch()
        
        # Estilo de la tarjeta (✅ SIN box-shadow)
        self.setStyleSheet(f"""
            QFrame#reporteCard {{
                background-color: {ModernTheme.COLORS['bg_card']};
                border: 2px solid {ModernTheme.COLORS['border']};
                border-radius: 12px;
                min-height: 220px;
            }}
            QFrame#reporteCard:hover {{
                border-color: {self.icon_color};
                background-color: #FAFAFA;
            }}
        """)
    
    def mousePressEvent(self, event):
        """Emite señal al hacer click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ReportesTabModern(QWidget):
    """
    Vista moderna de reportes con tarjetas clicables.
    """
    
    def __init__(self, firebase_manager: FirebaseManager, config=None, 
                 storage_manager: StorageManager = None, 
                 clientes_mapa: Dict = None,
                 equipos_mapa: Dict = None,
                 operadores_mapa: Dict = None,
                 parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.sm = storage_manager
        self.config = config or {'app': {'moneda': 'RD$'}}
        
        # Mapas
        self.clientes_mapa = clientes_mapa or {}
        self.equipos_mapa = equipos_mapa or {}
        self.operadores_mapa = operadores_mapa or {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel("Generador de Reportes")
        title.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_main']};
                font-size: 24px;
                font-weight: 800;
                background-color: transparent;
            }}
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Seleccione el tipo de reporte que desea generar")
        subtitle.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_muted']};
                font-size: 14px;
                background-color: transparent;
            }}
        """)
        header_layout.addWidget(subtitle)
        
        main_layout.addLayout(header_layout)
        
        # Grid de tarjetas
        grid = QGridLayout()
        grid.setSpacing(20)
        grid.setContentsMargins(0, 0, 0, 0)
        
        # Fila 1
        card_detallado = ReporteCard(
            "📄",
            "Reporte Detallado de Equipos",
            "Ingresos por alquiler con filtros avanzados",
            "#EF4444",
            "#FEE2E2"
        )
        card_detallado.clicked.connect(self._abrir_reporte_detallado)
        grid.addWidget(card_detallado, 0, 0)
        
        card_operadores = ReporteCard(
            "👷",
            "Reporte de Operadores",
            "Horas trabajadas y pagos por operador",
            "#3B82F6",
            "#DBEAFE"
        )
        card_operadores.clicked.connect(self._abrir_reporte_operadores)
        grid.addWidget(card_operadores, 0, 1)
        
        card_estado_cliente = ReporteCard(
            "🧾",
            "Estado de Cuenta Cliente",
            "Balance de facturación por cliente",
            "#8B5CF6",
            "#EDE9FE"
        )
        card_estado_cliente.clicked.connect(self._abrir_estado_cuenta_cliente)
        grid.addWidget(card_estado_cliente, 0, 2)
        
        # Fila 2
        card_estado_general = ReporteCard(
            "📊",
            "Estado de Cuenta General",
            "Balance consolidado de todos los clientes",
            "#10B981",
            "#D1FAE5"
        )
        card_estado_general.clicked.connect(self._abrir_estado_cuenta_general)
        grid.addWidget(card_estado_general, 1, 0)
        
        card_rendimientos = ReporteCard(
            "📈",
            "Reporte de Rendimientos",
            "Análisis de rentabilidad por equipo",
            "#F59E0B",
            "#FEF3C7"
        )
        card_rendimientos.clicked.connect(self._abrir_reporte_rendimientos)
        grid.addWidget(card_rendimientos, 1, 1)
        
        card_prograin = ReporteCard(
            "📑",
            "Exportar a PROGRAIN 5.0",
            "Formato Excel compatible con PROGRAIN",
            "#06B6D4",
            "#CFFAFE"
        )
        card_prograin.clicked.connect(self._abrir_exportador_prograin)
        grid.addWidget(card_prograin, 1, 2)
        
        main_layout.addLayout(grid)
        main_layout.addStretch()
    
    def actualizar_mapas(self, mapas: Dict):
        """Actualiza los mapas desde la ventana principal"""
        self.clientes_mapa = mapas.get('clientes', {})
        self.equipos_mapa = mapas.get('equipos', {})
        self.operadores_mapa = mapas.get('operadores', {})
        logger.info("Reportes: Mapas actualizados")
    
    def _abrir_reporte_detallado(self):
        """Abre el preview/generador de reporte detallado de equipos"""
        try:
            from dialogos.dialogo_preview_reporte_detallado import DialogoPreviewReporteDetallado
            
            dlg = DialogoPreviewReporteDetallado(
                fm=self.fm,
                clientes_mapa=self.clientes_mapa,
                config=self.config,
                storage_manager=self.sm,
                app_gui=None,
                parent=self
            )
            dlg.exec()
            
        except Exception as e:
            logger.error(f"Error abriendo reporte detallado: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el reporte:\n{e}")
    
    def _abrir_reporte_operadores(self):
        """Abre el generador de reporte de operadores"""
        try:
            from dialogos.dialogo_reporte_operadores_firebase import DialogoReporteOperadoresFirebase
            
            dlg = DialogoReporteOperadoresFirebase(
                fm=self.fm,
                operadores_mapa=self.operadores_mapa,
                equipos_mapa=self.equipos_mapa,
                clientes_mapa=self.clientes_mapa,  # ← AGREGAR ESTA LÍNEA
                proyecto_id=self.config.get('app', {}).get('proyecto_id', 8),
                parent=self
            )
            dlg.exec()
            
        except Exception as e:
            logger.error(f"Error abriendo reporte operadores: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el reporte:\n{e}")
    
    def _abrir_estado_cuenta_cliente(self):
        """Abre el diálogo de estado de cuenta de cliente"""
        try:
            from dialogos.estado_cuenta_dialog import EstadoCuentaDialog
            
            moneda = self.config.get('app', {}).get('moneda', 'RD$')
            
            dialog = EstadoCuentaDialog(
                self.fm,
                parent=self,
                currency_symbol=moneda
            )
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error abriendo estado de cuenta: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir:\n{e}")

    def _abrir_estado_cuenta_general(self):
        """Abre el estado de cuenta general (todos los clientes)"""
        try:
            from dialogos.estado_cuenta_dialog import EstadoCuentaDialog
            
            moneda = self.config.get('app', {}).get('moneda', 'RD$')
            
            dialog = EstadoCuentaDialog(
                self.fm,
                parent=self,
                currency_symbol=moneda
            )
            
            if hasattr(dialog, 'combo_cliente'):
                dialog.combo_cliente.setCurrentIndex(0)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir:\n{e}")
    
    def _abrir_reporte_rendimientos(self):
        """Abre el preview de reporte de rendimientos"""
        try:
            from dialogos.dialogo_preview_rendimientos import DialogoPreviewRendimientos
            
            dlg = DialogoPreviewRendimientos(
                fm=self.fm,
                equipos_mapa=self.equipos_mapa,
                config=self.config,
                storage_manager=self.sm,
                parent=self
            )
            dlg.exec()
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir:\n{e}")
    
    def _abrir_exportador_prograin(self):
        """Abre el exportador a PROGRAIN 5.0"""
        try:
            from dialogos.dialogo_exportador_prograin import DialogoExportadorPrograin
            
            # Obtener mapas completos
            parent_window = self.window()
            if hasattr(parent_window, 'cuentas_mapa'):
                mapas = {
                    'equipos': self.equipos_mapa,
                    'clientes': self.clientes_mapa,
                    'cuentas': parent_window.cuentas_mapa,
                    'categorias': parent_window.categorias_mapa,
                    'subcategorias': parent_window.subcategorias_mapa,
                    'proyectos': parent_window.proyectos_mapa
                }
            else:
                mapas = {
                    'equipos': self.equipos_mapa,
                    'clientes': self.clientes_mapa,
                    'cuentas': {},
                    'categorias': {},
                    'subcategorias': {},
                    'proyectos': {}
                }
            
            dialogo = DialogoExportadorPrograin(
                fm=self.fm,
                mapas=mapas,
                config=self.config,
                parent=self
            )
            dialogo.exec()
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir:\n{e}")