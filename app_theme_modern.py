"""
Sistema de Diseño Moderno para EQUIPOS 6.0
Tema "Tierra & Asfalto" - Inspirado en maquinaria industrial
Paleta de colores y estilos QSS globales
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont


class ModernTheme:
    """
    Define la paleta de colores moderna tipo aplicación web
    Estilo: Industrial/Construcción con acentos cálidos
    """
    
    # Paleta de Colores "Tierra & Asfalto"
    COLORS = {
        # Estructura
        'bg_body': '#F3F4F6',      # Fondo de las vistas (Concreto limpio)
        'bg_sidebar': '#1F2937',    # Menu lateral (Asfalto oscuro)
        'bg_card': '#FFFFFF',       # Fondo de tablas y KPIs
        'border': '#E5E7EB',        # Bordes sutiles
        
        # Acentos (Maquinaria)
        'primary': '#F59E0B',       # Amarillo Caterpillar/Ámbar
        'primary_hover': '#D97706',
        'primary_text': '#78350F',  # Texto oscuro sobre amarillo
        'secondary': '#3B82F6',     # Azul ingeniero
        
        # Texto
        'text_main': '#111827',     # Negro casi puro
        'text_muted': '#6B7280',    # Gris medio
        'text_sidebar': '#F9FAFB',  # Blanco para sidebar
        'text_sidebar_muted': '#9CA3AF',      # Gris para subtítulos en sidebar
        'text_sidebar_inactive': '#D1D5DB',   # ← LÍNEA AGREGADA - Botones sidebar inactivos
        
        # Estados
        'success_bg': '#DCFCE7',
        'success_text': '#166534',
        'success_dark': '#10B981',    # ← AGREGADO para consistencia
        'warning_bg': '#FEF3C7',
        'warning_text': '#92400E',
        'danger_bg': '#FEE2E2',
        'danger_text': '#991B1B',
        'danger_dark': '#EF4444',     # ← AGREGADO para consistencia
        
        # Fondos adicionales
        'bg_input': '#FFFFFF',
        'bg_hover': '#F9FAFB',
        'bg_sidebar_hover': 'rgba(255, 255, 255, 0.05)',
        
        # Estados adicionales (usados en componentes)
        'info_bg': '#EFF6FF',
        'info_text': '#1E40AF',
        'info_dark': '#3B82F6',
        'purple_bg': '#EEF2FF',
        'purple_text': '#4338CA',
        'purple_dark': '#6366F1',
        'warning_dark': '#F59E0B',
        'input_bg': '#F3F4F6',      # Para inputs con fondo gris
        'hover_bg': '#F9FAFB',       # Alias consistente
        'active_bg': '#F59E0B',      # Fondo activo
    }
    
    @staticmethod
    def get_stylesheet() -> str:
        """Retorna el stylesheet completo moderno de la aplicación"""
        c = ModernTheme.COLORS
        
        return f"""
        /* ============================================
           GLOBAL STYLES
           ============================================ */
        
        QMainWindow, QWidget {{
            background-color: {c['bg_body']};
            color: {c['text_main']};
            font-family: 'Segoe UI', 'Roboto', 'Inter', sans-serif;
            font-size: 14px;
        }}
        
        /* ============================================
           INPUTS
           ============================================ */
        
        QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {{
            background-color: {c['bg_input']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 8px 12px;
            color: {c['text_main']};
            min-height: 36px;
        }}
        
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus, 
        QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
            border: 2px solid {c['primary']};
            padding: 7px 11px; /* Compensar el borde más grueso */
        }}
        
        QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled,
        QSpinBox:disabled, QDoubleSpinBox:disabled, QTextEdit:disabled {{
            background-color: {c['bg_hover']};
            color: {c['text_muted']};
        }}
        
        /* ComboBox específico */
        QComboBox::drop-down {{
            border: none;
            padding-right: 8px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {c['text_muted']};
            margin-right: 8px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {c['bg_card']};
            color: {c['text_main']};
            selection-background-color: {c['primary']};
            selection-color: {c['primary_text']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 4px;
        }}
        
        /* ============================================
           BUTTONS
           ============================================ */
        
        QPushButton {{
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: 600;
            min-height: 36px;
            border: none;
        }}
        
        QPushButton.primary {{
            background-color: {c['primary']};
            color: {c['primary_text']};
        }}
        
        QPushButton.primary:hover {{
            background-color: {c['primary_hover']};
        }}
        
        QPushButton.primary:pressed {{
            background-color: #B45309;
        }}
        
        QPushButton.secondary {{
            background-color: transparent;
            border: 1px solid {c['border']};
            color: {c['text_main']};
        }}
        
        QPushButton.secondary:hover {{
            background-color: {c['bg_hover']};
        }}
        
        QPushButton.success {{
            background-color: #10B981;
            color: white;
        }}
        
        QPushButton.success:hover {{
            background-color: #059669;
        }}
        
        QPushButton.danger {{
            background-color: #EF4444;
            color: white;
        }}
        
        QPushButton.danger:hover {{
            background-color: #DC2626;
        }}
        
        QPushButton:disabled {{
            background-color: {c['bg_hover']};
            color: {c['text_muted']};
            border: 1px solid {c['border']};
        }}
        
        /* ============================================
           TABLES
           ============================================ */
        
        QTableWidget {{
            background-color: {c['bg_card']};
            border: none;
            border-radius: 8px;
            gridline-color: {c['border']};
            selection-background-color: {c['bg_hover']};
            selection-color: {c['text_main']};
        }}
        
        QTableWidget::item {{
            padding: 12px 8px;
            border-bottom: 1px solid {c['border']};
        }}
        
        QTableWidget::item:hover {{
            background-color: {c['bg_hover']};
        }}
        
        QTableWidget::item:selected {{
            background-color: {c['bg_hover']};
            color: {c['text_main']};
        }}
        
        QHeaderView::section {{
            background-color: {c['bg_hover']};
            color: {c['text_muted']};
            padding: 12px 8px;
            border: none;
            border-bottom: 1px solid {c['border']};
            font-weight: 700;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        
        QHeaderView::section:hover {{
            background-color: #F3F4F6;
        }}
        
        /* Ocultar líneas verticales de grilla */
        QTableWidget {{
            show-decoration-selected: 0;
        }}
        
        /* ============================================
           SCROLLBARS
           ============================================ */
        
        QScrollBar:vertical {{
            background-color: transparent;
            width: 8px;
            border-radius: 4px;
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {c['border']};
            border-radius: 4px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {c['text_muted']};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            background-color: transparent;
            height: 8px;
            border-radius: 4px;
            margin: 0px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {c['border']};
            border-radius: 4px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {c['text_muted']};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        /* ============================================
           GROUPBOX
           ============================================ */
        
        QGroupBox {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            margin-top: 12px;
            padding: 16px;
            font-weight: 600;
            color: {c['text_main']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            color: {c['text_muted']};
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        /* ============================================
           LABELS
           ============================================ */
        
        QLabel {{
            color: {c['text_main']};
        }}
        
        QLabel.secondary {{
            color: {c['text_muted']};
        }}
        
        QLabel.muted {{
            color: {c['text_muted']};
            font-size: 13px;
        }}
        
        /* ============================================
           TABS (si se necesitan)
           ============================================ */
        
        QTabWidget::pane {{
            border: 1px solid {c['border']};
            background-color: {c['bg_card']};
            border-radius: 8px;
        }}
        
        QTabBar::tab {{
            background-color: transparent;
            color: {c['text_muted']};
            padding: 12px 24px;
            margin-right: 4px;
            border: none;
            border-bottom: 2px solid transparent;
        }}
        
        QTabBar::tab:selected {{
            color: {c['primary']};
            border-bottom: 2px solid {c['primary']};
            font-weight: 600;
        }}
        
        QTabBar::tab:hover {{
            color: {c['text_main']};
            background-color: {c['bg_hover']};
        }}
        
        /* ============================================
           MENU
           ============================================ */
        
        QMenuBar {{
            background-color: {c['bg_card']};
            color: {c['text_main']};
            border-bottom: 1px solid {c['border']};
            padding: 4px;
        }}
        
        QMenuBar::item {{
            padding: 8px 16px;
            border-radius: 4px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {c['bg_hover']};
        }}
        
        QMenu {{
            background-color: {c['bg_card']};
            color: {c['text_main']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 8px 24px 8px 16px;
            border-radius: 4px;
        }}
        
        QMenu::item:selected {{
            background-color: {c['bg_hover']};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {c['border']};
            margin: 4px 8px;
        }}
        
        /* ============================================
           FRAMES
           ============================================ */
        
        QFrame.card {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border']};
            border-radius: 12px;
        }}
        
        QFrame.sidebar {{
            background-color: {c['bg_sidebar']};
            border-right: 1px solid #374151;
        }}
        
        /* ============================================
           CHECKBOX & RADIO
           ============================================ */
        
        QCheckBox, QRadioButton {{
            spacing: 8px;
            color: {c['text_main']};
        }}
        
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {c['border']};
            border-radius: 4px;
            background-color: {c['bg_input']};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {c['primary']};
            border-color: {c['primary']};
        }}
        
        QRadioButton::indicator {{
            border-radius: 9px;
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {c['primary']};
            border-color: {c['primary']};
        }}
        """
    
    @staticmethod
    def get_font(size: int = 14, weight: str = "normal") -> QFont:
        """
        Retorna una fuente configurada según el sistema de diseño.
        
        Args:
            size: Tamaño de la fuente en puntos
            weight: Peso de la fuente ('normal', 'bold', 'light')
        
        Returns:
            QFont configurado
        """
        font = QFont("Segoe UI", size)
        
        if weight == "bold":
            font.setWeight(QFont.Weight.Bold)
        elif weight == "light":
            font.setWeight(QFont.Weight.Light)
        else:
            font.setWeight(QFont.Weight.Normal)
        
        return font