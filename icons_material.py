"""
Sistema de Iconos Material Design Round para EQUIPOS 6.0
Iconos SVG monocromáticos que replican Material Icons Round de Google
"""

from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray, Qt

def get_material_icon(name: str, color: str = "#6B7280", size: int = 24) -> QIcon:
    """
    Genera un QIcon a partir de un SVG Material Design Round.
    
    Args:
        name: Nombre del icono (ej: 'dashboard', 'agriculture')
        color: Color en formato hex (ej: '#F59E0B')
        size: Tamaño en píxeles (default: 24)
    
    Returns:
        QIcon con el icono renderizado
    """
    svg_data = _get_svg_template(name, color)
    if not svg_data:
        # Icono por defecto si no existe
        svg_data = _get_svg_template('help_outline', color)
    
    return _svg_to_icon(svg_data, size)

def _svg_to_icon(svg_string: str, size: int) -> QIcon:
    """Convierte string SVG a QIcon"""
    svg_bytes = QByteArray(svg_string.encode('utf-8'))
    renderer = QSvgRenderer(svg_bytes)
    
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)

def _get_svg_template(name: str, color: str) -> str:
    """
    Retorna el template SVG para el icono solicitado.
    Basado en Material Icons Round de Google.
    """
    
    # Diccionario de iconos Material Design Round
    icons = {
        # --- NAVEGACIÓN ---
        'dashboard': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M11 21H5c-1.1 0-2-.9-2-2V5c0-1.1.9-2 2-2h6v18zm2 0h6c1.1 0 2-.9 2-2v-7h-8v9zm8-11V5c0-1.1-.9-2-2-2h-6v7h8z"/>
        </svg>''',
        
        'agriculture': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M19.5 12c.93 0 1.78.28 2.5.76V8c0-1.1-.9-2-2-2h-6.29l-1.06-1.06 1.41-1.41-.71-.71-3.53 3.53.71.71 1.41-1.41L13 6.71V9c0 1.1-.9 2-2 2h-.54A5.98 5.98 0 0112 15c0 .34-.04.67-.09 1h3.14L20 21.91l1.41-1.41L16.5 15.5H20c1.1 0 2-.9 2-2v-1.5c-.72-.48-1.57-.76-2.5-.76-2.49 0-4.5 2.01-4.5 4.5s2.01 4.5 4.5 4.5 4.5-2.01 4.5-4.5h-2c0 1.38-1.12 2.5-2.5 2.5s-2.5-1.12-2.5-2.5 1.12-2.5 2.5-2.5zM4 9h6c0-1.1-.9-2-2-2H4c-.55 0-1 .45-1 1s.45 1 1 1zm0 4h6c0-1.1-.9-2-2-2H4c-.55 0-1 .45-1 1s.45 1 1 1zm0 4h6c0-1.1-.9-2-2-2H4c-.55 0-1 .45-1 1s.45 1 1 1z"/>
        </svg>''',
        
        'payments': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M20 4H4c-1.11 0-1.99.89-1.99 2L2 18c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/>
        </svg>''',
        
        'engineering': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M9 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zm7 9c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1zm-7.58 5.59L6.59 17H4c-1.1 0-2 .9-2 2v3h2v-3h2.18l2.59 2.59c.39.39 1.02.39 1.41 0 .39-.39.39-1.02 0-1.41L8.41 18H11v-2H7.83l1.59-1.59c.39-.39.39-1.03 0-1.42-.39-.38-1.02-.38-1.41 0zM21.8 15.2c.4-.4.4-1.05 0-1.41l-1.47-1.47-1.41 1.41.88.88-.88.88-5.02-5.02.88-.88.88.88 1.41-1.41-1.47-1.47c-.39-.39-1.02-.39-1.41 0l-6.01 6.01c-.39.39-.39 1.02 0 1.41l6 6c.39.39 1.02.39 1.41 0l6.01-6.01z"/>
        </svg>''',
        
        'assessment': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM8 17c-.55 0-1-.45-1-1v-5c0-.55.45-1 1-1s1 .45 1 1v5c0 .55-.45 1-1 1zm4 0c-.55 0-1-.45-1-1V8c0-.55.45-1 1-1s1 .45 1 1v8c0 .55-.45 1-1 1zm4 0c-.55 0-1-.45-1-1v-2c0-.55.45-1 1-1s1 .45 1 1v2c0 .55-.45 1-1 1z"/>
        </svg>''',
        
        'settings': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M19.43 12.98c.04-.32.07-.64.07-.98 0-.34-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.09-.16-.26-.25-.44-.25-.06 0-.12.01-.17.03l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.06-.02-.12-.03-.18-.03-.17 0-.34.09-.43.25l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98 0 .33.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.09.16.26.25.44.25.06 0 .12-.01.17-.03l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.06.02.12.03.18.03.17 0 .34-.09.43-.25l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zm-1.98-1.71c.04.31.05.52.05.73 0 .21-.02.43-.05.73l-.14 1.13.89.7 1.08.84-.7 1.21-1.27-.51-1.04-.42-.9.68c-.43.32-.84.56-1.25.73l-1.06.43-.16 1.13-.2 1.35h-1.4l-.19-1.35-.16-1.13-1.06-.43c-.43-.18-.83-.41-1.23-.71l-.91-.7-1.06.43-1.27.51-.7-1.21 1.08-.84.89-.7-.14-1.13c-.03-.31-.05-.54-.05-.74s.02-.43.05-.73l.14-1.13-.89-.7-1.08-.84.7-1.21 1.27.51 1.04.42.9-.68c.43-.32.84-.56 1.25-.73l1.06-.43.16-1.13.2-1.35h1.39l.19 1.35.16 1.13 1.06.43c.43.18.83.41 1.23.71l.91.7 1.06-.43 1.27-.51.7 1.21-1.07.85-.89.7.14 1.13zM12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm0 6c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>
        </svg>''',
        
        'logout': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M5 5h7V3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h7v-2H5V5zm16 7-4-4v3H9v2h8v3l4-4z"/>
        </svg>''',
        
        # --- ICONOS DE DATOS ---
        'attach_money': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
        </svg>''',
        
        'pending_actions': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M17 12c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zm1.65 7.35L16.5 17.2V14h1v2.79l1.85 1.85-.7.71zM18 3h-3.18C14.4 1.84 13.3 1 12 1s-2.4.84-2.82 2H6c-1.1 0-2 .9-2 2v15c0 1.1.9 2 2 2h6.11c-.59-.57-1.07-1.25-1.42-2H6V5h2v3h8V5h2v5.08c.71.1 1.38.31 2 .6V5c0-1.1-.9-2-2-2zm-6-.25c.41 0 .75.34.75.75s-.34.75-.75.75-.75-.34-.75-.75.34-.75.75-.75z"/>
        </svg>''',
        
        'trending_up': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6h-6z"/>
        </svg>''',
        
        'precision_manufacturing': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M19.93 8.21l-3.6 1.68L14 7.7V6.3l2.33-2.19 3.6 1.68c.38.18.82.01 1-.36.18-.38.01-.82-.36-1L16.65 2.6c-.38-.18-.83-.1-1.13.2L13.78 4.9c-.18-.06-.37-.1-.58-.1-.18 0-.36.03-.53.08L10.8 2.4c-.45-.47-1.15-.5-1.64-.07L3.97 6.57c-.61.53-.66 1.47-.09 2.04l.58.58c.15.15.35.24.57.27h.01l1.02.09.62.61c.15.15.35.24.57.26l.01.01 1.02.09.62.61c.15.15.35.24.57.26l.01.01 1.02.09.61.61c.04.04.09.08.14.11.12.08.26.13.41.16h.01l1.03.09.61.61c.25.25.64.39.97.19l.4-.19c.11-.06.22-.13.31-.23l.71-.75.53.54c.49.49 1.28.49 1.77 0l5.66-5.66c.49-.49.49-1.28 0-1.77l-.53-.53 2.12-2.12c.39-.39.39-1.02 0-1.41-.39-.39-1.02-.39-1.41 0l-2.12 2.12zM10.94 20.52c-1.01-.44-1.74-1.43-1.74-2.59 0-1.55 1.26-2.81 2.81-2.81.96 0 1.8.49 2.31 1.23l2.09-2.09-2.28-2.28-6.27 6.27 2.33 2.33.75-.06zm8.26-11.19L17.45 11l1.55 1.55 1.75-1.75-1.55-1.47z"/>
        </svg>''',
        
        # --- ESTADOS ---
        'check_circle': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
        </svg>''',
        
        'schedule': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
        </svg>''',
        
        'warning': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>
        </svg>''',
        
        # --- ACCIONES ---
        'add': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
        </svg>''',
        
        'search': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
        </svg>''',
        
        'person': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
        </svg>''',
        
        'build': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M22.61 18.99l-9.08-9.08c.93-2.34.45-5.1-1.44-7C9.79.61 6.21.4 3.66 2.26L7.5 6.11 6.08 7.52 2.25 3.69C.39 6.23.6 9.82 2.9 12.11c1.86 1.86 4.57 2.35 6.89 1.48l9.11 9.11c.39.39 1.02.39 1.41 0l2.3-2.3c.4-.38.4-1.01 0-1.41zm-3 1.6-9.46-9.46c-.61.45-1.29.72-2 .82-1.36.2-2.79-.21-3.83-1.25C3.37 9.76 2.93 8.5 3 7.26l3.09 3.09 4.24-4.24-3.09-3.09c1.24-.07 2.49.37 3.44 1.31 1.08 1.08 1.49 2.57 1.24 3.96-.12.71-.42 1.37-.88 1.96l9.45 9.45-.88.89z"/>
        </svg>''',
        
        'description': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
        </svg>''',
        
        # --- SIDEBAR NUEVAS VISTAS ---
        'local_gas_station': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M19.77 7.23l.01-.01-3.72-3.72-1.06 1.06 2.11 2.11c-.94.36-1.61 1.26-1.61 2.33 0 1.38 1.12 2.5 2.5 2.5.36 0 .69-.08 1-.21v7.21c0 .55-.45 1-1 1s-1-.45-1-1V14c0-1.1-.9-2-2-2h-1V5c0-1.1-.9-2-2-2H6c-1.1 0-2 .9-2 2v16h10v-7.5h1.5v5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V9c0-.69-.28-1.32-.73-1.77zM18 10c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zM8 18v-4.5H6.5V18H5V5h8v13H8z"/>
        </svg>''',

        'account_balance': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M4 10v7h3v-7H4zm6 0v7h3v-7h-3zM2 22h19v-3H2v3zm14-12v7h3v-7h-3zM11.5 1 2 6v2h19V6l-9.5-5z"/>
        </svg>''',

        'chat': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
        </svg>''',

        # --- EXTRAS ---
        'help_outline': f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">
            <path d="M11 18h2v-2h-2v2zm1-16C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm0-14c-2.21 0-4 1.79-4 4h2c0-1.1.9-2 2-2s2 .9 2 2c0 2-3 1.75-3 5h2c0-2.25 3-2.5 3-5 0-2.21-1.79-4-4-4z"/>
        </svg>''',
    }
    
    return icons.get(name, '')


# Alias para facilidad de uso
def icon(name: str, color: str = "#6B7280", size: int = 24) -> QIcon:
    """Alias corto para get_material_icon()"""
    return get_material_icon(name, color, size)


# Exportar para uso externo
__all__ = ['get_material_icon', 'icon']