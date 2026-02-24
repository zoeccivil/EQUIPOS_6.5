"""
Componentes UI Reutilizables para EQUIPOS 6.0
Componentes que replican exactamente el prototipo HTML
"""

from PyQt6.QtWidgets import (
    QPushButton, QLabel, QFrame, QVBoxLayout, QHBoxLayout,
    QWidget, QLineEdit, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPainter
from app_theme_modern import ModernTheme
from icons_material import get_material_icon


# ============================================================
# SIDEBAR BUTTON - Botón de navegación con icono
# ============================================================

class SidebarButton(QPushButton):
    """
    Botón de navegación para el sidebar.
    
    Estados:
    - Normal: bg transparent, color #D1D5DB
    - Hover: bg rgba(255,255,255,0.05), color white
    - Active: bg #F59E0B, color #78350F, bold, shadow
    """
    
    def __init__(self, text: str, icon_name: str, parent=None):
        super().__init__(text, parent)
        self.icon_name = icon_name
        self.is_active = False
        
        # Configuración básica
        self.setCheckable(True)
        self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Establecer icono
        self._update_icon()
        self.setIconSize(QSize(20, 20))
        
        # Aplicar estilo
        self._apply_style()
        
        # Conectar señales
        self.toggled.connect(self._on_toggled)
    
    def _update_icon(self):
        """Actualiza el icono según el estado"""
        if self.is_active:
            color = ModernTheme.COLORS['primary_text']  # #78350F
        else:
            color = ModernTheme.COLORS['text_sidebar_inactive']  # #D1D5DB
        
        icon = get_material_icon(self.icon_name, color, 20)
        self.setIcon(icon)
    
    def _apply_style(self):
        """Aplica el estilo QSS al botón"""
        c = ModernTheme.COLORS
        
        if self.is_active:
            # Estado activo: amarillo con sombra
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['primary']};
                    color: {c['primary_text']};
                    border: none;
                    border-radius: 8px;
                    padding: 12px 16px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: 700;
                }}
            """)
            
            # Agregar sombra
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(6)
            shadow.setColor(QColor(245, 158, 11, 77))  # rgba(245, 158, 11, 0.3)
            shadow.setOffset(0, 4)
            self.setGraphicsEffect(shadow)
        else:
            # Estado normal/hover
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c['text_sidebar_inactive']};
                    border: none;
                    border-radius: 8px;
                    padding: 12px 16px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.05);
                    color: {c['text_sidebar']};
                }}
            """)
            self.setGraphicsEffect(None)
    
    def _on_toggled(self, checked: bool):
        """Callback cuando se togglea el botón"""
        self.is_active = checked
        self._update_icon()
        self._apply_style()
    
    def setActive(self, active: bool):
        """Establece el estado activo programáticamente"""
        self.setChecked(active)


# ============================================================
# STAT CARD - Tarjeta KPI con icono y barra de color
# ============================================================

