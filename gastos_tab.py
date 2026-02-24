# gastos_tab.py (PLACEHOLDER TEMPORAL)
"""
Vista de Gastos - Placeholder temporal
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

class GastosTab(QWidget):
    """Vista de Gastos (placeholder)"""
    
    recargar_dashboard = pyqtSignal()
    
    def __init__(self, firebase_manager, config, storage_manager, 
                 equipos_mapa, cuentas_mapa, categorias_mapa, subcategorias_mapa, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.config = config
        self.sm = storage_manager
        
        # Mapas
        self.equipos_mapa = equipos_mapa
        self.cuentas_mapa = cuentas_mapa
        self.categorias_mapa = categorias_mapa
        self.subcategorias_mapa = subcategorias_mapa
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        
        label = QLabel("📊 Vista de Gastos en Construcción")
        label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #6B7280;
            }
        """)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        desc = QLabel("Esta vista será actualizada en la próxima fase")
        desc.setStyleSheet("color: #9CA3AF; font-size: 14px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
    
    def actualizar_mapas(self, equipos_mapa, cuentas_mapa, categorias_mapa, subcategorias_mapa):
        """Actualiza los mapas de datos"""
        self.equipos_mapa = equipos_mapa
        self.cuentas_mapa = cuentas_mapa
        self.categorias_mapa = categorias_mapa
        self.subcategorias_mapa = subcategorias_mapa