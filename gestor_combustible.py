# gestor_combustible.py

"""
Gestor de Combustible - Control de consumo y eficiencia de equipos
Permite registrar cargas de combustible y analizar consumos
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox, QDateEdit,
    QComboBox, QMessageBox, QAbstractItemView, QGroupBox, QFrame,
    QTextEdit, QFileDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
import logging
from datetime import datetime, timedelta
from firebase_manager import FirebaseManager

logger = logging.getLogger(__name__)

# Estilos CSS
COMBUSTIBLE_STYLE = """
QWidget {
    background-color: #F3F4F6;
    font-family: 'Segoe UI';
}
QLabel[class="title"] {
    font-size: 20pt;
    font-weight: bold;
    color: #1F2937;
}
QLabel[class="stat-label"] {
    font-size: 10pt;
    color: #6B7280;
    font-weight: 500;
}
QLabel[class="stat-value"] {
    font-size: 18pt;
    font-weight: bold;
    color: #F59E0B;
}
QFrame[class="stat-card"] {
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 10px;
    padding: 15px;
}
QPushButton {
    background-color: #F59E0B;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 18px;
    font-size: 10pt;
    font-weight: 600;
    min-height: 25px;
}
QPushButton:hover {
    background-color: #D97706;
}
QPushButton:pressed {
    background-color: #B45309;
}
QPushButton[class="secondary"] {
    background-color: #E5E7EB;
    color: #374151;
}
QPushButton[class="secondary"]:hover {
    background-color: #D1D5DB;
}
QPushButton[class="danger"] {
    background-color: #DC2626;
    color: white;
}
QPushButton[class="danger"]:hover {
    background-color: #B91C1C;
}
QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F9FAFB;
    gridline-color: #E5E7EB;
    selection-background-color: #FEF3C7;
    selection-color: #1F2937;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
}
QTableWidget::item {
    padding: 8px;
}
QHeaderView::section {
    background-color: #1F2937;
    color: #FFFFFF;
    padding: 10px;
    border: none;
    font-weight: 600;
}
QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox, QTextEdit {
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 6px;
    padding: 8px 12px;
    color: #1F2937;
    font-size: 10pt;
}
QLineEdit:hover, QDoubleSpinBox:hover, QDateEdit:hover, QComboBox:hover {
    border: 2px solid #F59E0B;
}
QLineEdit:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {
    border: 2px solid #F59E0B;
}
QGroupBox {
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 10px;
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
"""


class StatCard(QFrame):
    """Tarjeta de estadística"""
    
    def __init__(self, label, value, parent=None):
        super().__init__(parent)
        self.setProperty("class", "stat-card")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        lbl_label = QLabel(label)
        lbl_label.setProperty("class", "stat-label")
        layout.addWidget(lbl_label)
        
        self.lbl_value = QLabel(value)
        self.lbl_value.setProperty("class", "stat-value")
        layout.addWidget(self.lbl_value)
    
    def actualizar(self, value):
        self.lbl_value.setText(value)


class GestorCombustible(QWidget):
    """Widget principal para gestión de combustible"""
    
    def __init__(self, fm: FirebaseManager, config: dict, parent=None):
        super().__init__(parent)
        self.fm = fm
        self.config = config
        self.moneda = config.get('app', {}).get('moneda', 'RD$')
        
        self.cargas = []
        self.equipos_mapa = {}
        
        self.setStyleSheet(COMBUSTIBLE_STYLE)
        
        self._init_ui()
        self._cargar_equipos()
        self._cargar_datos()
    
    def _init_ui(self):
        """Inicializa la interfaz"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        titulo = QLabel("⛽ Control de Combustible")
        titulo.setProperty("class", "title")
        header_layout.addWidget(titulo)
        
        header_layout.addStretch()
        
        # Filtro por equipo
        lbl_equipo = QLabel("Equipo:")
        lbl_equipo.setStyleSheet("font-weight: 600; color: #374151;")
        header_layout.addWidget(lbl_equipo)
        
        self.combo_equipo_filtro = QComboBox()
        self.combo_equipo_filtro.addItem("Todos", None)
        self.combo_equipo_filtro.currentIndexChanged.connect(self._aplicar_filtros)
        header_layout.addWidget(self.combo_equipo_filtro)
        
        # Filtro por período
        lbl_periodo = QLabel("Período:")
        lbl_periodo.setStyleSheet("font-weight: 600; color: #374151;")
        header_layout.addWidget(lbl_periodo)
        
        self.combo_periodo = QComboBox()
        self.combo_periodo.addItem("Última Semana", 7)
        self.combo_periodo.addItem("Último Mes", 30)
        self.combo_periodo.addItem("Últimos 3 Meses", 90)
        self.combo_periodo.addItem("Todo", 9999)
        self.combo_periodo.currentIndexChanged.connect(self._aplicar_filtros)
        header_layout.addWidget(self.combo_periodo)
        
        btn_nueva_carga = QPushButton("➕ Nueva Carga")
        btn_nueva_carga.clicked.connect(self._nueva_carga)
        header_layout.addWidget(btn_nueva_carga)
        
        btn_actualizar = QPushButton("🔄 Actualizar")
        btn_actualizar.clicked.connect(self._cargar_datos)
        header_layout.addWidget(btn_actualizar)
        
        layout.addLayout(header_layout)
        
        # === ESTADÍSTICAS ===
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.stat_total_litros = StatCard("Total Litros", "0.00 L")
        stats_layout.addWidget(self.stat_total_litros)
        
        self.stat_total_costo = StatCard("Costo Total", f"{self.moneda} 0.00")
        stats_layout.addWidget(self.stat_total_costo)
        
        self.stat_promedio_litro = StatCard("Precio Promedio/L", f"{self.moneda} 0.00")
        stats_layout.addWidget(self.stat_promedio_litro)
        
        self.stat_eficiencia = StatCard("Eficiencia Promedio", "0.00 L/h")
        stats_layout.addWidget(self.stat_eficiencia)
        
        layout.addLayout(stats_layout)
        
        # === GRÁFICO DE CONSUMO ===
        grupo_grafico = QGroupBox("📈 Historial de Consumo")
        layout_grafico = QVBoxLayout(grupo_grafico)
        self.chart_view = self._crear_grafico()
        layout_grafico.addWidget(self.chart_view)
        layout.addWidget(grupo_grafico)
        
        # === TABLA DE CARGAS ===
        grupo_tabla = QGroupBox("📋 Registro de Cargas")
        layout_tabla = QVBoxLayout(grupo_tabla)
        
        # Botones de acción
        botones_tabla_layout = QHBoxLayout()
        
        btn_editar = QPushButton("✏️ Editar")
        btn_editar.clicked.connect(self._editar_carga)
        botones_tabla_layout.addWidget(btn_editar)
        
        btn_eliminar = QPushButton("🗑️ Eliminar")
        btn_eliminar.setProperty("class", "danger")
        btn_eliminar.clicked.connect(self._eliminar_carga)
        botones_tabla_layout.addWidget(btn_eliminar)
        
        btn_exportar = QPushButton("📄 Exportar Excel")
        btn_exportar.setProperty("class", "secondary")
        btn_exportar.clicked.connect(self._exportar_excel)
        botones_tabla_layout.addWidget(btn_exportar)
        
        botones_tabla_layout.addStretch()
        layout_tabla.addLayout(botones_tabla_layout)
        
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Fecha", "Equipo", "Litros", "Precio/L", 
            "Costo Total", "Horómetro", "Eficiencia (L/h)"
        ])
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.itemDoubleClicked.connect(self._editar_carga)
        layout_tabla.addWidget(self.tabla)
        
        layout.addWidget(grupo_tabla)
    
    def _crear_grafico(self):
        """Crea el gráfico de consumo de combustible"""
        chart = QChart()
        chart.setTitle("Consumo Diario de Combustible")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setBackgroundBrush(QColor("#FFFFFF"))
        
        self.series_consumo = QLineSeries()
        self.series_consumo.setName("Litros")
        
        chart.addSeries(self.series_consumo)
        
        # Ejes
        axis_x = QDateTimeAxis()
        axis_x.setFormat("dd/MM")
        axis_x.setTitleText("Fecha")
        
        axis_y = QValueAxis()
        axis_y.setTitleText("Litros")
        
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        
        self.series_consumo.attachAxis(axis_x)
        self.series_consumo.attachAxis(axis_y)
        
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(chart_view.renderHints())
        chart_view.setMinimumHeight(300)
        
        return chart_view
    
    def _cargar_equipos(self):
        """Carga la lista de equipos"""
        try:
            equipos = self.fm.obtener_equipos(activo=True)
            self.equipos_mapa = {str(e['id']): e['nombre'] for e in equipos}
            
            self.combo_equipo_filtro.clear()
            self.combo_equipo_filtro.addItem("Todos", None)
            
            for eid, nombre in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
                self.combo_equipo_filtro.addItem(nombre, eid)
                
        except Exception as e:
            logger.error(f"Error cargando equipos: {e}", exc_info=True)
    
    def _cargar_datos(self):
        """Carga los datos de combustible desde Firebase"""
        try:
            # Obtener período
            dias = self.combo_periodo.currentData()
            fecha_inicio = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
            fecha_fin = datetime.now().strftime("%Y-%m-%d")
            
            # Cargar cargas de combustible
            self.cargas = self.fm.obtener_cargas_combustible(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            
            self._aplicar_filtros()
            
        except Exception as e:
            logger.error(f"Error cargando datos de combustible: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al cargar datos:\n{e}")
    
    def _aplicar_filtros(self):
        """Aplica filtros y actualiza la vista"""
        try:
            equipo_id = self.combo_equipo_filtro.currentData()
            
            # Filtrar cargas
            cargas_filtradas = self.cargas
            
            if equipo_id:
                cargas_filtradas = [c for c in cargas_filtradas if str(c.get('equipo_id')) == equipo_id]
            
            # Actualizar estadísticas
            self._actualizar_estadisticas(cargas_filtradas)
            
            # Actualizar tabla
            self._actualizar_tabla(cargas_filtradas)
            
            # Actualizar gráfico
            self._actualizar_grafico(cargas_filtradas)
            
        except Exception as e:
            logger.error(f"Error aplicando filtros: {e}", exc_info=True)
    
    def _actualizar_estadisticas(self, cargas):
        """Actualiza las estadísticas"""
        if not cargas:
            self.stat_total_litros.actualizar("0.00 L")
            self.stat_total_costo.actualizar(f"{self.moneda} 0.00")
            self.stat_promedio_litro.actualizar(f"{self.moneda} 0.00")
            self.stat_eficiencia.actualizar("0.00 L/h")
            return
        
        total_litros = sum(float(c.get('litros', 0)) for c in cargas)
        total_costo = sum(float(c.get('costo_total', 0)) for c in cargas)
        precio_promedio = total_costo / total_litros if total_litros > 0 else 0
        
        # Calcular eficiencia (litros/hora)
        cargas_con_horometro = [c for c in cargas if c.get('horometro_actual') and c.get('horometro_anterior')]
        
        if cargas_con_horometro:
            eficiencias = []
            for c in cargas_con_horometro:
                horas = float(c.get('horometro_actual', 0)) - float(c.get('horometro_anterior', 0))
                if horas > 0:
                    eficiencia = float(c.get('litros', 0)) / horas
                    eficiencias.append(eficiencia)
            
            eficiencia_promedio = sum(eficiencias) / len(eficiencias) if eficiencias else 0
        else:
            eficiencia_promedio = 0
        
        self.stat_total_litros.actualizar(f"{total_litros:,.2f} L")
        self.stat_total_costo.actualizar(f"{self.moneda} {total_costo:,.2f}")
        self.stat_promedio_litro.actualizar(f"{self.moneda} {precio_promedio:,.2f}")
        self.stat_eficiencia.actualizar(f"{eficiencia_promedio:.2f} L/h")
    
    def _actualizar_tabla(self, cargas):
        """Actualiza la tabla de cargas"""
        self.tabla.setRowCount(0)
        
        for carga in sorted(cargas, key=lambda x: x.get('fecha', ''), reverse=True):
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            
            carga_id = str(carga.get('id', ''))
            fecha = carga.get('fecha', '')
            equipo_id = str(carga.get('equipo_id', ''))
            equipo_nombre = self.equipos_mapa.get(equipo_id, f'ID: {equipo_id}')
            litros = float(carga.get('litros', 0))
            precio_litro = float(carga.get('precio_litro', 0))
            costo_total = float(carga.get('costo_total', 0))
            horometro = carga.get('horometro_actual', '-')
            
            # Calcular eficiencia
            if carga.get('horometro_actual') and carga.get('horometro_anterior'):
                horas = float(carga.get('horometro_actual', 0)) - float(carga.get('horometro_anterior', 0))
                eficiencia = litros / horas if horas > 0 else 0
                eficiencia_str = f"{eficiencia:.2f} L/h"
            else:
                eficiencia_str = "-"
            
            self.tabla.setItem(row, 0, QTableWidgetItem(carga_id))
            self.tabla.setItem(row, 1, QTableWidgetItem(fecha))
            self.tabla.setItem(row, 2, QTableWidgetItem(equipo_nombre))
            
            item_litros = QTableWidgetItem(f"{litros:.2f} L")
            item_litros.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 3, item_litros)
            
            item_precio = QTableWidgetItem(f"{self.moneda} {precio_litro:.2f}")
            item_precio.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 4, item_precio)
            
            item_costo = QTableWidgetItem(f"{self.moneda} {costo_total:,.2f}")
            item_costo.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 5, item_costo)
            
            item_horometro = QTableWidgetItem(str(horometro))
            item_horometro.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(row, 6, item_horometro)
            
            item_eficiencia = QTableWidgetItem(eficiencia_str)
            item_eficiencia.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 7, item_eficiencia)
    
    def _actualizar_grafico(self, cargas):
        """Actualiza el gráfico de consumo"""
        self.series_consumo.clear()
        
        if not cargas:
            return
        
        # Agrupar por fecha
        consumo_por_fecha = {}
        for carga in cargas:
            fecha = carga.get('fecha', '')
            litros = float(carga.get('litros', 0))
            
            if fecha in consumo_por_fecha:
                consumo_por_fecha[fecha] += litros
            else:
                consumo_por_fecha[fecha] = litros
        
        # Ordenar y agregar al gráfico
        for fecha, litros in sorted(consumo_por_fecha.items()):
            try:
                dt = datetime.strptime(fecha, "%Y-%m-%d")
                timestamp = dt.timestamp() * 1000  # Convertir a milisegundos
                self.series_consumo.append(timestamp, litros)
            except:
                continue
    
    def _nueva_carga(self):
        """Abre diálogo para nueva carga de combustible"""
        dialog = DialogoCargaCombustible(self.fm, self.equipos_mapa, self.moneda, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._cargar_datos()
    
    def _editar_carga(self):
        """Edita la carga seleccionada"""
        current_row = self.tabla.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Sin Selección", "Debe seleccionar una carga.")
            return
        
        carga_id = self.tabla.item(current_row, 0).text()
        carga = next((c for c in self.cargas if str(c.get('id')) == carga_id), None)
        
        if not carga:
            QMessageBox.warning(self, "Error", "No se encontró la carga.")
            return
        
        dialog = DialogoCargaCombustible(self.fm, self.equipos_mapa, self.moneda, carga=carga, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._cargar_datos()
    
    def _eliminar_carga(self):
        """Elimina la carga seleccionada"""
        current_row = self.tabla.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Sin Selección", "Debe seleccionar una carga.")
            return
        
        carga_id = self.tabla.item(current_row, 0).text()
        
        respuesta = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            "¿Está seguro de eliminar esta carga de combustible?\n\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                if self.fm.eliminar_carga_combustible(carga_id):
                    QMessageBox.information(self, "Éxito", "Carga eliminada correctamente.")
                    self._cargar_datos()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo eliminar la carga.")
            except Exception as e:
                logger.error(f"Error eliminando carga: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al eliminar:\n{e}")
    
    def _exportar_excel(self):
        """Exporta los datos a Excel"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill
            
            archivo, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte",
                f"Combustible_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "Excel (*.xlsx)"
            )
            
            if not archivo:
                return
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Cargas Combustible"
            
            # Encabezados
            headers = ["Fecha", "Equipo", "Litros", "Precio/L", "Costo Total", "Horómetro", "Eficiencia"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")
            
            # Datos
            equipo_id_filtro = self.combo_equipo_filtro.currentData()
            cargas_filtradas = self.cargas
            if equipo_id_filtro:
                cargas_filtradas = [c for c in cargas_filtradas if str(c.get('equipo_id')) == equipo_id_filtro]
            
            for row, carga in enumerate(sorted(cargas_filtradas, key=lambda x: x.get('fecha', '')), 2):
                equipo_id = str(carga.get('equipo_id', ''))
                equipo_nombre = self.equipos_mapa.get(equipo_id, f'ID: {equipo_id}')
                
                horas = 0
                if carga.get('horometro_actual') and carga.get('horometro_anterior'):
                    horas = float(carga.get('horometro_actual', 0)) - float(carga.get('horometro_anterior', 0))
                
                litros = float(carga.get('litros', 0))
                eficiencia = litros / horas if horas > 0 else 0
                
                ws.cell(row=row, column=1, value=carga.get('fecha', ''))
                ws.cell(row=row, column=2, value=equipo_nombre)
                ws.cell(row=row, column=3, value=litros)
                ws.cell(row=row, column=4, value=float(carga.get('precio_litro', 0)))
                ws.cell(row=row, column=5, value=float(carga.get('costo_total', 0)))
                ws.cell(row=row, column=6, value=carga.get('horometro_actual', ''))
                ws.cell(row=row, column=7, value=f"{eficiencia:.2f}" if eficiencia > 0 else "-")
            
            wb.save(archivo)
            
            QMessageBox.information(
                self,
                "Éxito",
                f"Reporte exportado correctamente:\n{archivo}\n\n¿Desea abrirlo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
        except ImportError:
            QMessageBox.critical(
                self,
                "Error",
                "Se requiere la librería 'openpyxl' para exportar a Excel.\n\n"
                "Instálela con: pip install openpyxl"
            )
        except Exception as e:
            logger.error(f"Error exportando a Excel: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al exportar:\n{e}")


class DialogoCargaCombustible(QDialog):
    """Diálogo para agregar/editar carga de combustible"""
    
    def __init__(self, fm: FirebaseManager, equipos_mapa: dict, moneda: str, carga=None, parent=None):
        super().__init__(parent)
        self.fm = fm
        self.equipos_mapa = equipos_mapa
        self.moneda = moneda
        self.carga = carga
        
        titulo = "Editar Carga" if carga else "Nueva Carga de Combustible"
        self.setWindowTitle(titulo)
        self.setMinimumWidth(500)
        
        self.setStyleSheet(COMBUSTIBLE_STYLE)
        
        self._init_ui()
        
        if carga:
            self._cargar_datos()
    
    def _init_ui(self):
        """Inicializa la interfaz"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # Título
        titulo_texto = "Editar Carga de Combustible" if self.carga else "Nueva Carga de Combustible"
        titulo = QLabel(titulo_texto)
        titulo.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1F2937;")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)
        
        # Formulario
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Fecha
        lbl_fecha = QLabel("Fecha:")
        lbl_fecha.setStyleSheet("font-weight: 600; color: #374151;")
        self.fecha = QDateEdit(calendarPopup=True)
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow(lbl_fecha, self.fecha)
        
        # Equipo
        lbl_equipo = QLabel("Equipo:")
        lbl_equipo.setStyleSheet("font-weight: 600; color: #374151;")
        self.combo_equipo = QComboBox()
        for eid, nombre in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
            self.combo_equipo.addItem(nombre, eid)
        form_layout.addRow(lbl_equipo, self.combo_equipo)
        
        # Litros
        lbl_litros = QLabel("Litros:")
        lbl_litros.setStyleSheet("font-weight: 600; color: #374151;")
        self.spin_litros = QDoubleSpinBox()
        self.spin_litros.setRange(0, 10000)
        self.spin_litros.setDecimals(2)
        self.spin_litros.setSuffix(" L")
        self.spin_litros.valueChanged.connect(self._calcular_costo)
        form_layout.addRow(lbl_litros, self.spin_litros)
        
        # Precio por litro
        lbl_precio = QLabel("Precio/Litro:")
        lbl_precio.setStyleSheet("font-weight: 600; color: #374151;")
        self.spin_precio = QDoubleSpinBox()
        self.spin_precio.setRange(0, 10000)
        self.spin_precio.setDecimals(2)
        self.spin_precio.setPrefix(f"{self.moneda} ")
        self.spin_precio.valueChanged.connect(self._calcular_costo)
        form_layout.addRow(lbl_precio, self.spin_precio)
        
        # Costo total (calculado)
        lbl_costo = QLabel("Costo Total:")
        lbl_costo.setStyleSheet("font-weight: 600; color: #374151;")
        self.lbl_costo_total = QLabel(f"{self.moneda} 0.00")
        self.lbl_costo_total.setStyleSheet("font-size: 14pt; font-weight: bold; color: #F59E0B;")
        form_layout.addRow(lbl_costo, self.lbl_costo_total)
        
        # Horómetro anterior (opcional)
        lbl_horometro_ant = QLabel("Horómetro Anterior:")
        lbl_horometro_ant.setStyleSheet("font-weight: 600; color: #374151;")
        self.spin_horometro_ant = QDoubleSpinBox()
        self.spin_horometro_ant.setRange(0, 999999)
        self.spin_horometro_ant.setDecimals(1)
        self.spin_horometro_ant.setSuffix(" h")
        self.spin_horometro_ant.setSpecialValueText("(Opcional)")
        form_layout.addRow(lbl_horometro_ant, self.spin_horometro_ant)
        
        # Horómetro actual (opcional)
        lbl_horometro_act = QLabel("Horómetro Actual:")
        lbl_horometro_act.setStyleSheet("font-weight: 600; color: #374151;")
        self.spin_horometro_act = QDoubleSpinBox()
        self.spin_horometro_act.setRange(0, 999999)
        self.spin_horometro_act.setDecimals(1)
        self.spin_horometro_act.setSuffix(" h")
        self.spin_horometro_act.setSpecialValueText("(Opcional)")
        form_layout.addRow(lbl_horometro_act, self.spin_horometro_act)
        
        # Observaciones
        lbl_obs = QLabel("Observaciones:")
        lbl_obs.setStyleSheet("font-weight: 600; color: #374151;")
        self.txt_observaciones = QTextEdit()
        self.txt_observaciones.setMaximumHeight(80)
        self.txt_observaciones.setPlaceholderText("Observaciones opcionales...")
        form_layout.addRow(lbl_obs, self.txt_observaciones)
        
        layout.addLayout(form_layout)
        
        layout.addSpacing(10)
        
        # Botones
        botones_layout = QHBoxLayout()
        botones_layout.setSpacing(10)
        
        btn_guardar = QPushButton("💾 Guardar")
        btn_guardar.clicked.connect(self._guardar)
        btn_guardar.setMinimumWidth(120)
        botones_layout.addWidget(btn_guardar)
        
        btn_cancelar = QPushButton("✖️ Cancelar")
        btn_cancelar.setProperty("class", "secondary")
        btn_cancelar.clicked.connect(self.reject)
        btn_cancelar.setMinimumWidth(120)
        botones_layout.addWidget(btn_cancelar)
        
        layout.addLayout(botones_layout)
    
    def _cargar_datos(self):
        """Carga los datos de la carga a editar"""
        if not self.carga:
            return
        
        fecha_str = self.carga.get('fecha', '')
        if fecha_str:
            self.fecha.setDate(QDate.fromString(fecha_str, "yyyy-MM-dd"))
        
        equipo_id = str(self.carga.get('equipo_id', ''))
        index = self.combo_equipo.findData(equipo_id)
        if index >= 0:
            self.combo_equipo.setCurrentIndex(index)
        
        self.spin_litros.setValue(float(self.carga.get('litros', 0)))
        self.spin_precio.setValue(float(self.carga.get('precio_litro', 0)))
        
        if self.carga.get('horometro_anterior'):
            self.spin_horometro_ant.setValue(float(self.carga.get('horometro_anterior', 0)))
        
        if self.carga.get('horometro_actual'):
            self.spin_horometro_act.setValue(float(self.carga.get('horometro_actual', 0)))
        
        self.txt_observaciones.setPlainText(self.carga.get('observaciones', ''))
    
    def _calcular_costo(self):
        """Calcula el costo total"""
        litros = self.spin_litros.value()
        precio = self.spin_precio.value()
        costo_total = litros * precio
        
        self.lbl_costo_total.setText(f"{self.moneda} {costo_total:,.2f}")
    
    def _guardar(self):
        """Guarda la carga de combustible"""
        # Validaciones
        if self.combo_equipo.currentIndex() < 0:
            QMessageBox.warning(self, "Validación", "Debe seleccionar un equipo.")
            return
        
        if self.spin_litros.value() <= 0:
            QMessageBox.warning(self, "Validación", "Los litros deben ser mayor a cero.")
            return
        
        if self.spin_precio.value() <= 0:
            QMessageBox.warning(self, "Validación", "El precio debe ser mayor a cero.")
            return
        
        # Validar horómetros
        if self.spin_horometro_ant.value() > 0 and self.spin_horometro_act.value() > 0:
            if self.spin_horometro_act.value() <= self.spin_horometro_ant.value():
                QMessageBox.warning(
                    self,
                    "Validación",
                    "El horómetro actual debe ser mayor al anterior."
                )
                return
        
        # Preparar datos
        datos = {
            'fecha': self.fecha.date().toString("yyyy-MM-dd"),
            'equipo_id': self.combo_equipo.currentData(),
            'litros': self.spin_litros.value(),
            'precio_litro': self.spin_precio.value(),
            'costo_total': self.spin_litros.value() * self.spin_precio.value(),
            'observaciones': self.txt_observaciones.toPlainText().strip()
        }
        
        if self.spin_horometro_ant.value() > 0:
            datos['horometro_anterior'] = self.spin_horometro_ant.value()
        
        if self.spin_horometro_act.value() > 0:
            datos['horometro_actual'] = self.spin_horometro_act.value()
        
        try:
            if self.carga:
                # Editar
                if self.fm.editar_carga_combustible(self.carga['id'], datos):
                    QMessageBox.information(self, "Éxito", "Carga actualizada correctamente.")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo actualizar la carga.")
            else:
                # Crear
                nuevo_id = self.fm.agregar_carga_combustible(datos)
                if nuevo_id:
                    QMessageBox.information(self, "Éxito", "Carga registrada correctamente.")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo registrar la carga.")
        
        except Exception as e:
            logger.error(f"Error guardando carga: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{e}")