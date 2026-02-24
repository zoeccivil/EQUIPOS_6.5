"""
Vista Moderna de Pagos a Operadores - EQUIPOS 6.0
Mismo layout que Gastos y Alquileres con filtros avanzados, búsqueda en tiempo real y adjuntos
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QComboBox, QMessageBox, QSizePolicy,
    QMenu, QLineEdit, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QPoint, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QBrush
from datetime import datetime
from typing import Dict, List
import logging
import webbrowser
import unicodedata

from app_theme_modern import ModernTheme
from ui_components import ModernButton, ModernDatePicker, ModernCard
from firebase_manager import FirebaseManager
from storage_manager import StorageManager
from dialogos.pago_operador_dialog import PagoOperadorDialog, METODOS_DEFECTO
from icon_loader import load_svg_icon

logger = logging.getLogger(__name__)


class TabPagosOperadoresModern(QWidget):
    """
    Vista moderna de pagos a operadores.
    Layout idéntico a Gastos y Alquileres.
    """
    
    recargar_dashboard = pyqtSignal()
    
    def __init__(self, firebase_manager: FirebaseManager, config=None, 
                 storage_manager: StorageManager = None, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.sm = storage_manager
        self.config = config or {'app': {'moneda': 'RD$'}}
        
        # Mapas de nombres
        self.operadores_mapa = {}
        self.cuentas_mapa = {}
        self.equipos_mapa = {}
        
        # Datos
        self.pagos_base = []
        self.pagos_filtrados = []
        
        # Debounce para búsqueda
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._aplicar_filtros_en_memoria)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz moderna (IGUAL QUE GASTOS)"""
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
        self.lbl_total_pagos = QLabel("Total Pagos: 0")
        self.lbl_monto_total_pagos = QLabel("Monto Total: RD$ 0.00")
        
        self.lbl_total_pagos.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_main']};
                font-size: 14px;
                font-weight: 600;
                background-color: transparent;
            }}
        """)
        self.lbl_monto_total_pagos.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['primary']};
                font-size: 16px;
                font-weight: 700;
                background-color: transparent;
            }}
        """)
        
        totales_layout.addStretch()
        totales_layout.addWidget(self.lbl_total_pagos)
        totales_layout.addSpacing(20)
        totales_layout.addWidget(self.lbl_monto_total_pagos)
        
        main_layout.addLayout(totales_layout)
        
        # Conexiones
        self._conectar_senales()
    
    def _crear_filtros(self) -> QWidget:
        """Crea la barra de filtros en 2 filas (IGUAL QUE GASTOS)"""
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
        self.date_desde_pagos = ModernDatePicker()
        self.date_desde_pagos.setDate(QDate.currentDate().addYears(-1))
        fila1.addWidget(self.date_desde_pagos)
        
        # Fecha Hasta
        self.date_hasta_pagos = ModernDatePicker()
        self.date_hasta_pagos.setDate(QDate.currentDate())
        fila1.addWidget(self.date_hasta_pagos)
        
        # Operador
        self.combo_operador = QComboBox()
        self.combo_operador.setStyleSheet(combo_style)
        self.combo_operador.addItem("Todos los Operadores", None)
        fila1.addWidget(self.combo_operador)
        
        # Método
        self.combo_metodo = QComboBox()
        self.combo_metodo.setStyleSheet(combo_style)
        self.combo_metodo.addItem("Todos", None)
        fila1.addWidget(self.combo_metodo)
        
        fila1.addStretch()
        container_layout.addLayout(fila1)
        
        # ========== FILA 2: Búsqueda y botones (ALINEADOS) ==========
        fila2 = QHBoxLayout()
        fila2.setSpacing(12)
        
        # Búsqueda libre
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar en descripción, comentario...")
        self.txt_buscar.setFixedHeight(40)
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
        
        # Botón Recargar
        self.btn_recargar = QPushButton()
        self.btn_recargar.setIcon(load_svg_icon("refresh", ModernTheme.COLORS['text_main']))
        self.btn_recargar.setIconSize(QSize(20, 20))
        self.btn_recargar.setFixedSize(40, 40)
        self.btn_recargar.setToolTip("Recargar pagos")
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
        
        # Botón Nuevo Pago
        self.btn_nuevo_pago = ModernButton("+ Nuevo Pago", "primary")
        self.btn_nuevo_pago.setFixedHeight(40)
        fila2.addWidget(self.btn_nuevo_pago)
        
        container_layout.addLayout(fila2)
        
        return container
    
    def _crear_tabla(self):
        """Crea la tabla de pagos (IGUAL QUE GASTOS)"""
        card = ModernCard(padding=0)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tabla con 7 columnas
        self.tabla = QTableWidget(0, 7)
        self.tabla.setHorizontalHeaderLabels([
            "Fecha", "Operador", "Concepto", "Método", "Monto", "Nota", "📎"
        ])
        
        # Configuración
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Fecha
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Operador
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Concepto
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Método
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Monto
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)          # Nota
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)            # Adjunto
        header.resizeSection(6, 80)
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
        self.tabla.verticalHeader().setDefaultSectionSize(50)
        
        # Estilo (IGUAL QUE GASTOS)
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
        self.btn_nuevo_pago.clicked.connect(self.abrir_dialogo_nuevo)
        
        # Filtros reactivos
        self.date_desde_pagos.dateChanged.connect(self._recargar_por_fecha)
        self.date_hasta_pagos.dateChanged.connect(self._recargar_por_fecha)
        self.combo_operador.currentIndexChanged.connect(self._aplicar_filtros_en_memoria)
        self.combo_metodo.currentIndexChanged.connect(self._aplicar_filtros_en_memoria)
        self.txt_buscar.textChanged.connect(self._on_search_changed)
        
        # Tabla
        self.tabla.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla.customContextMenuRequested.connect(self._mostrar_menu_contextual)
        self.tabla.cellClicked.connect(self._handle_cell_click)
        self.tabla.itemDoubleClicked.connect(self.editar_pago_seleccionado)
    
    # =========================================================================================
    # SECCIÓN: Actualización de mapas
    # =========================================================================================
    
    def actualizar_mapas(self, mapas: Dict[str, Dict[str, str]]):
        """Actualiza los mapas de operadores, cuentas y equipos"""
        self.operadores_mapa = mapas.get("operadores", {})
        self.cuentas_mapa = mapas.get("cuentas", {})
        self.equipos_mapa = mapas.get("equipos", {})
        
        try:
            # Poblar Operadores
            self.combo_operador.blockSignals(True)
            self.combo_operador.clear()
            self.combo_operador.addItem("Todos los Operadores", None)
            for op_id, nombre in sorted(self.operadores_mapa.items(), key=lambda i: i[1]):
                self.combo_operador.addItem(nombre, str(op_id))
            self.combo_operador.blockSignals(False)
            
            # Poblar Métodos
            self.combo_metodo.blockSignals(True)
            self.combo_metodo.clear()
            self.combo_metodo.addItem("Todos", None)
            for m in METODOS_DEFECTO:
                self.combo_metodo.addItem(m, m)
            self.combo_metodo.blockSignals(False)
            
            # Inicializar fechas
            self._inicializar_fechas_filtro()
            
            # Primera carga
            self._recargar_por_fecha()
            
        except Exception as e:
            logger.error(f"Error poblando filtros pagos: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"No se pudieron cargar filtros:\n{e}")
    
    def _inicializar_fechas_filtro(self):
        """Inicializa las fechas de filtro dinámicamente"""
        try:
            if hasattr(self.fm, "obtener_fecha_primera_transaccion_pagos"):
                primera_fecha_str = self.fm.obtener_fecha_primera_transaccion_pagos()
                if primera_fecha_str:
                    qd = QDate.fromString(primera_fecha_str, "yyyy-MM-dd")
                    if qd.isValid():
                        self.date_desde_pagos.setDate(qd)
                    else:
                        self.date_desde_pagos.setDate(QDate.currentDate().addYears(-1))
                else:
                    self.date_desde_pagos.setDate(QDate.currentDate().addYears(-1))
            else:
                self.date_desde_pagos.setDate(QDate.currentDate().addYears(-1))
            
            self.date_hasta_pagos.setDate(QDate.currentDate())
        except Exception as e:
            logger.error(f"Error inicializando fechas pagos: {e}", exc_info=True)
            self.date_desde_pagos.setDate(QDate.currentDate().addYears(-1))
            self.date_hasta_pagos.setDate(QDate.currentDate())
    
    # =========================================================================================
    # SECCIÓN: Carga de pagos
    # =========================================================================================
    
    def _recargar_por_fecha(self):
        """Carga los pagos desde Firestore por rango de fechas"""
        if not self.operadores_mapa:
            return
        
        try:
            logger.info("Cargando pagos a operadores...")
            self.pagos_base = self.fm.obtener_pagos_operadores({}) or []
            
            # Filtrar por rango de fechas
            fi = self.date_desde_pagos.date().toString("yyyy-MM-dd")
            ff = self.date_hasta_pagos.date().toString("yyyy-MM-dd")
            
            self.pagos_base = [
                p for p in self.pagos_base
                if fi <= (p.get("fecha") or "") <= ff
            ]
            
            logger.info(f"Pagos en rango: {len(self.pagos_base)}")
            self._aplicar_filtros_en_memoria()
            
        except Exception as e:
            logger.error(f"Error cargando pagos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los pagos:\n{e}")
    
    def _on_search_changed(self, _text: str):
        """Debounce para búsqueda de texto"""
        self._search_timer.start()
    
    def _aplicar_filtros_en_memoria(self):
        """Aplica filtros en memoria sobre los pagos cargados"""
        op_id = self.combo_operador.currentData()
        metodo = self.combo_metodo.currentData()
        texto = (self.txt_buscar.text() or "").strip()
        
        def norm(s: str) -> str:
            s = s or ""
            s2 = s.lower()
            s2 = "".join(c for c in unicodedata.normalize("NFD", s2) 
                        if unicodedata.category(c) != "Mn")
            return s2
        
        txt = norm(texto)
        
        filtrados = []
        for p in self.pagos_base or []:
            pid_op = str(p.get("operador_id")) if p.get("operador_id") else None
            
            if op_id and pid_op != str(op_id):
                continue
            
            if metodo and (p.get("metodo_pago") or "") != metodo:
                continue
            
            if txt:
                op_nom = self.operadores_mapa.get(pid_op, "")
                blob = " ".join([
                    p.get("descripcion", "") or p.get("concepto", ""),
                    p.get("comentario", "") or p.get("nota", ""),
                    op_nom
                ])
                if txt not in norm(blob):
                    continue
            
            filtrados.append(p)
        
        self.pagos_filtrados = filtrados
        self._actualizar_tabla()
    
    def _actualizar_tabla(self):
        """Actualiza la tabla con los pagos filtrados"""
        pagos = self.pagos_filtrados or []
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(0)
        
        if not pagos:
            self.lbl_total_pagos.setText("Total Pagos: 0")
            self.lbl_monto_total_pagos.setText("Monto Total: RD$ 0.00")
            self.tabla.setSortingEnabled(True)
            return
        
        moneda = self.config.get('app', {}).get('moneda', 'RD$')
        total_monto = 0.0
        
        self.tabla.setRowCount(len(pagos))
        
        for row, p in enumerate(pagos):
            pid_op = str(p.get("operador_id")) if p.get("operador_id") else None
            op_nom = self.operadores_mapa.get(pid_op, "—") if pid_op else "—"
            
            # Columna 0: Fecha (con ID en UserRole)
            item_fecha = QTableWidgetItem(p.get("fecha", ""))
            item_fecha.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.tabla.setItem(row, 0, item_fecha)
            
            # Columna 1: Operador
            self.tabla.setItem(row, 1, QTableWidgetItem(op_nom))
            
            # Columna 2: Concepto
            self.tabla.setItem(row, 2, QTableWidgetItem(p.get("descripcion", "") or p.get("concepto", "")))
            
            # Columna 3: Método
            self.tabla.setItem(row, 3, QTableWidgetItem(p.get("metodo_pago", "")))
            
            # Columna 4: Monto
            monto = p.get("monto", 0) or 0
            try:
                total_monto += float(monto)
                monto_str = f"{moneda} {float(monto):,.2f}"
            except Exception:
                monto_str = f"{moneda} {str(monto)}"
            
            monto_item = QTableWidgetItem(monto_str)
            monto_item.setFont(QFont("monospace", 11))
            monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 4, monto_item)
            
            # Columna 5: Nota
            self.tabla.setItem(row, 5, QTableWidgetItem(p.get("comentario", "") or p.get("nota", "")))
            
            # Columna 6: Adjunto (solo icono 📎)
            storage_path = p.get("archivo_storage_path", "")
            if storage_path:
                cell = QTableWidgetItem("📎")
                cell.setData(Qt.ItemDataRole.UserRole, storage_path)
                cell.setForeground(QBrush(QColor(ModernTheme.COLORS['primary'])))
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setFont(QFont("Segoe UI Emoji", 18))
                cell.setToolTip("Click para ver adjunto")
                self.tabla.setItem(row, 6, cell)
            else:
                self.tabla.setItem(row, 6, QTableWidgetItem(""))
        
        # Actualizar totales
        self.lbl_total_pagos.setText(f"Total Pagos: {len(pagos)}")
        self.lbl_monto_total_pagos.setText(f"Monto Total: {moneda} {total_monto:,.2f}")
        self.tabla.setSortingEnabled(True)
    
    # =========================================================================================
    # SECCIÓN: Acciones CRUD
    # =========================================================================================
    
    def _obtener_id_seleccionado(self) -> str:
        """Obtiene el ID del pago seleccionado"""
        sel = self.tabla.selectedItems()
        if not sel:
            return None
        row = sel[0].row()
        item = self.tabla.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole)
    
    def abrir_dialogo_nuevo(self):
        """Abre el diálogo para crear un nuevo pago"""
        self._abrir_dialogo_pago(None)
    
    def editar_pago_seleccionado(self):
        """Edita el pago seleccionado"""
        pid = self._obtener_id_seleccionado()
        if pid:
            pago = next((p for p in self.pagos_filtrados if p.get("id") == pid), None)
            if pago:
                self._abrir_dialogo_pago(pago)
        else:
            QMessageBox.warning(self, "Selección", "Seleccione un pago primero")
    
    def _abrir_dialogo_pago(self, pago: dict | None):
        """Abre el diálogo de edición/creación de pago"""
        try:
            moneda = self.config.get('app', {}).get('moneda', 'RD$')
            dialog = PagoOperadorDialog(
                firebase_manager=self.fm,
                storage_manager=self.sm,
                operadores_mapa=self.operadores_mapa,
                cuentas_mapa=self.cuentas_mapa,
                equipos_mapa=self.equipos_mapa,
                pago=pago,
                parent=self,
                moneda_symbol=moneda
            )
            if dialog.exec():
                self._recargar_por_fecha()
                self.recargar_dashboard.emit()
        except Exception as e:
            logger.error(f"Error abriendo diálogo pago: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el diálogo:\n{e}")
    
    def eliminar_pago_seleccionado(self):
        """Elimina el pago seleccionado"""
        pid = self._obtener_id_seleccionado()
        if not pid:
            QMessageBox.warning(self, "Selección", "Seleccione un pago primero")
            return
        
        reply = QMessageBox.question(
            self, "Eliminar", f"¿Eliminar pago ID: {pid}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ok = self.fm.eliminar_pago_operador(pid)
                if ok:
                    QMessageBox.information(self, "Éxito", "Pago eliminado")
                    self._recargar_por_fecha()
                    self.recargar_dashboard.emit()
                else:
                    QMessageBox.warning(self, "Error", "No se pudo eliminar")
            except Exception as e:
                logger.error(f"Error eliminando pago {pid}: {e}", exc_info=True)
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
            item_adj = self.tabla.item(fila, 6)
            if item_adj:
                sp = item_adj.data(Qt.ItemDataRole.UserRole)
                habilitar_ver = bool(sp and self.sm)
        
        act_ver.setEnabled(bool(habilitar_ver))
        
        action = menu.exec(self.tabla.viewport().mapToGlobal(pos))
        if action == act_editar:
            self.editar_pago_seleccionado()
        elif action == act_eliminar:
            self.eliminar_pago_seleccionado()
        elif action == act_ver:
            self._ver_adjunto_seleccionado()
    
    def _handle_cell_click(self, row: int, col: int):
        """Handler para clic en celda 'Adjunto' (columna 6)"""
        if col == 6:
            item_adj = self.tabla.item(row, 6)
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
        """Abre el adjunto del pago usando una URL FIRMADA (igual que gastos)"""
        sel = self.tabla.selectedItems()
        if not sel:
            QMessageBox.warning(self, "Selección", "Seleccione una fila")
            return
        
        row = sel[0].row()
        item_adj = self.tabla.item(row, 6)
        if not item_adj:
            QMessageBox.information(self, "Adjunto", "No hay adjunto en esta fila")
            return
        
        storage_path = item_adj.data(Qt.ItemDataRole.UserRole)
        if not storage_path:
            QMessageBox.information(self, "Adjunto", "No hay adjunto en esta fila")
            return
        
        try:
            # Si ya es una URL firmada, abrirla
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
            logger.error(f"Error abriendo adjunto de pago: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el adjunto:\n{e}")
    
    def _generar_url_firmada_fresca(self, storage_path: str, dias: int = 7) -> str:
        """Genera URL firmada fresca para adjuntos de pagos."""
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
            logger.warning(f"No se pudo generar URL firmada para pago: {e}")
            return None


# ============================================================================
# ALIAS PARA COMPATIBILIDAD
# ============================================================================
TabPagosOperadores = TabPagosOperadoresModern