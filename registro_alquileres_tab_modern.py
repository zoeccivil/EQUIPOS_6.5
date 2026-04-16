"""
Vista Moderna de Alquileres - EQUIPOS 6.0
Integración completa de funcionalidad antigua con diseño moderno
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QComboBox, QMessageBox, QSizePolicy,
    QMenu, QApplication, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QPoint
from PyQt6.QtGui import QFont, QColor, QBrush, QDesktopServices
from PyQt6.QtCore import QUrl
from datetime import datetime
from typing import Dict, List, Any
import logging

from app_theme_modern import ModernTheme
from ui_components import FilterBar, ModernButton, ModernDatePicker, ActionButton, StatusBadge
from firebase_manager import FirebaseManager
from storage_manager import StorageManager
from dialogos.alquiler_dialog import AlquilerDialog
from delegates_inline import DateDelegate, ComboDelegate, TextDelegate, NumericDelegate

logger = logging.getLogger(__name__)


class RegistroAlquileresTabModern(QWidget):
    """
    Vista moderna de registro de alquileres con funcionalidad completa.
    """
    
    recargar_dashboard = pyqtSignal()
    
    def __init__(self, firebase_manager: FirebaseManager, config=None, storage_manager: StorageManager = None, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.config = config if config else {'app': {'moneda': 'RD$'}}
        self.sm = storage_manager
        
        # Mapas de nombres
        self.clientes_mapa = {}
        self.equipos_mapa = {}
        self.operadores_mapa = {}
        
        # Datos
        self.alquileres_cargados = []
        self.alquileres_filtrados = []
        
        # Configuración de modalidad fijo
        self.mostrar_precio_en_modalidad_fijo = True
        
        logger.info(f"RegistroAlquileresTabModern iniciado con storage_manager={self.sm}")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)
        
        # ========== FILTROS ==========
        filtros = self._crear_filtros()
        main_layout.addWidget(filtros)
        
        # ========== TABLA ==========
        tabla_card = self._crear_tabla()
        main_layout.addWidget(tabla_card, stretch=1)
        
        # ========== TOTALES ==========
        totales_layout = QHBoxLayout()
        self.lbl_total_alquileres = QLabel("Total Alquileres: 0")
        self.lbl_total_monto = QLabel("Monto Total: RD$ 0.00")
        
        self.lbl_total_alquileres.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_main']};
                font-size: 14px;
                font-weight: 600;
                background-color: transparent;
            }}
        """)
        self.lbl_total_monto.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['primary']};
                font-size: 16px;
                font-weight: 700;
                background-color: transparent;
            }}
        """)
        
        totales_layout.addStretch()
        totales_layout.addWidget(self.lbl_total_alquileres)
        totales_layout.addSpacing(20)
        totales_layout.addWidget(self.lbl_total_monto)
        
        main_layout.addLayout(totales_layout)
        
        # Conexiones
        self._conectar_senales()
    
    def _conectar_senales(self):
        """Conecta todas las señales de la interfaz"""
        # Filtros reactivos
        self.date_desde.dateChanged.connect(self._aplicar_filtros)
        self.date_hasta.dateChanged.connect(self._aplicar_filtros)
        self.combo_cliente.currentIndexChanged.connect(self._aplicar_filtros)
        self.combo_equipo.currentIndexChanged.connect(self._aplicar_filtros)
        self.combo_operador.currentIndexChanged.connect(self._aplicar_filtros)
        self.combo_estado.currentIndexChanged.connect(self._aplicar_filtros)
        
        # Botones
        self.btn_recargar.clicked.connect(self._cargar_alquileres_desde_firebase)
        self.btn_nuevo.clicked.connect(lambda: self.abrir_dialogo_alquiler(None))
        
        # Tabla
        self.tabla.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        self.tabla.cellClicked.connect(self._handle_cell_click)
        # Doble-click activa el delegate inline; menú contextual ofrece "Editar" (diálogo completo)
    
    def _crear_filtros(self) -> FilterBar:
        """Crea la barra de filtros"""
        filtros = FilterBar()
        
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
        
        # Fecha Desde
        self.date_desde = ModernDatePicker()
        self.date_desde.setDate(QDate.currentDate().addMonths(-1))
        filtros.add_filter(self.date_desde)
        
        # Fecha Hasta
        self.date_hasta = ModernDatePicker()
        self.date_hasta.setDate(QDate.currentDate())
        filtros.add_filter(self.date_hasta)
        
        # Cliente
        self.combo_cliente = QComboBox()
        self.combo_cliente.setStyleSheet(combo_style)
        self.combo_cliente.addItem("Todos los Clientes", None)
        filtros.add_filter(self.combo_cliente)
        
        # Equipo
        self.combo_equipo = QComboBox()
        self.combo_equipo.setStyleSheet(combo_style)
        self.combo_equipo.addItem("Todos los Equipos", None)
        filtros.add_filter(self.combo_equipo)
        
        # Operador
        self.combo_operador = QComboBox()
        self.combo_operador.setStyleSheet(combo_style)
        self.combo_operador.addItem("Todos los Operadores", None)
        filtros.add_filter(self.combo_operador)
        
        # Estado
        self.combo_estado = QComboBox()
        self.combo_estado.setStyleSheet(combo_style)
        self.combo_estado.addItem("Todos los Estados", None)
        self.combo_estado.addItem("✓ Pagado", True)
        self.combo_estado.addItem("⏰ Pendiente", False)
        self.combo_estado.setMinimumWidth(180)
        filtros.add_filter(self.combo_estado)
        
        filtros.add_stretch()
        
        # Botón Recargar
        self.btn_recargar = ModernButton("🔄 Recargar", "secondary")
        filtros.add_button(self.btn_recargar)
        
        # Botón Nuevo
        self.btn_nuevo = ModernButton("+ Nuevo Alquiler", "primary")
        filtros.add_button(self.btn_nuevo)
        
        return filtros
    
    def _crear_tabla(self):
        """Crea la tabla de alquileres"""
        from ui_components import ModernCard
        
        card = ModernCard(padding=0)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # ✅ CAMBIO: Tabla con 10 columnas (igual que antes)
        self.tabla = QTableWidget(0, 10)
        
        # ✅ CAMBIO: Header con "CONDUCE" en lugar de "UBICACIÓN"
        self.tabla.setHorizontalHeaderLabels([
            "Fecha", "Cliente", "Equipo", "Operador", "Conduce",
            "Cantidad", "Precio", "Monto", "Estado", "C 📄"
        ])
        
        # Configuración
        header = self.tabla.horizontalHeader()
        self.tabla.verticalHeader().setDefaultSectionSize(45)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Fecha
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Cliente
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Equipo
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Operador
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # ✅ Conduce
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Cantidad
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, 100)  # Precio
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Monto
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(8, 150)  # Estado
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(9, 70)  # C 📄
        header.setStretchLastSection(False)
                
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(False)
        self.tabla.setShowGrid(False)
        self.tabla.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabla.setMinimumHeight(500)
        self.tabla.setSortingEnabled(True)
        
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
                background-color: transparent;
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
            QTableWidget QWidget {{
                background-color: transparent;
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

        # ── Delegates de edición inline ──────────────────────────────────────
        moneda = (self.config or {}).get('app', {}).get('moneda', 'RD$')
        self._delegate_fecha_alq    = DateDelegate(self._guardar_cambio_inline_alquiler, self)
        self._delegate_cliente      = ComboDelegate({}, self._guardar_cambio_inline_alquiler, self)
        self._delegate_equipo_alq   = ComboDelegate({}, self._guardar_cambio_inline_alquiler, self)
        self._delegate_operador     = ComboDelegate({}, self._guardar_cambio_inline_alquiler, self)
        self._delegate_conduce      = TextDelegate(self._guardar_cambio_inline_alquiler, self)
        self._delegate_cantidad     = NumericDelegate(self._guardar_cambio_inline_alquiler, prefix="", parent=self)
        self._delegate_precio       = NumericDelegate(self._guardar_cambio_inline_alquiler, prefix="", parent=self)
        # col 7 (Monto), 8 (Estado), 9 (C📄): no editables inline

        self.tabla.setItemDelegateForColumn(0, self._delegate_fecha_alq)
        self.tabla.setItemDelegateForColumn(1, self._delegate_cliente)
        self.tabla.setItemDelegateForColumn(2, self._delegate_equipo_alq)
        self.tabla.setItemDelegateForColumn(3, self._delegate_operador)
        self.tabla.setItemDelegateForColumn(4, self._delegate_conduce)
        self.tabla.setItemDelegateForColumn(5, self._delegate_cantidad)
        self.tabla.setItemDelegateForColumn(6, self._delegate_precio)
        # ────────────────────────────────────────────────────────────────────

        return card

    # =========================================================================================
    # SECCIÓN: Población de filtros y actualización de mapas
    # =========================================================================================
    
    def actualizar_mapas(self, mapas: Dict[str, Dict[str, str]]):
        """Recibe los mapas desde la ventana principal y puebla los filtros"""
        self.clientes_mapa = mapas.get('clientes', {})
        self.equipos_mapa = mapas.get('equipos', {})
        self.operadores_mapa = mapas.get('operadores', {})
        
        logger.info("RegistroAlquileres: Mapas recibidos. Poblando filtros...")
        
        try:
            # Poblar Cliente
            self.combo_cliente.blockSignals(True)
            self.combo_cliente.clear()
            self.combo_cliente.addItem("Todos los Clientes", None)
            for cid, nombre in sorted(self.clientes_mapa.items(), key=lambda x: x[1]):
                self.combo_cliente.addItem(nombre, cid)
            self.combo_cliente.blockSignals(False)
            
            # Poblar Equipo
            self.combo_equipo.blockSignals(True)
            self.combo_equipo.clear()
            self.combo_equipo.addItem("Todos los Equipos", None)
            for eid, nombre in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
                self.combo_equipo.addItem(nombre, eid)
            self.combo_equipo.blockSignals(False)
            
            # Poblar Operador
            self.combo_operador.blockSignals(True)
            self.combo_operador.clear()
            self.combo_operador.addItem("Todos los Operadores", None)
            for oid, nombre in sorted(self.operadores_mapa.items(), key=lambda x: x[1]):
                self.combo_operador.addItem(nombre, oid)
            self.combo_operador.blockSignals(False)
            
            # Actualizar mapas de delegates inline
            self._delegate_cliente.update_map({str(k): v for k, v in self.clientes_mapa.items()})
            self._delegate_equipo_alq.update_map({str(k): v for k, v in self.equipos_mapa.items()})
            self._delegate_operador.update_map({str(k): v for k, v in self.operadores_mapa.items()})

            # Inicializar fechas dinámicas
            self._inicializar_fechas_filtro()
            
        except Exception as e:
            logger.error(f"Error poblando filtros: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"No se pudieron cargar los filtros:\n{e}")
    
    def _inicializar_fechas_filtro(self):
        """Inicializa las fechas de filtro dinámicamente"""
        try:
            primera_fecha_str = self.fm.obtener_fecha_primera_transaccion_alquileres()
            
            if primera_fecha_str:
                primera_fecha = QDate.fromString(primera_fecha_str, "yyyy-MM-dd")
                self.date_desde.setDate(primera_fecha)
                logger.info(f"Fecha 'Desde' inicializada: {primera_fecha_str}")
            else:
                self.date_desde.setDate(QDate.currentDate().addMonths(-1))
                logger.warning("No hay transacciones, usando mes anterior")
            
            self.date_hasta.setDate(QDate.currentDate())
            
        except Exception as e:
            logger.error(f"Error inicializando fechas: {e}", exc_info=True)
            self.date_desde.setDate(QDate.currentDate().addMonths(-1))
            self.date_hasta.setDate(QDate.currentDate())
    
    # =========================================================================================
    # SECCIÓN: Helpers de modalidad
    # =========================================================================================
    
    def _formatear_cantidad_y_precio(self, alquiler: Dict[str, Any]) -> tuple:
        """Devuelve (cantidad_texto, precio_texto) según modalidad_facturacion"""
        modalidad = (alquiler.get("modalidad_facturacion") or "horas").strip().lower()
        
        if modalidad == "volumen":
            vol = float(alquiler.get("volumen_generado", 0) or 0)
            unidad = (alquiler.get("unidad_volumen") or "").strip()
            cantidad_txt = f"{vol:,.2f}" + (f" {unidad}" if unidad else "")
            precio_txt = f"{float(alquiler.get('precio_por_unidad', 0) or 0):,.2f}"
        elif modalidad == "fijo":
            cantidad_txt = "-"
            if self.mostrar_precio_en_modalidad_fijo:
                precio_base = float(alquiler.get("monto_fijo", alquiler.get("monto", 0) or 0) or 0)
                precio_txt = f"{precio_base:,.2f}"
            else:
                precio_txt = "-"
        else:
            horas = float(alquiler.get("horas", 0) or 0)
            pph = float(alquiler.get("precio_por_hora", 0) or 0)
            cantidad_txt = f"{horas:,.2f} h"
            precio_txt = f"{pph:,.2f}"
        
        return cantidad_txt, precio_txt
    
    # =========================================================================================
    # SECCIÓN: Carga de alquileres
    # =========================================================================================
    
    def _cargar_alquileres_desde_firebase(self):
        """Carga alquileres desde Firebase"""
        if not self.equipos_mapa:
            logger.warning("Mapas no listos, saltando carga")
            return
        
        try:
            fecha_desde = self.date_desde.date().toString("yyyy-MM-dd")
            fecha_hasta = self.date_hasta.date().toString("yyyy-MM-dd")
            
            filtros = {
                "fecha_inicio": fecha_desde,
                "fecha_fin": fecha_hasta
            }
            
            logger.info(f"Cargando alquileres con filtros: {filtros}")
            self.alquileres_cargados = self.fm.obtener_alquileres(filtros) or []
            
            self._aplicar_filtros()
            
        except Exception as e:
            logger.error(f"Error cargando alquileres: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los alquileres:\n{e}")
    
    def _aplicar_filtros(self):
        """Aplica los filtros de UI"""
        cliente_id = self.combo_cliente.currentData()
        equipo_id = self.combo_equipo.currentData()
        operador_id = self.combo_operador.currentData()
        estado = self.combo_estado.currentData()
        
        self.alquileres_filtrados = []
        
        for alq in self.alquileres_cargados:
            if cliente_id and str(alq.get('cliente_id')) != str(cliente_id):
                continue
            if equipo_id and str(alq.get('equipo_id')) != str(equipo_id):
                continue
            if operador_id and str(alq.get('operador_id')) != str(operador_id):
                continue
            if estado is not None:
                pagado = alq.get('pagado', False)
                if estado != pagado:
                    continue
            
            self.alquileres_filtrados.append(alq)
        
        self._actualizar_tabla()
    
    def _actualizar_tabla(self):
        """Actualiza la tabla con los alquileres filtrados"""
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(0)
        
        if not self.alquileres_filtrados:
            self.lbl_total_alquileres.setText("Total Alquileres: 0")
            self.lbl_total_monto.setText("Monto Total: RD$ 0.00")
            self.tabla.setSortingEnabled(True)
            return
        
        moneda = self.config.get('app', {}).get('moneda', 'RD$')
        total_monto = 0.0
        
        self.tabla.setRowCount(len(self.alquileres_filtrados))
        
        for row, alq in enumerate(self.alquileres_filtrados):
            cliente_id = str(alq.get('cliente_id', '') or '')
            equipo_id = str(alq.get('equipo_id', '') or '')
            operador_id = str(alq.get('operador_id', '') or '')
            
            cliente_nombre = self.clientes_mapa.get(cliente_id, f"ID:{cliente_id}")
            equipo_nombre = self.equipos_mapa.get(equipo_id, f"ID:{equipo_id}")
            operador_nombre = self.operadores_mapa.get(operador_id, f"ID:{operador_id}")
            
            # Columna 0: Fecha (con ID en UserRole)
            item_fecha = QTableWidgetItem(alq.get('fecha', ''))
            item_fecha.setData(Qt.ItemDataRole.UserRole, alq.get('id'))
            self.tabla.setItem(row, 0, item_fecha)
            
            # Columna 1: Cliente
            self.tabla.setItem(row, 1, QTableWidgetItem(cliente_nombre))
            
            # Columna 2: Equipo
            self.tabla.setItem(row, 2, QTableWidgetItem(equipo_nombre))
            
            # Columna 3: Operador
            self.tabla.setItem(row, 3, QTableWidgetItem(operador_nombre))
            
            # ✅ Columna 4: CONDUCE (antes era Ubicación)
            conduce_num = (alq.get('conduce') or '').strip()
            self.tabla.setItem(row, 4, QTableWidgetItem(conduce_num))
            
            # Columna 5 y 6: Cantidad y Precio
            cantidad_txt, precio_txt = self._formatear_cantidad_y_precio(alq)
            modalidad = (alq.get("modalidad_facturacion") or "horas").strip().lower()
            
            item_cantidad = QTableWidgetItem(cantidad_txt)
            item_precio = QTableWidgetItem(precio_txt)
            item_cantidad.setToolTip(f"Modalidad: {modalidad.upper()}")
            item_precio.setToolTip(f"Modalidad: {modalidad.upper()}")
            
            self.tabla.setItem(row, 5, item_cantidad)
            self.tabla.setItem(row, 6, item_precio)
            
            # Columna 7: Monto
            monto = float(alq.get('monto', 0) or 0)
            total_monto += monto
            monto_item = QTableWidgetItem(f"{moneda} {monto:,.2f}")
            monto_item.setFont(QFont("monospace", 11))
            monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 7, monto_item)
            
            # Columna 8: Estado (Badge)
            badge_container = QWidget()
            badge_container.setStyleSheet("QWidget { background-color: transparent; }")
            badge_layout = QHBoxLayout(badge_container)
            badge_layout.setContentsMargins(4, 0, 4, 0)
            badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            badge = StatusBadge()
            if alq.get('pagado', False):
                badge.setPaid()
            else:
                badge.setPending()
            
            badge_layout.addWidget(badge)
            self.tabla.setCellWidget(row, 8, badge_container)
            
            # Columna 9: Conduce 📄
            conduce_url = (alq.get('conduce_url') or alq.get('conduceUrl') or '').strip()
            storage_path = (
                alq.get('conduce_storage_path') or 
                alq.get('conducePath') or 
                alq.get('CondStorage') or ''
            ).strip()
            
            tiene_conduce = bool(conduce_num or conduce_url or storage_path)
            
            item_conduce = QTableWidgetItem("📄")
            item_conduce.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_conduce.setFont(QFont("Segoe UI Emoji", 16))
            
            if tiene_conduce:
                item_conduce.setForeground(QColor(ModernTheme.COLORS['primary']))
                item_conduce.setToolTip("Click para ver conduce")
            else:
                item_conduce.setForeground(QColor("#D1D5DB"))
                item_conduce.setToolTip("Sin conduce adjunto")
            
            self.tabla.setItem(row, 9, item_conduce)
        
        # Actualizar totales
        self.lbl_total_alquileres.setText(f"Total Alquileres: {len(self.alquileres_filtrados)}")
        self.lbl_total_monto.setText(f"Monto Total: {moneda} {total_monto:,.2f}")
        self.tabla.setSortingEnabled(True)
    
    # =========================================================================================
    # RESTO DEL CÓDIGO (Acciones CRUD, menú contextual, etc.) SIN CAMBIOS
    # =========================================================================================
    
    def _obtener_id_seleccionado(self) -> str:
        """Obtiene el ID del alquiler seleccionado"""
        selected_items = self.tabla.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Sin Selección", "Seleccione un alquiler de la tabla")
            return None
        
        selected_row = selected_items[0].row()
        item_fecha = self.tabla.item(selected_row, 0)
        return item_fecha.data(Qt.ItemDataRole.UserRole) if item_fecha else None
    
    def abrir_dialogo_alquiler(self, alquiler_id: str = None):
        """Abre el diálogo para crear o editar un alquiler"""
        alquiler_data = None
        
        if alquiler_id:
            try:
                alquiler_data = self.fm.obtener_alquiler_por_id(alquiler_id)
                if not alquiler_data:
                    QMessageBox.critical(self, "Error", f"No se encontró el alquiler ID: {alquiler_id}")
                    return
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al cargar alquiler:\n{e}")
                return
        
        logger.info(f"Abrir AlquilerDialog con storage_manager={self.sm}")
        
        dialog = AlquilerDialog(
            firebase_manager=self.fm,
            storage_manager=self.sm,
            equipos_mapa=self.equipos_mapa,
            clientes_mapa=self.clientes_mapa,
            operadores_mapa=self.operadores_mapa,
            alquiler_data=alquiler_data,
            parent=self,
        )
        
        if dialog.exec():
            self._cargar_alquileres_desde_firebase()
            self.recargar_dashboard.emit()
    
    def _editar_alquiler_seleccionado(self):
        """Edita el alquiler seleccionado"""
        alquiler_id = self._obtener_id_seleccionado()
        if alquiler_id:
            self.abrir_dialogo_alquiler(alquiler_id)
    
    # =========================================================================================
    # SECCIÓN: Guardado inline (callback de delegates)
    # =========================================================================================

    def _guardar_cambio_inline_alquiler(self, row: int, col: int, value):
        """
        Callback llamado por los delegates después de que el usuario confirma un cambio.
        Mapea (row, col) → (alquiler_id, campo_firebase) y persiste en Firestore.
        Para columnas de Cantidad y Precio también recalcula el monto.
        """
        item_fecha = self.tabla.item(row, 0)
        if not item_fecha:
            return
        alquiler_id = item_fecha.data(Qt.ItemDataRole.UserRole)
        if not alquiler_id:
            logger.warning("inline_alquiler: no hay alquiler_id en la fila")
            return

        # Obtener alquiler en memoria para saber la modalidad
        alq = next((a for a in self.alquileres_filtrados if a.get("id") == alquiler_id), None)
        modalidad = (alq.get("modalidad_facturacion") or "horas").strip().lower() if alq else "horas"

        # Mapa directo para columnas no dependientes de modalidad
        col_to_field = {
            0: "fecha",
            1: "cliente_id",
            2: "equipo_id",
            3: "operador_id",
            4: "conduce",
        }

        if col in col_to_field:
            campo = col_to_field[col]
            updates = {campo: value}
        elif col == 5:
            # Cantidad: horas o volumen según modalidad
            if modalidad == "volumen":
                campo = "volumen_generado"
            elif modalidad == "fijo":
                return  # Cantidad no aplica para fijo
            else:
                campo = "horas"
            updates = {campo: value}
            # Recalcular monto
            precio_actual = float((alq or {}).get(
                "precio_por_unidad" if modalidad == "volumen" else "precio_por_hora", 0) or 0)
            updates["monto"] = value * precio_actual
        elif col == 6:
            # Precio: precio_por_hora, precio_por_unidad o monto_fijo según modalidad
            if modalidad == "volumen":
                campo = "precio_por_unidad"
            elif modalidad == "fijo":
                campo = "monto_fijo"
                updates = {campo: value, "monto": value}
            else:
                campo = "precio_por_hora"
            if modalidad != "fijo":
                cantidad_actual = float((alq or {}).get(
                    "volumen_generado" if modalidad == "volumen" else "horas", 0) or 0)
                updates = {campo: value, "monto": cantidad_actual * value}
        else:
            return

        try:
            self.fm.editar_alquiler(alquiler_id, updates)
            # Actualizar en memoria
            if alq:
                alq.update(updates)
            for a in self.alquileres_cargados:
                if a.get("id") == alquiler_id:
                    a.update(updates)
                    break
            # Si hay monto nuevo, refrescar la celda visualmente
            if "monto" in updates:
                moneda = self.config.get('app', {}).get('moneda', 'RD$')
                from PyQt6.QtWidgets import QTableWidgetItem
                from PyQt6.QtGui import QFont
                monto_item = QTableWidgetItem(f"{moneda} {updates['monto']:,.2f}")
                monto_item.setFont(QFont("monospace", 11))
                from PyQt6.QtCore import Qt
                monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tabla.setItem(row, 7, monto_item)
                # Refrescar totales
                total = sum(float(a.get("monto", 0) or 0) for a in self.alquileres_filtrados)
                self.lbl_total_monto.setText(f"Monto Total: {moneda} {total:,.2f}")
            self.recargar_dashboard.emit()
            logger.info(f"inline_alquiler: {alquiler_id} → {updates}")
        except Exception as e:
            logger.error(f"Error guardando inline alquiler {alquiler_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo guardar el cambio:\n{e}")

    def _eliminar_alquiler(self, alquiler: Dict[str, Any]):
        """Elimina un alquiler tras confirmación"""
        alquiler_id = alquiler.get('id')
        
        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar este alquiler?\n\nID: {alquiler_id}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.fm.eliminar_alquiler(alquiler_id):
                    QMessageBox.information(self, "Éxito", "Alquiler eliminado correctamente")
                    self._cargar_alquileres_desde_firebase()
                    self.recargar_dashboard.emit()
                else:
                    QMessageBox.warning(self, "Error", "No se pudo eliminar el alquiler")
            except Exception as e:
                logger.error(f"Error eliminando alquiler {alquiler_id}: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al eliminar:\n{e}")
    
    def _marcar_pagado(self, alquiler: Dict[str, Any]):
        """Marca un alquiler como pagado con validación de pagos"""
        alquiler_id = alquiler.get('id')
        
        try:
            pagos_docs = (
                self.fm.db.collection("alquileres")
                .document(alquiler_id)
                .collection("pagos")
                .stream()
            )
            
            total_pagado = 0.0
            for pdoc in pagos_docs:
                pdata = pdoc.to_dict() or {}
                total_pagado += float(pdata.get("monto", 0) or 0)
            
            monto_total = float(alquiler.get("monto", 0) or 0)
            
            if monto_total > 0 and total_pagado < monto_total:
                respuesta = QMessageBox.question(
                    self,
                    "Advertencia",
                    (
                        f"Los pagos acumulados ({total_pagado:,.2f}) son menores "
                        f"que el monto del alquiler ({monto_total:,.2f}).\n\n"
                        "Marcar manualmente como Pagado puede ser sobrescrito luego "
                        "por un recalculo automático al registrar abonos.\n\n"
                        "¿Desea marcarlo como Pagado igualmente?"
                    ),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if respuesta == QMessageBox.StandardButton.No:
                    return
            
            ok = self.fm.editar_alquiler(alquiler_id, {"pagado": True})
            if ok:
                self._cargar_alquileres_desde_firebase()
                self.recargar_dashboard.emit()
                QMessageBox.information(self, "Éxito", "Alquiler marcado como pagado")
            else:
                QMessageBox.warning(self, "Error", "No se pudo actualizar el estado")
                
        except Exception as e:
            logger.error(f"Error al marcar pagado {alquiler_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo actualizar:\n{e}")
    
    def _mostrar_menu_contextual(self, pos: QPoint):
        """Muestra el menú contextual en la tabla"""
        index = self.tabla.indexAt(pos)
        hay_fila = index.isValid()
        fila = index.row() if hay_fila else self.tabla.currentRow()
        
        menu = QMenu(self)
        
        act_nuevo = menu.addAction("➕ Registrar Nuevo Alquiler")
        act_nuevo.triggered.connect(lambda: self.abrir_dialogo_alquiler(None))
        
        menu.addSeparator()
        
        act_editar = menu.addAction("✏️ Editar Seleccionado")
        act_editar.triggered.connect(self._editar_alquiler_seleccionado)
        act_editar.setEnabled(hay_fila or fila >= 0)
        
        act_eliminar = menu.addAction("🗑️ Eliminar Seleccionado")
        act_eliminar.triggered.connect(lambda: self._eliminar_alquiler_desde_menu())
        act_eliminar.setEnabled(hay_fila or fila >= 0)
        
        act_ver_conduce = menu.addAction("📄 Ver Conduce")
        act_ver_conduce.triggered.connect(self._accion_ver_conduce)
        
        habilitar_ver = False
        if fila is not None and fila >= 0:
            try:
                item_fecha = self.tabla.item(fila, 0)
                alquiler_id = item_fecha.data(Qt.ItemDataRole.UserRole) if item_fecha else None
                if alquiler_id:
                    alq = next((a for a in self.alquileres_filtrados if a.get('id') == alquiler_id), None)
                    if alq:
                        conduce_txt = (alq.get('conduce') or '').strip()
                        storage_path = (alq.get('conduce_storage_path') or '').strip()
                        habilitar_ver = bool(conduce_txt or storage_path)
            except Exception as e:
                logger.warning(f"Error verificando conduce: {e}", exc_info=True)
        
        act_ver_conduce.setEnabled(bool(fila is not None and habilitar_ver))
        
        act_toggle = menu.addAction("💳 Marcar como Pagado/No pagado")
        act_toggle.triggered.connect(self._accion_toggle_pagado)
        act_toggle.setEnabled(hay_fila or fila >= 0)
        
        menu.addSeparator()
        
        act_copiar_celda = menu.addAction("📋 Copiar celda")
        act_copiar_celda.triggered.connect(self._accion_copiar_celda)
        act_copiar_celda.setEnabled(len(self.tabla.selectedItems()) > 0)
        
        act_copiar_fila = menu.addAction("📋 Copiar fila")
        act_copiar_fila.triggered.connect(self._accion_copiar_fila)
        act_copiar_fila.setEnabled(hay_fila or fila >= 0)
        
        menu.exec(self.tabla.viewport().mapToGlobal(pos))
    
    def _eliminar_alquiler_desde_menu(self):
        """Elimina el alquiler seleccionado desde el menú contextual"""
        alquiler_id = self._obtener_id_seleccionado()
        if alquiler_id:
            alq = next((a for a in self.alquileres_filtrados if a.get('id') == alquiler_id), None)
            if alq:
                self._eliminar_alquiler(alq)
    
    def _accion_ver_conduce(self):
        """Ver conduce con URL firmada fresca"""
        alquiler_id = self._obtener_id_seleccionado()
        if not alquiler_id:
            return
        
        try:
            alq = next((a for a in self.alquileres_filtrados if a.get('id') == alquiler_id), None)
            if not alq:
                QMessageBox.warning(self, "Error", "No se encontró el alquiler")
                return
            
            storage_path = (alq.get("conduce_storage_path") or "").strip()
            
            if not storage_path:
                QMessageBox.information(self, "Conduce", "Este alquiler no tiene conduce adjunto")
                return
            
            if not self.sm:
                QMessageBox.warning(self, "Storage", "Storage no está configurado")
                return
            
            url_fresca = self._generar_url_firmada_fresca(storage_path, dias=7)
            
            if url_fresca:
                import webbrowser
                webbrowser.open(url_fresca)
            else:
                QMessageBox.warning(self, "Conduce", "No se pudo generar la URL del conduce")
                
        except Exception as e:
            logger.error(f"Error abriendo conduce {alquiler_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el conduce:\n{e}")
    
    def _accion_toggle_pagado(self):
        """Alterna el estado pagado/pendiente"""
        alquiler_id = self._obtener_id_seleccionado()
        if not alquiler_id:
            return
        
        try:
            alq = next((a for a in self.alquileres_filtrados if a.get('id') == alquiler_id), None)
            if not alq:
                return
            
            actual_pagado = bool(alq.get("pagado", False))
            nuevo_estado = not actual_pagado
            
            if nuevo_estado:
                pagos_docs = (
                    self.fm.db.collection("alquileres")
                    .document(alquiler_id)
                    .collection("pagos")
                    .stream()
                )
                
                total_pagado = 0.0
                for pdoc in pagos_docs:
                    pdata = pdoc.to_dict() or {}
                    total_pagado += float(pdata.get("monto", 0) or 0)
                
                monto_total = float(alq.get("monto", 0) or 0)
                
                if monto_total > 0 and total_pagado < monto_total:
                    respuesta = QMessageBox.question(
                        self,
                        "Advertencia",
                        (
                            f"Los pagos acumulados ({total_pagado:,.2f}) son menores "
                            f"que el monto del alquiler ({monto_total:,.2f}).\n\n"
                            "¿Desea marcarlo como Pagado igualmente?"
                        ),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if respuesta == QMessageBox.StandardButton.No:
                        return
            
            ok = self.fm.editar_alquiler(alquiler_id, {"pagado": nuevo_estado})
            if ok:
                self._cargar_alquileres_desde_firebase()
                self.recargar_dashboard.emit()
            else:
                QMessageBox.warning(self, "Error", "No se pudo actualizar el estado")
                
        except Exception as e:
            logger.error(f"Error toggle pagado: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo actualizar:\n{e}")
    
    def _accion_copiar_celda(self):
        """Copia el texto de la celda seleccionada"""
        sel = self.tabla.selectedItems()
        if sel:
            QApplication.clipboard().setText(sel[0].text())
    
    def _accion_copiar_fila(self):
        """Copia toda la fila como texto tabulado"""
        sel = self.tabla.selectedItems()
        if not sel:
            return
        
        row = sel[0].row()
        valores = []
        for c in range(self.tabla.columnCount()):
            item = self.tabla.item(row, c)
            valores.append(item.text() if item else "")
        
        QApplication.clipboard().setText("\t".join(valores))
    
    def _generar_url_firmada_fresca(self, storage_path: str, dias: int = 7) -> str:
        """Genera URL firmada fresca (igual que gastos)"""
        try:
            if not self.sm:
                return None
            
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
            logger.warning(f"No se pudo generar URL firmada: {e}")
            return None
    
    def _handle_cell_click(self, row: int, col: int):
        """Maneja el click en celda 'Conduce' (columna 9)"""
        try:
            if col != 9:
                return
            
            item = self.tabla.item(row, col)
            if not item or not item.text().strip():
                return
            
            self.tabla.selectRow(row)
            self._accion_ver_conduce()
            
        except Exception as e:
            logger.error(f"Error en click de celda: {e}", exc_info=True)