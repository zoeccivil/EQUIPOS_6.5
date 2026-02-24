"""
Vista Moderna de Gastos - EQUIPOS 6.0
Tabla con filtros avanzados, búsqueda en tiempo real, adjuntos y exportación
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QComboBox, QMessageBox, QSizePolicy,
    QMenu, QLineEdit, QLabel, QFileDialog, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QPoint, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QBrush
from datetime import datetime
from typing import Dict, List, Any
import logging
import webbrowser
import unicodedata

from app_theme_modern import ModernTheme
from ui_components import ModernButton, ModernDatePicker, ModernCard
from firebase_manager import FirebaseManager
from storage_manager import StorageManager
from dialogos.gasto_dialog import GastoDialog
from reporte_gastos import ReporteGastos
from icon_loader import load_svg_icon
from app_theme_modern import ModernTheme

logger = logging.getLogger(__name__)


class GastosTabModern(QWidget):
    """
    Vista moderna de gastos de equipos.
    
    Características:
    - Filtros avanzados reactivos (fecha, equipo, cuenta, categoría, subcategoría)
    - Búsqueda en tiempo real con debounce
    - Tabla optimizada con acciones inline
    - Ver adjuntos (URLs públicas permanentes)
    - Exportación a PDF y Excel
    - Menú contextual completo
    """
    
    recargar_dashboard = pyqtSignal()
    
    def __init__(self, firebase_manager: FirebaseManager, config=None, 
                 storage_manager: StorageManager = None, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.sm = storage_manager
        self.config = config or {'app': {'moneda': 'RD$'}}
        
        # Mapas de nombres
        self.equipos_mapa = {}
        self.cuentas_mapa = {}
        self.categorias_mapa = {}
        self.subcategorias_mapa = {}
        self.subcategorias_by_cat = {}
        
        # Datos
        self.gastos_base = []
        self.gastos_filtrados = []
        
        # Debounce para búsqueda
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._aplicar_filtros_en_memoria)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz moderna"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)
        
        # ========== FILTROS (2 FILAS) ==========
        filtros_widget = self._crear_filtros()
        main_layout.addWidget(filtros_widget)
        
        # ========== TABLA ==========
        tabla_card = self._crear_tabla()
        main_layout.addWidget(tabla_card, stretch=1)
        
        # ========== TOTALES ==========
        totales_layout = QHBoxLayout()
        self.lbl_total_gastos = QLabel("Total Gastos: 0")
        self.lbl_monto_total_gastos = QLabel("Monto Total: RD$ 0.00")
        
        self.lbl_total_gastos.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_main']};
                font-size: 14px;
                font-weight: 600;
                background-color: transparent;
            }}
        """)
        self.lbl_monto_total_gastos.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['primary']};
                font-size: 16px;
                font-weight: 700;
                background-color: transparent;
            }}
        """)
        
        totales_layout.addStretch()
        totales_layout.addWidget(self.lbl_total_gastos)
        totales_layout.addSpacing(20)
        totales_layout.addWidget(self.lbl_monto_total_gastos)
        
        main_layout.addLayout(totales_layout)
        
        # Conexiones
        self._conectar_senales()
    
    def _crear_filtros(self) -> QWidget:
        """Crea la barra de filtros en 2 filas"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(12)
        
        # Estilo común para combos
        combo_style = f"""
            QComboBox {{
                background-color: transparent;
                color: {ModernTheme.COLORS['text_main']};
                border: 1px solid {ModernTheme.COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                min-width: 150px;
            }}
            QComboBox:hover {{
                border-color: {ModernTheme.COLORS['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {ModernTheme.COLORS['bg_card']};
                border: 1px solid {ModernTheme.COLORS['border']};
                selection-background-color: {ModernTheme.COLORS['primary']};
                selection-color: {ModernTheme.COLORS['primary_text']};
            }}
        """
        
        # ========== FILA 1: Fechas y filtros principales ==========
        fila1 = QHBoxLayout()
        fila1.setSpacing(12)
        
        # Fecha Desde
        self.date_desde_gastos = ModernDatePicker()
        self.date_desde_gastos.setDate(QDate.currentDate().addMonths(-1))
        fila1.addWidget(self.date_desde_gastos)
        
        # Fecha Hasta
        self.date_hasta_gastos = ModernDatePicker()
        self.date_hasta_gastos.setDate(QDate.currentDate())
        fila1.addWidget(self.date_hasta_gastos)
        
        # Equipo
        self.combo_equipo_gastos = QComboBox()
        self.combo_equipo_gastos.setStyleSheet(combo_style)
        self.combo_equipo_gastos.addItem("Todos los Equipos", None)
        fila1.addWidget(self.combo_equipo_gastos)
        
        # Cuenta
        self.combo_cuenta_gastos = QComboBox()
        self.combo_cuenta_gastos.setStyleSheet(combo_style)
        self.combo_cuenta_gastos.addItem("Todas las Cuentas", None)
        fila1.addWidget(self.combo_cuenta_gastos)
        
        # Categoría
        self.combo_categoria_gastos = QComboBox()
        self.combo_categoria_gastos.setStyleSheet(combo_style)
        self.combo_categoria_gastos.addItem("Todas las Categorías", None)
        fila1.addWidget(self.combo_categoria_gastos)
        
        # Subcategoría
        self.combo_subcategoria_gastos = QComboBox()
        self.combo_subcategoria_gastos.setStyleSheet(combo_style)
        self.combo_subcategoria_gastos.addItem("Todas las Subcategorías", None)
        self.combo_subcategoria_gastos.setMinimumWidth(180)
        fila1.addWidget(self.combo_subcategoria_gastos)
        
        fila1.addStretch()
        container_layout.addLayout(fila1)
        
        # ========== FILA 2: Búsqueda y botones (ALINEADOS) ==========
        fila2 = QHBoxLayout()
        fila2.setSpacing(12)
        
        # Búsqueda libre
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar en descripción, comentario...")
        self.txt_buscar.setFixedHeight(40)  # ✅ Altura fija igual a botones
        self.txt_buscar.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                color: {ModernTheme.COLORS['text_main']};
                border: 1px solid {ModernTheme.COLORS['border']};
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 14px;
                min-width: 250px;
            }}
            QLineEdit:focus {{
                border-color: {ModernTheme.COLORS['primary']};
            }}
        """)
        fila2.addWidget(self.txt_buscar)
        
        fila2.addStretch()
        
        # ✅ Botón Recargar (SVG)
        self.btn_recargar = QPushButton()
        self.btn_recargar.setIcon(load_svg_icon("refresh", ModernTheme.COLORS['text_main']))
        self.btn_recargar.setIconSize(QSize(20, 20))
        self.btn_recargar.setFixedSize(40, 40)
        self.btn_recargar.setToolTip("Recargar gastos")
        self.btn_recargar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_recargar.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernTheme.COLORS['bg_input']};
                border: 1px solid {ModernTheme.COLORS['border']};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {ModernTheme.COLORS['hover_bg']};
                border-color: {ModernTheme.COLORS['primary']};
            }}
        """)
        fila2.addWidget(self.btn_recargar)
        
        # ✅ Botón PDF (SVG)
        self.btn_exportar_pdf = QPushButton()
        self.btn_exportar_pdf.setIcon(load_svg_icon("pdf", "#EF4444"))  # Rojo
        self.btn_exportar_pdf.setIconSize(QSize(20, 20))
        self.btn_exportar_pdf.setFixedSize(40, 40)
        self.btn_exportar_pdf.setToolTip("Exportar a PDF")
        self.btn_exportar_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exportar_pdf.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernTheme.COLORS['bg_input']};
                border: 1px solid {ModernTheme.COLORS['border']};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {ModernTheme.COLORS['hover_bg']};
                border-color: #EF4444;
            }}
        """)
        fila2.addWidget(self.btn_exportar_pdf)
        
        # ✅ Botón Excel (SVG)
        self.btn_exportar_excel = QPushButton()
        self.btn_exportar_excel.setIcon(load_svg_icon("excel", "#10B981"))  # Verde
        self.btn_exportar_excel.setIconSize(QSize(20, 20))
        self.btn_exportar_excel.setFixedSize(40, 40)
        self.btn_exportar_excel.setToolTip("Exportar a Excel")
        self.btn_exportar_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exportar_excel.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernTheme.COLORS['bg_input']};
                border: 1px solid {ModernTheme.COLORS['border']};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {ModernTheme.COLORS['hover_bg']};
                border-color: #10B981;
            }}
        """)
        fila2.addWidget(self.btn_exportar_excel)
        
        # ✅ Botón Nuevo Gasto (alineado verticalmente)
        self.btn_nuevo_gasto = ModernButton("+ Nuevo Gasto", "primary")
        self.btn_nuevo_gasto.setFixedHeight(40)  # ✅ Misma altura que los demás
        fila2.addWidget(self.btn_nuevo_gasto)
        
        container_layout.addLayout(fila2)
        
        return container
    
    def _crear_tabla(self):
        """Crea la tabla de gastos"""
        card = ModernCard(padding=0)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tabla con 9 columnas
        self.tabla = QTableWidget(0, 9)
        self.tabla.setHorizontalHeaderLabels([
            "Fecha", "Equipo", "Cuenta", "Categoría", "Subcategoría",
            "Descripción", "Monto", "Comentario", "📎"  # ✅ Icono en header
        ])
        
        # Configuración
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Fecha
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Equipo
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Cuenta
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Categoría
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Subcategoría
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Descripción
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Monto
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Comentario
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)  # Adjunto
        header.resizeSection(8, 80)  # ✅ CAMBIAR: 60 → 80 para más espacio
        header.setStretchLastSection(False)
        
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(False)
        self.tabla.setShowGrid(False)
        self.tabla.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabla.setMinimumHeight(500)
        self.tabla.setSortingEnabled(True)
        self.tabla.verticalHeader().setDefaultSectionSize(50)  # Altura uniforme
        
        # Estilo
        self.tabla.setStyleSheet(f"""
            QTableWidget {{
                background-color: {ModernTheme.COLORS['bg_card']};
                border: none;
                gridline-color: transparent;
                selection-background-color: transparent;
            }}
            QTableWidget::item {{
                padding: 12px 16px;
                border-bottom: 1px solid {ModernTheme.COLORS['border']};
                border-left: none;
                border-right: none;
                border-top: none;
            }}
            QTableWidget::item:selected {{
                background-color: {ModernTheme.COLORS['hover_bg']};
                color: {ModernTheme.COLORS['text_main']};
                border: none;
            }}
            QTableWidget::item:focus {{
                background-color: {ModernTheme.COLORS['hover_bg']};
                outline: none;
                border: none;
            }}
            QHeaderView::section {{
                background-color: {ModernTheme.COLORS['bg_card']};
                color: {ModernTheme.COLORS['text_muted']};
                padding: 12px 16px;
                border: none;
                border-bottom: 2px solid {ModernTheme.COLORS['border']};
                font-weight: 600;
                font-size: 12px;
                text-transform: uppercase;
            }}
        """)
        
        layout.addWidget(self.tabla)
        card.add_layout(layout)
        
        return card
    
    def _conectar_senales(self):
        """Conecta todas las señales"""
        # Botones
        self.btn_recargar.clicked.connect(self._recargar_por_fecha)
        self.btn_nuevo_gasto.clicked.connect(self.abrir_dialogo_nuevo)
        self.btn_exportar_pdf.clicked.connect(self._exportar_pdf)
        self.btn_exportar_excel.clicked.connect(self._exportar_excel)
        
        # Filtros reactivos
        self.date_desde_gastos.dateChanged.connect(self._recargar_por_fecha)
        self.date_hasta_gastos.dateChanged.connect(self._recargar_por_fecha)
        self.combo_equipo_gastos.currentIndexChanged.connect(self._aplicar_filtros_en_memoria)
        self.combo_cuenta_gastos.currentIndexChanged.connect(self._aplicar_filtros_en_memoria)
        self.combo_categoria_gastos.currentIndexChanged.connect(self._on_categoria_changed)
        self.combo_subcategoria_gastos.currentIndexChanged.connect(self._aplicar_filtros_en_memoria)
        self.txt_buscar.textChanged.connect(self._on_search_changed)
        
        # Tabla
        self.tabla.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        self.tabla.cellClicked.connect(self._handle_cell_click)
        self.tabla.itemDoubleClicked.connect(self.editar_gasto_seleccionado)
    
    # =========================================================================================
    # SECCIÓN: Actualización de mapas
    # =========================================================================================
    
    def actualizar_mapas(self, mapas: Dict[str, Dict[str, str]]):
        """Actualiza los mapas de equipos, cuentas, categorías y subcategorías"""
        self.equipos_mapa = mapas.get("equipos", {})
        self.cuentas_mapa = mapas.get("cuentas", {})
        self.categorias_mapa = mapas.get("categorias", {})
        self.subcategorias_mapa = mapas.get("subcategorias", {})
        
        # Armar subcategorias_by_cat
        self.subcategorias_by_cat = mapas.get("subcategorias_by_cat", {})
        if not self.subcategorias_by_cat:
            catalogo = mapas.get("subcategorias_catalogo", [])
            by_cat = {}
            for item in catalogo or []:
                sid = str(item.get("id"))
                cid = str(item.get("categoria_id")) if item.get("categoria_id") is not None else None
                nom = item.get("nombre") or self.subcategorias_mapa.get(sid) or ""
                if cid:
                    by_cat.setdefault(cid, {})[sid] = nom
            self.subcategorias_by_cat = by_cat
        
        try:
            # Poblar Equipos
            self.combo_equipo_gastos.blockSignals(True)
            self.combo_equipo_gastos.clear()
            self.combo_equipo_gastos.addItem("Todos los Equipos", None)
            for eq_id, nombre in sorted(self.equipos_mapa.items(), key=lambda i: i[1]):
                self.combo_equipo_gastos.addItem(nombre, str(eq_id))
            self.combo_equipo_gastos.blockSignals(False)
            
            # Poblar Cuentas
            self.combo_cuenta_gastos.blockSignals(True)
            self.combo_cuenta_gastos.clear()
            self.combo_cuenta_gastos.addItem("Todas las Cuentas", None)
            for ct_id, nombre in sorted(self.cuentas_mapa.items(), key=lambda i: i[1]):
                self.combo_cuenta_gastos.addItem(nombre, str(ct_id))
            self.combo_cuenta_gastos.blockSignals(False)
            
            # Poblar Categorías
            self.combo_categoria_gastos.blockSignals(True)
            self.combo_categoria_gastos.clear()
            self.combo_categoria_gastos.addItem("Todas las Categorías", None)
            for cat_id, nombre in sorted(self.categorias_mapa.items(), key=lambda i: i[1]):
                self.combo_categoria_gastos.addItem(nombre, str(cat_id))
            self.combo_categoria_gastos.blockSignals(False)
            
            # Poblar Subcategorías (inicialmente todas)
            self.combo_subcategoria_gastos.blockSignals(True)
            self.combo_subcategoria_gastos.clear()
            self.combo_subcategoria_gastos.addItem("Todas las Subcategorías", None)
            self.combo_subcategoria_gastos.blockSignals(False)
            
            # Inicializar fechas
            self._inicializar_fechas_filtro()
            
            # Primera carga
            self._recargar_por_fecha()
            
        except Exception as e:
            logger.error(f"Error poblando filtros gastos: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"No se pudieron cargar filtros:\n{e}")
    
    def _inicializar_fechas_filtro(self):
        """Inicializa las fechas de filtro dinámicamente"""
        try:
            primera_fecha_str = self.fm.obtener_fecha_primera_transaccion_gastos()
            if primera_fecha_str:
                qd = QDate.fromString(primera_fecha_str, "yyyy-MM-dd")
                if qd.isValid():
                    self.date_desde_gastos.setDate(qd)
                    logger.info(f"Fecha 'Desde' gastos: {primera_fecha_str}")
                else:
                    self.date_desde_gastos.setDate(QDate.currentDate().addMonths(-1))
            else:
                self.date_desde_gastos.setDate(QDate.currentDate().addMonths(-1))
            self.date_hasta_gastos.setDate(QDate.currentDate())
        except Exception as e:
            logger.error(f"Error inicializando fechas gastos: {e}", exc_info=True)
            self.date_desde_gastos.setDate(QDate.currentDate().addMonths(-1))
            self.date_hasta_gastos.setDate(QDate.currentDate())
    
    def _on_categoria_changed(self):
        """Handler cuando cambia la categoría"""
        self._repopular_subcategorias()
        self._aplicar_filtros_en_memoria()
    
    def _repopular_subcategorias(self):
        """Repobla el combo de Subcategoría según la categoría actual"""
        cat_id = self.combo_categoria_gastos.currentData()
        self.combo_subcategoria_gastos.blockSignals(True)
        self.combo_subcategoria_gastos.clear()
        self.combo_subcategoria_gastos.addItem("Todas las Subcategorías", None)
        
        if cat_id and str(cat_id) in self.subcategorias_by_cat:
            submap = self.subcategorias_by_cat[str(cat_id)]
            for sub_id, nombre in sorted(submap.items(), key=lambda i: i[1]):
                self.combo_subcategoria_gastos.addItem(nombre, str(sub_id))
        else:
            for sid, nombre in sorted(self.subcategorias_mapa.items(), key=lambda i: i[1]):
                self.combo_subcategoria_gastos.addItem(nombre, str(sid))
        
        self.combo_subcategoria_gastos.blockSignals(False)
    
    # =========================================================================================
    # SECCIÓN: Carga de gastos
    # =========================================================================================
    
    def _recargar_por_fecha(self):
        """Carga los gastos desde Firestore por rango de fechas"""
        if not self.equipos_mapa:
            return
        
        filtros = {
            "fecha_inicio": self.date_desde_gastos.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.date_hasta_gastos.date().toString("yyyy-MM-dd"),
        }
        
        try:
            logger.info(f"Cargando gastos: {filtros}")
            self.gastos_base = self.fm.obtener_gastos(filtros) or []
            self._aplicar_filtros_en_memoria()
        except Exception as e:
            logger.error(f"Error cargando gastos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los gastos:\n{e}")
    
    def _on_search_changed(self, _text: str):
        """Debounce para búsqueda de texto"""
        self._search_timer.start()
    
    def _aplicar_filtros_en_memoria(self):
        """Aplica filtros en memoria sobre los gastos cargados"""
        eq_id = self.combo_equipo_gastos.currentData()
        ct_id = self.combo_cuenta_gastos.currentData()
        cat_id = self.combo_categoria_gastos.currentData()
        sub_id = self.combo_subcategoria_gastos.currentData()
        texto = (self.txt_buscar.text() or "").strip()
        
        def norm(s: str) -> str:
            s = s or ""
            s2 = s.lower()
            s2 = "".join(c for c in unicodedata.normalize("NFD", s2) 
                        if unicodedata.category(c) != "Mn")
            return s2
        
        txt = norm(texto)
        
        filtrados = []
        for g in self.gastos_base or []:
            gid_eq = str(g.get("equipo_id")) if g.get("equipo_id") not in (None, "") else None
            gid_ct = str(g.get("cuenta_id")) if g.get("cuenta_id") not in (None, "") else None
            gid_cat = str(g.get("categoria_id")) if g.get("categoria_id") not in (None, "") else None
            gid_sub = str(g.get("subcategoria_id")) if g.get("subcategoria_id") not in (None, "") else None
            
            if eq_id and gid_eq != str(eq_id):
                continue
            if ct_id and gid_ct != str(ct_id):
                continue
            if cat_id and gid_cat != str(cat_id):
                continue
            if sub_id and gid_sub != str(sub_id):
                continue
            
            if txt:
                equipo_nom = self.equipos_mapa.get(gid_eq, "Sin equipo")
                cuenta_nom = self.cuentas_mapa.get(gid_ct, "")
                categoria_nom = self.categorias_mapa.get(gid_cat, "")
                sub_nom = (self.subcategorias_by_cat.get(gid_cat, {}) or {}).get(gid_sub) or \
                          self.subcategorias_mapa.get(gid_sub, "")
                blob = " ".join([
                    str(g.get("descripcion", "")),
                    str(g.get("comentario", "")),
                    equipo_nom, cuenta_nom, categoria_nom, sub_nom
                ])
                if txt not in norm(blob):
                    continue
            
            filtrados.append(g)
        
        self.gastos_filtrados = filtrados
        self._actualizar_tabla()
    
    def _actualizar_tabla(self):
        """Actualiza la tabla con los gastos filtrados"""
        gastos = self.gastos_filtrados or []
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(0)
        
        if not gastos:
            self.lbl_total_gastos.setText("Total Gastos: 0")
            self.lbl_monto_total_gastos.setText("Monto Total: RD$ 0.00")
            self.tabla.setSortingEnabled(True)
            return
        
        moneda = self.config.get('app', {}).get('moneda', 'RD$')
        total_monto = 0.0
        
        self.tabla.setRowCount(len(gastos))
        
        for row, g in enumerate(gastos):
            gid_eq = str(g.get('equipo_id')) if g.get('equipo_id') not in (None, "") else None
            gid_ct = str(g.get('cuenta_id')) if g.get('cuenta_id') not in (None, "") else None
            gid_cat = str(g.get('categoria_id')) if g.get('categoria_id') not in (None, "") else None
            gid_sub = str(g.get('subcategoria_id')) if g.get('subcategoria_id') not in (None, "") else None
            
            equipo_nombre = self.equipos_mapa.get(gid_eq, 'Sin equipo') if gid_eq else 'Sin equipo'
            cuenta_nombre = self.cuentas_mapa.get(gid_ct, "")
            categoria_nombre = self.categorias_mapa.get(gid_cat, "")
            sub_nom = (self.subcategorias_by_cat.get(gid_cat, {}) or {}).get(gid_sub) or \
                     self.subcategorias_mapa.get(gid_sub, "")
            
            # Columna 0: Fecha (con ID en UserRole)
            item_fecha = QTableWidgetItem(g.get('fecha', ''))
            item_fecha.setData(Qt.ItemDataRole.UserRole, g['id'])
            self.tabla.setItem(row, 0, item_fecha)
            
            # Columna 1: Equipo
            self.tabla.setItem(row, 1, QTableWidgetItem(equipo_nombre))
            
            # Columna 2: Cuenta
            self.tabla.setItem(row, 2, QTableWidgetItem(cuenta_nombre))
            
            # Columna 3: Categoría
            self.tabla.setItem(row, 3, QTableWidgetItem(categoria_nombre))
            
            # Columna 4: Subcategoría
            self.tabla.setItem(row, 4, QTableWidgetItem(sub_nom))
            
            # Columna 5: Descripción
            self.tabla.setItem(row, 5, QTableWidgetItem(g.get('descripcion', '')))
            
            # Columna 6: Monto
            monto = g.get('monto', 0) or 0
            try:
                total_monto += float(monto)
                monto_str = f"{moneda} {float(monto):,.2f}"
            except Exception:
                monto_str = f"{moneda} {str(monto)}"
            
            monto_item = QTableWidgetItem(monto_str)
            monto_item.setFont(QFont("monospace", 11))
            monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 6, monto_item)
            
            # Columna 7: Comentario
            self.tabla.setItem(row, 7, QTableWidgetItem(g.get('comentario', '')))
            
            # Columna 8: Adjunto (solo icono 📎)
            storage_path = g.get("archivo_storage_path", "")
            if storage_path:
                cell = QTableWidgetItem("📎")  # ✅ Solo icono
                cell.setData(Qt.ItemDataRole.UserRole, storage_path)
                cell.setForeground(QBrush(QColor(ModernTheme.COLORS['primary'])))
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setFont(QFont("Segoe UI Emoji", 18))  # ✅ Más grande
                cell.setToolTip("Click para ver adjunto")
                self.tabla.setItem(row, 8, cell)
            else:
                self.tabla.setItem(row, 8, QTableWidgetItem(""))
        
        # Actualizar totales
        self.lbl_total_gastos.setText(f"Total Gastos: {len(gastos)}")
        self.lbl_monto_total_gastos.setText(f"Monto Total: {moneda} {total_monto:,.2f}")
        self.tabla.setSortingEnabled(True)
    
    # =========================================================================================
    # SECCIÓN: Acciones CRUD
    # =========================================================================================
    
    def _obtener_id_seleccionado(self) -> str:
        """Obtiene el ID del gasto seleccionado"""
        sel = self.tabla.selectedItems()
        if not sel:
            return None
        row = sel[0].row()
        item = self.tabla.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole)
    
    def abrir_dialogo_nuevo(self):
        """Abre el diálogo para crear un nuevo gasto"""
        self._abrir_dialogo_gasto(None)
    
    def editar_gasto_seleccionado(self):
        """Edita el gasto seleccionado"""
        gid = self._obtener_id_seleccionado()
        if gid:
            self._abrir_dialogo_gasto(gid)
        else:
            QMessageBox.warning(self, "Selección", "Seleccione un gasto primero")
    
    def _abrir_dialogo_gasto(self, gasto_id: str | None):
        """Abre el diálogo de edición/creación de gasto"""
        try:
            moneda = self.config.get('app', {}).get('moneda', 'RD$')
            dialog = GastoDialog(
                firebase_manager=self.fm,
                storage_manager=self.sm,
                equipos_mapa=self.equipos_mapa,
                cuentas_mapa=self.cuentas_mapa,
                categorias_mapa=self.categorias_mapa,
                subcategorias_mapa=self.subcategorias_mapa,
                gasto_id=gasto_id,
                parent=self,
                moneda_symbol=moneda
            )
            if dialog.exec():
                self._recargar_por_fecha()
                self.recargar_dashboard.emit()
        except Exception as e:
            logger.error(f"Error abriendo diálogo gasto: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el diálogo:\n{e}")
    
    def eliminar_gasto_seleccionado(self):
        """Elimina el gasto seleccionado"""
        gid = self._obtener_id_seleccionado()
        if not gid:
            QMessageBox.warning(self, "Selección", "Seleccione un gasto primero")
            return
        
        reply = QMessageBox.question(
            self, "Eliminar", f"¿Eliminar gasto ID: {gid}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ok = self.fm.eliminar_gasto(gid)
                if ok:
                    QMessageBox.information(self, "Éxito", "Gasto eliminado")
                    self._recargar_por_fecha()
                    self.recargar_dashboard.emit()
                else:
                    QMessageBox.warning(self, "Error", "No se pudo eliminar")
            except Exception as e:
                logger.error(f"Error eliminando gasto {gid}: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"No se pudo eliminar:\n{e}")
    
    # =========================================================================================
    # SECCIÓN: Menú contextual y adjuntos
    # =========================================================================================
    
    def _mostrar_menu_contextual(self, pos: QPoint):
        """Muestra menú contextual con opciones CRUD"""
        menu = QMenu(self)
        
        act_editar = menu.addAction("✏️ Editar")
        act_eliminar = menu.addAction("🗑️ Eliminar")
        act_ver = menu.addAction("📎 Ver Adjunto")
        
        index = self.tabla.indexAt(pos)
        fila_valida = index.isValid()
        fila = index.row() if fila_valida else self.tabla.currentRow()
        
        habilitar_ver = False
        if fila is not None and fila >= 0:
            item_adj = self.tabla.item(fila, 8)
            if item_adj:
                sp = item_adj.data(Qt.ItemDataRole.UserRole)
                habilitar_ver = bool(sp and self.sm)
        
        act_ver.setEnabled(bool(habilitar_ver))
        
        action = menu.exec(self.tabla.viewport().mapToGlobal(pos))
        if action == act_editar:
            self.editar_gasto_seleccionado()
        elif action == act_eliminar:
            self.eliminar_gasto_seleccionado()
        elif action == act_ver:
            self._ver_adjunto_seleccionado()
    
    def _handle_cell_click(self, row: int, col: int):
        """Handler para clic en celda 'Adjunto' (columna 8)"""
        if col == 8:
            item_adj = self.tabla.item(row, 8)
            if not item_adj:
                return
            storage_path = item_adj.data(Qt.ItemDataRole.UserRole)
            if storage_path:
                try:
                    self.tabla.selectRow(row)
                    self._ver_adjunto_seleccionado()
                except Exception as e:
                    logger.error(f"Error abriendo adjunto: {e}", exc_info=True)
    
    def _ver_adjunto_seleccionado(self):
        """Abre el adjunto del gasto usando una URL FIRMADA (Igual que conduces)"""
        sel = self.tabla.selectedItems()
        if not sel:
            QMessageBox.warning(self, "Selección", "Seleccione una fila")
            return
        
        row = sel[0].row()
        item_adj = self.tabla.item(row, 8)
        if not item_adj:
            QMessageBox.information(self, "Adjunto", "No hay adjunto en esta fila")
            return
        
        storage_path = item_adj.data(Qt.ItemDataRole.UserRole)
        if not storage_path:
            QMessageBox.information(self, "Adjunto", "No hay adjunto en esta fila")
            return
        
        try:
            # Si ya es una URL firmada de Firebase (contiene token), abrirla
            if storage_path.startswith("http") and "alt=media" in storage_path:
                url = storage_path
            else:
                # ✅ Generar URL firmada fresca (7 días)
                url = self._generar_url_firmada_fresca(storage_path, dias=7)
            
            if url:
                webbrowser.open(url)
            else:
                QMessageBox.warning(self, "Error", "No se pudo generar el acceso seguro al archivo.")
                
        except Exception as e:
            logger.error(f"Error abriendo adjunto de gasto: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el adjunto:\n{e}")
    
    # =========================================================================================
    # SECCIÓN: Exportación PDF y Excel
    # =========================================================================================
    
    def _exportar_pdf(self):
        """Exporta los gastos filtrados a PDF"""
        if not self.gastos_filtrados:
            QMessageBox.warning(self, "Exportar", "No hay gastos para exportar")
            return
        
        archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Reporte PDF",
            f"Gastos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if not archivo:
            return
        
        try:
            filtros = {
                "fecha_inicio": self.date_desde_gastos.date().toString("yyyy-MM-dd"),
                "fecha_fin": self.date_hasta_gastos.date().toString("yyyy-MM-dd"),
                "equipo_nombre": self.combo_equipo_gastos.currentText() \
                    if self.combo_equipo_gastos.currentData() else None,
                "cuenta_nombre": self.combo_cuenta_gastos.currentText() \
                    if self.combo_cuenta_gastos.currentData() else None,
                "categoria_nombre": self.combo_categoria_gastos.currentText() \
                    if self.combo_categoria_gastos.currentData() else None,
                "subcategoria_nombre": self.combo_subcategoria_gastos.currentText() \
                    if self.combo_subcategoria_gastos.currentData() else None,
                "texto_busqueda": self.txt_buscar.text() if self.txt_buscar.text().strip() else None
            }
            
            moneda = self.config.get('app', {}).get('moneda', 'RD$')
            reporte = ReporteGastos(datos_empresa={}, moneda_symbol=moneda)
            
            mapas = {
                "equipos": self.equipos_mapa,
                "cuentas": self.cuentas_mapa,
                "categorias": self.categorias_mapa,
                "subcategorias": self.subcategorias_mapa
            }
            
            exito = reporte.generar_pdf(
                gastos=self.gastos_filtrados,
                filtros_aplicados=filtros,
                mapas=mapas,
                output_path=archivo,
                orientacion="landscape"
            )
            
            if exito:
                QMessageBox.information(self, "Éxito", f"Reporte PDF generado:\n{archivo}")
                webbrowser.open(archivo)
            else:
                QMessageBox.warning(self, "Error", "No se pudo generar el reporte PDF")
        except Exception as e:
            logger.error(f"Error exportando PDF: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al exportar:\n{e}")
    
    def _exportar_excel(self):
        """Exporta los gastos filtrados a Excel"""
        if not self.gastos_filtrados:
            QMessageBox.warning(self, "Exportar", "No hay gastos para exportar")
            return
        
        archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Reporte Excel",
            f"Gastos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not archivo:
            return
        
        try:
            filtros = {
                "fecha_inicio": self.date_desde_gastos.date().toString("yyyy-MM-dd"),
                "fecha_fin": self.date_hasta_gastos.date().toString("yyyy-MM-dd"),
                "equipo_nombre": self.combo_equipo_gastos.currentText() \
                    if self.combo_equipo_gastos.currentData() else None,
                "cuenta_nombre": self.combo_cuenta_gastos.currentText() \
                    if self.combo_cuenta_gastos.currentData() else None,
                "categoria_nombre": self.combo_categoria_gastos.currentText() \
                    if self.combo_categoria_gastos.currentData() else None,
                "subcategoria_nombre": self.combo_subcategoria_gastos.currentText() \
                    if self.combo_subcategoria_gastos.currentData() else None,
                "texto_busqueda": self.txt_buscar.text() if self.txt_buscar.text().strip() else None
            }
            
            moneda = self.config.get('app', {}).get('moneda', 'RD$')
            reporte = ReporteGastos(datos_empresa={}, moneda_symbol=moneda)
            
            mapas = {
                "equipos": self.equipos_mapa,
                "cuentas": self.cuentas_mapa,
                "categorias": self.categorias_mapa,
                "subcategorias": self.subcategorias_mapa
            }
            
            exito = reporte.generar_excel(
                gastos=self.gastos_filtrados,
                filtros_aplicados=filtros,
                mapas=mapas,
                output_path=archivo
            )
            
            if exito:
                QMessageBox.information(self, "Éxito", f"Reporte Excel generado:\n{archivo}")
                webbrowser.open(archivo)
            else:
                QMessageBox.warning(self, "Error", "No se pudo generar el reporte Excel")
        except Exception as e:
            logger.error(f"Error exportando Excel: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al exportar:\n{e}")


    def _generar_url_firmada_fresca(self, storage_path: str, dias: int = 7) -> str:
        """Genera URL firmada fresca para adjuntos de gastos."""
        try:
            if not self.sm:
                return None
            
            # Intentar métodos en inglés/español según tu StorageManager
            gen_en = getattr(self.sm, "generate_signed_url", None)
            gen_es = getattr(self.sm, "generar_url_firmada", None)
            
            if callable(gen_en):
                try:
                    return gen_en(storage_path, expiration_days=dias)
                except TypeError:
                    return gen_en(storage_path, dias)
            
            if callable(gen_es):
                try:
                    return gen_es(storage_path, dias)
                except TypeError:
                    return gen_es(storage_path, expiration_days=dias)
            
            return None
        except Exception as e:
            logger.warning(f"No se pudo generar URL firmada para gasto: {e}")
            return None