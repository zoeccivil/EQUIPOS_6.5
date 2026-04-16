from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
    QFileDialog, QWidget, QSizePolicy, QSpacerItem, QStyle
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from typing import Dict, Any, List, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EstadoCuentaDialog(QDialog):
    """
    Estado de Cuenta (Firebase)
    - Permite generar estado de cuenta por cliente o general (Todos).
    - Filtros: Cliente, Equipo, Operador, Fecha desde/hasta.
    - Al elegir cliente, 'Desde' se fija en la primera transacción de ese cliente; 'Hasta' = hoy.
    - Preview en pantalla:
        * Tabla de facturas (alquileres)
        * Tabla de abonos agrupados por fecha
        * Resumen: total facturado, total abonado y saldo
    - get_filtros() devuelve cliente/equipo/operador y rango de fechas.

    Notas sobre índices en Firestore:
    - Para consultas por cliente_id + rango de fecha: crear índice compuesto (cliente_id ASC, fecha ASC).
    - Si además filtras por equipo_id y/o operador_id (opcionales), podrías necesitar índices adicionales:
      * cliente_id + fecha + equipo_id
      * cliente_id + fecha + operador_id
      * fecha + equipo_id
      * fecha + operador_id
    Ajusta según tus consultas reales en FirebaseManager.
    """

    def __init__(self, firebase_manager, parent=None, currency_symbol: str = "RD$",
                 cliente_id: str = None):
        super().__init__(parent)
        self.setWindowTitle("Estado de Cuenta")
        self.setMinimumWidth(900)
        self.firebase_manager = firebase_manager
        self.currency_symbol = currency_symbol or "RD$"
        self._preselect_cliente_id = str(cliente_id) if cliente_id else None

        # Mapas para mostrar nombres en preview
        self.clientes_mapa: Dict[str, str] = {}
        self.equipos_mapa: Dict[str, str] = {}
        self.operadores_mapa: Dict[str, str] = {}

        self._build_ui()
        self._cargar_listas()
        self._conectar_eventos()

        # Pre-seleccionar cliente si se proporcionó
        if self._preselect_cliente_id:
            for i in range(self.combo_cliente.count()):
                if self.combo_cliente.itemData(i) == self._preselect_cliente_id:
                    self.combo_cliente.setCurrentIndex(i)
                    break

        # Selección inicial y preview
        self._ajustar_fechas_por_cliente()
        self._cargar_preview()

    # ------------------------ UI ------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Grupo filtros
        filtros_box = QGroupBox("Filtros")
        filtros_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #2a5adf;
                border: 1px solid #2a5adf;
                border-radius: 6px;
                margin-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
            }
        """)
        filtros_layout = QHBoxLayout(filtros_box)

        # Cliente
        cliente_col = QVBoxLayout()
        cliente_col.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.setMinimumWidth(220)
        cliente_col.addWidget(self.combo_cliente)
        filtros_layout.addLayout(cliente_col)

        # Equipo
        equipo_col = QVBoxLayout()
        equipo_col.addWidget(QLabel("Equipo:"))
        self.combo_equipo = QComboBox()
        self.combo_equipo.setMinimumWidth(200)
        equipo_col.addWidget(self.combo_equipo)
        filtros_layout.addLayout(equipo_col)

        # Operador
        operador_col = QVBoxLayout()
        operador_col.addWidget(QLabel("Operador:"))
        self.combo_operador = QComboBox()
        self.combo_operador.setMinimumWidth(200)
        operador_col.addWidget(self.combo_operador)
        filtros_layout.addLayout(operador_col)

        # Fechas
        fechas_col = QVBoxLayout()
        fechas_fila = QHBoxLayout()
        fechas_fila.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        fechas_fila.addWidget(self.fecha_inicio)

        fechas_fila.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit(calendarPopup=True)
        self.fecha_fin.setDisplayFormat("yyyy-MM-dd")
        fechas_fila.addWidget(self.fecha_fin)
        fechas_col.addLayout(fechas_fila)

        filtros_layout.addLayout(fechas_col)
        layout.addWidget(filtros_box)

        # Barra de acciones
        acciones = QHBoxLayout()
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_generar = QPushButton("Generar Reporte")
        self.btn_generar.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))

        acciones.addWidget(self.btn_actualizar)
        acciones.addStretch()
        acciones.addWidget(self.btn_generar)
        acciones.addWidget(self.btn_cancelar)
        layout.addLayout(acciones)

        # Preview: Facturas
        facturas_box = QGroupBox("Facturas (Alquileres)")
        facturas_box.setStyleSheet("""
            QGroupBox { font-weight: bold; color: #1f7a1f; border: 1px solid #1f7a1f; border-radius: 6px; margin-top: 8px;}
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 6px;}
        """)
        v_fact = QVBoxLayout(facturas_box)
        self.tbl_facturas = QTableWidget(0, 7)
        self.tbl_facturas.setHorizontalHeaderLabels([
            "Fecha", "Cliente", "Equipo", "Operador", "Conduce", "Horas", "Monto"
        ])
        self.tbl_facturas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_facturas.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_facturas.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        v_fact.addWidget(self.tbl_facturas)
        layout.addWidget(facturas_box)

        # Preview: Abonos por fecha
        abonos_box = QGroupBox("Abonos agrupados por fecha")
        abonos_box.setStyleSheet("""
            QGroupBox { font-weight: bold; color: #a35d00; border: 1px solid #a35d00; border-radius: 6px; margin-top: 8px;}
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 6px;}
        """)
        v_abo = QVBoxLayout(abonos_box)
        self.tbl_abonos = QTableWidget(0, 2)
        self.tbl_abonos.setHorizontalHeaderLabels(["Fecha", "Total Abonado"])
        self.tbl_abonos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_abonos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_abonos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        v_abo.addWidget(self.tbl_abonos)
        layout.addWidget(abonos_box)

        # Resumen
        resumen = QHBoxLayout()
        self.lbl_total_facturas = QLabel("Total Facturas: 0.00")
        self.lbl_total_abonos = QLabel("Total Abonos: 0.00")
        self.lbl_saldo = QLabel("Saldo: 0.00")

        self.lbl_total_facturas.setStyleSheet("font-weight:bold; color:#1f7a1f;")
        self.lbl_total_abonos.setStyleSheet("font-weight:bold; color:#a35d00;")
        self.lbl_saldo.setStyleSheet("font-weight:bold; color:#b30000;")

        resumen.addStretch()
        resumen.addWidget(self.lbl_total_facturas)
        resumen.addSpacing(20)
        resumen.addWidget(self.lbl_total_abonos)
        resumen.addSpacing(20)
        resumen.addWidget(self.lbl_saldo)
        layout.addLayout(resumen)

    def _conectar_eventos(self):
        # Filtros reactivos
        self.combo_cliente.currentIndexChanged.connect(self._on_cliente_cambiado)
        self.combo_equipo.currentIndexChanged.connect(self._cargar_preview)
        self.combo_operador.currentIndexChanged.connect(self._cargar_preview)
        self.fecha_inicio.dateChanged.connect(self._cargar_preview)
        self.fecha_fin.dateChanged.connect(self._cargar_preview)

        # Botones
        self.btn_actualizar.clicked.connect(self._cargar_preview)
        self.btn_generar.clicked.connect(self.accept)
        self.btn_cancelar.clicked.connect(self.reject)

    # ------------------------ Datos combos ------------------------

    def _cargar_listas(self):
        """
        Carga clientes, equipos y operadores en los combos.
        Intenta activo=True y, si no hay resultados (porque en BD está 1/0),
        reintenta con activo=None (sin filtrar).
        Además rellena los mapas id->nombre para el preview.
        """
        # Clientes
        self.combo_cliente.blockSignals(True)
        self.combo_cliente.clear()
        self.combo_cliente.addItem("Todos", None)
        try:
            clientes = self.firebase_manager.obtener_entidades(tipo="Cliente", activo=True)
            if not clientes:
                logger.info("EstadoCuenta: clientes activo=True devolvió 0; reintentando con activo=None")
                clientes = self.firebase_manager.obtener_entidades(tipo="Cliente", activo=None)
        except Exception as e:
            logger.warning(f"EstadoCuenta: error obteniendo clientes: {e}")
            clientes = []

        self.clientes_mapa.clear()
        for cli in clientes:
            cid = str(cli.get("id"))
            nombre = cli.get("nombre", f"ID:{cid}")
            self.combo_cliente.addItem(nombre, cid)
            self.clientes_mapa[cid] = nombre
        self.combo_cliente.blockSignals(False)

        # Equipos
        self.combo_equipo.blockSignals(True)
        self.combo_equipo.clear()
        self.combo_equipo.addItem("Todos", None)
        try:
            equipos = self.firebase_manager.obtener_equipos(activo=True)
            if not equipos:
                logger.info("EstadoCuenta: equipos activo=True devolvió 0; reintentando con activo=None")
                equipos = self.firebase_manager.obtener_equipos(activo=None)
        except Exception as e:
            logger.warning(f"EstadoCuenta: error obteniendo equipos: {e}")
            equipos = []

        self.equipos_mapa.clear()
        for eq in equipos:
            eid = str(eq.get("id"))
            nombre = eq.get("nombre", f"ID:{eid}")
            self.combo_equipo.addItem(nombre, eid)
            self.equipos_mapa[eid] = nombre
        self.combo_equipo.blockSignals(False)

        # Operadores
        self.combo_operador.blockSignals(True)
        self.combo_operador.clear()
        self.combo_operador.addItem("Todos", None)
        try:
            operadores = self.firebase_manager.obtener_entidades(tipo="Operador", activo=True)
            if not operadores:
                logger.info("EstadoCuenta: operadores activo=True devolvió 0; reintentando con activo=None")
                operadores = self.firebase_manager.obtener_entidades(tipo="Operador", activo=None)
        except Exception as e:
            logger.warning(f"EstadoCuenta: error obteniendo operadores: {e}")
            operadores = []

        self.operadores_mapa.clear()
        for op in operadores:
            oid = str(op.get("id"))
            nombre = op.get("nombre", f"ID:{oid}")
            self.combo_operador.addItem(nombre, oid)
            self.operadores_mapa[oid] = nombre
        self.combo_operador.blockSignals(False)

        logger.info(f"EstadoCuenta: combos cargados -> clientes={len(self.clientes_mapa)}, equipos={len(self.equipos_mapa)}, operadores={len(self.operadores_mapa)}")

    # ------------------------ Lógica fechas ------------------------

    def _on_cliente_cambiado(self):
        self._ajustar_fechas_por_cliente()
        self._cargar_preview()

    def _ajustar_fechas_por_cliente(self):
        """
        Si hay cliente específico:
          - fecha_inicio = primera transacción de ese cliente
        Si es 'Todos':
          - intentar con primera transacción global; si no, último mes.
        fecha_fin = hoy.
        """
        cliente_id = self.combo_cliente.currentData()
        fecha_inicio_str = None

        try:
            if cliente_id:
                # Primera del cliente
                fecha_inicio_str = self.firebase_manager.obtener_fecha_primera_transaccion_cliente(cliente_id)
            else:
                # Primera global de alquileres
                fecha_inicio_str = self.firebase_manager.obtener_fecha_primera_transaccion_alquileres()
        except Exception as e:
            logger.warning(f"No se pudo obtener fecha inicial: {e}")

        if fecha_inicio_str:
            qd = QDate.fromString(fecha_inicio_str, "yyyy-MM-dd")
            if qd.isValid():
                self.fecha_inicio.setDate(qd)
            else:
                self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
        else:
            self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))

        self.fecha_fin.setDate(QDate.currentDate())

    # ------------------------ Preview ------------------------

    def _cargar_preview(self):
        """
        Carga facturas y abonos (agrupados por fecha) en las tablas y calcula totales.
        Usa FirebaseManager:
          - alquileres con filtros (cliente_id opcional, equipo_id/operador_id opcionales y rango de fechas)
          - abonos con cliente_id opcional y rango de fechas
        """
        filtros = self.get_filtros()
        cliente_id = filtros["cliente_id"]
        equipo_id = filtros["equipo_id"]
        operador_id = filtros["operador_id"]
        fecha_inicio = filtros["fecha_inicio"]
        fecha_fin = filtros["fecha_fin"]

        # 1) Facturas
        filtros_alq = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
        }
        if cliente_id:
            filtros_alq["cliente_id"] = cliente_id
        if equipo_id:
            filtros_alq["equipo_id"] = equipo_id
        if operador_id:
            filtros_alq["operador_id"] = operador_id

        try:
            facturas = self.firebase_manager.obtener_alquileres(filtros_alq)
        except Exception as e:
            logger.error(f"Error obteniendo facturas para preview: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"No se pudieron obtener las facturas:\n{e}")
            facturas = []

        # 2) Abonos (agrupados por fecha)
        try:
            abonos = self.firebase_manager.obtener_abonos(
                cliente_id=cliente_id,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
        except Exception as e:
            logger.error(f"Error obteniendo abonos para preview: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"No se pudieron obtener los abonos:\n{e}")
            abonos = []

        abonos_por_fecha = self._agrupar_abonos_por_fecha(abonos)

        # 3) Pintar preview
        self._pintar_facturas(facturas, cliente_id is None)
        self._pintar_abonos_por_fecha(abonos_por_fecha)

        total_fact = sum(float(x.get("monto", 0) or 0) for x in facturas)
        total_abono = sum(monto for (_, monto) in abonos_por_fecha)
        saldo = total_fact - total_abono

        self.lbl_total_facturas.setText(f"Total Facturas: {self.currency_symbol} {total_fact:,.2f}")
        self.lbl_total_abonos.setText(f"Total Abonos: {self.currency_symbol} {total_abono:,.2f}")
        self.lbl_saldo.setText(f"Saldo: {self.currency_symbol} {saldo:,.2f}")

    def _pintar_facturas(self, facturas: List[Dict[str, Any]], es_general: bool):
        """
        Llena la tabla de facturas.
        Si es_general=True, se muestra la columna de Cliente con nombre.
        """
        self.tbl_facturas.setRowCount(0)

        # Ajustar encabezados si es general (mostrar cliente)
        headers = ["Fecha", "Cliente", "Equipo", "Operador", "Conduce", "Horas", "Monto"] if es_general \
            else ["Fecha", "Equipo", "Operador", "Conduce", "Horas", "Monto"]
        col_cliente_incluida = es_general

        # Resetear columnas según headers
        self.tbl_facturas.setColumnCount(len(headers))
        self.tbl_facturas.setHorizontalHeaderLabels(headers)
        self.tbl_facturas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for row, f in enumerate(facturas):
            self.tbl_facturas.insertRow(row)

            fecha = f.get("fecha", "")
            equipo_id = str(f.get("equipo_id", "") or "")
            operador_id = str(f.get("operador_id", "") or "")
            cliente_id = str(f.get("cliente_id", "") or "")

            equipo_nombre = self.equipos_mapa.get(equipo_id, f"ID:{equipo_id}")
            operador_nombre = self.operadores_mapa.get(operador_id, f"ID:{operador_id}")
            cliente_nombre = self.clientes_mapa.get(cliente_id, f"ID:{cliente_id}")

            conduce = f.get("conduce", "") or ""
            horas = float(f.get("horas", 0) or 0)
            monto = float(f.get("monto", 0) or 0)

            c = 0
            self.tbl_facturas.setItem(row, c, QTableWidgetItem(str(fecha))); c += 1
            if col_cliente_incluida:
                self.tbl_facturas.setItem(row, c, QTableWidgetItem(cliente_nombre)); c += 1
            self.tbl_facturas.setItem(row, c, QTableWidgetItem(equipo_nombre)); c += 1
            self.tbl_facturas.setItem(row, c, QTableWidgetItem(operador_nombre)); c += 1
            self.tbl_facturas.setItem(row, c, QTableWidgetItem(conduce)); c += 1
            self.tbl_facturas.setItem(row, c, QTableWidgetItem(f"{horas:,.2f}")); c += 1
            self.tbl_facturas.setItem(row, c, QTableWidgetItem(f"{self.currency_symbol} {monto:,.2f}"))

    def _agrupar_abonos_por_fecha(self, abonos: List[Dict[str, Any]]) -> List[Tuple[str, float]]:
        """
        Agrupa abonos por fecha y devuelve una lista [(fecha, total_fecha)] ordenada por fecha asc.
        """
        acumulado: Dict[str, float] = {}
        for a in abonos:
            fecha = a.get("fecha")
            if not fecha:
                continue
            monto = float(a.get("monto", 0) or 0)
            acumulado[fecha] = acumulado.get(fecha, 0.0) + monto

        # Orden ascendente por fecha (YYYY-MM-DD)
        ordenado = sorted(acumulado.items(), key=lambda x: x[0])
        return ordenado

    def _pintar_abonos_por_fecha(self, abonos_por_fecha: List[Tuple[str, float]]):
        self.tbl_abonos.setRowCount(0)
        for row, (fecha, total) in enumerate(abonos_por_fecha):
            self.tbl_abonos.insertRow(row)
            self.tbl_abonos.setItem(row, 0, QTableWidgetItem(str(fecha)))
            self.tbl_abonos.setItem(row, 1, QTableWidgetItem(f"{self.currency_symbol} {total:,.2f}"))

    # ------------------------ Salida ------------------------

    def get_filtros(self) -> Dict[str, Any]:
        """
        Devuelve los filtros seleccionados. None significa "Todos" en cada combo.
        """
        cliente_id = self.combo_cliente.currentData()
        equipo_id = self.combo_equipo.currentData()
        operador_id = self.combo_operador.currentData()

        return {
            "cliente_nombre": self.combo_cliente.currentText(),
            "cliente_id": cliente_id,  # None = general
            "equipo_nombre": self.combo_equipo.currentText(),
            "equipo_id": equipo_id,    # None = todos
            "operador_nombre": self.combo_operador.currentText(),
            "operador_id": operador_id,  # None = todos
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
        }
    
    def accept(self):
        """
        Genera el PDF del Estado de Cuenta al hacer click en 'Generar Reporte'.
        Usa ReportGenerator con los datos del preview.
        """
        try:
            from PyQt6.QtWidgets import QFileDialog
            from report_generator import ReportGenerator
            import os

            # Obtener filtros
            filtros = self.get_filtros()
            cliente_nombre = filtros["cliente_nombre"]
            fecha_inicio = filtros["fecha_inicio"]
            fecha_fin = filtros["fecha_fin"]

            # Diálogo para guardar
            nombre_sugerido = f"Estado_Cuenta_{cliente_nombre.replace(' ', '_')}_{fecha_inicio}_a_{fecha_fin}.pdf"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Estado de Cuenta",
                nombre_sugerido,
                "PDF (*.pdf)"
            )

            if not file_path:
                return  # Usuario canceló

            # Preparar datos para ReportGenerator
            cliente_id = filtros["cliente_id"]
            equipo_id = filtros["equipo_id"]
            operador_id = filtros["operador_id"]

            # Obtener facturas
            filtros_alq = {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
            }
            if cliente_id:
                filtros_alq["cliente_id"] = cliente_id
            if equipo_id:
                filtros_alq["equipo_id"] = equipo_id
            if operador_id:
                filtros_alq["operador_id"] = operador_id

            facturas = self.firebase_manager.obtener_alquileres(filtros_alq) or []

            # Enriquecer facturas con nombres para el PDF
            for f in facturas:
                cid = str(f.get("cliente_id", "") or "")
                eid = str(f.get("equipo_id", "") or "")
                oid = str(f.get("operador_id", "") or "")
                
                f["cliente_nombre"] = self.clientes_mapa.get(cid, f"ID:{cid}")
                f["equipo_nombre"] = self.equipos_mapa.get(eid, f"ID:{eid}")
                f["operador_nombre"] = self.operadores_mapa.get(oid, f"ID:{oid}")

            # Obtener abonos
            abonos = self.firebase_manager.obtener_abonos(
                cliente_id=cliente_id,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            ) or []

            abonos_por_fecha = self._agrupar_abonos_por_fecha(abonos)

            # Calcular totales
            total_facturado = sum(float(x.get("monto", 0) or 0) for x in facturas)
            total_abonado = sum(monto for (_, monto) in abonos_por_fecha)
            saldo = total_facturado - total_abonado

            # --- Calcular horas y precio por hora por equipo ---
            from collections import defaultdict
            equipo_horas = defaultdict(float)
            equipo_monto = defaultdict(float)

            for f in facturas:
                nombre_equipo = f.get("equipo_nombre", "")
                horas = float(f.get("horas", 0) or 0)
                monto = float(f.get("monto", 0) or 0)
                equipo_horas[nombre_equipo] += horas
                equipo_monto[nombre_equipo] += monto

            horas_por_equipo = []
            precio_hora_equipo = []
            for nombre in sorted(equipo_horas.keys()):
                h = equipo_horas[nombre]
                m = equipo_monto[nombre]
                horas_por_equipo.append({"equipo_nombre": nombre, "horas": h})
                precio_hora_equipo.append({
                    "equipo_nombre": nombre,
                    "horas": h,
                    "monto": m,
                    "precio_hora": m / h if h > 0 else 0,
                })

            # Column map para el PDF
            es_general = (cliente_id is None)
            if es_general:
                column_map = {
                    "fecha": "Fecha",
                    "cliente_nombre": "Cliente",
                    "equipo_nombre": "Equipo",
                    "operador_nombre": "Operador",
                    "conduce": "Conduce",
                    "horas": "Horas",
                    "monto": "Monto",
                }
            else:
                column_map = {
                    "fecha": "Fecha",
                    "equipo_nombre": "Equipo",
                    "operador_nombre": "Operador",
                    "conduce": "Conduce",
                    "horas": "Horas",
                    "monto": "Monto",
                }

            # Crear ReportGenerator
            titulo = f"ESTADO DE CUENTA - {cliente_nombre.upper()}"
            date_range = f"{fecha_inicio} a {fecha_fin}"

            # Obtener storage_manager desde firebase_manager
            storage_manager = None
            if hasattr(self.firebase_manager, 'storage_manager'):
                storage_manager = self.firebase_manager.storage_manager
            elif hasattr(self, 'parent') and self.parent() and hasattr(self.parent(), 'sm'):
                storage_manager = self.parent().sm

            rg = ReportGenerator(
                data=facturas,
                title=titulo,
                cliente=cliente_nombre,
                date_range=date_range,
                currency_symbol=self.currency_symbol,
                storage_manager=storage_manager,
                column_map=column_map
            )

            # Asignar datos de abonos y totales
            rg.abonos = abonos
            rg.abonos_por_fecha = abonos_por_fecha
            rg.total_facturado = total_facturado
            rg.total_abonado = total_abonado
            rg.saldo = saldo
            rg.horas_por_equipo = horas_por_equipo
            rg.precio_hora_equipo = precio_hora_equipo

            # Generar PDF
            exito, error = rg.to_pdf(file_path)

            if exito:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Estado de cuenta generado exitosamente:\n{file_path}"
                )
                super().accept()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo generar el reporte:\n{error}"
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error",
                f"Error generando el estado de cuenta:\n{e}"
            )