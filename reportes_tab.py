"""
Tab de Reportes para EQUIPOS 4.0
Permite generar reportes PDF de alquileres, operadores y estados de cuenta
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit, 
    QPushButton, QFileDialog, QMessageBox, QSpacerItem, QSizePolicy, QGroupBox
)
from PyQt6.QtCore import QDate
from datetime import datetime
import logging

from report_generator import ReportGenerator
from firebase_manager import FirebaseManager # Asegúrate de importar FirebaseManager
from storage_manager import StorageManager # Asegúrate de importar StorageManager

logger = logging.getLogger(__name__)


class ReportesTab(QWidget):
    """
    Tab para generación de reportes PDF.
    """
    
    def __init__(self, firebase_manager: FirebaseManager, storage_manager: StorageManager = None, 
                 clientes_mapa=None, operadores_mapa=None, equipos_mapa=None, parent=None):
        """
        Inicializa el tab de reportes.
        """
        super().__init__(parent)
        self.fm = firebase_manager
        self.sm = storage_manager
        self.clientes_mapa = clientes_mapa or {}
        self.operadores_mapa = operadores_mapa or {}
        self.equipos_mapa = equipos_mapa or {}
        
        self._setup_ui()
        self._cargar_filtros()
    
    def _setup_ui(self):
        """Configura la interfaz del tab."""
        layout = QVBoxLayout(self)
        
        # Grupo de filtros
        filtros_group = QGroupBox("Filtros de Reporte")
        filtros_layout = QVBoxLayout()
        
        # Primera fila: Cliente, Operador, Equipo
        fila1 = QHBoxLayout()
        fila1.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.setMinimumWidth(200)
        fila1.addWidget(self.combo_cliente)
        
        fila1.addWidget(QLabel("Operador:"))
        self.combo_operador = QComboBox()
        self.combo_operador.setMinimumWidth(200)
        fila1.addWidget(self.combo_operador)
        
        fila1.addWidget(QLabel("Equipo:"))
        self.combo_equipo = QComboBox()
        self.combo_equipo.setMinimumWidth(200)
        fila1.addWidget(self.combo_equipo)
        
        fila1.addStretch()
        filtros_layout.addLayout(fila1)
        
        # Segunda fila: Fechas
        fila2 = QHBoxLayout()
        fila2.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        fila2.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setCalendarPopup(True)
        # Fecha inicial se establecerá dinámicamente en _actualizar_fecha_desde()
        self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        fila2.addWidget(self.fecha_inicio)
        
        fila2.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit()
        self.fecha_fin.setCalendarPopup(True)
        # Fecha "Hasta" siempre es la fecha actual
        self.fecha_fin.setDate(QDate.currentDate())
        self.fecha_fin.setDisplayFormat("yyyy-MM-dd")
        fila2.addWidget(self.fecha_fin)
        
        fila2.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        filtros_layout.addLayout(fila2)
        
        filtros_group.setLayout(filtros_layout)
        layout.addWidget(filtros_group)
        
        # Grupo de botones de reportes
        reportes_group = QGroupBox("Generar Reportes")
        botones_layout = QVBoxLayout()
        
        # Fila 1: Reporte Detallado
        fila_detallado = QHBoxLayout()
        self.btn_detallado_pdf = QPushButton("📄 Reporte Detallado de Alquileres (PDF)")
        self.btn_detallado_pdf.setMinimumHeight(40)
        self.btn_detallado_pdf.clicked.connect(self.generar_reporte_detallado_pdf)
        fila_detallado.addWidget(self.btn_detallado_pdf)
        botones_layout.addLayout(fila_detallado)
        
        # Fila 2: Reporte Operadores
        fila_operadores = QHBoxLayout()
        self.btn_operadores_pdf = QPushButton("👷 Reporte de Horas por Operador (PDF)")
        self.btn_operadores_pdf.setMinimumHeight(40)
        self.btn_operadores_pdf.clicked.connect(self.generar_reporte_operadores_pdf)
        fila_operadores.addWidget(self.btn_operadores_pdf)
        botones_layout.addLayout(fila_operadores)
        
        # Fila 3: Estado de Cuenta
        fila_estado = QHBoxLayout()
        self.btn_estado_cuenta_pdf = QPushButton("💰 Estado de Cuenta de Cliente (PDF)")
        self.btn_estado_cuenta_pdf.setMinimumHeight(40)
        self.btn_estado_cuenta_pdf.clicked.connect(self.generar_estado_cuenta_cliente_pdf)
        fila_estado.addWidget(self.btn_estado_cuenta_pdf)
        botones_layout.addLayout(fila_estado)
        
        reportes_group.setLayout(botones_layout)
        layout.addWidget(reportes_group)
        
        # Spacer al final
        layout.addStretch()
    
    def _cargar_filtros(self):
        """Carga los combos de filtros con datos."""
        # Cargar clientes
        self.combo_cliente.clear()
        self.combo_cliente.addItem("Todos", None)
        for id_cliente, nombre in sorted(self.clientes_mapa.items(), key=lambda x: x[1]):
            self.combo_cliente.addItem(nombre, id_cliente)
        
        # Cargar operadores
        self.combo_operador.clear()
        self.combo_operador.addItem("Todos", None)
        for id_operador, nombre in sorted(self.operadores_mapa.items(), key=lambda x: x[1]):
            self.combo_operador.addItem(nombre, id_operador)
        
        # Cargar equipos
        self.combo_equipo.clear()
        self.combo_equipo.addItem("Todos", None)
        for id_equipo, nombre in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
            self.combo_equipo.addItem(nombre, id_equipo)
        
        # Conectar señales para actualizar fechas dinámicamente
        self.combo_cliente.currentIndexChanged.connect(self._actualizar_fecha_desde)
        self.combo_equipo.currentIndexChanged.connect(self._actualizar_fecha_desde)
        self.combo_operador.currentIndexChanged.connect(self._actualizar_fecha_desde)
        
        # Inicializar fechas
        self._actualizar_fecha_desde()
    
    def _actualizar_fecha_desde(self):
        """
        Actualiza la fecha "Desde" dinámicamente basándose en el filtro seleccionado.
        
        Prioridad:
        1. Si hay un cliente seleccionado, usa la fecha de su primera transacción
        2. Si hay un equipo seleccionado, usa la fecha de su primera transacción
        3. Si hay un operador seleccionado, usa la fecha de su primera transacción
        4. Si todos están en "Todos", usa la fecha de la primera transacción general de alquileres
        """
        try:
            primera_fecha_str = None
            
            # Verificar cliente
            cliente_id = self.combo_cliente.currentData()
            if cliente_id:
                primera_fecha_str = self.fm.obtener_fecha_primera_transaccion_cliente(str(cliente_id))
                logger.info(f"Fecha desde actualizada por cliente {cliente_id}: {primera_fecha_str}")
            
            # Si no hay cliente específico, verificar equipo
            elif self.combo_equipo.currentData():
                equipo_id = self.combo_equipo.currentData()
                primera_fecha_str = self.fm.obtener_fecha_primera_transaccion_equipo(str(equipo_id))
                logger.info(f"Fecha desde actualizada por equipo {equipo_id}: {primera_fecha_str}")
            
            # Si no hay equipo específico, verificar operador
            elif self.combo_operador.currentData():
                operador_id = self.combo_operador.currentData()
                primera_fecha_str = self.fm.obtener_fecha_primera_transaccion_operador(str(operador_id))
                logger.info(f"Fecha desde actualizada por operador {operador_id}: {primera_fecha_str}")
            
            # Si todos están en "Todos", usar primera transacción general
            else:
                primera_fecha_str = self.fm.obtener_fecha_primera_transaccion_alquileres()
                logger.info(f"Fecha desde actualizada con primera transacción general: {primera_fecha_str}")
            
            # Aplicar la fecha obtenida
            if primera_fecha_str:
                primera_fecha = QDate.fromString(primera_fecha_str, "yyyy-MM-dd")
                self.fecha_inicio.setDate(primera_fecha)
            else:
                # Si no hay datos, usar un mes atrás como default
                self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
                logger.warning("No hay datos para el filtro seleccionado, usando fecha por defecto")
            
            # La fecha "Hasta" siempre es la fecha actual
            self.fecha_fin.setDate(QDate.currentDate())
            
        except Exception as e:
            logger.error(f"Error al actualizar fecha desde: {e}", exc_info=True)
            # En caso de error, usar fechas por defecto
            self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
            self.fecha_fin.setDate(QDate.currentDate())
    
    def _get_current_filters(self):
        """
        Obtiene los filtros actuales seleccionados.
        ¡CORREGIDO (V8)! Convierte IDs a int.
        
        Returns:
            dict: Filtros para consultar Firebase
        """
        filtros = {
            'fecha_inicio': self.fecha_inicio.date().toString("yyyy-MM-dd"),
            'fecha_fin': self.fecha_fin.date().toString("yyyy-MM-dd")
        }
        
        # --- ¡INICIO DE CORRECCIÓN (V8)! ---
        # Cliente
        cliente_id_str = self.combo_cliente.currentData()
        if cliente_id_str:
            filtros['cliente_id'] = int(cliente_id_str)
        
        # Operador
        operador_id_str = self.combo_operador.currentData()
        if operador_id_str:
            filtros['operador_id'] = int(operador_id_str)
        
        # Equipo
        equipo_id_str = self.combo_equipo.currentData()
        if equipo_id_str:
            filtros['equipo_id'] = int(equipo_id_str)
        # --- FIN DE CORRECCIÓN (V8)! ---
        
        return filtros
    
    def generar_reporte_detallado_pdf(self):
        """Genera reporte detallado de alquileres en PDF."""
        try:
            filtros = self._get_current_filters()
            
            # Obtener alquileres desde Firebase
            alquileres = self.fm.obtener_alquileres(filtros)
            
            if not alquileres:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No hay alquileres para el período/filtros seleccionados."
                )
                return
            
            # Convertir a formato para el reporte
            data_reporte = []
            for alq in alquileres:
                # Convertir IDs a nombres
                try:
                    equipo_id = str(int(alq.get('equipo_id', 0)))
                except (ValueError, TypeError):
                    equipo_id = "0"
                
                try:
                    cliente_id = str(int(alq.get('cliente_id', 0)))
                except (ValueError, TypeError):
                    cliente_id = "0"
                
                try:
                    operador_id = str(int(alq.get('operador_id', 0)))
                except (ValueError, TypeError):
                    operador_id = "0"
                
                data_reporte.append({
                    'Fecha': alq.get('fecha', ''),
                    'Conduce': alq.get('conduce', ''),
                    'Equipo': self.equipos_mapa.get(equipo_id, 'Desconocido'),
                    'Cliente': self.clientes_mapa.get(cliente_id, 'Desconocido'),
                    'Operador': self.operadores_mapa.get(operador_id, 'Desconocido'),
                    'Ubicación': alq.get('ubicacion', ''),
                    'Horas': alq.get('horas', 0),
                    'Monto': alq.get('monto', 0),
                    'CondStorage': alq.get('conduce_storage_path', '')
                })
            
            # Nombre del cliente para el reporte
            cliente_selec = self.combo_cliente.currentText()
            
            # Mapeo de columnas para el reporte
            column_map = {
                'Fecha': 'Fecha',
                'Conduce': 'Conduce',
                'Equipo': 'Equipo',
                'Ubicación': 'Ubicación',
                'Horas': 'Horas',
                'Monto': 'Monto',
                'CondStorage': 'CondStorage'
            }
            
            # Crear generador de reporte
            date_range = f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"
            rg = ReportGenerator(
                data=data_reporte,
                title="REPORTE DETALLADO DE ALQUILERES",
                cliente=cliente_selec,
                date_range=date_range,
                currency_symbol="RD$",
                storage_manager=self.sm,
                column_map=column_map
            )
            
            # Seleccionar ubicación para guardar
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte Detallado",
                f"Reporte_Detallado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "PDF (*.pdf)"
            )
            
            if not file_path:
                return
            
            # Generar PDF
            ok, mensaje = rg.to_pdf(file_path)
            
            if ok:
                QMessageBox.information(self, "Éxito", mensaje)
            else:
                QMessageBox.critical(self, "Error", mensaje)
                
        except Exception as e:
            logger.error(f"Error al generar reporte detallado: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo generar el reporte:\n{str(e)}"
            )
    
    def generar_reporte_operadores_pdf(self):
        """Genera reporte de horas por operador en PDF."""
        try:
            filtros = self._get_current_filters()
            
            # Obtener alquileres
            alquileres = self.fm.obtener_alquileres(filtros)
            
            if not alquileres:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No hay alquileres para el período/filtros seleccionados."
                )
                return
            
            # Agrupar por operador
            operadores_horas = {}
            for alq in alquileres:
                try:
                    operador_id = str(int(alq.get('operador_id', 0)))
                except (ValueError, TypeError):
                    operador_id = "0"

                if operador_id != "0":
                    nombre_op = self.operadores_mapa.get(operador_id, f'ID: {operador_id}')
                    horas = float(alq.get('horas', 0))
                    
                    if nombre_op not in operadores_horas:
                        operadores_horas[nombre_op] = 0
                    operadores_horas[nombre_op] += horas
            
            # Convertir a lista
            data_reporte = [
                {'Operador': nombre, 'Total Horas': horas}
                for nombre, horas in sorted(operadores_horas.items(), key=lambda x: x[1], reverse=True)
            ]
            
            if not data_reporte:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No hay datos de operadores para el período seleccionado."
                )
                return
            
            # Crear reporte
            date_range = f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"
            rg = ReportGenerator(
                data=data_reporte,
                title="REPORTE DE HORAS POR OPERADOR",
                cliente="",
                date_range=date_range,
                currency_symbol="RD$",
                storage_manager=None,
                column_map={'Operador': 'Operador', 'Total Horas': 'Total Horas'}
            )
            
            # Guardar
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte de Operadores",
                f"Reporte_Operadores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "PDF (*.pdf)"
            )
            
            if not file_path:
                return
            
            ok, mensaje = rg.to_pdf(file_path)
            
            if ok:
                QMessageBox.information(self, "Éxito", mensaje)
            else:
                QMessageBox.critical(self, "Error", mensaje)
                
        except Exception as e:
            logger.error(f"Error al generar reporte de operadores: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo generar el reporte:\n{str(e)}"
            )
    
    def generar_estado_cuenta_cliente_pdf(self):
        """Genera estado de cuenta de un cliente en PDF."""
        cliente_nombre = self.combo_cliente.currentText()
        
        if cliente_nombre == "Todos":
            QMessageBox.warning(
                self,
                "Cliente Requerido",
                "Por favor, seleccione un cliente específico para el estado de cuenta."
            )
            return
        
        self.generar_reporte_detallado_pdf()  # Usa el mismo formato que el detallado