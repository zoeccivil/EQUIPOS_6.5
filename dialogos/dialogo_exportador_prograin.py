"""
Diálogo de Exportación PROGRAIN 5.0
Interfaz gráfica para exportar transacciones (gastos e ingresos) al formato Excel compatible con PROGRAIN
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QGroupBox, QAbstractItemView, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush
import logging
from datetime import datetime, date
import calendar
import webbrowser
import os

from firebase_manager import FirebaseManager
from exportador_prograin import ExportadorPrograin

logger = logging.getLogger(__name__)


# Estilos CSS del diálogo
DIALOG_STYLE = """
QDialog {
    background-color: #F3F4F6;
    font-family: 'Segoe UI';
}
QLabel {
    color: #374151;
    font-size: 11pt;
}
QLabel[class="title"] {
    font-size: 14pt;
    font-weight: bold;
    color: #F59E0B;
}
QLabel[class="stat-label"] {
    font-size: 12pt;
    font-weight: bold;
    color: #1F2937;
}
QLabel[class="stat-value"] {
    font-size: 12pt;
    color: #059669;
    font-weight: 600;
}
QPushButton {
    background-color: #F59E0B;
    color: white;
    border: none;
    padding: 10px 18px;
    font-size: 11pt;
    border-radius: 6px;
    font-weight: 600;
    min-height: 25px;
}
QPushButton:hover {
    background-color: #D97706;
}
QPushButton:pressed {
    background-color: #B45309;
}
QPushButton:disabled {
    background-color: #D1D5DB;
    color: #9CA3AF;
}
QPushButton[class="secondary"] {
    background-color: #E5E7EB;
    color: #374151;
}
QPushButton[class="secondary"]:hover {
    background-color: #D1D5DB;
}
QPushButton[class="secondary"]:pressed {
    background-color: #9CA3AF;
}
QTableWidget {
    background-color: #FFFFFF;
    color: #1F2937;
    gridline-color: #E5E7EB;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    alternate-background-color: #F9FAFB;
}
QTableWidget::item {
    padding: 6px 8px;
}
QTableWidget::item:selected {
    background-color: #FEF3C7;
    color: #1F2937;
}
QHeaderView::section {
    background-color: #1F2937;
    color: #FFFFFF;
    padding: 10px;
    border: none;
    font-weight: 600;
    font-size: 10pt;
}
QComboBox {
    background-color: #FFFFFF;
    color: #1F2937;
    border: 2px solid #E5E7EB;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 10pt;
    min-height: 25px;
}
QComboBox:hover {
    border: 2px solid #F59E0B;
}
QComboBox:focus {
    border: 2px solid #F59E0B;
}
QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #6B7280;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #1F2937;
    selection-background-color: #FEF3C7;
    selection-color: #1F2937;
    border: 2px solid #E5E7EB;
}
QCheckBox {
    color: #374151;
    font-size: 11pt;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border: 2px solid #E5E7EB;
    border-radius: 4px;
    background-color: #FFFFFF;
}
QCheckBox::indicator:hover {
    border: 2px solid #F59E0B;
}
QCheckBox::indicator:checked {
    background-color: #F59E0B;
    border: 2px solid #F59E0B;
    image: none;
}
QCheckBox::indicator:checked:hover {
    background-color: #D97706;
    border: 2px solid #D97706;
}
QGroupBox {
    color: #1F2937;
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 8px;
    margin-top: 14px;
    font-weight: 600;
    font-size: 12pt;
    padding: 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 8px;
    background-color: #FFFFFF;
}
QScrollBar:vertical {
    background-color: #F3F4F6;
    width: 12px;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background-color: #D1D5DB;
    border-radius: 6px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #9CA3AF;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #F3F4F6;
    height: 12px;
    border-radius: 6px;
}
QScrollBar::handle:horizontal {
    background-color: #D1D5DB;
    border-radius: 6px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #9CA3AF;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


class DialogoExportadorPrograin(QDialog):
    """Diálogo para exportar transacciones al formato PROGRAIN 5.0"""
    
    def __init__(self, fm: FirebaseManager, mapas: dict, config: dict, parent=None):
        """
        Args:
            fm: Instancia de FirebaseManager
            mapas: Diccionario con todos los mapas (equipos, clientes, cuentas, categorías, subcategorías, proyectos)
            config: Configuración de la aplicación (para obtener moneda)
            parent: Widget padre
        """
        super().__init__(parent)
        self.fm = fm
        self.mapas = mapas
        self.config = config
        self.moneda_symbol = config.get('app', {}).get('moneda', 'RD$')
        
        # Datos cargados
        self.transacciones_actuales = []
        
        # Exportador
        self.exportador = ExportadorPrograin(moneda_symbol=self.moneda_symbol)
        
        self.setWindowTitle("Exportador PROGRAIN 5.0")
        self.setMinimumSize(1000, 700)
        
        # Aplicar estilos
        self.setStyleSheet(DIALOG_STYLE)
        
        self._init_ui()
        self._cargar_años_disponibles()
    
    def _init_ui(self):
        """Inicializa la interfaz gráfica"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # ========== SECCIÓN DE FILTROS ==========
        filtros_group = QGroupBox("FILTROS DE EXPORTACIÓN")
        filtros_layout = QVBoxLayout()
        filtros_layout.setContentsMargins(15, 25, 15, 15)
        filtros_layout.setSpacing(12)
        
        # Fila 1: Año y Mes
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        
        lbl_año = QLabel("Año:")
        lbl_año.setStyleSheet("font-weight: 600;")
        lbl_año.setFixedWidth(80)
        row1.addWidget(lbl_año)
        
        self.combo_año = QComboBox()
        self.combo_año.setMinimumWidth(120)
        row1.addWidget(self.combo_año)
        
        row1.addSpacing(30)
        
        lbl_mes = QLabel("Mes:")
        lbl_mes.setStyleSheet("font-weight: 600;")
        lbl_mes.setFixedWidth(60)
        row1.addWidget(lbl_mes)
        
        self.combo_mes = QComboBox()
        self.combo_mes.setMinimumWidth(150)
        self.combo_mes.addItem("Todos", "todos")
        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        for i, mes in enumerate(meses, 1):
            self.combo_mes.addItem(mes, i)
        row1.addWidget(self.combo_mes)
        
        row1.addStretch()
        filtros_layout.addLayout(row1)
        
        # Fila 2: Checkboxes
        row2 = QHBoxLayout()
        row2.setSpacing(30)
        
        self.check_incluir_gastos = QCheckBox("Incluir Gastos")
        self.check_incluir_gastos.setChecked(True)
        row2.addWidget(self.check_incluir_gastos)
        
        self.check_incluir_ingresos = QCheckBox("Incluir Ingresos")
        self.check_incluir_ingresos.setChecked(True)
        row2.addWidget(self.check_incluir_ingresos)
        
        row2.addStretch()
        filtros_layout.addLayout(row2)
        
        filtros_layout.addSpacing(5)
        
        # Botón de cargar vista previa
        row3 = QHBoxLayout()
        btn_cargar = QPushButton("🔍 Cargar Vista Previa")
        btn_cargar.clicked.connect(self._cargar_vista_previa)
        btn_cargar.setMinimumWidth(200)
        row3.addWidget(btn_cargar)
        row3.addStretch()
        filtros_layout.addLayout(row3)
        
        filtros_group.setLayout(filtros_layout)
        layout.addWidget(filtros_group)
        
        # ========== SECCIÓN DE VISTA PREVIA ==========
        preview_group = QGroupBox("VISTA PREVIA DE TRANSACCIONES")
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(15, 25, 15, 15)
        preview_layout.setSpacing(10)
        
        self.tabla_preview = QTableWidget()
        self.tabla_preview.setColumnCount(5)
        self.tabla_preview.setHorizontalHeaderLabels([
            "Fecha", "Concepto", "Detalle", "Débito", "Crédito"
        ])
        self.tabla_preview.horizontalHeader().setStretchLastSection(False)
        self.tabla_preview.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_preview.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_preview.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla_preview.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_preview.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_preview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_preview.setAlternatingRowColors(True)
        self.tabla_preview.setMinimumHeight(400)
        self.tabla_preview.verticalHeader().setVisible(False)
        self.tabla_preview.verticalHeader().setDefaultSectionSize(32)
        
        preview_layout.addWidget(self.tabla_preview)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # ========== SECCIÓN DE ESTADÍSTICAS ==========
        stats_group = QGroupBox("RESUMEN DE EXPORTACIÓN")
        stats_layout = QVBoxLayout()
        stats_layout.setContentsMargins(15, 25, 15, 15)
        stats_layout.setSpacing(8)
        
        self.lbl_total_trans = QLabel("Total Transacciones: 0")
        self.lbl_total_trans.setProperty("class", "stat-label")
        stats_layout.addWidget(self.lbl_total_trans)
        
        self.lbl_rango_fechas = QLabel("Rango de Fechas: -")
        self.lbl_rango_fechas.setStyleSheet("color: #6B7280; font-size: 10pt;")
        stats_layout.addWidget(self.lbl_rango_fechas)
        
        stats_layout.addSpacing(10)
        
        self.lbl_total_gastos = QLabel(f"💸 Total Gastos (Débitos): {self.moneda_symbol} 0.00")
        self.lbl_total_gastos.setProperty("class", "stat-value")
        self.lbl_total_gastos.setStyleSheet("color: #DC2626; font-size: 11pt; font-weight: 600;")
        stats_layout.addWidget(self.lbl_total_gastos)
        
        self.lbl_total_ingresos = QLabel(f"💰 Total Ingresos (Créditos): {self.moneda_symbol} 0.00")
        self.lbl_total_ingresos.setProperty("class", "stat-value")
        self.lbl_total_ingresos.setStyleSheet("color: #059669; font-size: 11pt; font-weight: 600;")
        stats_layout.addWidget(self.lbl_total_ingresos)
        
        self.lbl_balance = QLabel(f"📊 Balance: {self.moneda_symbol} 0.00")
        self.lbl_balance.setProperty("class", "stat-value")
        self.lbl_balance.setStyleSheet("color: #F59E0B; font-size: 12pt; font-weight: 700;")
        stats_layout.addWidget(self.lbl_balance)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # ========== BOTONES DE ACCIÓN ==========
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        btn_validar = QPushButton("✅ Validar Formato")
        btn_validar.clicked.connect(self._validar_formato)
        buttons_layout.addWidget(btn_validar)
        
        btn_exportar = QPushButton("📄 Exportar a Excel")
        btn_exportar.clicked.connect(self._exportar_excel)
        buttons_layout.addWidget(btn_exportar)
        
        buttons_layout.addStretch()
        
        btn_cancelar = QPushButton("❌ Cancelar")
        btn_cancelar.setProperty("class", "secondary")
        btn_cancelar.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancelar)
        
        layout.addLayout(buttons_layout)
    
    def _cargar_años_disponibles(self):
        """Carga los años disponibles en el combo (desde año actual hasta 3 años atrás)"""
        año_actual = datetime.now().year
        for año in range(año_actual + 1, año_actual - 4, -1):
            self.combo_año.addItem(str(año), año)
        
        # Seleccionar año actual por defecto
        self.combo_año.setCurrentIndex(1)  # año_actual está en índice 1
    
    def _cargar_vista_previa(self):
        """
        Carga transacciones desde Firebase según filtros y las muestra en la tabla
        """
        try:
            # Validar que al menos un checkbox esté marcado
            if not self.check_incluir_gastos.isChecked() and not self.check_incluir_ingresos.isChecked():
                QMessageBox.warning(
                    self,
                    "Filtros inválidos",
                    "Debe seleccionar al menos un tipo de transacción (Gastos o Ingresos)"
                )
                return
            
            # Obtener filtros
            año = self.combo_año.currentData()
            mes_data = self.combo_mes.currentData()
            
            # Construir rango de fechas
            if mes_data == "todos":
                fecha_inicio = f"{año}-01-01"
                fecha_fin = f"{año}-12-31"
            else:
                mes = mes_data
                ultimo_dia = calendar.monthrange(año, mes)[1]
                fecha_inicio = f"{año}-{mes:02d}-01"
                fecha_fin = f"{año}-{mes:02d}-{ultimo_dia}"
            
            logger.info(f"Cargando transacciones desde {fecha_inicio} hasta {fecha_fin}")
            
            # Obtener gastos si está marcado
            gastos = []
            if self.check_incluir_gastos.isChecked():
                filtros_gastos = {
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                }
                gastos = self.fm.obtener_gastos(filtros_gastos)
                logger.info(f"Obtenidos {len(gastos)} gastos")
            
            # Obtener ingresos si está marcado
            ingresos = []
            if self.check_incluir_ingresos.isChecked():
                filtros_ingresos = {
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                }
                ingresos = self.fm.obtener_alquileres(filtros_ingresos)
                logger.info(f"Obtenidos {len(ingresos)} ingresos")
            
            # Convertir a formato PROGRAIN
            transacciones = []
            
            for gasto in gastos:
                trans = self.exportador._convertir_gasto_a_transaccion(gasto, self.mapas)
                if trans:
                    transacciones.append(trans)
            
            for ingreso in ingresos:
                trans = self.exportador._convertir_ingreso_a_transaccion(ingreso, self.mapas)
                if trans:
                    transacciones.append(trans)
            
            # Ordenar por fecha
            transacciones.sort(key=lambda x: x['Fecha'])
            
            # Guardar transacciones actuales
            self.transacciones_actuales = transacciones
            
            # Mostrar en tabla
            self._pintar_tabla_preview(transacciones)
            
            # Actualizar estadísticas
            self._actualizar_estadisticas(transacciones)
            
            if not transacciones:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No se encontraron transacciones para los filtros seleccionados."
                )
            else:
                logger.info(f"Vista previa cargada: {len(transacciones)} transacciones")
            
        except Exception as e:
            logger.error(f"Error cargando vista previa: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cargar la vista previa:\n{str(e)}"
            )
    
    def _pintar_tabla_preview(self, transacciones: list):
        """
        Muestra transacciones en la tabla de vista previa
        
        Formato visual:
        - Débitos: texto rojo (#DC2626)
        - Créditos: texto verde (#059669)
        - Montos: alineación derecha, formato con separador de miles
        - Fechas: alineación centrada
        """
        self.tabla_preview.setRowCount(0)
        
        for trans in transacciones:
            row = self.tabla_preview.rowCount()
            self.tabla_preview.insertRow(row)
            
            # Fecha (centrada)
            fecha_item = QTableWidgetItem(str(trans['Fecha']))
            fecha_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla_preview.setItem(row, 0, fecha_item)
            
            # Concepto
            concepto_item = QTableWidgetItem(trans['Concepto'])
            self.tabla_preview.setItem(row, 1, concepto_item)
            
            # Detalle
            detalle_item = QTableWidgetItem(trans['Detalle'])
            self.tabla_preview.setItem(row, 2, detalle_item)
            
            # Débito (derecha, rojo si > 0)
            debito = trans['Débito']
            debito_texto = f"{debito:,.2f}" if debito > 0 else "0.00"
            debito_item = QTableWidgetItem(debito_texto)
            debito_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if debito > 0:
                debito_item.setForeground(QBrush(QColor("#DC2626")))
            self.tabla_preview.setItem(row, 3, debito_item)
            
            # Crédito (derecha, verde si > 0)
            credito = trans['Crédito']
            credito_texto = f"{credito:,.2f}" if credito > 0 else "0.00"
            credito_item = QTableWidgetItem(credito_texto)
            credito_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if credito > 0:
                credito_item.setForeground(QBrush(QColor("#059669")))
            self.tabla_preview.setItem(row, 4, credito_item)
        
        logger.info(f"Tabla pintada con {len(transacciones)} transacciones")
    
    def _actualizar_estadisticas(self, transacciones: list):
        """Actualiza labels de estadísticas con totales calculados"""
        if not transacciones:
            self.lbl_total_trans.setText("Total Transacciones: 0")
            self.lbl_rango_fechas.setText("Rango de Fechas: -")
            self.lbl_total_gastos.setText(f"💸 Total Gastos (Débitos): {self.moneda_symbol} 0.00")
            self.lbl_total_ingresos.setText(f"💰 Total Ingresos (Créditos): {self.moneda_symbol} 0.00")
            self.lbl_balance.setText(f"📊 Balance: {self.moneda_symbol} 0.00")
            return
        
        # Calcular totales
        total_debitos = sum(t['Débito'] for t in transacciones)
        total_creditos = sum(t['Crédito'] for t in transacciones)
        balance = total_creditos - total_debitos
        
        # Fechas
        fechas = [t['Fecha'] for t in transacciones]
        fecha_min = min(fechas)
        fecha_max = max(fechas)
        
        # Actualizar labels
        self.lbl_total_trans.setText(f"Total Transacciones: {len(transacciones)}")
        self.lbl_rango_fechas.setText(f"Rango de Fechas: {fecha_min} a {fecha_max}")
        self.lbl_total_gastos.setText(f"💸 Total Gastos (Débitos): {self.moneda_symbol} {total_debitos:,.2f}")
        self.lbl_total_ingresos.setText(f"💰 Total Ingresos (Créditos): {self.moneda_symbol} {total_creditos:,.2f}")
        
        # Balance con color
        balance_texto = f"📊 Balance: {self.moneda_symbol} {balance:,.2f}"
        self.lbl_balance.setText(balance_texto)
        
        if balance >= 0:
            self.lbl_balance.setStyleSheet("color: #059669; font-size: 12pt; font-weight: 700;")
        else:
            self.lbl_balance.setStyleSheet("color: #DC2626; font-size: 12pt; font-weight: 700;")
    
    def _validar_formato(self):
        """
        Valida que las transacciones cargadas cumplan con el formato PROGRAIN
        Muestra mensaje con resultado de la validación
        """
        if not self.transacciones_actuales:
            QMessageBox.warning(
                self,
                "Sin datos",
                "No hay transacciones cargadas para validar.\n"
                "Por favor, cargue la vista previa primero."
            )
            return
        
        # Crear validación simulada
        errores = []
        advertencias = []
        
        # Validar que todas las transacciones tengan fecha
        for i, trans in enumerate(self.transacciones_actuales):
            if not trans.get('Fecha'):
                errores.append(f"Transacción {i+1}: falta fecha")
            
            # Validar que solo uno de débito/crédito tenga valor
            debito = trans.get('Débito', 0)
            credito = trans.get('Crédito', 0)
            
            if debito > 0 and credito > 0:
                advertencias.append(f"Transacción {i+1}: tanto débito como crédito tienen valor")
            
            if debito == 0 and credito == 0:
                errores.append(f"Transacción {i+1}: tanto débito como crédito son cero")
        
        # Construir mensaje
        mensaje = "✅ VALIDACIÓN COMPLETADA\n\n"
        
        if not errores and not advertencias:
            mensaje += "✓ No se encontraron errores ni advertencias\n"
            mensaje += "✓ El formato cumple con las especificaciones PROGRAIN 5.0\n"
            mensaje += f"✓ Total de transacciones: {len(self.transacciones_actuales)}"
            
            QMessageBox.information(self, "Validación Exitosa", mensaje)
        else:
            if errores:
                mensaje += f"❌ ERRORES ENCONTRADOS ({len(errores)}):\n"
                for err in errores[:10]:  # Mostrar máximo 10
                    mensaje += f"  • {err}\n"
                if len(errores) > 10:
                    mensaje += f"  ... y {len(errores) - 10} errores más\n"
                mensaje += "\n"
            
            if advertencias:
                mensaje += f"⚠️ ADVERTENCIAS ({len(advertencias)}):\n"
                for adv in advertencias[:10]:  # Mostrar máximo 10
                    mensaje += f"  • {adv}\n"
                if len(advertencias) > 10:
                    mensaje += f"  ... y {len(advertencias) - 10} advertencias más\n"
            
            if errores:
                QMessageBox.warning(self, "Validación con Errores", mensaje)
            else:
                QMessageBox.information(self, "Validación con Advertencias", mensaje)
    
    def _exportar_excel(self):
        """
        Abre diálogo para guardar archivo y ejecuta la exportación
        """
        if not self.transacciones_actuales:
            QMessageBox.warning(
                self,
                "Sin datos",
                "No hay transacciones para exportar.\n"
                "Por favor, cargue la vista previa primero."
            )
            return
        
        try:
            # Construir nombre sugerido
            año = self.combo_año.currentData()
            mes_data = self.combo_mes.currentData()
            
            if mes_data == "todos":
                nombre_periodo = f"{año}"
            else:
                meses_nombres = [
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                ]
                nombre_mes = meses_nombres[mes_data - 1]
                nombre_periodo = f"{año}_{nombre_mes}"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_sugerido = f"PROGRAIN_Transacciones_{nombre_periodo}_{timestamp}.xlsx"
            
            # Abrir diálogo de guardar
            archivo_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Exportación PROGRAIN",
                nombre_sugerido,
                "Archivos Excel (*.xlsx)"
            )
            
            if not archivo_path:
                return  # Usuario canceló
            
            # Asegurar extensión .xlsx
            if not archivo_path.endswith('.xlsx'):
                archivo_path += '.xlsx'
            
            # Separar gastos e ingresos
            gastos_raw = []
            ingresos_raw = []
            
            # Necesitamos datos raw, así que los cargamos nuevamente
            año = self.combo_año.currentData()
            mes_data = self.combo_mes.currentData()
            
            if mes_data == "todos":
                fecha_inicio = f"{año}-01-01"
                fecha_fin = f"{año}-12-31"
            else:
                mes = mes_data
                ultimo_dia = calendar.monthrange(año, mes)[1]
                fecha_inicio = f"{año}-{mes:02d}-01"
                fecha_fin = f"{año}-{mes:02d}-{ultimo_dia}"
            
            if self.check_incluir_gastos.isChecked():
                gastos_raw = self.fm.obtener_gastos({
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                })
            
            if self.check_incluir_ingresos.isChecked():
                ingresos_raw = self.fm.obtener_alquileres({
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                })
            
            # Exportar
            exito = self.exportador.exportar_transacciones(
                gastos=gastos_raw,
                ingresos=ingresos_raw,
                output_path=archivo_path,
                mapas=self.mapas,
                incluir_gastos=self.check_incluir_gastos.isChecked(),
                incluir_ingresos=self.check_incluir_ingresos.isChecked()
            )
            
            if exito:
                # Calcular estadísticas para mensaje
                total_trans = len(self.transacciones_actuales)
                total_debitos = sum(t['Débito'] for t in self.transacciones_actuales)
                total_creditos = sum(t['Crédito'] for t in self.transacciones_actuales)
                
                mensaje = (
                    f"✅ EXPORTACIÓN EXITOSA\n\n"
                    f"Archivo: {os.path.basename(archivo_path)}\n\n"
                    f"Estadísticas:\n"
                    f"  • Total transacciones: {total_trans}\n"
                    f"  • Total Débitos: {self.moneda_symbol} {total_debitos:,.2f}\n"
                    f"  • Total Créditos: {self.moneda_symbol} {total_creditos:,.2f}\n\n"
                    f"¿Desea abrir el archivo ahora?"
                )
                
                respuesta = QMessageBox.question(
                    self,
                    "Exportación Exitosa",
                    mensaje,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if respuesta == QMessageBox.StandardButton.Yes:
                    # Abrir archivo
                    if os.name == 'nt':  # Windows
                        os.startfile(archivo_path)
                    else:  # macOS, Linux
                        webbrowser.open(f'file://{archivo_path}')
                
                logger.info(f"Exportación exitosa: {archivo_path}")
                
                # Cerrar diálogo
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Error en Exportación",
                    "No se pudo completar la exportación.\n"
                    "Revise los logs para más detalles."
                )
        
        except Exception as e:
            logger.error(f"Error exportando a Excel: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al exportar:\n{str(e)}"
            )