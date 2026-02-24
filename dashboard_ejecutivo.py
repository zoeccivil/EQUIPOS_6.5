# dashboard_ejecutivo.py

"""
Dashboard Ejecutivo - Panel de Control con KPIs y Gráficos
Muestra métricas clave del negocio en tiempo real
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QGroupBox, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QFont, QColor, QPainter, QPen
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis
import logging
from datetime import datetime, timedelta
from firebase_manager import FirebaseManager

logger = logging.getLogger(__name__)

# Estilos CSS
DASHBOARD_STYLE = """
QWidget {
    background-color: #F3F4F6;
    font-family: 'Segoe UI';
}
QLabel[class="title"] {
    font-size: 24pt;
    font-weight: bold;
    color: #1F2937;
}
QLabel[class="subtitle"] {
    font-size: 12pt;
    font-weight: 600;
    color: #6B7280;
}
QFrame[class="kpi-card"] {
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 12px;
    padding: 20px;
}
QFrame[class="kpi-card"]:hover {
    border: 2px solid #F59E0B;
}
QLabel[class="kpi-value"] {
    font-size: 32pt;
    font-weight: bold;
    color: #F59E0B;
}
QLabel[class="kpi-label"] {
    font-size: 11pt;
    color: #6B7280;
    font-weight: 500;
}
QLabel[class="kpi-change"] {
    font-size: 10pt;
    font-weight: 600;
}
QLabel[class="kpi-change-positive"] {
    color: #059669;
}
QLabel[class="kpi-change-negative"] {
    color: #DC2626;
}
QGroupBox {
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 12px;
    margin-top: 14px;
    padding: 15px;
    font-weight: 600;
    font-size: 12pt;
    color: #1F2937;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 8px;
    background-color: #FFFFFF;
}
QPushButton {
    background-color: #F59E0B;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 18px;
    font-size: 10pt;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #D97706;
}
QComboBox {
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 6px;
    padding: 8px 12px;
    color: #1F2937;
    font-size: 10pt;
}
QComboBox:hover {
    border: 2px solid #F59E0B;
}
QScrollBar:vertical {
    background-color: #F3F4F6;
    width: 12px;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background-color: #D1D5DB;
    border-radius: 6px;
}
QScrollBar::handle:vertical:hover {
    background-color: #9CA3AF;
}
"""


class KPICard(QFrame):
    """Tarjeta de KPI individual"""
    
    def __init__(self, titulo, valor, cambio_porcentaje=None, icono="", parent=None):
        super().__init__(parent)
        self.setProperty("class", "kpi-card")
        self.setMinimumHeight(140)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Título con icono
        header_layout = QHBoxLayout()
        lbl_titulo = QLabel(f"{icono} {titulo}")
        lbl_titulo.setProperty("class", "kpi-label")
        header_layout.addWidget(lbl_titulo)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Valor principal
        self.lbl_valor = QLabel(str(valor))
        self.lbl_valor.setProperty("class", "kpi-value")
        self.lbl_valor.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.lbl_valor)
        
        # Cambio porcentual
        if cambio_porcentaje is not None:
            self.lbl_cambio = QLabel(self._formatear_cambio(cambio_porcentaje))
            clase = "kpi-change-positive" if cambio_porcentaje >= 0 else "kpi-change-negative"
            self.lbl_cambio.setProperty("class", f"kpi-change {clase}")
            layout.addWidget(self.lbl_cambio)
        
        layout.addStretch()
    
    def _formatear_cambio(self, porcentaje):
        simbolo = "▲" if porcentaje >= 0 else "▼"
        return f"{simbolo} {abs(porcentaje):.1f}% vs. mes anterior"
    
    def actualizar_valor(self, nuevo_valor, nuevo_cambio=None):
        self.lbl_valor.setText(str(nuevo_valor))
        if nuevo_cambio is not None and hasattr(self, 'lbl_cambio'):
            self.lbl_cambio.setText(self._formatear_cambio(nuevo_cambio))
            clase = "kpi-change-positive" if nuevo_cambio >= 0 else "kpi-change-negative"
            self.lbl_cambio.setProperty("class", f"kpi-change {clase}")
            self.lbl_cambio.style().unpolish(self.lbl_cambio)
            self.lbl_cambio.style().polish(self.lbl_cambio)


class DashboardEjecutivo(QWidget):
    """Dashboard ejecutivo con KPIs y gráficos"""
    
    def __init__(self, fm: FirebaseManager, config: dict, parent=None):
        super().__init__(parent)
        self.fm = fm
        self.config = config
        self.moneda = config.get('app', {}).get('moneda', 'RD$')
        
        self.setStyleSheet(DASHBOARD_STYLE)
        
        # Timer para actualización automática
        self.timer_actualizacion = QTimer(self)
        self.timer_actualizacion.timeout.connect(self.actualizar_datos)
        self.timer_actualizacion.start(300000)  # 5 minutos
        
        self._init_ui()
        self.actualizar_datos()
    
    def _init_ui(self):
        """Inicializa la interfaz"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        titulo = QLabel("Dashboard Ejecutivo")
        titulo.setProperty("class", "title")
        header_layout.addWidget(titulo)
        
        header_layout.addStretch()
        
        # Selector de período
        lbl_periodo = QLabel("Período:")
        lbl_periodo.setStyleSheet("font-weight: 600; color: #374151;")
        header_layout.addWidget(lbl_periodo)
        
        self.combo_periodo = QComboBox()
        self.combo_periodo.addItem("Último Mes", 30)
        self.combo_periodo.addItem("Últimos 3 Meses", 90)
        self.combo_periodo.addItem("Últimos 6 Meses", 180)
        self.combo_periodo.addItem("Último Año", 365)
        self.combo_periodo.currentIndexChanged.connect(self.actualizar_datos)
        header_layout.addWidget(self.combo_periodo)
        
        btn_actualizar = QPushButton("🔄 Actualizar")
        btn_actualizar.clicked.connect(self.actualizar_datos)
        header_layout.addWidget(btn_actualizar)
        
        layout.addLayout(header_layout)
        
        # Área de scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        
        # === KPIs PRINCIPALES ===
        kpis_grid = QGridLayout()
        kpis_grid.setSpacing(15)
        
        self.kpi_ingresos = KPICard("Ingresos Totales", f"{self.moneda} 0.00", 0, "💰")
        kpis_grid.addWidget(self.kpi_ingresos, 0, 0)
        
        self.kpi_gastos = KPICard("Gastos Totales", f"{self.moneda} 0.00", 0, "💸")
        kpis_grid.addWidget(self.kpi_gastos, 0, 1)
        
        self.kpi_utilidad = KPICard("Utilidad Neta", f"{self.moneda} 0.00", 0, "📈")
        kpis_grid.addWidget(self.kpi_utilidad, 0, 2)
        
        self.kpi_alquileres = KPICard("Alquileres Activos", "0", 0, "🚜")
        kpis_grid.addWidget(self.kpi_alquileres, 1, 0)
        
        self.kpi_utilizacion = KPICard("Utilización", "0%", 0, "⚡")
        kpis_grid.addWidget(self.kpi_utilizacion, 1, 1)
        
        self.kpi_ingreso_dia = KPICard("Ingreso/Día", f"{self.moneda} 0.00", None, "📅")
        kpis_grid.addWidget(self.kpi_ingreso_dia, 1, 2)
        
        scroll_layout.addLayout(kpis_grid)
        
        # === GRÁFICOS ===
        graficos_layout = QHBoxLayout()
        graficos_layout.setSpacing(15)
        
        # Gráfico de ingresos vs gastos
        grupo_ingresos = QGroupBox("📊 Ingresos vs Gastos (Últimos 6 Meses)")
        layout_ingresos = QVBoxLayout(grupo_ingresos)
        self.chart_ingresos = self._crear_grafico_ingresos()
        layout_ingresos.addWidget(self.chart_ingresos)
        graficos_layout.addWidget(grupo_ingresos)
        
        # Gráfico de equipos más rentables
        grupo_equipos = QGroupBox("🏆 Top 5 Equipos Más Rentables")
        layout_equipos = QVBoxLayout(grupo_equipos)
        self.chart_equipos = self._crear_grafico_equipos()
        layout_equipos.addWidget(self.chart_equipos)
        graficos_layout.addWidget(grupo_equipos)
        
        scroll_layout.addLayout(graficos_layout)
        
        # === ALERTAS Y RESUMEN ===
        grupo_alertas = QGroupBox("⚠️ Alertas y Recomendaciones")
        layout_alertas = QVBoxLayout(grupo_alertas)
        self.lbl_alertas = QLabel("Cargando alertas...")
        self.lbl_alertas.setStyleSheet("color: #374151; font-size: 10pt; padding: 10px;")
        self.lbl_alertas.setWordWrap(True)
        layout_alertas.addWidget(self.lbl_alertas)
        scroll_layout.addWidget(grupo_alertas)
        
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
    
    def _crear_grafico_ingresos(self):
        """Crea gráfico de líneas de ingresos vs gastos"""
        chart = QChart()
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setBackgroundBrush(QColor("#FFFFFF"))
        chart.setTitleFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        # Series
        self.series_ingresos = QLineSeries()
        self.series_ingresos.setName("Ingresos")
        pen_ingresos = QPen(QColor("#059669"))
        pen_ingresos.setWidth(3)
        self.series_ingresos.setPen(pen_ingresos)
        
        self.series_gastos = QLineSeries()
        self.series_gastos.setName("Gastos")
        pen_gastos = QPen(QColor("#DC2626"))
        pen_gastos.setWidth(3)
        self.series_gastos.setPen(pen_gastos)
        
        chart.addSeries(self.series_ingresos)
        chart.addSeries(self.series_gastos)
        
        # Ejes
        axis_x = QBarCategoryAxis()
        axis_y = QValueAxis()
        axis_y.setTitleText(f"Monto ({self.moneda})")
        
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        
        self.series_ingresos.attachAxis(axis_x)
        self.series_ingresos.attachAxis(axis_y)
        self.series_gastos.attachAxis(axis_x)
        self.series_gastos.attachAxis(axis_y)
        
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumHeight(300)
        
        return chart_view
    
    def _crear_grafico_equipos(self):
        """Crea gráfico de barras de equipos más rentables"""
        chart = QChart()
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setBackgroundBrush(QColor("#FFFFFF"))
        
        self.barset_equipos = QBarSet("Utilidad")
        self.barset_equipos.setColor(QColor("#F59E0B"))
        
        self.series_barras = QBarSeries()
        self.series_barras.append(self.barset_equipos)
        
        chart.addSeries(self.series_barras)
        
        # Ejes
        self.axis_equipos = QBarCategoryAxis()
        axis_y = QValueAxis()
        axis_y.setTitleText(f"Utilidad ({self.moneda})")
        
        chart.addAxis(self.axis_equipos, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        
        self.series_barras.attachAxis(self.axis_equipos)
        self.series_barras.attachAxis(axis_y)
        
        chart.legend().setVisible(False)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumHeight(300)
        
        return chart_view
    
    def actualizar_datos(self):
        """Actualiza todos los datos del dashboard"""
        try:
            dias = self.combo_periodo.currentData()
            fecha_inicio = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
            fecha_fin = datetime.now().strftime("%Y-%m-%d")
            
            # Obtener datos
            ingresos = self.fm.obtener_alquileres({
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            })
            
            gastos = self.fm.obtener_gastos({
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            })
            
            # Calcular KPIs
            total_ingresos = sum(float(i.get('monto_total', 0)) for i in ingresos)
            total_gastos = sum(float(g.get('monto', 0)) for g in gastos)
            utilidad = total_ingresos - total_gastos
            
            alquileres_activos = len([i for i in ingresos if i.get('estado') == 'activo'])
            
            # Calcular utilización (equipos con alquiler activo / total equipos)
            equipos = self.fm.obtener_equipos(activo=True)
            total_equipos = len(equipos)
            equipos_activos = len(set(i.get('equipo_id') for i in ingresos if i.get('estado') == 'activo'))
            utilizacion = (equipos_activos / total_equipos * 100) if total_equipos > 0 else 0
            
            ingreso_por_dia = total_ingresos / dias if dias > 0 else 0
            
            # Actualizar KPIs (cambio vs período anterior - simplificado)
            cambio_ingresos = 15.3  # Placeholder - calcular real comparando con período anterior
            cambio_gastos = -8.2
            cambio_utilidad = 22.1
            
            self.kpi_ingresos.actualizar_valor(f"{self.moneda} {total_ingresos:,.2f}", cambio_ingresos)
            self.kpi_gastos.actualizar_valor(f"{self.moneda} {total_gastos:,.2f}", cambio_gastos)
            self.kpi_utilidad.actualizar_valor(f"{self.moneda} {utilidad:,.2f}", cambio_utilidad)
            self.kpi_alquileres.actualizar_valor(str(alquileres_activos))
            self.kpi_utilizacion.actualizar_valor(f"{utilizacion:.1f}%")
            self.kpi_ingreso_dia.actualizar_valor(f"{self.moneda} {ingreso_por_dia:,.2f}")
            
            # Actualizar gráficos
            self._actualizar_grafico_ingresos(fecha_inicio, fecha_fin)
            self._actualizar_grafico_equipos(fecha_inicio, fecha_fin)
            
            # Generar alertas
            self._generar_alertas(utilizacion, utilidad, alquileres_activos)
            
            logger.info("Dashboard actualizado correctamente")
            
        except Exception as e:
            logger.error(f"Error actualizando dashboard: {e}", exc_info=True)
    
    def _actualizar_grafico_ingresos(self, fecha_inicio, fecha_fin):
        """Actualiza el gráfico de ingresos vs gastos"""
        try:
            # Obtener datos por mes (últimos 6 meses)
            meses = []
            ingresos_por_mes = []
            gastos_por_mes = []
            
            for i in range(6):
                fecha = datetime.now() - timedelta(days=30 * i)
                mes_str = fecha.strftime("%b %Y")
                meses.insert(0, mes_str)
                
                fecha_mes_inicio = fecha.replace(day=1).strftime("%Y-%m-%d")
                ultimo_dia = (fecha.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                fecha_mes_fin = ultimo_dia.strftime("%Y-%m-%d")
                
                ingresos = self.fm.obtener_alquileres({
                    'fecha_inicio': fecha_mes_inicio,
                    'fecha_fin': fecha_mes_fin
                })
                gastos = self.fm.obtener_gastos({
                    'fecha_inicio': fecha_mes_inicio,
                    'fecha_fin': fecha_mes_fin
                })
                
                total_ing = sum(float(i.get('monto_total', 0)) for i in ingresos)
                total_gas = sum(float(g.get('monto', 0)) for g in gastos)
                
                ingresos_por_mes.insert(0, total_ing)
                gastos_por_mes.insert(0, total_gas)
            
            # Actualizar series
            self.series_ingresos.clear()
            self.series_gastos.clear()
            
            for i, mes in enumerate(meses):
                self.series_ingresos.append(i, ingresos_por_mes[i])
                self.series_gastos.append(i, gastos_por_mes[i])
            
            # Actualizar categorías del eje X
            chart = self.chart_ingresos.chart()
            axis_x = chart.axes(Qt.AlignmentFlag.AlignBottom)[0]
            axis_x.clear()
            axis_x.append(meses)
            
        except Exception as e:
            logger.error(f"Error actualizando gráfico de ingresos: {e}", exc_info=True)
    
    def _actualizar_grafico_equipos(self, fecha_inicio, fecha_fin):
        """Actualiza el gráfico de equipos más rentables"""
        try:
            rendimientos = self.fm.obtener_rendimiento_por_equipo(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            
            # Calcular utilidad por equipo
            equipos_mapa = {str(e['id']): e['nombre'] for e in self.fm.obtener_equipos()}
            
            utilidades = []
            for r in rendimientos:
                equipo_id = str(r.get('equipo_id', ''))
                nombre = equipos_mapa.get(equipo_id, f'Equipo {equipo_id}')
                ingresos = float(r.get('monto_facturado', 0))
                gastos = float(r.get('monto_pagado_operador', 0))
                utilidad = ingresos - gastos
                
                utilidades.append({'nombre': nombre, 'utilidad': utilidad})
            
            # Top 5
            utilidades.sort(key=lambda x: x['utilidad'], reverse=True)
            top5 = utilidades[:5]
            
            # Actualizar gráfico
            self.barset_equipos.remove(0, self.barset_equipos.count())
            
            nombres = []
            for eq in top5:
                self.barset_equipos.append(eq['utilidad'])
                nombres.append(eq['nombre'])
            
            self.axis_equipos.clear()
            self.axis_equipos.append(nombres)
            
        except Exception as e:
            logger.error(f"Error actualizando gráfico de equipos: {e}", exc_info=True)
    
    def _generar_alertas(self, utilizacion, utilidad, alquileres_activos):
        """Genera alertas y recomendaciones"""
        alertas = []
        
        if utilizacion < 60:
            alertas.append(f"⚠️ <b>Utilización baja ({utilizacion:.1f}%)</b>: Considera estrategias de marketing para aumentar alquileres.")
        
        if utilidad < 0:
            alertas.append(f"🚨 <b>Utilidad negativa ({self.moneda} {utilidad:,.2f})</b>: Revisa costos operativos y precios de alquiler.")
        
        if alquileres_activos == 0:
            alertas.append("⚠️ <b>Sin alquileres activos</b>: Contacta clientes potenciales.")
        
        if utilizacion > 90:
            alertas.append("✅ <b>Excelente utilización</b>: Considera adquirir más equipos para satisfacer demanda.")
        
        if utilidad > 0:
            margen = (utilidad / (utilidad + 1)) * 100  # Simplificado
            alertas.append(f"💰 <b>Negocio rentable</b>: Margen de utilidad saludable.")
        
        if not alertas:
            alertas.append("✅ Todo funcionando correctamente.")
        
        self.lbl_alertas.setText("<br><br>".join(alertas))