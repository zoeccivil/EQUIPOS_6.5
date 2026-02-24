"""
Dashboard Moderno - Vista Principal con KPIs y Actividad Reciente
Replica exactamente el diseño del prototipo HTML con todas las correcciones visuales
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QPushButton, QAbstractItemView,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app_theme_modern import ModernTheme
from ui_components import StatCard, StatusBadge, ModernCard, ModernButton


class DashboardTab(QWidget):
    """
    Vista del Dashboard moderno con KPIs y tabla de actividad reciente.
    
    CORRECCIONES APLICADAS:
    - ✅ Filtros sin fondos visibles
    - ✅ Líneas de progreso dentro de cards
    - ✅ Iconos visibles con emojis
    - ✅ Tabla expandida hasta el final
    - ✅ Estilo consistente
    """
    
    recargar_dashboard = pyqtSignal()
    
    def __init__(self, firebase_manager, config=None, storage_manager=None, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.config = config if config else {'app': {'moneda': 'RD$'}}
        self.sm = storage_manager
        
        # Variables de estado
        self.ano_actual = datetime.now().year
        self.mes_actual = datetime.now().month
        self.equipo_filtro = None
        
        # Mapas de nombres (se actualizan desde app_gui)
        self.equipos_mapa = {}
        self.clientes_mapa = {}
        self.operadores_mapa = {}
        
        # Datos calculados
        self.kpi_data = {}
        self.actividad_reciente = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz del dashboard"""
        # Layout principal con padding
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)
        
        # ========== FILTROS ==========
        filtros_card = self._crear_filtros()
        main_layout.addWidget(filtros_card)
        
        # ========== GRID DE KPIs (4 columnas) ==========
        self.kpis_grid = QGridLayout()
        self.kpis_grid.setSpacing(24)
        
        # Crear las 4 tarjetas KPI
        self.kpi_ingresos = StatCard(
            title="Ingresos Totales",
            value="RD$ 0.00",
            icon_name="attach_money",
            accent_color="#3B82F6",
            footer_text="Cargando..."
        )
        
        self.kpi_pendiente = StatCard(
            title="Pendiente Cobro",
            value="RD$ 0.00",
            icon_name="pending_actions",
            accent_color="#F59E0B",
            footer_text="Cargando..."
        )
        
        self.kpi_utilidad = StatCard(
            title="Utilidad Neta",
            value="RD$ 0.00",
            icon_name="trending_up",
            accent_color="#10B981",
            footer_text="Cargando..."
        )
        
        self.kpi_ocupacion = StatCard(
            title="Ocupación",
            value="0%",
            icon_name="precision_manufacturing",
            accent_color="#6366F1",
            footer_text="Cargando..."
        )
        
        # Agregar al grid
        self.kpis_grid.addWidget(self.kpi_ingresos, 0, 0)
        self.kpis_grid.addWidget(self.kpi_pendiente, 0, 1)
        self.kpis_grid.addWidget(self.kpi_utilidad, 0, 2)
        self.kpis_grid.addWidget(self.kpi_ocupacion, 0, 3)
        
        main_layout.addLayout(self.kpis_grid)
        
        # ========== TARJETAS "TOP" (2 columnas) ==========
        top_layout = QHBoxLayout()
        top_layout.setSpacing(24)
        
        self.top_equipo_card = self._crear_top_card(
            "🚜 Equipo Más Rentable",
            "Cargando...",
            "RD$ 0.00"
        )
        top_layout.addWidget(self.top_equipo_card)
        
        self.top_operador_card = self._crear_top_card(
            "👤 Operador con Más Horas",
            "Cargando...",
            "0.0 hrs"
        )
        top_layout.addWidget(self.top_operador_card)
        
        main_layout.addLayout(top_layout)
        
        # ========== TABLA DE ACTIVIDAD RECIENTE ==========
        tabla_card = self._crear_tabla_actividad()
        main_layout.addWidget(tabla_card, stretch=1)  # ✅ stretch=1 para expandir
    
    def _crear_filtros(self) -> ModernCard:
        """Crea la tarjeta de filtros (SIN FONDOS VISIBLES)"""
        card = ModernCard(padding=20)
        
        filtros_layout = QHBoxLayout()
        filtros_layout.setSpacing(16)
        
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
        filtros_layout.addWidget(label)
        
        # ✅ ESTILO CORREGIDO PARA COMBOS (sin fondo visible)
        combo_style = f"""
            QComboBox {{
                background-color: transparent;
                color: {ModernTheme.COLORS['text_main']};
                border: 1px solid {ModernTheme.COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QComboBox:hover {{
                border-color: {ModernTheme.COLORS['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {ModernTheme.COLORS['text_muted']};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {ModernTheme.COLORS['bg_card']};
                border: 1px solid {ModernTheme.COLORS['border']};
                selection-background-color: {ModernTheme.COLORS['primary']};
                selection-color: {ModernTheme.COLORS['primary_text']};
                padding: 4px;
            }}
        """
        
        # Combo Año
        self.combo_ano = QComboBox()
        self.combo_ano.setMinimumWidth(100)
        self.combo_ano.setStyleSheet(combo_style)
        ano_actual = datetime.now().year
        for ano in range(ano_actual - 2, ano_actual + 2):
            self.combo_ano.addItem(str(ano), ano)
        self.combo_ano.setCurrentText(str(self.ano_actual))
        self.combo_ano.currentIndexChanged.connect(self._on_filtro_changed)
        filtros_layout.addWidget(self.combo_ano)
        
        # Combo Mes
        self.combo_mes = QComboBox()
        self.combo_mes.setMinimumWidth(120)
        self.combo_mes.setStyleSheet(combo_style)
        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        for i, mes in enumerate(meses, 1):
            self.combo_mes.addItem(mes, i)
        self.combo_mes.setCurrentIndex(self.mes_actual - 1)
        self.combo_mes.currentIndexChanged.connect(self._on_filtro_changed)
        filtros_layout.addWidget(self.combo_mes)
        
        # Combo Equipo
        self.combo_equipo = QComboBox()
        self.combo_equipo.setMinimumWidth(200)
        self.combo_equipo.setStyleSheet(combo_style)
        self.combo_equipo.addItem("Todos los Equipos", None)
        self.combo_equipo.currentIndexChanged.connect(self._on_filtro_changed)
        filtros_layout.addWidget(self.combo_equipo)
        
        filtros_layout.addStretch()
        
        card.add_layout(filtros_layout)
        return card
    
    def _crear_top_card(self, titulo: str, nombre: str, valor: str) -> ModernCard:
        """Crea una tarjeta 'Top' (Equipo o Operador)"""
        card = ModernCard(padding=24)
        card.setMinimumHeight(120)
        
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # ✅ TÍTULO (sin fondo)
        titulo_label = QLabel(titulo)
        titulo_label.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_muted']};
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                background-color: transparent;  /* ✅ CRÍTICO */
            }}
        """)
        layout.addWidget(titulo_label)
        
        # ✅ NOMBRE (sin fondo)
        nombre_label = QLabel(nombre)
        nombre_label.setObjectName("top_nombre")
        nombre_label.setStyleSheet(f"""
            QLabel#top_nombre {{
                color: {ModernTheme.COLORS['text_main']};
                font-size: 20px;
                font-weight: 700;
                background-color: transparent;  /* ✅ CRÍTICO */
            }}
        """)
        layout.addWidget(nombre_label)
        
        # ✅ VALOR (sin fondo)
        valor_label = QLabel(valor)
        valor_label.setObjectName("top_valor")
        valor_label.setStyleSheet(f"""
            QLabel#top_valor {{
                color: {ModernTheme.COLORS['text_muted']};
                font-size: 14px;
                background-color: transparent;  /* ✅ CRÍTICO */
            }}
        """)
        layout.addWidget(valor_label)
        
        card.add_layout(layout)
        
        # Guardar referencias
        card.nombre_label = nombre_label
        card.valor_label = valor_label
        
        return card
    
    def _crear_tabla_actividad(self) -> ModernCard:
        """Crea la tarjeta con la tabla de actividad reciente (EXPANDIDA)"""
        card = ModernCard(padding=0)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # ✅ Expandir
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border-bottom: 1px solid {ModernTheme.COLORS['border']};
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(24, 20, 24, 20)
        
        titulo = QLabel("Actividad Reciente")
        titulo.setStyleSheet(f"""
            QLabel {{
                color: {ModernTheme.COLORS['text_main']};
                font-size: 16px;
                font-weight: 700;
                background-color: transparent;
            }}
        """)
        toolbar_layout.addWidget(titulo)
        toolbar_layout.addStretch()
        
        btn_ver_todo = ModernButton("Ver Todo", "primary")
        btn_ver_todo.clicked.connect(self._ver_todo_alquileres)
        toolbar_layout.addWidget(btn_ver_todo)
        
        layout.addWidget(toolbar)
        
        # ✅ TABLA EXPANDIDA
        self.tabla_actividad = QTableWidget(0, 5)
        self.tabla_actividad.setHorizontalHeaderLabels([
            "Fecha", "Equipo", "Cliente", "Monto", "Estado"
        ])
        
        # ✅ CONFIGURACIÓN PARA EXPANDIR
        self.tabla_actividad.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_actividad.horizontalHeader().setStretchLastSection(True)
        self.tabla_actividad.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_actividad.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla_actividad.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_actividad.verticalHeader().setVisible(False)
        self.tabla_actividad.setAlternatingRowColors(False)
        self.tabla_actividad.setShowGrid(False)
        self.tabla_actividad.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabla_actividad.setMinimumHeight(400)  # ✅ Altura mínima
        
        # ✅ ESTILO SIN BORDES VERTICALES
        self.tabla_actividad.setStyleSheet(f"""
            QTableWidget {{
                background-color: {ModernTheme.COLORS['bg_card']};
                border: none;
                gridline-color: transparent;
            }}
            QTableWidget::item {{
                padding: 16px 24px;
                border-bottom: 1px solid {ModernTheme.COLORS['border']};
                border-left: none;
                border-right: none;
                border-top: none;
            }}
            QTableWidget::item:selected {{
                background-color: {ModernTheme.COLORS['hover_bg']};
                color: {ModernTheme.COLORS['text_main']};
            }}
            QHeaderView::section {{
                background-color: {ModernTheme.COLORS['bg_card']};
                color: {ModernTheme.COLORS['text_muted']};
                padding: 12px 24px;
                border: none;
                border-bottom: 2px solid {ModernTheme.COLORS['border']};
                font-weight: 600;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """)
        
        layout.addWidget(self.tabla_actividad, stretch=1)  # ✅ stretch=1
        
        card.add_layout(layout)
        return card
    
    def _on_filtro_changed(self):
        """Callback cuando cambian los filtros"""
        self.ano_actual = self.combo_ano.currentData()
        self.mes_actual = self.combo_mes.currentData()
        self.equipo_filtro = self.combo_equipo.currentData()
        self.refrescar_datos()
    
    def refrescar_datos(self):
        """Recarga y actualiza todos los datos del dashboard"""
        # Calcular fechas del período
        fecha_inicio = f"{self.ano_actual}-{self.mes_actual:02d}-01"
        
        if self.mes_actual == 12:
            ultimo_dia = 31
        else:
            ultimo_dia = (datetime(self.ano_actual, self.mes_actual + 1, 1) - timedelta(days=1)).day
        
        fecha_fin = f"{self.ano_actual}-{self.mes_actual:02d}-{ultimo_dia:02d}"
        
        # Obtener alquileres
        filtros = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }
        
        if self.equipo_filtro:
            filtros["equipo_id"] = self.equipo_filtro
        
        alquileres = self.fm.obtener_alquileres(filtros) or []
        
        # Calcular KPIs
        self._calcular_kpis(alquileres)
        
        # Actualizar UI
        self._actualizar_kpis()
        self._actualizar_tops(alquileres)
        self._actualizar_tabla_actividad(alquileres)
        self._actualizar_combo_equipos()
    
    def _calcular_kpis(self, alquileres: List[Dict[str, Any]]):
        """Calcula los KPIs a partir de los alquileres"""
        total_ingresos = 0.0
        total_pendiente = 0.0
        
        for alq in alquileres:
            monto = float(alq.get('monto', 0) or 0)
            total_ingresos += monto
            
            if not alq.get('pagado', False):
                total_pendiente += monto
        
        # Obtener gastos
        filtros_gastos = {
            "fecha_inicio": f"{self.ano_actual}-{self.mes_actual:02d}-01",
            "fecha_fin": f"{self.ano_actual}-{self.mes_actual:02d}-31"
        }
        gastos = self.fm.obtener_gastos(filtros_gastos) or []
        total_gastos = sum(float(g.get('monto', 0) or 0) for g in gastos)
        
        utilidad_neta = total_ingresos - total_gastos
        margen = (utilidad_neta / total_ingresos * 100) if total_ingresos > 0 else 0
        
        # Ocupación
        equipos_activos = len(set(alq.get('equipo_id') for alq in alquileres if alq.get('equipo_id')))
        total_equipos = len(self.fm.obtener_equipos(activo=True) or [])
        ocupacion = (equipos_activos / total_equipos * 100) if total_equipos > 0 else 0
        
        self.kpi_data = {
            'ingresos': total_ingresos,
            'pendiente': total_pendiente,
            'utilidad': utilidad_neta,
            'margen': margen,
            'ocupacion': ocupacion,
            'equipos_activos': equipos_activos,
            'total_equipos': total_equipos
        }
    
    def _actualizar_kpis(self):
        """Actualiza las tarjetas KPI"""
        moneda = self.config.get('app', {}).get('moneda', 'RD$')
        
        # Ingresos
        ingresos = self.kpi_data.get('ingresos', 0)
        self.kpi_ingresos.set_value(f"{moneda} {ingresos:,.2f}")
        self.kpi_ingresos.set_footer("Cargando...")
        
        # Pendiente
        pendiente = self.kpi_data.get('pendiente', 0)
        facturas_pendientes = sum(1 for alq in self.actividad_reciente if not alq.get('pagado', False))
        self.kpi_pendiente.set_value(f"{moneda} {pendiente:,.2f}")
        self.kpi_pendiente.set_footer(f"{facturas_pendientes} facturas abiertas")
        
        # Utilidad
        utilidad = self.kpi_data.get('utilidad', 0)
        margen = self.kpi_data.get('margen', 0)
        self.kpi_utilidad.set_value(f"{moneda} {utilidad:,.2f}")
        self.kpi_utilidad.set_footer(f"Margen global: {margen:.0f}%")
        
        # Ocupación
        ocupacion = self.kpi_data.get('ocupacion', 0)
        equipos_activos = self.kpi_data.get('equipos_activos', 0)
        total_equipos = self.kpi_data.get('total_equipos', 0)
        self.kpi_ocupacion.set_value(f"{ocupacion:.0f}%")
        self.kpi_ocupacion.set_footer(f"{equipos_activos} de {total_equipos} equipos activos")
    
    def _actualizar_tops(self, alquileres: List[Dict[str, Any]]):
        """Actualiza las tarjetas Top"""
        moneda = self.config.get('app', {}).get('moneda', 'RD$')
        
        # Top Equipo
        equipos_ingresos = {}
        for alq in alquileres:
            equipo_id = alq.get('equipo_id')
            if equipo_id:
                monto = float(alq.get('monto', 0) or 0)
                equipos_ingresos[equipo_id] = equipos_ingresos.get(equipo_id, 0) + monto
        
        if equipos_ingresos:
            top_equipo_id = max(equipos_ingresos, key=equipos_ingresos.get)
            top_equipo_nombre = self.equipos_mapa.get(str(top_equipo_id), f"ID:{top_equipo_id}")
            top_equipo_monto = equipos_ingresos[top_equipo_id]
            
            self.top_equipo_card.nombre_label.setText(top_equipo_nombre)
            self.top_equipo_card.valor_label.setText(f"{moneda} {top_equipo_monto:,.2f}")
        else:
            self.top_equipo_card.nombre_label.setText("Sin datos")
            self.top_equipo_card.valor_label.setText(f"{moneda} 0.00")
        
        # Top Operador
        operadores_horas = {}
        for alq in alquileres:
            operador_id = alq.get('operador_id')
            if operador_id:
                horas = float(alq.get('horas', 0) or 0)
                operadores_horas[operador_id] = operadores_horas.get(operador_id, 0) + horas
        
        if operadores_horas:
            top_operador_id = max(operadores_horas, key=operadores_horas.get)
            top_operador_nombre = self.operadores_mapa.get(str(top_operador_id), f"ID:{top_operador_id}")
            top_operador_horas = operadores_horas[top_operador_id]
            
            self.top_operador_card.nombre_label.setText(top_operador_nombre)
            self.top_operador_card.valor_label.setText(f"{top_operador_horas:.1f} Horas")
        else:
            self.top_operador_card.nombre_label.setText("Sin datos")
            self.top_operador_card.valor_label.setText("0.0 Horas")
    
    def _actualizar_tabla_actividad(self, alquileres: List[Dict[str, Any]]):
        """Actualiza la tabla de actividad reciente"""
        self.tabla_actividad.setRowCount(0)
        
        alquileres_recientes = sorted(
            alquileres,
            key=lambda x: x.get('fecha', ''),
            reverse=True
        )[:10]
        
        self.actividad_reciente = alquileres_recientes
        moneda = self.config.get('app', {}).get('moneda', 'RD$')
        
        for alq in alquileres_recientes:
            row = self.tabla_actividad.rowCount()
            self.tabla_actividad.insertRow(row)
            
            # Fecha
            fecha = alq.get('fecha', '')
            self.tabla_actividad.setItem(row, 0, QTableWidgetItem(fecha))
            
            # Equipo
            equipo_nombre = self.equipos_mapa.get(str(alq.get('equipo_id', '')), "Sin equipo")
            self.tabla_actividad.setItem(row, 1, QTableWidgetItem(equipo_nombre))
            
            # Cliente
            cliente_nombre = self.clientes_mapa.get(str(alq.get('cliente_id', '')), "Sin cliente")
            self.tabla_actividad.setItem(row, 2, QTableWidgetItem(cliente_nombre))
            
            # Monto
            monto = float(alq.get('monto', 0) or 0)
            monto_item = QTableWidgetItem(f"{moneda} {monto:,.2f}")
            monto_item.setFont(QFont("monospace", 10))
            self.tabla_actividad.setItem(row, 3, monto_item)
            
            # Estado
            badge = StatusBadge()
            if alq.get('pagado', False):
                badge.setPaid()
            else:
                try:
                    fecha_alq = datetime.strptime(fecha, '%Y-%m-%d')
                    dias_desde = (datetime.now() - fecha_alq).days
                    if dias_desde > 30:
                        badge.setOverdue()
                    else:
                        badge.setPending()
                except:
                    badge.setPending()
            
            self.tabla_actividad.setCellWidget(row, 4, badge)
    
    def _actualizar_combo_equipos(self):
        """Actualiza el combo de equipos"""
        current_equipo = self.combo_equipo.currentData()
        
        self.combo_equipo.blockSignals(True)
        self.combo_equipo.clear()
        self.combo_equipo.addItem("Todos los Equipos", None)
        
        equipos = self.fm.obtener_equipos(activo=True) or []
        for eq in equipos:
            equipo_id = str(eq.get('id'))
            equipo_nombre = eq.get('nombre', f"ID:{equipo_id}")
            self.combo_equipo.addItem(equipo_nombre, equipo_id)
        
        if current_equipo:
            index = self.combo_equipo.findData(current_equipo)
            if index >= 0:
                self.combo_equipo.setCurrentIndex(index)
        
        self.combo_equipo.blockSignals(False)
    
    def actualizar_mapas(self, mapas: Dict[str, Dict[str, str]]):
        """Actualiza los mapas de nombres desde app_gui"""
        self.equipos_mapa = mapas.get('equipos', {})
        self.clientes_mapa = mapas.get('clientes', {})
        self.operadores_mapa = mapas.get('operadores', {})
    
    def _ver_todo_alquileres(self):
        """Callback para el botón 'Ver Todo'"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Ver Alquileres",
            "Esta función cambiará a la vista de Alquileres.\n"
            "Por ahora, usa el menú lateral para navegar."
        )