"""
Tab de Gastos de Equipos para EQUIPOS 4.0
- Filtros dinámicos (sin botón)
- Menú contextual (Editar / Eliminar / Ver Adjunto)
- Doble clic para editar
- Columna 'Adjunto' (Ver) si existe archivo en Storage
- Integración con GastoDialog
- FIX: color 'Ver' con QColor/QBrush (PyQt6)
- Mostrar 'Sin equipo' cuando no hay equipo_id
- NUEVO: filtro de Subcategoría (dependiente de Categoría)
- NUEVO: búsqueda de texto en memoria (descripción, comentario, equipo, cuenta, categoría, subcategoría)
- NUEVO: Exportación a PDF y Excel con todos los filtros aplicados
- URLs públicas permanentes para adjuntos
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QLabel, QDateEdit, QSpacerItem, QSizePolicy, QMenu, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QPoint, QTimer
from PyQt6.QtGui import QColor, QBrush
import logging
import webbrowser
from datetime import datetime

from firebase_manager import FirebaseManager
from dialogos. gasto_dialog import GastoDialog
from reporte_gastos import ReporteGastos

logger = logging.getLogger(__name__)


class TabGastosEquipos(QWidget):
    recargar_dashboard = pyqtSignal()

    def __init__(self, firebase_manager:  FirebaseManager, storage_manager=None, datos_empresa:  dict = None):
        super().__init__()
        self.fm = firebase_manager
        self.sm = storage_manager
        self.datos_empresa = datos_empresa or {}

        # Datos en memoria
        self.gastos_base = []
        self.gastos_filtrados = []

        # Mapas
        self.equipos_mapa = {}
        self.cuentas_mapa = {}
        self.categorias_mapa = {}
        self.subcategorias_mapa = {}
        self.subcategorias_by_cat = {}

        # Debounce para búsqueda
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._aplicar_filtros_en_memoria)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1) Filtros
        filtros_layout = QHBoxLayout()

        filtros_layout.addWidget(QLabel("Desde:"))
        self.date_desde_gastos = QDateEdit(calendarPopup=True)
        self.date_desde_gastos.setDisplayFormat("yyyy-MM-dd")
        self.date_desde_gastos.setDate(QDate.currentDate().addMonths(-1))
        filtros_layout.addWidget(self.date_desde_gastos)

        filtros_layout.addWidget(QLabel("Hasta:"))
        self.date_hasta_gastos = QDateEdit(calendarPopup=True)
        self.date_hasta_gastos.setDisplayFormat("yyyy-MM-dd")
        self.date_hasta_gastos.setDate(QDate.currentDate())
        filtros_layout.addWidget(self.date_hasta_gastos)

        filtros_layout.addSpacerItem(QSpacerItem(12, 12, QSizePolicy.Policy. Fixed, QSizePolicy.Policy. Minimum))

        filtros_layout.addWidget(QLabel("Cuenta:"))
        self.combo_cuenta_gastos = QComboBox()
        self.combo_cuenta_gastos.setMinimumWidth(150)
        filtros_layout.addWidget(self.combo_cuenta_gastos)

        filtros_layout.addWidget(QLabel("Categoría:"))
        self.combo_categoria_gastos = QComboBox()
        self.combo_categoria_gastos.setMinimumWidth(150)
        self.combo_categoria_gastos. currentIndexChanged.connect(self._repopulate_subcategorias)
        filtros_layout.addWidget(self.combo_categoria_gastos)

        filtros_layout.addWidget(QLabel("Subcategoría:"))
        self.combo_subcategoria_gastos = QComboBox()
        self.combo_subcategoria_gastos.setMinimumWidth(180)
        filtros_layout.addWidget(self.combo_subcategoria_gastos)

        filtros_layout.addWidget(QLabel("Equipo:"))
        self.combo_equipo_gastos = QComboBox()
        self.combo_equipo_gastos. setMinimumWidth(180)
        filtros_layout.addWidget(self.combo_equipo_gastos)

        filtros_layout. addSpacerItem(QSpacerItem(12, 12, QSizePolicy.Policy.Fixed, QSizePolicy.Policy. Minimum))

        filtros_layout.addWidget(QLabel("Buscar:"))
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("texto libre…")
        filtros_layout. addWidget(self.txt_buscar)

        filtros_layout.addStretch()
        main_layout.addLayout(filtros_layout)

        # 2) Acciones
        acciones_layout = QHBoxLayout()
        
        self.btn_buscar_gastos = QPushButton("🔍 Buscar (manual)")
        acciones_layout.addWidget(self.btn_buscar_gastos)
        
        self.btn_nuevo_gasto = QPushButton("➕ Registrar Nuevo Gasto")
        acciones_layout.addWidget(self.btn_nuevo_gasto)
        
        self.btn_editar_gasto = QPushButton("✏️ Editar Seleccionado")
        acciones_layout.addWidget(self. btn_editar_gasto)
        
        self.btn_eliminar_gasto = QPushButton("🗑️ Eliminar Seleccionado")
        acciones_layout.addWidget(self.btn_eliminar_gasto)
        
        acciones_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy. Minimum))
        
        # NUEVOS:  Botones de exportación
        self.btn_exportar_pdf = QPushButton("📄 Exportar PDF")
        acciones_layout.addWidget(self.btn_exportar_pdf)
        
        self.btn_exportar_excel = QPushButton("📊 Exportar Excel")
        acciones_layout. addWidget(self.btn_exportar_excel)
        
        acciones_layout.addStretch()
        main_layout.addLayout(acciones_layout)

        # 3) Tabla
        self.tabla_gastos = QTableWidget()
        self.tabla_gastos.setColumnCount(9)
        headers = [
            "Fecha", "Equipo", "Cuenta", "Categoría", "Subcategoría",
            "Descripción", "Monto", "Comentario", "Adjunto"
        ]
        self.tabla_gastos.setHorizontalHeaderLabels(headers)
        self.tabla_gastos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_gastos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_gastos.setAlternatingRowColors(True)
        self.tabla_gastos.setSortingEnabled(True)

        header = self.tabla_gastos.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode. Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode. ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode. ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode. Stretch)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)

        main_layout.addWidget(self. tabla_gastos)

        # 4) Totales
        totales_layout = QHBoxLayout()
        self.lbl_total_gastos = QLabel("Total Gastos:  0")
        self.lbl_monto_total_gastos = QLabel("Monto Total: 0.00")
        totales_layout.addStretch()
        totales_layout.addWidget(self.lbl_total_gastos)
        totales_layout. addSpacing(20)
        totales_layout.addWidget(self.lbl_monto_total_gastos)
        main_layout. addLayout(totales_layout)

        self.setLayout(main_layout)

        # Conexiones
        self.btn_buscar_gastos.clicked.connect(self._recargar_por_fecha)
        self.btn_nuevo_gasto.clicked.connect(self. abrir_dialogo_nuevo)
        self.btn_editar_gasto.clicked.connect(self.editar_gasto_seleccionado)
        self.btn_eliminar_gasto. clicked.connect(self.eliminar_gasto_seleccionado)
        self.btn_exportar_pdf.clicked.connect(self._exportar_pdf)
        self.btn_exportar_excel. clicked.connect(self._exportar_excel)

        # Filtros dinámicos
        self. date_desde_gastos.dateChanged.connect(self._recargar_por_fecha)
        self.date_hasta_gastos.dateChanged.connect(self._recargar_por_fecha)
        self.combo_equipo_gastos.currentIndexChanged.connect(self._aplicar_filtros_en_memoria)
        self.combo_cuenta_gastos.currentIndexChanged. connect(self._aplicar_filtros_en_memoria)
        self.combo_categoria_gastos.currentIndexChanged.connect(self._aplicar_filtros_en_memoria)
        self.combo_subcategoria_gastos. currentIndexChanged.connect(self._aplicar_filtros_en_memoria)
        self.txt_buscar. textChanged.connect(self._on_search_changed)

        # Tabla:  doble clic y menú contextual
        self.tabla_gastos.itemDoubleClicked.connect(self. editar_gasto_seleccionado)
        self.tabla_gastos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla_gastos. customContextMenuRequested.connect(self._mostrar_menu_contextual)
        self.tabla_gastos. cellClicked.connect(self._handle_cell_click)

    def actualizar_mapas(self, mapas:  dict):
        """Actualiza los mapas de equipos, cuentas, categorías y subcategorías."""
        self.equipos_mapa = mapas.get("equipos", {})
        self.cuentas_mapa = mapas. get("cuentas", {})
        self.categorias_mapa = mapas.get("categorias", {})
        self.subcategorias_mapa = mapas.get("subcategorias", {})

        # Armar subcategorias_by_cat si no viene
        self.subcategorias_by_cat = mapas.get("subcategorias_by_cat", {})
        if not self.subcategorias_by_cat:
            catalogo = mapas.get("subcategorias_catalogo", [])
            by_cat = {}
            for item in catalogo or []:
                sid = str(item.get("id"))
                cid = str(item.get("categoria_id")) if item.get("categoria_id") is not None else None
                nom = item.get("nombre") or self.subcategorias_mapa.get(sid) or ""
                if cid:
                    by_cat. setdefault(cid, {})[sid] = nom
            self.subcategorias_by_cat = by_cat

        try:
            # Cuenta
            self.combo_cuenta_gastos.clear()
            self.combo_cuenta_gastos. addItem("Todas", None)
            for ct_id, nombre in sorted(self.cuentas_mapa.items(), key=lambda i: i[1]):
                self.combo_cuenta_gastos.addItem(nombre, str(ct_id))

            # Categoría
            self.combo_categoria_gastos.clear()
            self.combo_categoria_gastos. addItem("Todas", None)
            for cat_id, nombre in sorted(self.categorias_mapa.items(), key=lambda i: i[1]):
                self.combo_categoria_gastos.addItem(nombre, str(cat_id))

            # Subcategoría
            self.combo_subcategoria_gastos.clear()
            self.combo_subcategoria_gastos.addItem("Todas", None)

            # Equipo
            self.combo_equipo_gastos.clear()
            self.combo_equipo_gastos.addItem("Todos", None)
            for eq_id, nombre in sorted(self. equipos_mapa.items(), key=lambda i: i[1]):
                self.combo_equipo_gastos.addItem(nombre, str(eq_id))

            # Fechas
            self._inicializar_fechas_filtro()

            # Primera carga
            self._recargar_por_fecha()

        except Exception as e:
            logger.error(f"Error poblando filtros gastos: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"No se pudieron cargar filtros: {e}")

    def _inicializar_fechas_filtro(self):
        """Inicializa las fechas de filtro dinámicamente."""
        try:
            primera_fecha_str = self.fm.obtener_fecha_primera_transaccion_gastos()
            if primera_fecha_str:
                qd = QDate.fromString(primera_fecha_str, "yyyy-MM-dd")
                if qd.isValid():
                    self.date_desde_gastos.setDate(qd)
                    logger.info(f"Fecha 'Desde' inicializada gastos: {primera_fecha_str}")
                else:
                    self.date_desde_gastos. setDate(QDate.currentDate().addMonths(-1))
            else:
                self.date_desde_gastos.setDate(QDate.currentDate().addMonths(-1))
            self.date_hasta_gastos. setDate(QDate.currentDate())
        except Exception as e:
            logger.error(f"Error inicializando fechas gastos: {e}", exc_info=True)
            self.date_desde_gastos. setDate(QDate.currentDate().addMonths(-1))
            self.date_hasta_gastos.setDate(QDate. currentDate())

    def _repopulate_subcategorias(self):
        """Repobla el combo de Subcategoría según la categoría actual."""
        cat_id = self.combo_categoria_gastos.currentData()
        self.combo_subcategoria_gastos.blockSignals(True)
        self.combo_subcategoria_gastos.clear()
        self.combo_subcategoria_gastos.addItem("Todas", None)
        if cat_id and str(cat_id) in self.subcategorias_by_cat: 
            submap = self.subcategorias_by_cat[str(cat_id)]
            for sub_id, nombre in sorted(submap.items(), key=lambda i: i[1]):
                self. combo_subcategoria_gastos.addItem(nombre, str(sub_id))
        else:
            for sid, nombre in sorted(self.subcategorias_mapa.items(), key=lambda i: i[1]):
                self.combo_subcategoria_gastos.addItem(nombre, str(sid))
        self.combo_subcategoria_gastos. blockSignals(False)

    def _recargar_por_fecha(self):
        """Carga los gastos desde Firestore por rango de fechas."""
        if not self.equipos_mapa:
            return
        filtros = {
            "fecha_inicio": self.date_desde_gastos.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.date_hasta_gastos.date().toString("yyyy-MM-dd"),
        }
        try:
            logger.info(f"Cargando gastos (solo por fecha) {filtros}")
            self.gastos_base = self. fm.obtener_gastos(filtros)
            self._aplicar_filtros_en_memoria()
        except Exception as e:
            logger.error(f"Error cargando gastos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los gastos:\n{e}")

    def _on_search_changed(self, _text: str):
        """Debounce para búsqueda de texto."""
        self._search_timer.start()

    def _aplicar_filtros_en_memoria(self):
        """Aplica filtros en memoria sobre los gastos cargados."""
        eq_id = self.combo_equipo_gastos.currentData()
        ct_id = self.combo_cuenta_gastos.currentData()
        cat_id = self.combo_categoria_gastos.currentData()
        sub_id = self.combo_subcategoria_gastos.currentData()
        texto = (self.txt_buscar.text() or "").strip()

        def norm(s: str) -> str:
            import unicodedata
            s = s or ""
            s2 = s.lower()
            s2 = "".join(c for c in unicodedata.normalize("NFD", s2) if unicodedata.category(c) != "Mn")
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
                categoria_nom = self. categorias_mapa.get(gid_cat, "")
                sub_nom = (self.subcategorias_by_cat.get(gid_cat, {}) or {}).get(gid_sub) or self.subcategorias_mapa. get(gid_sub, "")
                blob = " ".join([
                    str(g.get("descripcion", "")),
                    str(g.get("comentario", "")),
                    equipo_nom, cuenta_nom, categoria_nom, sub_nom
                ])
                if txt not in norm(blob):
                    continue

            filtrados.append(g)

        self.gastos_filtrados = filtrados
        self._pintar_tabla()

    def _pintar_tabla(self):
        """Pinta la tabla con los gastos filtrados."""
        gastos = self.gastos_filtrados or []
        self.tabla_gastos.setSortingEnabled(False)
        self.tabla_gastos.setRowCount(0)

        total_monto = 0.0
        self.tabla_gastos.setRowCount(len(gastos))
        for row, g in enumerate(gastos):
            gid_eq = str(g.get('equipo_id')) if g.get('equipo_id') not in (None, "") else None
            gid_ct = str(g.get('cuenta_id')) if g.get('cuenta_id') not in (None, "") else None
            gid_cat = str(g.get('categoria_id')) if g.get('categoria_id') not in (None, "") else None
            gid_sub = str(g.get('subcategoria_id')) if g.get('subcategoria_id') not in (None, "") else None

            equipo_nombre = self.equipos_mapa.get(gid_eq, g.get('equipo_nombre', 'Sin equipo')) if gid_eq else 'Sin equipo'
            cuenta_nombre = self.cuentas_mapa.get(gid_ct, "")
            categoria_nombre = self.categorias_mapa.get(gid_cat, "")
            sub_nom = (self.subcategorias_by_cat.get(gid_cat, {}) or {}).get(gid_sub) or self.subcategorias_mapa.get(gid_sub, "")

            item_fecha = QTableWidgetItem(g.get('fecha', ''))
            item_fecha.setData(Qt.ItemDataRole.UserRole, g['id'])
            self.tabla_gastos.setItem(row, 0, item_fecha)
            self.tabla_gastos. setItem(row, 1, QTableWidgetItem(equipo_nombre))
            self.tabla_gastos.setItem(row, 2, QTableWidgetItem(cuenta_nombre))
            self.tabla_gastos.setItem(row, 3, QTableWidgetItem(categoria_nombre))
            self.tabla_gastos.setItem(row, 4, QTableWidgetItem(sub_nom))
            self.tabla_gastos.setItem(row, 5, QTableWidgetItem(g.get('descripcion', '')))

            monto = g.get('monto', 0) or 0
            try:
                total_monto += float(monto)
                monto_str = f"{float(monto):,.2f}"
            except Exception: 
                monto_str = str(monto)
            self.tabla_gastos. setItem(row, 6, QTableWidgetItem(monto_str))
            self.tabla_gastos. setItem(row, 7, QTableWidgetItem(g.get('comentario', '')))

            storage_path = g.get("archivo_storage_path", "")
            if storage_path:
                cell = QTableWidgetItem("Ver")
                cell.setData(Qt.ItemDataRole.UserRole, storage_path)
                cell.setForeground(QBrush(QColor("royalblue")))
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tabla_gastos.setItem(row, 8, cell)
            else:
                self.tabla_gastos.setItem(row, 8, QTableWidgetItem(""))

        self.lbl_total_gastos.setText(f"Total Gastos: {len(gastos)}")
        self.lbl_monto_total_gastos.setText(f"Monto Total: {total_monto: ,.2f}")
        self.tabla_gastos. setSortingEnabled(True)

    def _mostrar_menu_contextual(self, pos:  QPoint):
        """Muestra menú contextual con opciones CRUD."""
        menu = QMenu(self)

        act_editar = menu.addAction("✏️ Editar")
        act_eliminar = menu. addAction("🗑️ Eliminar")
        act_ver = menu.addAction("📎 Ver Adjunto")

        index = self.tabla_gastos. indexAt(pos)
        fila_valida = index.isValid()
        fila = index.row() if fila_valida else self.tabla_gastos.currentRow()

        habilitar_ver = False
        if fila is not None and fila >= 0:
            item_adj = self.tabla_gastos. item(fila, 8)
            if item_adj: 
                sp = item_adj.data(Qt.ItemDataRole.UserRole)
                habilitar_ver = bool(sp and self.sm)

        act_ver.setEnabled(bool(habilitar_ver))

        action = menu.exec(self.tabla_gastos.viewport().mapToGlobal(pos))
        if action == act_editar:
            self. editar_gasto_seleccionado()
        elif action == act_eliminar:
            self.eliminar_gasto_seleccionado()
        elif action == act_ver:
            self._ver_adjunto_seleccionado()

    def _handle_cell_click(self, row: int, col: int):
        """Handler para clic en celda 'Adjunto' (columna 8)."""
        if col == 8:
            item_adj = self.tabla_gastos.item(row, 8)
            if not item_adj:
                return
            storage_path = item_adj.data(Qt.ItemDataRole.UserRole)
            if storage_path:
                try:
                    self.tabla_gastos.selectRow(row)
                    self._ver_adjunto_seleccionado()
                except Exception as e:
                    logger.error(f"Error abriendo adjunto desde celda {storage_path}: {e}", exc_info=True)

    def _ver_adjunto_seleccionado(self):
        """Abre el adjunto del gasto seleccionado (URL pública permanente)."""
        sel = self.tabla_gastos.selectedItems()
        if not sel: 
            QMessageBox.warning(self, "Selección", "Seleccione una fila.")
            return
        row = sel[0].row()
        item_adj = self.tabla_gastos.item(row, 8)
        if not item_adj:
            QMessageBox.information(self, "Adjunto", "No hay adjunto en esta fila.")
            return

        storage_path = item_adj.data(Qt.ItemDataRole.UserRole)
        if not storage_path:
            QMessageBox. information(self, "Adjunto", "No hay adjunto en esta fila.")
            return

        try:
            if storage_path.startswith("http"):
                url = storage_path
            else: 
                bucket_name = self.sm.bucket. name if self.sm and self.sm.bucket else "equipos-zoec. firebasestorage.app"
                url = f"https://storage.googleapis.com/{bucket_name}/{storage_path}"

            webbrowser.open(url)

        except Exception as e:
            logger.error(f"Error abriendo adjunto {storage_path}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el adjunto:\n{e}")

    def _obtener_id_seleccionado_gasto(self):
        """Obtiene el ID del gasto seleccionado."""
        sel = self.tabla_gastos.selectedItems()
        if not sel: 
            return None
        row = sel[0].row()
        item = self.tabla_gastos.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole)

    def abrir_dialogo_nuevo(self):
        """Abre el diálogo para crear un nuevo gasto."""
        self._abrir_dialogo_gasto(None)

    def editar_gasto_seleccionado(self):
        """Edita el gasto seleccionado."""
        gid = self._obtener_id_seleccionado_gasto()
        if gid: 
            self._abrir_dialogo_gasto(gid)
        else:
            QMessageBox.warning(self, "Selección", "Seleccione un gasto primero.")

    def _abrir_dialogo_gasto(self, gasto_id: str | None):
        """Abre el diálogo de edición/creación de gasto."""
        try:
            dialog = GastoDialog(
                firebase_manager=self.fm,
                storage_manager=self.sm,
                equipos_mapa=self.equipos_mapa,
                cuentas_mapa=self. cuentas_mapa,
                categorias_mapa=self.categorias_mapa,
                subcategorias_mapa=self.subcategorias_mapa,
                gasto_id=gasto_id,
                parent=self,
                moneda_symbol="RD$"
            )
            if dialog.exec():
                self._recargar_por_fecha()
                self. recargar_dashboard. emit()
        except Exception as e:
            logger.error(f"Error abriendo diálogo gasto: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el diálogo:\n{e}")

    def eliminar_gasto_seleccionado(self):
        """Elimina el gasto seleccionado."""
        gid = self._obtener_id_seleccionado_gasto()
        if not gid:
            QMessageBox.warning(self, "Selección", "Seleccione un gasto primero.")
            return
        reply = QMessageBox.question(
            self, "Eliminar", f"¿Eliminar gasto ID: {gid}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ok = self.fm.eliminar_gasto(gid)
                if ok:
                    QMessageBox.information(self, "Éxito", "Gasto eliminado.")
                    self._recargar_por_fecha()
                    self.recargar_dashboard.emit()
                else:
                    QMessageBox.warning(self, "Error", "No se pudo eliminar.")
            except Exception as e: 
                logger.error(f"Error eliminando gasto {gid}: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"No se pudo eliminar:\n{e}")

    # =====================================================================================
    # SECCIÓN:  EXPORTACIÓN PDF Y EXCEL
    # =====================================================================================

    def _exportar_pdf(self):
        """Exporta los gastos filtrados a PDF."""
        if not self.gastos_filtrados:
            QMessageBox.warning(self, "Exportar", "No hay gastos para exportar.")
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
            # Preparar filtros aplicados
            filtros = {
                "fecha_inicio": self. date_desde_gastos.date().toString("yyyy-MM-dd"),
                "fecha_fin": self.date_hasta_gastos.date().toString("yyyy-MM-dd"),
                "equipo_nombre": self.combo_equipo_gastos.currentText() if self.combo_equipo_gastos.currentData() else None,
                "cuenta_nombre":  self.combo_cuenta_gastos.currentText() if self.combo_cuenta_gastos.currentData() else None,
                "categoria_nombre": self.combo_categoria_gastos.currentText() if self.combo_categoria_gastos.currentData() else None,
                "subcategoria_nombre":  self.combo_subcategoria_gastos.currentText() if self.combo_subcategoria_gastos.currentData() else None,
                "texto_busqueda": self.txt_buscar.text() if self.txt_buscar. text().strip() else None
            }

            # Generar reporte
            reporte = ReporteGastos(datos_empresa=self.datos_empresa, moneda_symbol="RD$")

            mapas = {
                "equipos":  self.equipos_mapa,
                "cuentas": self.cuentas_mapa,
                "categorias": self. categorias_mapa,
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
                QMessageBox. information(self, "Éxito", f"Reporte PDF generado:\n{archivo}")
                webbrowser.open(archivo)
            else:
                QMessageBox.warning(self, "Error", "No se pudo generar el reporte PDF.")

        except Exception as e:
            logger.error(f"Error exportando PDF: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al exportar:\n{e}")

    def _exportar_excel(self):
        """Exporta los gastos filtrados a Excel."""
        if not self.gastos_filtrados:
            QMessageBox.warning(self, "Exportar", "No hay gastos para exportar.")
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
                "equipo_nombre": self.combo_equipo_gastos.currentText() if self.combo_equipo_gastos.currentData() else None,
                "cuenta_nombre": self.combo_cuenta_gastos.currentText() if self.combo_cuenta_gastos.currentData() else None,
                "categoria_nombre": self. combo_categoria_gastos.currentText() if self.combo_categoria_gastos.currentData() else None,
                "subcategoria_nombre": self.combo_subcategoria_gastos.currentText() if self.combo_subcategoria_gastos.currentData() else None,
                "texto_busqueda": self.txt_buscar.text() if self.txt_buscar.text().strip() else None
            }

            reporte = ReporteGastos(datos_empresa=self.datos_empresa, moneda_symbol="RD$")

            mapas = {
                "equipos": self.equipos_mapa,
                "cuentas":  self.cuentas_mapa,
                "categorias": self.categorias_mapa,
                "subcategorias": self. subcategorias_mapa
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
                QMessageBox.warning(self, "Error", "No se pudo generar el reporte Excel.")

        except Exception as e:
            logger.error(f"Error exportando Excel:  {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al exportar:\n{e}")