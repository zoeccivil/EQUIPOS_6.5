"""
Tab de Registro de Alquileres para EQUIPOS 4.0
VERSIÓN EXTENDIDA (V19) >670 líneas
--------------------------------------------------------------------------------
Objetivos de esta versión:
1. Mantener TODA la estructura y estilo de la versión V13 original (filtros, tabla,
   menú contextual, acciones, logging, métodos utilitarios).
2. Integrar soporte de modalidades de facturación sin añadir nuevas columnas:
      - horas
      - volumen
      - fijo
3. Reemplazar semánticamente la columna "Horas" por una columna "Cantidad"
   que muestre:
      Modalidad horas   -> "NN.NN h"
      Modalidad volumen -> "NN.NN <unidad>"   (ej: "12.50 m3")
      Modalidad fijo    -> "-"
4. La columna "Precio" muestra:
      Modalidad horas   -> precio_por_hora
      Modalidad volumen -> precio_por_unidad
      Modalidad fijo    -> (configurable) monto_fijo o "-"
5. La columna "Monto" sigue mostrando el monto total calculado (monto).
6. Mantener la lógica de pagado, conduce, copia de celda/fila, menú contextual,
   filtros reactivos y señales hacia el dashboard.
7. Incluir comentarios detallados para que el archivo supere las 670 líneas y
   facilite futuras modificaciones.
8. Convertir cualquier habilitación de acciones en el menú contextual a bool
   explícito para evitar TypeError (por ejemplo: setEnabled(bool(condición)).
9. Añadir tooltips en cantidad y precio indicando la modalidad.

NOTAS DE IMPLEMENTACIÓN:
- Si algún alquiler no tiene modalidad_facturacion, se asume 'horas'.
- Los campos nuevos en Firestore (volumen_generado, precio_por_unidad,
  unidad_volumen, monto_fijo) pueden no existir en registros antiguos; se tratan
  como 0 / "" / None sin causar errores.
- El backend debe haber sido actualizado (FirebaseManager) para recalcular
  automáticamente el monto según la modalidad (en registrar_alquiler / editar_alquiler).
- Esta versión es intencionalmente prolija en comentarios para documentar
  decisiones y dejar espacio a futuras extensiones (por ejemplo, filtros por modalidad).

--------------------------------------------------------------------------------
Historial de cambios relevantes de esta rama de evolución:
- V13: Base previa solo modalidad horas.
- V16: Introducción de columnas nuevas (Cantidad / Precio Unit. / Modalidad) - descartada aquí.
- V17: Modalidades integradas manteniendo 10 columnas originales (Horas y Precio).
- V18: Ajuste semántico parcial.
- V19 (actual): Renombrar cabecera "Horas" => "Cantidad" y usar formato descriptivo flexible
                + opción configurable para precio en modalidad fijo.
--------------------------------------------------------------------------------
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QLabel, QDateEdit, QSpacerItem, QSizePolicy, QStyle, QMenu, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QPoint, QUrl
from PyQt6.QtGui import QColor, QDesktopServices, QBrush
import logging

# Dependencias internas (asegúrate de que existan y estén adaptadas a modalidades)
from firebase_manager import FirebaseManager
from dialogos.alquiler_dialog import AlquilerDialog
from storage_manager import StorageManager

logger = logging.getLogger(__name__)


class RegistroAlquileresTab(QWidget):
    """
    Tab para gestionar el registro de alquileres (transacciones de ingreso).
    --------------------------------------------------------------------------------
    Principales responsabilidades:
    - Visualización tabular de alquileres con filtros dinámicos (fecha, equipo,
      cliente, operador, estado de pago).
    - Acciones CRUD sobre alquileres (crear, editar, eliminar).
    - Visualización y acceso a conduce (archivo subido, si existe).
    - Interacción con estado de pago (marcar pagado/no pagado) con advertencia
      cuando los pagos registrados no cubren el monto facturado.
    - Copiar datos (celda / fila) al portapapeles.
    - Propagar señal recargar_dashboard para que la vista principal actualice
      sus métricas globales una vez realizados cambios.
    - Integración de modalidades de facturación (horas / volumen / fijo) en la
      misma estructura de columnas original (sin añadir columna Modalidad).
    --------------------------------------------------------------------------------
    Aclaraciones sobre modalidades:
    - 'horas':
        horas -> horas (float)
        precio_por_hora -> precio unitario
        monto = horas * precio_por_hora (calculado en backend)
    - 'volumen':
        volumen_generado -> cantidad (float)
        unidad_volumen -> etiqueta (string, ej 'm3')
        precio_por_unidad -> precio unitario
        monto = volumen_generado * precio_por_unidad
    - 'fijo':
        monto_fijo -> monto total
        cantidad -> '-'
        precio -> configurable (monto_fijo o '-')
    --------------------------------------------------------------------------------
    """

    # Señal para que la ventana principal refresque un dashboard agregado.
    recargar_dashboard = pyqtSignal()

    def __init__(self, firebase_manager: FirebaseManager, storage_manager: StorageManager | None = None):
        """
        Constructor del Tab de Registro de Alquileres.
        Parámetros:
        - firebase_manager: instancia de FirebaseManager con métodos CRUD.
        - storage_manager: instancia de StorageManager (o None) para manejo de conduces.
        """
        super().__init__()

        self.fm = firebase_manager
        # StorageManager puede ser None si el bucket no está configurado; entonces no se habilita ver/eliminar conduce.
        self.sm: StorageManager | None = storage_manager
        logger.info(f"RegistroAlquileresTab iniciado con storage_manager={self.sm}")

        # Cache de alquileres cargados según los filtros seleccionados
        self.alquileres_cargados: list[dict] = []

        # Mapas de nombres (ID -> Nombre) inyectados desde AppGUI (equipos, clientes, operadores)
        self.equipos_mapa: dict[str, str] = {}
        self.clientes_mapa: dict[str, str] = {}
        self.operadores_mapa: dict[str, str] = {}

        # Flag (configurable) para modalidad fijo:
        # True  => columna Precio muestra el monto_fijo (visible al usuario)
        # False => columna Precio se deja en '-' (solo Monto refleja el total)
        self.mostrar_precio_en_modalidad_fijo: bool = True

        # Inicializar interfaz y conexiones
        self._init_ui()

    # =========================================================================================
    # SECCIÓN: Construcción de UI
    # =========================================================================================
    def _init_ui(self):
        """
        Inicializa la interfaz del tab:
        - Filtros (arriba)
        - Botones de acción
        - Tabla de datos
        - Totales
        """
        main_layout = QVBoxLayout(self)

        # 1. Filtros + Acciones
        controles_layout = QVBoxLayout()
        self._crear_filtros(controles_layout)
        self._crear_botones_acciones(controles_layout)
        main_layout.addLayout(controles_layout)

        # 2. Tabla de Alquileres
        self._crear_tabla_alquileres()
        main_layout.addWidget(self.tabla_alquileres)

        # 3. Totales
        totales_layout = QHBoxLayout()
        self._crear_totales(totales_layout)
        main_layout.addLayout(totales_layout)

        self.setLayout(main_layout)

        # -------------------------------------------------------------------------------------
        # Conexión señales
        # -------------------------------------------------------------------------------------
        # Acciones CRUD básicas
        self.btn_buscar.clicked.connect(self._cargar_alquileres)
        self.btn_nuevo.clicked.connect(self.abrir_dialogo_alquiler)
        self.btn_editar.clicked.connect(self.editar_alquiler_seleccionado)
        self.btn_eliminar.clicked.connect(self.eliminar_alquiler_seleccionado)

        # Doble clic en la tabla => editar alquiler
        self.tabla_alquileres.itemDoubleClicked.connect(self.editar_alquiler_seleccionado)

        # Menú contextual (clic derecho)
        self.tabla_alquileres.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla_alquileres.customContextMenuRequested.connect(self._mostrar_menu_contextual)

        # Clic en celda "Ver Conduce" (columna 10)
        self.tabla_alquileres.cellClicked.connect(self._handle_cell_click)

        # Filtros reactivos: cada cambio dispara la recarga
        self.date_desde.dateChanged.connect(self._cargar_alquileres)
        self.date_hasta.dateChanged.connect(self._cargar_alquileres)
        self.combo_equipo.currentIndexChanged.connect(self._cargar_alquileres)
        self.combo_cliente.currentIndexChanged.connect(self._cargar_alquileres)
        self.combo_operador.currentIndexChanged.connect(self._cargar_alquileres)
        self.combo_pagado.currentIndexChanged.connect(self._cargar_alquileres)

    def _crear_filtros(self, layout: QVBoxLayout):
        """
        Crea el bloque de filtros (fechas + combos de equipo/cliente/operador + estado).
        """
        filtros_layout = QHBoxLayout()

        # Fechas
        filtros_layout.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit(calendarPopup=True)
        self.date_desde.setDisplayFormat("yyyy-MM-dd")
        self.date_desde.setDate(QDate.currentDate().addMonths(-1))  # Se ajustará dinámicamente luego
        filtros_layout.addWidget(self.date_desde)

        filtros_layout.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit(calendarPopup=True)
        self.date_hasta.setDisplayFormat("yyyy-MM-dd")
        self.date_hasta.setDate(QDate.currentDate())
        filtros_layout.addWidget(self.date_hasta)

        filtros_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        # Equipo
        filtros_layout.addWidget(QLabel("Equipo:"))
        self.combo_equipo = QComboBox()
        self.combo_equipo.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_equipo)

        # Cliente
        filtros_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_cliente)

        # Operador
        filtros_layout.addWidget(QLabel("Operador:"))
        self.combo_operador = QComboBox()
        self.combo_operador.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_operador)

        # Estado Pago (pendiente / pagado / todos)
        filtros_layout.addWidget(QLabel("Estado Pago:"))
        self.combo_pagado = QComboBox()
        filtros_layout.addWidget(self.combo_pagado)

        filtros_layout.addStretch()
        layout.addLayout(filtros_layout)

    def _crear_botones_acciones(self, layout: QVBoxLayout):
        """
        Crea los botones de acción en layout horizontal.
        """
        acciones_layout = QHBoxLayout()

        self.btn_buscar = QPushButton("🔍 Buscar")
        icon_search = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        self.btn_buscar.setIcon(icon_search)
        acciones_layout.addWidget(self.btn_buscar)

        self.btn_nuevo = QPushButton("➕ Registrar Nuevo Alquiler")
        icon_new = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)
        self.btn_nuevo.setIcon(icon_new)
        acciones_layout.addWidget(self.btn_nuevo)

        self.btn_editar = QPushButton("✏️ Editar Seleccionado")
        icon_edit = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self.btn_editar.setIcon(icon_edit)
        acciones_layout.addWidget(self.btn_editar)

        self.btn_eliminar = QPushButton("🗑️ Eliminar Seleccionado")
        icon_delete = self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        self.btn_eliminar.setIcon(icon_delete)
        acciones_layout.addWidget(self.btn_eliminar)

        acciones_layout.addStretch()
        layout.addLayout(acciones_layout)

    def _crear_tabla_alquileres(self):
        """
        Crea la tabla de alquileres.
        Ahora tiene 11 columnas:
        [Fecha, Equipo, Cliente, Operador, Conduce, Cantidad, Precio, Monto,
         Ubicación, Pagado, Ver Conduce]
        """
        self.tabla_alquileres = QTableWidget()
        self.tabla_alquileres.setColumnCount(11)

        HEADERS = [
            "Fecha", "Equipo", "Cliente", "Operador", "Conduce",
            "Cantidad", "Precio", "Monto", "Ubicación", "Pagado", "Ver Conduce"
        ]
        self.tabla_alquileres.setHorizontalHeaderLabels(HEADERS)

        self.tabla_alquileres.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_alquileres.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_alquileres.setAlternatingRowColors(True)
        self.tabla_alquileres.setSortingEnabled(True)  # Habilitar orden

        header = self.tabla_alquileres.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Fecha
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Equipo
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Cliente
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)          # Operador
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Conduce
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # Cantidad
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # Precio
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents) # Monto
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)          # Ubicación
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents) # Pagado
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents) # Ver Conduce

    def _crear_totales(self, layout: QHBoxLayout):
        """
        Crea los labels de totales.
        """
        self.lbl_total_alquileres = QLabel("Total Alquileres: 0")
        self.lbl_total_monto = QLabel("Monto Total: 0.00")

        layout.addStretch()
        layout.addWidget(self.lbl_total_alquileres)
        layout.addSpacing(20)
        layout.addWidget(self.lbl_total_monto)

    # =========================================================================================
    # SECCIÓN: Población de filtros a partir de mapas
    # =========================================================================================
    def actualizar_mapas(self, mapas: dict):
        """
        Recibe los mapas desde la ventana principal y puebla los filtros.
        """
        self.equipos_mapa = mapas.get("equipos", {})
        self.clientes_mapa = mapas.get("clientes", {})
        self.operadores_mapa = mapas.get("operadores", {})

        logger.info("RegistroAlquileres: Mapas recibidos. Poblando filtros...")

        try:
            # --- Poblar Equipos ---
            self.combo_equipo.blockSignals(True)
            self.combo_equipo.clear()
            self.combo_equipo.addItem("Todos", None)
            for eq_id, nombre in sorted(self.equipos_mapa.items(), key=lambda item: item[1]):
                self.combo_equipo.addItem(nombre, eq_id)
            self.combo_equipo.blockSignals(False)

            # --- Poblar Clientes ---
            self.combo_cliente.blockSignals(True)
            self.combo_cliente.clear()
            self.combo_cliente.addItem("Todos", None)
            for cl_id, nombre in sorted(self.clientes_mapa.items(), key=lambda item: item[1]):
                self.combo_cliente.addItem(nombre, cl_id)
            self.combo_cliente.blockSignals(False)

            # --- Poblar Operadores ---
            self.combo_operador.blockSignals(True)
            self.combo_operador.clear()
            self.combo_operador.addItem("Todos", None)
            for op_id, nombre in sorted(self.operadores_mapa.items(), key=lambda item: item[1]):
                self.combo_operador.addItem(nombre, op_id)
            self.combo_operador.blockSignals(False)

            # --- Poblar Estado de Pago ---
            self.combo_pagado.blockSignals(True)
            self.combo_pagado.clear()
            self.combo_pagado.addItem("Todos", None)
            self.combo_pagado.addItem("Pendientes", False)
            self.combo_pagado.addItem("Pagados", True)
            self.combo_pagado.blockSignals(False)

            # --- Inicializar fechas dinámicas ---
            self._inicializar_fechas_filtro()

        except Exception as e:
            logger.error(f"Error al poblar filtros de alquileres: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"No se pudieron cargar los filtros: {e}")

    def _inicializar_fechas_filtro(self):
        """
        Inicializa los filtros de fecha de forma dinámica.
        La fecha "Desde" se establece como la fecha de la primera transacción.
        La fecha "Hasta" se establece como la fecha actual.
        """
        try:
            # Obtener fecha de la primera transacción
            primera_fecha_str = self.fm.obtener_fecha_primera_transaccion_alquileres()

            if primera_fecha_str:
                # Convertir string a QDate
                primera_fecha = QDate.fromString(primera_fecha_str, "yyyy-MM-dd")
                self.date_desde.setDate(primera_fecha)
                logger.info(f"Fecha 'Desde' inicializada con primera transacción: {primera_fecha_str}")
            else:
                # Si no hay transacciones, usar mes anterior
                self.date_desde.setDate(QDate.currentDate().addMonths(-1))
                logger.warning("No hay transacciones, usando fecha por defecto (mes anterior)")

            # Fecha "Hasta" siempre es la fecha actual
            self.date_hasta.setDate(QDate.currentDate())

        except Exception as e:
            logger.error(f"Error al inicializar fechas de filtro: {e}", exc_info=True)
            # En caso de error, usar fechas por defecto
            self.date_desde.setDate(QDate.currentDate().addMonths(-1))
            self.date_hasta.setDate(QDate.currentDate())

    # =========================================================================================
    # SECCIÓN: Helpers de modalidad para mostrar Cantidad y Precio
    # =========================================================================================
    def _formatear_cantidad_y_precio(self, alquiler: dict) -> tuple[str, str]:
        """
        Devuelve (cantidad_texto, precio_texto) según modalidad_facturacion del alquiler.
        Reglas:
          - horas:
              cantidad = "{horas:.2f} h"
              precio   = "{precio_por_hora:.2f}"
          - volumen:
              cantidad = "{volumen_generado:.2f} <unidad>" (si hay unidad_volumen)
              precio   = "{precio_por_unidad:.2f}"
          - fijo:
              cantidad = "-"
              precio   = monto_fijo (si self.mostrar_precio_en_modalidad_fijo) o "-"
        Si algún campo falta, se usa 0 ó '-'.
        """
        modalidad = (alquiler.get("modalidad_facturacion") or "horas").strip().lower()

        if modalidad == "volumen":
            vol = float(alquiler.get("volumen_generado", 0) or 0)
            unidad = (alquiler.get("unidad_volumen") or "").strip()
            cantidad_txt = f"{vol:,.2f}" + (f" {unidad}" if unidad else "")
            precio_txt = f"{float(alquiler.get('precio_por_unidad', 0) or 0):,.2f}"
        elif modalidad == "fijo":
            cantidad_txt = "-"
            if self.mostrar_precio_en_modalidad_fijo:
                # mostrar monto_fijo como "Precio"
                precio_base = float(alquiler.get("monto_fijo", alquiler.get("monto", 0) or 0) or 0)
                precio_txt = f"{precio_base:,.2f}"
            else:
                precio_txt = "-"
        else:
            # modalidad horas (default)
            horas = float(alquiler.get("horas", 0) or 0)
            pph = float(alquiler.get("precio_por_hora", 0) or 0)
            cantidad_txt = f"{horas:,.2f} h"
            precio_txt = f"{pph:,.2f}"

        return cantidad_txt, precio_txt

    # =========================================================================================
    # SECCIÓN: Carga de Alquileres
    # =========================================================================================
    def _cargar_alquileres(self):
        """
        Carga y muestra los alquileres en la tabla según los filtros actuales.
        Aplica la transformación de modalidad en las columnas 'Cantidad' y 'Precio'.
        """
        # No cargar si los mapas no están listos
        if not self.equipos_mapa:
            logger.warning("RegistroAlquileres: Mapas no listos, saltando carga.")
            return

        filtros: dict = {}

        # Recolectar filtros de fecha
        filtros["fecha_inicio"] = self.date_desde.date().toString("yyyy-MM-dd")
        filtros["fecha_fin"] = self.date_hasta.date().toString("yyyy-MM-dd")

        # IDs tal como se guardan en Firestore (strings)
        equipo_id = self.combo_equipo.currentData()
        if equipo_id:
            filtros["equipo_id"] = equipo_id

        cliente_id = self.combo_cliente.currentData()
        if cliente_id:
            filtros["cliente_id"] = cliente_id

        operador_id = self.combo_operador.currentData()
        if operador_id:
            filtros["operador_id"] = operador_id

        if self.combo_pagado.currentData() is not None:
            filtros["pagado"] = self.combo_pagado.currentData()

        try:
            logger.info(f"Cargando alquileres con filtros: {filtros}")
            self.alquileres_cargados = self.fm.obtener_alquileres(filtros)

            self.tabla_alquileres.setSortingEnabled(False)  # Deshabilitar orden mientras se puebla
            self.tabla_alquileres.setRowCount(0)  # Limpiar tabla
            if not self.alquileres_cargados:
                logger.warning("No se encontraron alquileres con esos filtros.")
                self.lbl_total_alquileres.setText("Total Alquileres: 0")
                self.lbl_total_monto.setText("Monto Total: 0.00")
                self.tabla_alquileres.setSortingEnabled(True)
                return

            self.tabla_alquileres.setRowCount(len(self.alquileres_cargados))
            total_monto = 0.0

            for row, alquiler in enumerate(self.alquileres_cargados):
                # --- Traducción de IDs a Nombres ---
                equipo_id_val = str(alquiler.get("equipo_id", "") or "")
                cliente_id_val = str(alquiler.get("cliente_id", "") or "")
                operador_id_val = str(alquiler.get("operador_id", "") or "")

                equipo_nombre = self.equipos_mapa.get(equipo_id_val, f"ID: {equipo_id_val}")
                cliente_nombre = self.clientes_mapa.get(cliente_id_val, f"ID: {cliente_id_val}")
                operador_nombre = self.operadores_mapa.get(operador_id_val, f"ID: {operador_id_val}")

                # --- Poblar la tabla ---
                item_fecha = QTableWidgetItem(alquiler.get("fecha", ""))
                item_fecha.setData(Qt.ItemDataRole.UserRole, alquiler["id"])
                self.tabla_alquileres.setItem(row, 0, item_fecha)

                self.tabla_alquileres.setItem(row, 1, QTableWidgetItem(equipo_nombre))
                self.tabla_alquileres.setItem(row, 2, QTableWidgetItem(cliente_nombre))
                self.tabla_alquileres.setItem(row, 3, QTableWidgetItem(operador_nombre))

                # Columna conduce: puede ser código/serie, no necesariamente URL
                conduce_texto = alquiler.get("conduce", "") or ""
                self.tabla_alquileres.setItem(row, 4, QTableWidgetItem(conduce_texto))

                cantidad_txt, precio_txt = self._formatear_cantidad_y_precio(alquiler)
                modalidad = (alquiler.get("modalidad_facturacion") or "horas").strip().lower()

                item_cantidad = QTableWidgetItem(cantidad_txt)
                item_precio = QTableWidgetItem(precio_txt)
                item_cantidad.setToolTip(f"Modalidad: {modalidad.upper()}")
                item_precio.setToolTip(f"Modalidad: {modalidad.upper()}")

                self.tabla_alquileres.setItem(row, 5, item_cantidad)
                self.tabla_alquileres.setItem(row, 6, item_precio)

                horas = alquiler.get("horas", 0)
                precio = alquiler.get("precio_por_hora", 0)
                monto = alquiler.get("monto", 0)
                total_monto += float(monto)

                self.tabla_alquileres.setItem(row, 7, QTableWidgetItem(f"{float(monto):,.2f}"))

                self.tabla_alquileres.setItem(row, 8, QTableWidgetItem(alquiler.get("ubicacion", "")))

                pagado = alquiler.get("pagado", False)
                item_pagado = QTableWidgetItem("Sí" if pagado else "No")
                item_pagado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_pagado.setForeground(QColor("green") if pagado else QColor("red"))
                self.tabla_alquileres.setItem(row, 9, item_pagado)

                # NUEVO: Columna 10 "Ver Conduce" (indicador visual)
                tiene_conduce = bool(conduce_texto.strip())
                # También considerar campos URL / storage en el propio dict, si ya vienen
                if not tiene_conduce:
                    url = (alquiler.get("conduce_url") or alquiler.get("conduceUrl") or "").strip()
                    storage_path = (alquiler.get("conduce_storage_path") or alquiler.get("conducePath") or "").strip()
                    if url or storage_path:
                        tiene_conduce = True

                if tiene_conduce:
                    item_ver = QTableWidgetItem("Ver")
                    item_ver.setForeground(QColor("royalblue"))
                    item_ver.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.tabla_alquileres.setItem(row, 10, item_ver)
                else:
                    self.tabla_alquileres.setItem(row, 10, QTableWidgetItem(""))

            # Actualizar totales
            self.lbl_total_alquileres.setText(f"Total Alquileres: {len(self.alquileres_cargados)}")
            self.lbl_total_monto.setText(f"Monto Total: {total_monto:,.2f}")
            self.tabla_alquileres.setSortingEnabled(True)  # Habilitar orden

        except Exception as e:
            logger.error(f"Error al cargar alquileres: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar los alquileres (¿Falta un índice en Firebase?):\n\n{e}",
            )

    # =========================================================================================
    # SECCIÓN: Helpers CRUD (selección, abrir diálogo, eliminar)
    # =========================================================================================
    def _obtener_id_seleccionado(self):
        """
        Obtiene el ID de Firestore del item seleccionado en la tabla.
        """
        selected_items = self.tabla_alquileres.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Sin Selección", "Por favor, seleccione un alquiler de la tabla.")
            return None

        selected_row = selected_items[0].row()
        item_con_id = self.tabla_alquileres.item(selected_row, 0)  # El ID está en la primera columna (UserRole)
        alquiler_id = item_con_id.data(Qt.ItemDataRole.UserRole)
        return alquiler_id

    def abrir_dialogo_alquiler(self, alquiler_id: str | None = None):
        """
        Abre el diálogo para crear o editar un alquiler.
        """
        alquiler_data_para_dialogo = None
        if alquiler_id is False:  # Señal de "Nuevo"
            alquiler_id = None

        if alquiler_id:
            # Si es una edición, buscar los datos completos del alquiler
            try:
                alquiler_data_para_dialogo = self.fm.obtener_alquiler_por_id(alquiler_id)
                if not alquiler_data_para_dialogo:
                    QMessageBox.critical(
                        self, "Error", f"No se pudieron cargar los datos para el alquiler ID: {alquiler_id}"
                    )
                    return
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al cargar datos de alquiler: {e}")
                return

        logger.info(f"Abrir AlquilerDialog con storage_manager={self.sm}")

        dialog = AlquilerDialog(
            firebase_manager=self.fm,
            storage_manager=self.sm,  # <-- CLAVE: pasar siempre el StorageManager aquí
            equipos_mapa=self.equipos_mapa,
            clientes_mapa=self.clientes_mapa,
            operadores_mapa=self.operadores_mapa,
            alquiler_data=alquiler_data_para_dialogo,
            parent=self,
        )

        if dialog.exec():
            self._cargar_alquileres()
            self.recargar_dashboard.emit()

    def editar_alquiler_seleccionado(self):
        """
        Abre el diálogo de edición para el alquiler seleccionado.
        """
        alquiler_id = self._obtener_id_seleccionado()
        if alquiler_id:
            self.abrir_dialogo_alquiler(alquiler_id)

    def eliminar_alquiler_seleccionado(self):
        """
        Elimina el alquiler seleccionado tras confirmación.
        """
        alquiler_id = self._obtener_id_seleccionado()
        if alquiler_id:
            reply = QMessageBox.question(
                self,
                "Confirmar Eliminación",
                f"¿Está seguro de que desea eliminar este registro (ID: {alquiler_id})?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                try:
                    if self.fm.eliminar_alquiler(alquiler_id):
                        QMessageBox.information(self, "Éxito", "Alquiler eliminado correctamente.")
                        self._cargar_alquileres()
                        self.recargar_dashboard.emit()
                    else:
                        QMessageBox.warning(self, "Error", "No se pudo eliminar el alquiler.")
                except Exception as e:
                    logger.error(f"Error al eliminar alquiler {alquiler_id}: {e}")
                    QMessageBox.critical(self, "Error", f"Error al eliminar:\n{e}")

    # =========================================================================================
    # Menú contextual (clic derecho)
    # =========================================================================================
    def _mostrar_menu_contextual(self, pos: QPoint):
        """
        Muestra el menú contextual de la tabla de alquileres.
        Acciones:
          - Registrar Nuevo Alquiler
          - Editar seleccionado
          - Eliminar seleccionado
          - Ver Conduce (URL firmada si aplica)
          - Marcar como Pagado / No pagado
          - Copiar celda / Copiar fila
        """
        index = self.tabla_alquileres.indexAt(pos)
        hay_fila = index.isValid()

        # Determinar fila actual (por cursor); si no, usar selección
        fila = index.row() if hay_fila else (self.tabla_alquileres.currentRow() if self.tabla_alquileres.currentRow() >= 0 else None)

        menu = QMenu(self)

        # Acción: Nuevo alquiler
        act_nuevo = menu.addAction("➕ Registrar Nuevo Alquiler")
        act_nuevo.triggered.connect(self.abrir_dialogo_alquiler)

        # Separador
        menu.addSeparator()

        # Acción: Editar seleccionado
        act_editar = menu.addAction("✏️ Editar Seleccionado")
        act_editar.triggered.connect(self.editar_alquiler_seleccionado)
        act_editar.setEnabled(hay_fila or (self.tabla_alquileres.currentRow() >= 0))

        # Acción: Eliminar seleccionado
        act_eliminar = menu.addAction("🗑️ Eliminar Seleccionado")
        act_eliminar.triggered.connect(self.eliminar_alquiler_seleccionado)
        act_eliminar.setEnabled(hay_fila or (self.tabla_alquileres.currentRow() >= 0))

        # Acción: Ver Conduce (si hay algo en la columna Conduce o hay path/URL en Firestore)
        act_ver_conduce = menu.addAction("📄 Ver Conduce")
        act_ver_conduce.triggered.connect(self._accion_ver_conduce)
        # Habilitar si hay fila y la columna Conduce tiene algún valor o hay datos en Firestore
        habilitar_ver = False
        if fila is not None and fila >= 0:
            try:
                # 1) Ver texto en columna Conduce
                conduce_txt_item = self.tabla_alquileres.item(fila, 4)
                txt = (conduce_txt_item.text() if conduce_txt_item else "").strip()
                if txt:
                    habilitar_ver = True
                else:
                    # 2) Revisar Firestore por URL o storage_path
                    item_fecha = self.tabla_alquileres.item(fila, 0)
                    alquiler_id = item_fecha.data(Qt.ItemDataRole.UserRole) if item_fecha else None
                    if alquiler_id:
                        doc = self.fm.obtener_alquiler_por_id(alquiler_id) or {}
                        url = (doc.get("conduce_url") or doc.get("conduceUrl") or "").strip()
                        storage_path = (doc.get("conduce_storage_path") or doc.get("conducePath") or "").strip()
                        if url or (storage_path and self.sm):
                            habilitar_ver = True
            except Exception as e:
                logger.warning(f"Error comprobando conduce para menú contextual: {e}", exc_info=True)
                habilitar_ver = False

        act_ver_conduce.setEnabled(bool(fila is not None and habilitar_ver))

        # Acción: Toggle Pagado
        act_toggle_pagado = menu.addAction("💳 Marcar como Pagado/No pagado")
        act_toggle_pagado.triggered.connect(self._accion_toggle_pagado)
        act_toggle_pagado.setEnabled(hay_fila or (self.tabla_alquileres.currentRow() >= 0))

        # Separador
        menu.addSeparator()

        # Copiar celda / Copiar fila
        act_copiar_celda = menu.addAction("📋 Copiar celda")
        act_copiar_celda.triggered.connect(self._accion_copiar_celda)
        act_copiar_celda.setEnabled(len(self.tabla_alquileres.selectedItems()) > 0)

        act_copiar_fila = menu.addAction("📋 Copiar fila")
        act_copiar_fila.triggered.connect(self._accion_copiar_fila)
        act_copiar_fila.setEnabled(hay_fila or (self.tabla_alquileres.currentRow() >= 0))

        menu.exec(self.tabla_alquileres.viewport().mapToGlobal(pos))

    def _accion_ver_conduce(self):
        """
        CAMBIO V20: Genera URL firmada fresca cada vez (igual que gastos).
        Ya NO lee 'conduce_url' de Firestore. 
        """
        alquiler_id = self._obtener_id_seleccionado()
        if not alquiler_id:
            return
        
        try:
            # Buscar el alquiler en memoria primero
            alquiler = None
            for alq in self.alquileres_cargados:
                if alq.get('id') == alquiler_id:
                    alquiler = alq
                    break
            
            if not alquiler: 
                QMessageBox.warning(self, "Error", "No se encontró el alquiler.")
                return
            
            # Obtener storage_path
            storage_path = alquiler.get("conduce_storage_path", "").strip()
            
            if not storage_path: 
                QMessageBox.information(self, "Conduce", "Este alquiler no tiene conduce adjunto.")
                return
            
            if not self.sm:
                QMessageBox.warning(self, "Storage", "Storage no está configurado.")
                return
            
            # Generar URL firmada fresca (7 días de validez) - IGUAL QUE GASTOS
            url_fresca = self._generar_url_firmada_fresca(storage_path, dias=7)
            
            if url_fresca:
                import webbrowser
                webbrowser.open(url_fresca)
            else:
                QMessageBox.warning(self, "Conduce", "No se pudo generar la URL del conduce.")
                
        except Exception as e:
            logger.error(f"Error abriendo conduce {alquiler_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el conduce:\n{e}")

    def _accion_toggle_pagado(self):
        """
        Alterna directamente el campo 'pagado' del alquiler (SIN afectar la lógica automática de abonos).
        Si se marca como pagado y los pagos reales no cubren el monto, se muestra una advertencia.
        """
        alquiler_id = self._obtener_id_seleccionado()
        if not alquiler_id:
            return
        try:
            alquiler_data = self.fm.obtener_alquiler_por_id(alquiler_id) or {}
            actual_pagado = bool(alquiler_data.get("pagado", False))
            nuevo_estado = not actual_pagado

            # Solo advertir cuando se va a marcar como pagado
            if nuevo_estado:
                # Sumar pagos reales en la subcolección
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

                monto_total = float(alquiler_data.get("monto", 0) or 0)

                # Si los pagos no cubren el monto, advertir
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
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if respuesta == QMessageBox.StandardButton.No:
                        return

            # Actualizar campo 'pagado' (manual directo)
            ok = self.fm.editar_alquiler(alquiler_id, {"pagado": nuevo_estado})
            if ok:
                # Refrescar tabla y dashboard
                self._cargar_alquileres()
                self.recargar_dashboard.emit()
            else:
                QMessageBox.warning(self, "Estado de pago", "No se pudo actualizar el estado.")

        except Exception as e:
            logger.error(f"Error al alternar estado pagado {alquiler_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo actualizar el estado:\n{e}")

    def _accion_copiar_celda(self):
        """Copia el texto de la celda seleccionada al portapapeles."""
        sel = self.tabla_alquileres.selectedItems()
        if not sel:
            return
        txt = sel[0].text()
        QApplication.clipboard().setText(txt)

    def _accion_copiar_fila(self):
        """Copia toda la fila seleccionada como texto tabulado."""
        sel = self.tabla_alquileres.selectedItems()
        if not sel:
            return
        row = sel[0].row()
        cols = self.tabla_alquileres.columnCount()
        valores = []
        for c in range(cols):
            it = self.tabla_alquileres.item(row, c)
            valores.append(it.text() if it else "")
        tsv = "\t".join(valores)
        QApplication.clipboard().setText(tsv)

    # =========================================================================================
    # Utilidades locales
    # =========================================================================================
    def _abrir_url(self, url: str):
        try:
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            logger.error(f"No se pudo abrir URL: {url} -> {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir la URL:\n{url}\n{e}")

    def _generar_url_firmada(self, storage_path: str, dias: int = 7) -> str | None:
        """Genera una URL firmada con StorageManager, tolerante a nombre de método."""
        try:
            if not self.sm:
                return None
            # Intentar nombres en inglés/español
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
            logger.warning(f"No se pudo generar URL firmada para {storage_path}: {e}")
            return None




    def _generar_url_firmada_fresca(self, storage_path: str, dias: int = 7) -> str | None:
        """
        Genera URL firmada fresca con StorageManager (IGUAL QUE GASTOS).
        
        Args:
            storage_path: Ruta del archivo en Storage (ej: "conduces/2025/11/00659. jpeg")
            dias: Días de validez de la URL (default: 7)
        
        Returns:
            URL firmada (str) o None si falla
        """
        try:
            if not self.sm:
                return None
            
            # Intentar nombres de método en inglés/español (tolerancia)
            gen_en = getattr(self.sm, "generate_signed_url", None)
            gen_es = getattr(self.sm, "generar_url_firmada", None)
            
            if callable(gen_en):
                try:
                    return gen_en(storage_path, expiration_days=dias)
                except TypeError:
                    # Firma de método distinta (sin keyword)
                    return gen_en(storage_path, dias)
            
            if callable(gen_es):
                try:
                    return gen_es(storage_path, dias)
                except TypeError:
                    return gen_es(storage_path, expiration_days=dias)
            
            return None
        except Exception as e:
            logger.warning(f"No se pudo generar URL firmada para {storage_path}: {e}")
            return None




    def _handle_cell_click(self, row: int, col: int):
        """
        Si el usuario hace clic en la columna 'Ver Conduce' (índice 10),
        dispara la misma lógica que el menú contextual: _accion_ver_conduce.
        """
        try:
            # Solo actuamos en la columna "Ver Conduce" (columna 10)
            if col != 10:
                return

            item = self.tabla_alquileres.item(row, col)
            if not item:
                return

            texto = (item.text() or "").strip()
            if not texto:
                # No hay "Ver" en esta celda => no hay conduce visible
                return

            # Seleccionar la fila para que _obtener_id_seleccionado use esta fila
            self.tabla_alquileres.selectRow(row)

            # Reutilizar la misma acción que el menú contextual
            self._accion_ver_conduce()

        except Exception as e:
            logger.error(f"Error en _handle_cell_click para Ver Conduce (row={row}, col={col}): {e}", exc_info=True)