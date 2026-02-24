"""
Diálogo de Configuración - Placeholder
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

class ConfiguracionDialog(QDialog):
    """Diálogo de configuración (placeholder)"""
    
    def __init__(self, firebase_manager, config, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.config = config
        
        self.setWindowTitle("Configuración")
        self.setMinimumSize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # Título
        titulo = QLabel("⚙️ Configuración del Sistema")
        titulo.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #111827;
                padding: 20px;
            }
        """)
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)
        
        # Mensaje
        mensaje = QLabel(
            "Esta sección está en construcción.\n\n"
            "Próximamente podrás configurar:\n"
            "• Moneda y formato de números\n"
            "• Información de la empresa\n"
            "• Gestión de proyecto activo\n"
            "• Backup y restauración de datos\n"
            "• Preferencias de la aplicación"
        )
        mensaje.setStyleSheet("""
            QLabel {
                color: #6B7280;
                font-size: 14px;
                padding: 20px;
                line-height: 1.6;
            }
        """)
        mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(mensaje)
        
        layout.addStretch()
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setMinimumWidth(100)
        btn_cerrar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cerrar)
        
        layout.addLayout(btn_layout)