"""
Gestor de temas para EQUIPOS 4.0
Proporciona 4 temas modernos para la interfaz gráfica
ACTUALIZADO: Ahora usa AppTheme como tema por defecto (Industrial Dark Mode)
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt
from app_theme import AppTheme


class ThemeManager:
    """
    Gestor de temas para la aplicación.
    Proporciona 4 temas modernos: Claro, Oscuro (AppTheme), Azul y Morado
    """
    
    THEMES = {
        "Claro": "light",
        "Oscuro": "dark",
        "Azul Corporativo": "blue",
        "Morado Moderno": "purple"
    }
    
    @staticmethod
    def apply_theme(app: QApplication, theme_name: str = "Oscuro"):
        """
        Aplica un tema a la aplicación.
        
        Args:
            app: Instancia de QApplication
            theme_name: Nombre del tema ("Claro", "Oscuro", "Azul Corporativo", "Morado Moderno")
        """
        theme_key = ThemeManager.THEMES.get(theme_name, "dark")
        
        if theme_key == "light":
            ThemeManager._apply_light_theme(app)
        elif theme_key == "dark":
            ThemeManager._apply_dark_theme(app)
        elif theme_key == "blue":
            ThemeManager._apply_blue_theme(app)
        elif theme_key == "purple":
            ThemeManager._apply_purple_theme(app)
    
    @staticmethod
    def _apply_light_theme(app: QApplication):
        """Tema claro (por defecto de Qt6)"""
        app.setStyle("Fusion")
        palette = QPalette()
        
        # Colores base
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 102, 204))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        app.setPalette(palette)
        app.setStyleSheet("")
    
    @staticmethod
    def _apply_dark_theme(app: QApplication):
        """Tema oscuro moderno - Ahora usa AppTheme (Industrial Dark Mode)"""
        app.setStyle("Fusion")
        
        # Aplicar el stylesheet de AppTheme
        app.setStyleSheet(AppTheme.get_stylesheet())
        
        # Configurar paleta base para compatibilidad
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(AppTheme.COLORS["bg_main"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(AppTheme.COLORS["text_primary"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(AppTheme.COLORS["bg_surface"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(AppTheme.COLORS["bg_input"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(AppTheme.COLORS["text_primary"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(AppTheme.COLORS["bg_surface"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(AppTheme.COLORS["text_primary"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(AppTheme.COLORS["primary"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(AppTheme.COLORS["text_primary"]))
        
        app.setPalette(palette)
    
    @staticmethod
    def _apply_blue_theme(app: QApplication):
        """Tema azul corporativo"""
        app.setStyle("Fusion")
        palette = QPalette()
        
        # Colores azules
        palette.setColor(QPalette.ColorRole.Window, QColor(235, 241, 247))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 245, 250))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(225, 235, 245))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 102, 204))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        app.setPalette(palette)
        
        # CSS para acentuar el azul
        stylesheet = """
            QMenuBar {
                background-color: #0078d7;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #005a9e;
            }
            QMenu {
                background-color: #f0f5fa;
                color: #000000;
                border: 1px solid #0078d7;
            }
            QMenu::item:selected {
                background-color: #cce4f7;
            }
            QPushButton {
                background-color: #0078d7;
                color: #ffffff;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QTabWidget::pane {
                border: 1px solid #0078d7;
            }
            QTabBar::tab {
                background-color: #e1ebf5;
                color: #000000;
                padding: 8px 12px;
                border: 1px solid #0078d7;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #0078d7;
                color: #ffffff;
            }
        """
        app.setStyleSheet(stylesheet)
    
    @staticmethod
    def _apply_purple_theme(app: QApplication):
        """Tema morado moderno"""
        app.setStyle("Fusion")
        palette = QPalette()
        
        # Colores morados
        palette.setColor(QPalette.ColorRole.Window, QColor(245, 240, 250))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(250, 245, 255))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(235, 225, 245))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(138, 43, 226))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(147, 51, 234))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        app.setPalette(palette)
        
        # CSS para acentuar el morado
        stylesheet = """
            QMenuBar {
                background-color: #9333ea;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #7e22ce;
            }
            QMenu {
                background-color: #faf5ff;
                color: #000000;
                border: 1px solid #9333ea;
            }
            QMenu::item:selected {
                background-color: #e9d5ff;
            }
            QPushButton {
                background-color: #9333ea;
                color: #ffffff;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #7e22ce;
            }
            QPushButton:pressed {
                background-color: #6b21a8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QTabWidget::pane {
                border: 1px solid #9333ea;
            }
            QTabBar::tab {
                background-color: #ebe1f5;
                color: #000000;
                padding: 8px 12px;
                border: 1px solid #9333ea;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #9333ea;
                color: #ffffff;
            }
        """
        app.setStyleSheet(stylesheet)
    
    @staticmethod
    def get_available_themes():
        """Retorna lista de temas disponibles"""
        return list(ThemeManager.THEMES.keys())