class StatCard(QFrame):
    """Tarjeta KPI del dashboard."""
    
    def __init__(
        self,
        title: str,
        value: str,
        icon_name: str,
        accent_color: str,
        footer_text: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.accent_color = accent_color
        
        # Configuración del frame
        self.setObjectName("modern_card")
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(12)
        
        # Header: icono + label
        header = QHBoxLayout()
        header.setSpacing(12)
        
        # Icon box
        icon_map = {
            "attach_money": "💰",
            "pending_actions": "⏳",
            "trending_up": "📈",
            "precision_manufacturing": "📊",
        }
        
        icon_box = QLabel(icon_map.get(icon_name, "📊"))
        icon_box.setFixedSize(40, 40)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Background del icono
        icon_bg_color = self._lighten_color(accent_color)
        icon_box.setStyleSheet(f"""
            QLabel {{
                background-color: {icon_bg_color};
                border-radius: 8px;
                font-size: 20px;
            }}
        """)
        header.addWidget(icon_box)
        
        header.addStretch()
        
        # ✅ LABEL DEL TÍTULO (sin fondo gris)
        label = QLabel(title.upper())
        label.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_muted']};
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
                background-color: transparent;  /* ✅ SIN FONDO */
            }}
        """)
        header.addWidget(label)
        
        layout.addLayout(header)
        
        # ✅ VALOR PRINCIPAL (sin fondo gris)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("kpi_value")
        self.value_label.setStyleSheet(f"""
            QLabel#kpi_value {{
                color: {ModernTheme.COLORS['text_main']};
                font-size: 28px;
                font-weight: 800;
                background-color: transparent;  /* ✅ SIN FONDO */
            }}
        """)
        layout.addWidget(self.value_label)
        
        # ✅ FOOTER (sin fondo gris)
        self.footer_label = QLabel(footer_text)
        self.footer_label.setObjectName("kpi_footer")
        self.footer_label.setStyleSheet(f"""
            QLabel#kpi_footer {{
                color: {ModernTheme.COLORS['text_muted']};
                font-size: 12px;
                background-color: transparent;  /* ✅ SIN FONDO */
            }}
        """)
        layout.addWidget(self.footer_label)
        
        layout.addStretch()
        
        # Barra de progreso
        self.progress_container = QFrame()
        self.progress_container.setFixedHeight(4)
        self.progress_container.setStyleSheet(f"""
            QFrame {{
                background-color: {accent_color};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.progress_container)
        
        # ✅ ESTILO DEL CARD (fondo blanco limpio)
        self.setStyleSheet(f"""
            QFrame#modern_card {{
                background-color: {ModernTheme.COLORS['bg_card']};
                border: 1px solid {ModernTheme.COLORS['border']};
                border-radius: 12px;
            }}
            /* ✅ Asegurar que todos los QLabel hijos tengan fondo transparente */
            QFrame#modern_card QLabel {{
                background-color: transparent;
            }}
        """)
        
        # Sombra
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(3)
        shadow.setColor(QColor(0, 0, 0, 13))
        shadow.setOffset(0, 1)
        self.setGraphicsEffect(shadow)
    
    
    def _lighten_color(self, hex_color: str) -> str:
        """Genera un color más claro para el fondo del icono"""
        color_map = {
            '#3B82F6': '#EFF6FF',  # Azul
            '#F59E0B': '#FFFBEB',  # Amarillo
            '#10B981': '#ECFDF5',  # Verde
            '#6366F1': '#EEF2FF',  # Morado
        }
        return color_map.get(hex_color, '#F3F4F6')
    
    def set_value(self, value: str):
        """Actualiza el valor del KPI"""
        self.value_label.setText(value)
    
    def set_footer(self, text: str):
        """Actualiza el texto del footer"""
        self.footer_label.setText(text)


# ============================================================
# STATUS BADGE - Píldora de estado (Pagado/Pendiente/Vencido)
# ============================================================

class StatusBadge(QLabel):
    """Badge tipo píldora para indicar estados."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(24)  # ✅ REDUCIR: 28 → 24px
        self.setMinimumWidth(90)  # ✅ REDUCIR: 110 → 90px
        
        # Estilo base de píldora
        self._base_style = """
            QLabel {{
                background-color: {bg};
                color: {text};
                border-radius: 12px;  /* ✅ REDUCIR: 14 → 12px */
                padding: 2px 8px;  /* ✅ REDUCIR: 4px 12px → 3px 10px */
                font-size: 10px;  /* ✅ REDUCIR: 12 → 10px */
                font-weight: 550;
            }}
        """
    
    def setPaid(self):
        """Estado: Pagado (verde)"""
        c = ModernTheme.COLORS
        self.setStyleSheet(self._base_style.format(
            bg=c['success_bg'],
            text=c['success_text']
        ))
        self.setText("✓ Pagado")
    
    def setPending(self):
        """Estado: Pendiente (amarillo)"""
        c = ModernTheme.COLORS
        self.setStyleSheet(self._base_style.format(
            bg=c['warning_bg'],
            text=c['warning_text']
        ))
        self.setText("⏰ Pend.")  # ✅ ACORTAR: "Pendiente" → "Pend."
    
    def setOverdue(self):
        """Estado: Vencido (rojo)"""
        c = ModernTheme.COLORS
        self.setStyleSheet(self._base_style.format(
            bg=c['danger_bg'],
            text=c['danger_text']
        ))
        self.setText("⚠ Venc.")  # ✅ ACORTAR: "Vencido" → "Venc."
    
    def setCustom(self, text: str, bg_color: str, text_color: str):
        """Estado personalizado"""
        self.setStyleSheet(self._base_style.format(
            bg=bg_color,
            text=text_color
        ))
        self.setText(text)


# ============================================================
# BRAND HEADER - Logo "Z" + Texto
# ============================================================

class BrandHeader(QWidget):
    """Logo y título de la marca en el sidebar"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(12)
        
        # Logo circular
        logo_label = QLabel("Z")
        logo_label.setFixedSize(48, 48)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet(f"""
            QLabel {{
                background-color: {ModernTheme.COLORS['primary']};
                color: {ModernTheme.COLORS['primary_text']};
                border-radius: 24px;
                font-size: 24px;
                font-weight: 700;
            }}
        """)
        layout.addWidget(logo_label)
        
        # Texto
        text_container = QWidget()
        text_container.setStyleSheet("background-color: transparent;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        
        title = QLabel("ZOEC CIVIL")
        title.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_sidebar']};
                font-size: 14px;
                font-weight: 700;
                background-color: transparent;
            }}
        """)
        
        subtitle = QLabel("EQUIPOS PESADOS")
        subtitle.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_sidebar_muted']};
                font-size: 10px;
                font-weight: 500;
                background-color: transparent;
            }}
        """)
        
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        layout.addWidget(text_container)
        layout.addStretch()


