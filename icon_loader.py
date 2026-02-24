"""
Helper para cargar iconos SVG como QIcon
"""
from PyQt6.QtGui import QIcon
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray, Qt
import os

def load_svg_icon(name: str, color: str = "#6B7280") -> QIcon:
    """
    Carga un icono SVG desde la carpeta icons/
    
    Args:
        name: Nombre del archivo sin extensión (ej: 'refresh')
        color: Color hex del icono (ej: '#F59E0B')
    
    Returns:
        QIcon con el SVG cargado
    """
    icon_path = os.path.join("icons", f"{name}.svg")
    
    if not os.path.exists(icon_path):
        # Fallback: devolver icono vacío
        return QIcon()
    
    try:
        with open(icon_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        
        # Reemplazar color si el SVG usa 'currentColor'
        svg_content = svg_content.replace('currentColor', color)
        svg_content = svg_content.replace('fill="black"', f'fill="{color}"')
        svg_content = svg_content.replace('stroke="black"', f'stroke="{color}"')
        
        # Crear QIcon desde el SVG
        svg_bytes = QByteArray(svg_content.encode('utf-8'))
        renderer = QSvgRenderer(svg_bytes)
        
        from PyQt6.QtGui import QPixmap, QPainter
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        return QIcon(pixmap)
    except Exception as e:
        print(f"Error cargando icono {name}: {e}")
        return QIcon()