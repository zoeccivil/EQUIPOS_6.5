from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QLineEdit, QDateEdit, QPushButton, QMessageBox, QHeaderView, QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, QDate, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
import logging
import webbrowser

from firebase_manager import FirebaseManager
from dialogos.pago_operador_dialog import PagoOperadorDialog, METODOS_DEFECTO

logger = logging.getLogger(__name__)


class TabPagosOperadores(QWidget):
    recargar_dashboard = pyqtSignal()

    def __init__(self, firebase_manager: FirebaseManager, storage_manager=None, parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.sm = storage_manager

        self.operadores_mapa = {}
        self.cuentas_mapa = {}
        self.equipos_mapa = {}

        self.pagos_base = []
        self.pagos_filtrados = []

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._aplicar_filtros_en_memoria)

        self._build_ui()

    # --------------------------------------------------------------------- UI
    def _build_ui(self):
        main = QVBoxLayout(self)

        # --- Filtros superiores ---
        filtros = QHBoxLayout()
        filtros.addWidget(QLabel("Desde:"))
        self.dt_desde = QDateEdit(calendarPopup=True)
        self.dt_desde.setDisplayFormat("yyyy-MM-dd")
        self.dt_desde.setDate(QDate.currentDate().addMonths(-1))
        filtros.addWidget(self.dt_desde)

        filtros.addWidget(QLabel("Hasta:"))
        self.dt_hasta = QDateEdit(calendarPopup=True)
        self.dt_hasta.setDisplayFormat("yyyy-MM-dd")
        self.dt_hasta.setDate(QDate.currentDate())
        filtros.addWidget(self.dt_hasta)

        filtros.addSpacing(10)
        filtros.addWidget(QLabel("Operador:"))
        self.cb_operador = QComboBox()
        self.cb_operador.setMinimumWidth(200)
        filtros.addWidget(self.cb_operador)

        filtros.addWidget(QLabel("Método:"))
        self.cb_metodo = QComboBox()
        self.cb_metodo.setMinimumWidth(140)
        filtros.addWidget(self.cb_metodo)

        filtros.addWidget(QLabel("Buscar:"))
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("concepto/nota/operador…")
        filtros.addWidget(self.txt_buscar)

        filtros.addStretch()
        main.addLayout(filtros)

        # --- Botones de acción ---
        acciones = QHBoxLayout()
        self.btn_buscar = QPushButton("Buscar (manual)")
        self.btn_nuevo = QPushButton("Registrar Pago")
        self.btn_editar = QPushButton("Editar Seleccionado")
        self.btn_eliminar = QPushButton("Eliminar Seleccionado")
        acciones.addWidget(self.btn_buscar)
        acciones.addWidget(self.btn_nuevo)
        acciones.addWidget(self.btn_editar)
        acciones.addWidget(self.btn_eliminar)
        acciones.addStretch()
        main.addLayout(acciones)

        # --- Tabla ---
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels(
            ["Fecha", "Operador", "Concepto", "Método", "Monto", "Nota", "Adjunto"]
        )
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSortingEnabled(True)

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        main.addWidget(self.tabla)
        self.setLayout(main)

        # --- Conexiones ---
        self.btn_buscar.clicked.connect(self._recargar_por_fecha)
        self.btn_nuevo.clicked.connect(self._nuevo_pago)
        self.btn_editar.clicked.connect(self._editar_pago_sel)
        self.btn_eliminar.clicked.connect(self._eliminar_pago_sel)

        self.dt_desde.dateChanged.connect(self._recargar_por_fecha)
        self.dt_hasta.dateChanged.connect(self._recargar_por_fecha)
        self.cb_operador.currentIndexChanged.connect(self._aplicar_filtros_en_memoria)
        self.cb_metodo.currentIndexChanged.connect(self._aplicar_filtros_en_memoria)
        self.txt_buscar.textChanged.connect(lambda _: self._search_timer.start())

        self.tabla.itemDoubleClicked.connect(self._editar_pago_sel)
        self.tabla.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla.customContextMenuRequested.connect(self._menu_contexto)
        self.tabla.cellClicked.connect(self._click_celda)

    # ----------------------------------------------------------- Datos/mapas
    def actualizar_mapas(self, mapas: dict):
        """
        Recibe los mapas desde la ventana principal:
          - operadores: {id: nombre}
          - cuentas: {id: nombre}
          - equipos: {id: nombre}
        Y luego inicializa filtros y carga los pagos.
        """
        self.operadores_mapa = mapas.get("operadores", {}) or {}
        self.cuentas_mapa = mapas.get("cuentas", {}) or {}
        self.equipos_mapa = mapas.get("equipos", {}) or {}

        # Operador
        self.cb_operador.clear()
        self.cb_operador.addItem("Todos", None)
        for oid, nom in sorted(self.operadores_mapa.items(), key=lambda i: i[1]):
            self.cb_operador.addItem(nom, str(oid))

        # Método
        self.cb_metodo.clear()
        self.cb_metodo.addItem("Todos", None)
        for m in METODOS_DEFECTO:
            self.cb_metodo.addItem(m, m)

        # Rango de fechas: desde primer pago hasta hoy
        hoy = QDate.currentDate()
        try:
            if hasattr(self.fm, "obtener_fecha_primera_transaccion_pagos"):
                f0 = self.fm.obtener_fecha_primera_transaccion_pagos()
            else:
                f0 = None
            if f0:
                qd = QDate.fromString(f0, "yyyy-MM-dd")
                if qd.isValid():
                    self.dt_desde.setDate(qd)
                else:
                    self.dt_desde.setDate(QDate(hoy.year(), 1, 1))
            else:
                self.dt_desde.setDate(QDate(hoy.year(), 1, 1))
        except Exception as e:
            logger.warning(f"No se pudo inicializar fecha mínima de pagos: {e}")
            self.dt_desde.setDate(QDate(hoy.year(), 1, 1))

        self.dt_hasta.setDate(hoy)
        self._recargar_por_fecha()

    # -------------------------------------------------------- Carga Firestore
    def _recargar_por_fecha(self):
        """
        Carga pagos desde Firestore.
        Traemos todos los documentos de 'pagos_operadores' y aplicamos el
        filtro de fechas en memoria para ser compatibles con datos migrados.
        """
        try:
            logger.info("Cargando pagos a operadores (sin filtro de fecha en Firestore)")
            self.pagos_base = self.fm.obtener_pagos_operadores({})
        except Exception as e:
            logger.error(f"Error cargando pagos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los pagos:\n{e}")
            self.pagos_base = []
            return

        fi = self.dt_desde.date().toString("yyyy-MM-dd")
        ff = self.dt_hasta.date().toString("yyyy-MM-dd")

        def in_range(p):
            f = p.get("fecha")
            if not isinstance(f, str):
                return False
            return fi <= f <= ff

        self.pagos_base = [p for p in (self.pagos_base or []) if in_range(p)]
        self._aplicar_filtros_en_memoria()

    # ------------------------------------------------------------- Filtro UI
    def _aplicar_filtros_en_memoria(self):
        op_id = self.cb_operador.currentData()
        metodo = self.cb_metodo.currentData()
        texto = (self.txt_buscar.text() or "").strip()

        def norm(s: str) -> str:
            import unicodedata
            s = s or ""
            s2 = s.lower()
            s2 = "".join(
                c for c in unicodedata.normalize("NFD", s2)
                if unicodedata.category(c) != "Mn"
            )
            return s2

        txt = norm(texto)
        out = []

        for p in self.pagos_base or []:
            pid_op = str(p.get("operador_id")) if p.get("operador_id") not in (None, "") else None
            if op_id and pid_op != str(op_id):
                continue
            if metodo and (p.get("metodo_pago") or "") != metodo:
                continue
            if txt:
                op_nom = self.operadores_mapa.get(pid_op, "")
                blob = " ".join([
                    p.get("descripcion", "") or p.get("concepto", ""),
                    p.get("comentario", "") or p.get("nota", ""),
                    op_nom,
                    str(p.get("metodo_pago") or "")
                ])
                if txt not in norm(blob):
                    continue
            out.append(p)

        self.pagos_filtrados = out
        self._pintar_tabla()

    # ---------------------------------------------------------- Pintar tabla
    def _pintar_tabla(self):
        t = self.pagos_filtrados or []
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(len(t))

        for r, p in enumerate(t):
            pid = p.get("id")
            f = p.get("fecha", "")
            op_id = str(p.get("operador_id")) if p.get("operador_id") not in (None, "") else None
            op_nom = self.operadores_mapa.get(op_id, "—") if op_id else "—"

            itf = QTableWidgetItem(f)
            itf.setData(Qt.ItemDataRole.UserRole, pid)
            self.tabla.setItem(r, 0, itf)

            self.tabla.setItem(r, 1, QTableWidgetItem(op_nom))
            self.tabla.setItem(r, 2, QTableWidgetItem(p.get("descripcion", "") or p.get("concepto", "")))
            self.tabla.setItem(r, 3, QTableWidgetItem(p.get("metodo_pago", "")))

            try:
                monto = float(p.get("monto", 0) or 0)
                mtxt = f"{monto:,.2f}"
            except Exception:
                mtxt = str(p.get("monto", ""))
            self.tabla.setItem(r, 4, QTableWidgetItem(mtxt))

            self.tabla.setItem(r, 5, QTableWidgetItem(p.get("comentario", "") or p.get("nota", "")))

            sp = p.get("archivo_storage_path", "")
            if sp:
                cell = QTableWidgetItem("Ver")
                cell.setData(Qt.ItemDataRole.UserRole, sp)
                cell.setForeground(QBrush(QColor("royalblue")))
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tabla.setItem(r, 6, cell)
            else:
                self.tabla.setItem(r, 6, QTableWidgetItem(""))

        self.tabla.setSortingEnabled(True)

    # ----------------------------------------------------------- UI helpers
    def _menu_contexto(self, pos: QPoint):
        menu = QMenu(self)
        a1 = menu.addAction("Editar")
        a2 = menu.addAction("Eliminar")
        a3 = menu.addAction("Ver Adjunto")
        act = menu.exec(self.tabla.viewport().mapToGlobal(pos))
        if act == a1:
            self._editar_pago_sel()
        elif act == a2:
            self._eliminar_pago_sel()
        elif act == a3:
            self._ver_adjunto_sel()

    def _click_celda(self, row: int, col: int):
        if col != 6:
            return
        it = self.tabla.item(row, 6)
        if not it:
            return
        sp = it.data(Qt.ItemDataRole.UserRole)
        if sp and self.sm:
            try:
                url = self.sm.get_download_url(sp, prefer_firmada=True)
                if url:
                    webbrowser.open(url)
            except Exception as e:
                logger.error(f"No se pudo abrir adjunto {sp}: {e}", exc_info=True)

    def _id_seleccionado(self):
        sel = self.tabla.selectedItems()
        if not sel:
            return None
        row = sel[0].row()
        it = self.tabla.item(row, 0)
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    # ------------------------------------------------------------------ CRUD
    def _nuevo_pago(self):
        # Modo creación: sin pago inicial
        self._abrir_dialogo(None)

    def _editar_pago_sel(self):
        pid = self._id_seleccionado()
        if not pid:
            QMessageBox.warning(self, "Selección", "Seleccione un pago.")
            return

        # Buscar el dict completo del pago en self.pagos_filtrados
        pago = next((p for p in self.pagos_filtrados or [] if p.get("id") == pid), None)
        if not pago:
            QMessageBox.warning(self, "Error", "No se encontraron los datos del pago seleccionado.")
            return

        self._abrir_dialogo(pago)

    def _abrir_dialogo(self, pago: dict | None):
        try:
            dialog = PagoOperadorDialog(
                firebase_manager=self.fm,
                storage_manager=self.sm,
                operadores_mapa=self.operadores_mapa,
                cuentas_mapa=self.cuentas_mapa,
                equipos_mapa=self.equipos_mapa,
                pago=pago,            # aquí va el dict, no pago_id
                parent=self,
                moneda_symbol="RD$",
            )
            if dialog.exec():
                self._recargar_por_fecha()
                self.recargar_dashboard.emit()
        except Exception as e:
            logger.error(f"Error abriendo diálogo de pago: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el diálogo:\n{e}")

    def _eliminar_pago_sel(self):
        pid = self._id_seleccionado()
        if not pid:
            QMessageBox.warning(self, "Selección", "Seleccione un pago.")
            return
        resp = QMessageBox.question(
            self,
            "Eliminar",
            f"¿Eliminar pago ID: {pid}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            ok = self.fm.eliminar_pago_operador(pid)
            if ok:
                QMessageBox.information(self, "Éxito", "Pago eliminado.")
                self._recargar_por_fecha()
                self.recargar_dashboard.emit()
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar.")
        except Exception as e:
            logger.error(f"Error eliminando pago {pid}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo eliminar:\n{e}")

    def _ver_adjunto_sel(self):
        pid = self._id_seleccionado()
        if not pid:
            QMessageBox.warning(self, "Selección", "Seleccione una fila.")
            return

        row = self.tabla.currentRow()
        it = self.tabla.item(row, 6)
        if not it:
            QMessageBox.information(self, "Adjunto", "No hay adjunto.")
            return

        sp = it.data(Qt.ItemDataRole.UserRole)
        if not sp:
            QMessageBox.information(self, "Adjunto", "No hay adjunto.")
            return

        try:
            url = self.sm.get_download_url(sp, prefer_firmada=True) if self.sm else None
            if url:
                webbrowser.open(url)
            else:
                QMessageBox.warning(self, "Adjunto", "No se pudo obtener URL del adjunto.")
        except Exception as e:
            logger.error(f"Error abriendo adjunto {sp}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo abrir el adjunto:\n{e}")