# ============================================================
# TOP BAR - Barra superior con título y búsqueda
# ============================================================

class TopBar(QWidget):
    """
    Barra superior de navegación con título y búsqueda.
    """
    
    searchRequested = pyqtSignal(str)
    
    def __init__(self, title: str = "Dashboard", show_search: bool = True, parent=None):
        super().__init__(parent)
        self.setFixedHeight(70)
        
        # Layout horizontal
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 0, 32, 0)
        layout.setSpacing(20)
        
        # ✅ TÍTULO CON ESTILO MEJORADO
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_main']};
                font-size: 24px;  /* ✅ Más grande */
                font-weight: 800;  /* ✅ Más bold */
                background-color: transparent;
            }}
        """)
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Barra de búsqueda
        if show_search:
            search_container = QFrame()
            search_container.setFixedWidth(300)
            search_container.setFixedHeight(40)
            search_container.setStyleSheet(f"""
                QFrame {{
                    background-color: {ModernTheme.COLORS['input_bg']};
                    border: 1px solid {ModernTheme.COLORS['border']};
                    border-radius: 8px;
                }}
            """)
            
            search_layout = QHBoxLayout(search_container)
            search_layout.setContentsMargins(16, 0, 16, 0)
            search_layout.setSpacing(10)
            
            # Icono
            search_icon = QLabel("🔍")
            search_icon.setStyleSheet("font-size: 16px; background-color: transparent;")
            search_layout.addWidget(search_icon)
            
            # Input
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText("Buscar equipo, cliente o ID...")
            self.search_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: transparent;
                    border: none;
                    color: {ModernTheme.COLORS['text_main']};
                    font-size: 14px;
                }}
                QLineEdit::placeholder {{
                    color: {ModernTheme.COLORS['text_muted']};
                }}
            """)
            self.search_input.returnPressed.connect(self._on_search)
            search_layout.addWidget(self.search_input)
            
            layout.addWidget(search_container)
        
        # ✅ ESTILO MEJORADO (fondo diferenciado)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #FAFAFA;  /* ✅ Gris muy claro (casi blanco pero diferenciado) */
                border-bottom: 1px solid {ModernTheme.COLORS['border']};
            }}
        """)
    
    def setTitle(self, title: str):
        """Cambia el título"""
        self.title_label.setText(title)
    
    def _on_search(self):
        """Emite señal de búsqueda"""
        text = self.search_input.text().strip()
        if text:
            self.searchRequested.emit(text)
    
    def setTitle(self, title: str):
        """Cambia el título"""
        self.title_label.setText(title)
    
    def _on_search(self):
        """Emite señal de búsqueda"""
        text = self.search_input.text().strip()
        if text:
            self.searchRequested.emit(text)


# ============================================================
# MODERN CARD - Contenedor blanco con sombra
# ============================================================

class ModernCard(QFrame):
    """Contenedor tipo tarjeta con fondo blanco, borde y sombra."""
    
    def __init__(self, title: str = None, padding: int = 20, parent=None):
        super().__init__(parent)
        self.setObjectName("modern_card")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(padding, padding, padding, padding)
        self.main_layout.setSpacing(16)
        
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet(f"""
                QLabel {{
                    color: {ModernTheme.COLORS['text_main']};
                    font-size: 16px;
                    font-weight: 700;
                    background-color: transparent;  /* ✅ CRÍTICO */
                }}
            """)
            self.main_layout.addWidget(title_label)
        
        # ✅ ESTILO MEJORADO (forzar transparencia en hijos)
        self.setStyleSheet(f"""
            QFrame#modern_card {{
                background-color: {ModernTheme.COLORS['bg_card']};
                border: 1px solid {ModernTheme.COLORS['border']};
                border-radius: 12px;
            }}
            /* ✅ FORZAR que TODOS los QLabel dentro sean transparentes */
            QFrame#modern_card QLabel {{
                background-color: transparent;
            }}
            /* ✅ También los QFrame internos */
            QFrame#modern_card QFrame {{
                background-color: transparent;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(3)
        shadow.setColor(QColor(0, 0, 0, 13))
        shadow.setOffset(0, 1)
        self.setGraphicsEffect(shadow)
    
    def add_widget(self, widget: QWidget):
        """Agrega un widget"""
        self.main_layout.addWidget(widget)
    
    def add_layout(self, layout):
        """Agrega un layout"""
        self.main_layout.addLayout(layout)


