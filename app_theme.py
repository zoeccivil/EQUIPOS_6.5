"""
Sistema de Diseño para EQUIPOS 4.0
Estilo: Técnico / Industrial (Dark Mode)
Inspirado en Linear y software financiero de alta gama
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
)


class AppTheme:
    """
    Define la paleta de colores y estilos para la aplicación.
    Estilo: Técnico / Industrial (Dark Mode por defecto)
    """
    
    # Paleta Dark Mode (Industrial)
    COLORS = {
        "primary": "#0F62FE",       # IBM Blue (Acciones principales)
        "primary_hover": "#0353E9",
        "bg_main": "#121212",       # Fondo Ventana
        "bg_surface": "#1E1E1E",    # Fondo Cards/Paneles
        "bg_input": "#2C2C2C",      # Fondo Inputs
        "text_primary": "#FFFFFF",
        "text_secondary": "#A0A0A0",
        "border": "#333333",
        "success": "#24A148",       # Pagado / Activo
        "warning": "#F1C21B",       # Pendiente / Mantenimiento
        "danger": "#DA1E28"         # Deuda / Error
    }

    @staticmethod
    def get_stylesheet():
        """Retorna el stylesheet completo de la aplicación"""
        return f"""
        QMainWindow {{ 
            background-color: {AppTheme.COLORS["bg_main"]}; 
        }}
        
        QWidget {{ 
            color: {AppTheme.COLORS["text_primary"]}; 
            font-family: 'Inter', 'Segoe UI', sans-serif; 
            font-size: 14px; 
        }}
        
        QFrame.card {{
            background-color: {AppTheme.COLORS["bg_surface"]};
            border: 1px solid {AppTheme.COLORS["border"]};
            border-radius: 8px;
            padding: 12px;
        }}
        
        QPushButton {{ 
            border-radius: 6px; 
            padding: 8px 16px; 
            font-weight: 600; 
            min-height: 32px;
        }}
        
        QPushButton.primary {{ 
            background-color: {AppTheme.COLORS["primary"]}; 
            color: white; 
            border: none; 
        }}
        
        QPushButton.primary:hover {{ 
            background-color: {AppTheme.COLORS["primary_hover"]}; 
        }}
        
        QPushButton.secondary {{ 
            background-color: transparent; 
            border: 1px solid {AppTheme.COLORS["border"]}; 
            color: {AppTheme.COLORS["text_primary"]}; 
        }}
        
        QPushButton.secondary:hover {{
            background-color: {AppTheme.COLORS["bg_input"]};
        }}
        
        QPushButton.success {{
            background-color: {AppTheme.COLORS["success"]};
            color: white;
            border: none;
        }}
        
        QPushButton.danger {{
            background-color: {AppTheme.COLORS["danger"]};
            color: white;
            border: none;
        }}
        
        QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {{
            background-color: {AppTheme.COLORS["bg_input"]};
            border: 1px solid {AppTheme.COLORS["border"]};
            border-radius: 6px;
            padding: 8px;
            color: white;
            min-height: 32px;
        }}
        
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
            border: 1px solid {AppTheme.COLORS["primary"]};
        }}
        
        QComboBox::drop-down {{
            border: none;
            padding-right: 8px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {AppTheme.COLORS["bg_input"]};
            color: {AppTheme.COLORS["text_primary"]};
            selection-background-color: {AppTheme.COLORS["primary"]};
            border: 1px solid {AppTheme.COLORS["border"]};
        }}
        
        QTableWidget {{
            background-color: {AppTheme.COLORS["bg_surface"]};
            gridline-color: {AppTheme.COLORS["border"]};
            border: none;
            border-radius: 8px;
        }}
        
        QTableWidget::item {{
            padding: 8px;
            min-height: 45px;
        }}
        
        QTableWidget::item:selected {{
            background-color: {AppTheme.COLORS["primary"]};
        }}
        
        QHeaderView::section {{
            background-color: {AppTheme.COLORS["bg_main"]};
            color: {AppTheme.COLORS["text_secondary"]};
            padding: 12px 8px;
            border: none;
            border-bottom: 2px solid {AppTheme.COLORS["border"]};
            font-weight: bold;
            text-transform: uppercase;
            font-size: 12px;
        }}
        
        QGroupBox {{
            background-color: {AppTheme.COLORS["bg_surface"]};
            border: 1px solid {AppTheme.COLORS["border"]};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: bold;
            color: {AppTheme.COLORS["text_primary"]};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            color: {AppTheme.COLORS["text_secondary"]};
        }}
        
        QLabel {{
            color: {AppTheme.COLORS["text_primary"]};
        }}
        
        QLabel.secondary {{
            color: {AppTheme.COLORS["text_secondary"]};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {AppTheme.COLORS["border"]};
            background-color: {AppTheme.COLORS["bg_main"]};
            border-radius: 4px;
        }}
        
        QTabBar::tab {{
            background-color: {AppTheme.COLORS["bg_surface"]};
            color: {AppTheme.COLORS["text_secondary"]};
            padding: 10px 20px;
            margin-right: 2px;
            border: 1px solid {AppTheme.COLORS["border"]};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {AppTheme.COLORS["bg_main"]};
            color: {AppTheme.COLORS["text_primary"]};
            border-bottom: 2px solid {AppTheme.COLORS["primary"]};
        }}
        
        QTabBar::tab:hover {{
            background-color: {AppTheme.COLORS["bg_input"]};
        }}
        
        QMenuBar {{
            background-color: {AppTheme.COLORS["bg_surface"]};
            color: {AppTheme.COLORS["text_primary"]};
            border-bottom: 1px solid {AppTheme.COLORS["border"]};
        }}
        
        QMenuBar::item:selected {{
            background-color: {AppTheme.COLORS["bg_input"]};
        }}
        
        QMenu {{
            background-color: {AppTheme.COLORS["bg_surface"]};
            color: {AppTheme.COLORS["text_primary"]};
            border: 1px solid {AppTheme.COLORS["border"]};
        }}
        
        QMenu::item:selected {{
            background-color: {AppTheme.COLORS["primary"]};
        }}
        
        QScrollBar:vertical {{
            background-color: {AppTheme.COLORS["bg_surface"]};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {AppTheme.COLORS["border"]};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {AppTheme.COLORS["text_secondary"]};
        }}
        
        QScrollBar:horizontal {{
            background-color: {AppTheme.COLORS["bg_surface"]};
            height: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {AppTheme.COLORS["border"]};
            border-radius: 6px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {AppTheme.COLORS["text_secondary"]};
        }}
        
        QScrollBar::add-line, QScrollBar::sub-line {{
            border: none;
            background: none;
        }}
        """


class KPICard(QFrame):
    """
    Tarjeta KPI reutilizable para mostrar métricas.
    
    Args:
        title: Título de la métrica
        value: Valor de la métrica
        change: Cambio porcentual (opcional)
        color: Color del valor (opcional, por defecto text_primary)
    """
    
    def __init__(self, title: str, value: str = "N/A", change: str = None, 
                 color: str = None, parent: QWidget = None):
        super().__init__(parent)
        self.setProperty("class", "card")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # Título
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {AppTheme.COLORS['text_secondary']}; font-size: 12px; font-weight: 600; text-transform: uppercase;")
        layout.addWidget(self.title_label)
        
        # Valor
        self.value_label = QLabel(value)
        value_font = QFont("JetBrains Mono", 24)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        
        if color:
            self.value_label.setStyleSheet(f"color: {color};")
        else:
            self.value_label.setStyleSheet(f"color: {AppTheme.COLORS['text_primary']};")
        
        layout.addWidget(self.value_label)
        
        # Cambio (opcional)
        if change:
            self.change_label = QLabel(change)
            change_color = AppTheme.COLORS['success'] if '+' in change else AppTheme.COLORS['danger']
            self.change_label.setStyleSheet(f"color: {change_color}; font-size: 12px;")
            layout.addWidget(self.change_label)
        else:
            self.change_label = None
        
        layout.addStretch()
    
    def update_value(self, value: str, change: str = None):
        """Actualiza el valor de la tarjeta"""
        self.value_label.setText(value)
        if change and self.change_label:
            self.change_label.setText(change)
            change_color = AppTheme.COLORS['success'] if '+' in change else AppTheme.COLORS['danger']
            self.change_label.setStyleSheet(f"color: {change_color}; font-size: 12px;")


class ModernTable(QTableWidget):
    """
    Tabla moderna pre-configurada con el estilo de la aplicación.
    
    Args:
        headers: Lista de encabezados de columna
    """
    
    def __init__(self, headers: list[str], parent: QWidget = None):
        super().__init__(parent)
        
        # Configurar columnas
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Configuración general
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Ajustar columnas
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        # Ocultar numeración de filas
        self.verticalHeader().setVisible(False)
        
        # Altura mínima de filas
        self.verticalHeader().setDefaultSectionSize(45)
    
    def add_row(self, data: list):
        """
        Añade una fila a la tabla.
        
        Args:
            data: Lista de valores para cada columna
        """
        row_position = self.rowCount()
        self.insertRow(row_position)
        
        for col, value in enumerate(data):
            item = QTableWidgetItem(str(value))
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.setItem(row_position, col, item)
    
    def clear_table(self):
        """Limpia todas las filas de la tabla"""
        self.setRowCount(0)


class StatusBadge(QLabel):
    """
    Etiqueta de estado redondeada con color.
    
    Args:
        text: Texto del badge
        status_type: Tipo de estado ('success', 'warning', 'danger', 'default')
    """
    
    def __init__(self, text: str, status_type: str = "default", parent: QWidget = None):
        super().__init__(text, parent)
        
        color_map = {
            "success": AppTheme.COLORS["success"],
            "warning": AppTheme.COLORS["warning"],
            "danger": AppTheme.COLORS["danger"],
            "default": AppTheme.COLORS["text_secondary"]
        }
        
        bg_color = color_map.get(status_type, color_map["default"])
        text_color = "#FFFFFF" if status_type != "default" else AppTheme.COLORS["bg_main"]
        
        self.setStyleSheet(f"""
            background-color: {bg_color};
            color: {text_color};
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
        """)
        
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMaximumWidth(120)


class ModernButton(QPushButton):
    """
    Botón moderno con estilo predefinido.
    
    Args:
        text: Texto del botón
        button_type: Tipo de botón ('primary', 'secondary', 'success', 'danger')
    """
    
    def __init__(self, text: str, button_type: str = "primary", parent: QWidget = None):
        super().__init__(text, parent)
        self.setProperty("class", button_type)