# ============================================================
# MODERN BUTTON - Botón con variantes
# ============================================================

class ModernButton(QPushButton):
    """Botón moderno con variantes de estilo."""
    
    def __init__(self, text: str, button_type: str = "secondary", icon_name: str = None, parent=None):
        super().__init__(text, parent)
        self.button_type = button_type
        self.icon_name = icon_name
        
        self.setMinimumHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if icon_name:
            self.setIconSize(QSize(20, 20))
        
        self._apply_style()
    
    def _apply_style(self):
        """Aplica el estilo según el tipo"""
        c = ModernTheme.COLORS
        
        styles = {
            'primary': f"""
                QPushButton {{
                    background-color: {c['primary']};
                    color: {c['primary_text']};
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: 600;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {c['primary_hover']};
                }}
            """,
            'secondary': f"""
                QPushButton {{
                    background-color: {c['bg_card']};
                    color: {c['text_main']};
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: 600;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {c['hover_bg']};
                }}
            """,
        }
        
        self.setStyleSheet(styles.get(self.button_type, styles['secondary']))

# ============================================================
# DATE PICKER - Selector de fecha moderno
# ============================================================

from PyQt6.QtWidgets import QDateEdit
from PyQt6.QtCore import QDate

class ModernDatePicker(QDateEdit):
    """Selector de fecha con estilo moderno"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yyyy-MM-dd")
        self.setDate(QDate.currentDate())
        
        self.setStyleSheet(f"""
            QDateEdit {{
                background-color: {ModernTheme.COLORS['bg_card']};
                color: {ModernTheme.COLORS['text_main']};
                border: 1px solid {ModernTheme.COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                min-width: 140px;
            }}
            QDateEdit:hover {{
                border-color: {ModernTheme.COLORS['primary']};
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 30px;
            }}
            QDateEdit::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {ModernTheme.COLORS['text_muted']};
                margin-right: 8px;
            }}
            QCalendarWidget {{
                background-color: {ModernTheme.COLORS['bg_card']};
                border: 1px solid {ModernTheme.COLORS['border']};
            }}
            QCalendarWidget QWidget {{
                alternate-background-color: {ModernTheme.COLORS['hover_bg']};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {ModernTheme.COLORS['text_main']};
                selection-background-color: {ModernTheme.COLORS['primary']};
                selection-color: {ModernTheme.COLORS['primary_text']};
            }}
        """)


# ============================================================
# ACTION BUTTON - Botón de acción pequeño para tablas
# ============================================================

class ActionButton(QPushButton):
    """Botón pequeño de acción para usar en tablas"""
    
    def __init__(self, icon_name: str, tooltip: str = "", color: str = None, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.color = color or ModernTheme.COLORS['text_muted']
        
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        
        # Emoji fallback para iconos
        icon_map = {
            "visibility": "👁️",
            "edit": "✏️",
            "delete": "🗑️",
            "payments": "💰",
            "attach_file": "📎",
            "download": "⬇️",
        }
        
        emoji = icon_map.get(icon_name, "•")
        self.setText(emoji)
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {ModernTheme.COLORS['border']};
                border-radius: 6px;
                color: {self.color};
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {ModernTheme.COLORS['hover_bg']};
                border-color: {self.color};
            }}
            QPushButton:pressed {{
                background-color: {ModernTheme.COLORS['border']};
            }}
        """)


# ============================================================
# FILTER BAR - Barra de filtros reutilizable
# ============================================================

class FilterBar(ModernCard):
    """Barra de filtros con campos comunes"""
    
    def __init__(self, parent=None):
        super().__init__(padding=20, parent=parent)
        
        self.filters_layout = QHBoxLayout()
        self.filters_layout.setSpacing(12)
        
        # Label "Filtros:"
        label = QLabel("Filtros:")
        label.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_main']};
                font-size: 14px;
                font-weight: 600;
                background-color: transparent;
            }}
        """)
        self.filters_layout.addWidget(label)
        
        self.add_layout(self.filters_layout)
    
    def add_filter(self, widget: QWidget):
        """Agrega un widget de filtro"""
        self.filters_layout.addWidget(widget)
    
    def add_stretch(self):
        """Agrega espacio flexible"""
        self.filters_layout.addStretch()
    
    def add_button(self, button: QPushButton):
        """Agrega un botón al final"""
        self.filters_layout.addWidget(button)


# Actualizar __all__ al final del archivo
__all__ = [
    'SidebarButton',
    'StatCard',
    'StatusBadge',
    'BrandHeader',
    'TopBar',
    'ModernCard',
    'ModernButton',
    'ModernDatePicker',
    'ActionButton',
    'FilterBar',
]
