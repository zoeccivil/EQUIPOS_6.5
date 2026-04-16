from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QDateEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
    QTabWidget,
    QWidget,
    QGroupBox,
    QAbstractItemView,
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont
import logging

from firebase_manager import FirebaseManager
from report_generator import ReportGenerator

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
# ESTILOS
# ════════════════════════════════════════════════════════════

DIALOG_STYLE = """
QDialog {
    background-color: #FAFAFA;
    font-family: 'Segoe UI';
}

QGroupBox {
    font-weight: bold;
    color: #F59E0B;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
}

QTabWidget::pane {
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    background-color: #FFFFFF;
}
QTabBar::tab {
    background-color: #F3F4F6;
    color: #374151;
    padding: 8px 18px;
    border: 1px solid #E5E7EB;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
    font-size: 10pt;
}
QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #F59E0B;
    border-bottom: 2px solid #F59E0B;
}
QTabBar::tab:hover {
    background-color: #FEF3C7;
}

QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F9FAFB;
    gridline-color: #E5E7EB;
    selection-background-color: #FEF3C7;
    selection-color: #1F2937;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    font-size: 10pt;
}
QTableWidget::item {
    padding: 4px 8px;
    color: #1F2937;
}
QTableWidget::item:selected {
    background-color: #FEF3C7;
    color: #1F2937;
}

QHeaderView::section {
    background-color: #1F2937;
    color: #FFFFFF;
    padding: 8px 6px;
    border: none;
    font-weight: 600;
    font-size: 9pt;
}

QComboBox {
    background-color: #FFFFFF;
    color: #1F2937;
    border: 2px solid #E5E7EB;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 10pt;
    min-height: 25px;
}
QComboBox:hover {
    border: 2px solid #F59E0B;
}

QDateEdit {
    background-color: #FFFFFF;
    color: #1F2937;
    border: 2px solid #E5E7EB;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 10pt;
    min-height: 25px;
}
QDateEdit:hover {
    border: 2px solid #F59E0B;
}

QPushButton {
    background-color: #F59E0B;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
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

QLabel {
    color: #374151;
    font-size: 10pt;
}
"""


class DialogoPreviewReporteDetallado(QDialog):
    """
    Vista previa del Reporte Detallado de Equipos - V2.

    Tabs:
      1. Facturas (alquileres)
      2. Pagos y Rendimientos por Equipo
      3. Totales Globales

    Filtros: Cliente, Equipo, Rango de fechas.
    Exporta a PDF / Excel con gráfico de horas por equipo (matplotlib).
    """

    def __init__(
        self,
        fm: FirebaseManager,
        clientes_mapa: dict,
        config: dict,
        storage_manager,
        app_gui,
        parent=None,
    ):
        super().__init__(parent)
        self.fm = fm
        self.clientes_mapa = clientes_mapa or {}
        self.config = config or {}
        self.sm = storage_manager
        self.app = app_gui

        self.moneda = self.config.get("app", {}).get("moneda", "RD$")

        # Cargar mapas de equipos y operadores
        self.equipos_mapa = {}
        self.operadores_mapa = {}
        try:
            for eq in (self.fm.obtener_equipos(activo=None) or []):
                self.equipos_mapa[str(eq["id"])] = eq.get("nombre", f"Equipo {eq['id']}")
        except Exception as e:
            logger.error(f"Error cargando equipos: {e}")
        try:
            for ent in (self.fm.obtener_entidades(tipo="Operador", activo=None) or []):
                self.operadores_mapa[str(ent["id"])] = ent.get("nombre", f"Operador {ent['id']}")
        except Exception as e:
            logger.error(f"Error cargando operadores: {e}")

        # ═══════════════ VENTANA ═══════════════
        self.setWindowTitle("Preview - Reporte Detallado de Equipos")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(1200, 700)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)

        # ═══════════════ FILTROS ═══════════════
        filtros_box = QGroupBox("Filtros")
        filtros_layout = QHBoxLayout(filtros_box)

        # Cliente
        filtros_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.addItem("Todos", None)
        for cid, nombre in sorted(self.clientes_mapa.items(), key=lambda x: x[1]):
            self.combo_cliente.addItem(nombre, str(cid))
        filtros_layout.addWidget(self.combo_cliente)

        # Equipo
        filtros_layout.addWidget(QLabel("Equipo:"))
        self.combo_equipo = QComboBox()
        self.combo_equipo.addItem("Todos", None)
        for eid, nombre in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
            self.combo_equipo.addItem(nombre, str(eid))
        filtros_layout.addWidget(self.combo_equipo)

        # Fechas
        filtros_layout.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        filtros_layout.addWidget(self.fecha_inicio)

        filtros_layout.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit(calendarPopup=True)
        self.fecha_fin.setDisplayFormat("yyyy-MM-dd")
        filtros_layout.addWidget(self.fecha_fin)

        self.btn_actualizar = QPushButton("🔄 Actualizar")
        filtros_layout.addWidget(self.btn_actualizar)

        layout.addWidget(filtros_box)

        # ═══════════════ TABS ═══════════════
        self.tabs = QTabWidget()

        # Tab 1: Facturas
        self.tab_facturas = QWidget()
        tab1_layout = QVBoxLayout(self.tab_facturas)
        self.table_facturas = self._crear_tabla(
            8,
            ["Fecha", "Cliente", "Equipo", "Operador",
             "Ubicación", "Conduce", "Horas", f"Monto ({self.moneda})"],
        )
        tab1_layout.addWidget(self.table_facturas)
        # Fila de totales
        self.lbl_total_facturas = QLabel("")
        self.lbl_total_facturas.setStyleSheet(
            "font-weight: bold; font-size: 12pt; color: #1F7A1F; padding: 6px;"
        )
        tab1_layout.addWidget(self.lbl_total_facturas)
        self.tabs.addTab(self.tab_facturas, "📋 Facturas")

        # Tab 2: Pagos y Rendimientos
        self.tab_rendimientos = QWidget()
        tab2_layout = QVBoxLayout(self.tab_rendimientos)
        self.table_rendimientos = self._crear_tabla(
            6,
            ["Equipo",
             f"Facturado ({self.moneda})",
             f"Gastos ({self.moneda})",
             f"Pagos Op. ({self.moneda})",
             f"Rendimiento ({self.moneda})",
             "% Rendimiento"],
        )
        tab2_layout.addWidget(self.table_rendimientos)
        self.tabs.addTab(self.tab_rendimientos, "📊 Pagos y Rendimientos")

        # Tab 3: Totales Globales
        self.tab_totales = QWidget()
        tab3_layout = QVBoxLayout(self.tab_totales)
        self.table_totales = self._crear_tabla(
            2,
            ["Concepto", "Valor"],
            row_count=4,
            show_row_numbers=False,
        )
        tab3_layout.addWidget(self.table_totales)
        self.tabs.addTab(self.tab_totales, "💰 Totales Globales")

        layout.addWidget(self.tabs)

        # ═══════════════ BOTONES ═══════════════
        botones_layout = QHBoxLayout()
        self.btn_pdf = QPushButton("📄 Exportar PDF")
        self.btn_excel = QPushButton("📊 Exportar Excel")
        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.setStyleSheet(
            "background-color: #6B7280; color: white;"
        )

        botones_layout.addWidget(self.btn_pdf)
        botones_layout.addWidget(self.btn_excel)
        botones_layout.addStretch()
        botones_layout.addWidget(self.btn_cerrar)
        layout.addLayout(botones_layout)

        # ═══════════════ CONEXIONES ═══════════════
        self.btn_actualizar.clicked.connect(self.cargar_datos)
        self.btn_pdf.clicked.connect(lambda: self.exportar("pdf"))
        self.btn_excel.clicked.connect(lambda: self.exportar("excel"))
        self.btn_cerrar.clicked.connect(self.reject)

        self.combo_cliente.currentIndexChanged.connect(self.cargar_datos)
        self.combo_equipo.currentIndexChanged.connect(self.cargar_datos)
        self.fecha_inicio.dateChanged.connect(lambda _d: self.cargar_datos())
        self.fecha_fin.dateChanged.connect(lambda _d: self.cargar_datos())

        # Inicializar
        self._init_fechas()
        self.cargar_datos()

    # ════════════════════════════════════════════════════════════
    # HELPER: Crear tablas con estilo consistente
    # ════════════════════════════════════════════════════════════

    def _crear_tabla(self, col_count: int, headers: list, row_count: int = 0,
                     show_row_numbers: bool = True) -> QTableWidget:
        """Crea un QTableWidget con estilo limpio y consistente."""
        table = QTableWidget(row_count, col_count)
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)

        # Vertical header (números de fila)
        if show_row_numbers:
            table.verticalHeader().setVisible(True)
            table.verticalHeader().setDefaultSectionSize(28)
            table.verticalHeader().setMinimumSectionSize(22)
            table.verticalHeader().setFixedWidth(35)
            table.verticalHeader().setStyleSheet("""
                QHeaderView::section {
                    background-color: #F3F4F6;
                    color: #6B7280;
                    border: none;
                    border-bottom: 1px solid #E5E7EB;
                    font-size: 8pt;
                    padding: 2px 4px;
                }
            """)
        else:
            table.verticalHeader().setVisible(False)

        return table

    # ════════════════════════════════════════════════════════════
    # FECHAS
    # ════════════════════════════════════════════════════════════

    def _init_fechas(self):
        try:
            fecha_str = self.fm.obtener_fecha_primera_transaccion()
        except Exception:
            fecha_str = None

        if fecha_str:
            qd = QDate.fromString(fecha_str, "yyyy-MM-dd")
            if qd.isValid():
                self.fecha_inicio.setDate(qd)
            else:
                self.fecha_inicio.setDate(QDate.currentDate())
        else:
            self.fecha_inicio.setDate(QDate.currentDate())

        self.fecha_fin.setDate(QDate.currentDate())

    def _obtener_filtros(self) -> dict:
        cliente_id = self.combo_cliente.currentData()
        equipo_id = self.combo_equipo.currentData()
        if cliente_id is not None:
            cliente_id = str(cliente_id)
        if equipo_id is not None:
            equipo_id = str(equipo_id)

        return {
            "cliente_id": cliente_id,
            "equipo_id": equipo_id,
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
        }

    # ════════════════════════════════════════════════════════════
    # CARGA DE DATOS
    # ════════════════════════════════════════════════════════════

    def cargar_datos(self):
        """Carga las 3 pestañas con datos desde Firebase."""
        filtros = self._obtener_filtros()

        self._cargar_tab_facturas(filtros)
        self._cargar_tab_rendimientos(filtros)
        self._cargar_tab_totales(filtros)

    def _cargar_tab_facturas(self, filtros: dict):
        """Tab 1: Tabla de facturas/alquileres."""
        try:
            filtros_alq = {
                "fecha_inicio": filtros["fecha_inicio"],
                "fecha_fin": filtros["fecha_fin"],
            }
            if filtros["cliente_id"]:
                filtros_alq["cliente_id"] = filtros["cliente_id"]
            if filtros["equipo_id"]:
                filtros_alq["equipo_id"] = filtros["equipo_id"]

            alquileres = self.fm.obtener_alquileres(filtros_alq) or []
        except Exception as e:
            logger.error(f"Error obteniendo alquileres: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los alquileres:\n{e}")
            return

        # Enriquecer con nombres
        try:
            if hasattr(self.app, "_enriquecer_facturas_con_nombres"):
                self.app._enriquecer_facturas_con_nombres(alquileres)
        except Exception as e:
            logger.error(f"Error enriqueciendo nombres: {e}", exc_info=True)

        self.table_facturas.setRowCount(0)
        total_horas = 0.0
        total_monto = 0.0

        for row_data in alquileres:
            horas = float(row_data.get("horas", 0) or 0)
            monto = float(row_data.get("monto", 0) or 0)
            total_horas += horas
            total_monto += monto

            fila = self.table_facturas.rowCount()
            self.table_facturas.insertRow(fila)

            valores = [
                str(row_data.get("fecha", "")),
                row_data.get("cliente_nombre", ""),
                row_data.get("equipo_nombre", ""),
                row_data.get("operador_nombre", ""),
                row_data.get("ubicacion", ""),
                row_data.get("conduce", ""),
                f"{horas:,.2f}",
                f"{self.moneda} {monto:,.2f}",
            ]
            for col, val in enumerate(valores):
                self.table_facturas.setItem(fila, col, QTableWidgetItem(str(val)))

        self.lbl_total_facturas.setText(
            f"Total: {len(alquileres)} facturas  |  "
            f"Horas: {total_horas:,.2f}  |  "
            f"Monto: {self.moneda} {total_monto:,.2f}"
        )

    def _cargar_tab_rendimientos(self, filtros: dict):
        """Tab 2: Pagos y Rendimientos por Equipo."""
        fi = filtros["fecha_inicio"]
        ff = filtros["fecha_fin"]
        equipo_filtro = filtros.get("equipo_id")

        try:
            # Facturado por equipo
            filtros_alq = {"fecha_inicio": fi, "fecha_fin": ff}
            if filtros["cliente_id"]:
                filtros_alq["cliente_id"] = filtros["cliente_id"]
            if equipo_filtro:
                filtros_alq["equipo_id"] = equipo_filtro

            alquileres = self.fm.obtener_alquileres(filtros_alq) or []

            facturado_por_equipo = {}
            for alq in alquileres:
                eid = str(alq.get("equipo_id") or "")
                if not eid:
                    continue
                monto = float(alq.get("monto", 0) or 0)
                facturado_por_equipo[eid] = facturado_por_equipo.get(eid, 0.0) + monto

            # Gastos por equipo
            filtros_gastos = {"fecha_inicio": fi, "fecha_fin": ff}
            if equipo_filtro:
                filtros_gastos["equipo_id"] = equipo_filtro
            gastos_list = self.fm.obtener_gastos(filtros_gastos) or []

            gastos_por_equipo = {}
            for g in gastos_list:
                eid = str(g.get("equipo_id") or "")
                if not eid:
                    continue
                monto = float(g.get("monto", 0) or 0)
                gastos_por_equipo[eid] = gastos_por_equipo.get(eid, 0.0) + monto

            # Pagos operadores por equipo
            filtros_pagos = {"fecha_inicio": fi, "fecha_fin": ff}
            pagos_op_list = self.fm.obtener_pagos_operadores(filtros_pagos) or []

            pagos_op_por_equipo = {}
            for p in pagos_op_list:
                eid = str(p.get("equipo_id") or "")
                if not eid:
                    continue
                if equipo_filtro and eid != equipo_filtro:
                    continue
                monto = float(p.get("monto", 0) or 0)
                pagos_op_por_equipo[eid] = pagos_op_por_equipo.get(eid, 0.0) + monto

            all_eids = set(facturado_por_equipo.keys()) | set(gastos_por_equipo.keys()) | set(pagos_op_por_equipo.keys())

            self.table_rendimientos.setRowCount(0)
            self._rendimientos_data = []

            for eid in sorted(all_eids, key=lambda x: self.equipos_mapa.get(x, x)):
                nombre = self.equipos_mapa.get(eid, f"Equipo {eid}")
                facturado = facturado_por_equipo.get(eid, 0.0)
                gastos = gastos_por_equipo.get(eid, 0.0)
                pagos_op = pagos_op_por_equipo.get(eid, 0.0)
                rendimiento = facturado - (gastos + pagos_op)
                pct = (rendimiento / facturado * 100.0) if facturado > 0 else 0.0

                self._rendimientos_data.append({
                    "equipo": nombre,
                    "facturado": facturado,
                    "gastos": gastos,
                    "pagos_op": pagos_op,
                    "rendimiento": rendimiento,
                    "pct": pct,
                })

                fila = self.table_rendimientos.rowCount()
                self.table_rendimientos.insertRow(fila)

                items = [
                    nombre,
                    f"{self.moneda} {facturado:,.2f}",
                    f"{self.moneda} {gastos:,.2f}",
                    f"{self.moneda} {pagos_op:,.2f}",
                    f"{self.moneda} {rendimiento:,.2f}",
                    f"{pct:,.1f}%",
                ]
                for col, val in enumerate(items):
                    item = QTableWidgetItem(str(val))
                    if col == 4:
                        item.setForeground(
                            QColor("#2E7D32") if rendimiento >= 0 else QColor("#D32F2F")
                        )
                        item.setFont(QFont("Segoe UI", weight=QFont.Weight.Bold))
                    if col == 5:
                        item.setForeground(
                            QColor("#2E7D32") if pct >= 0 else QColor("#D32F2F")
                        )
                    self.table_rendimientos.setItem(fila, col, item)

        except Exception as e:
            logger.error(f"Error cargando rendimientos: {e}", exc_info=True)

    def _cargar_tab_totales(self, filtros: dict):
        """Tab 3: Totales Globales."""
        fi = filtros["fecha_inicio"]
        ff = filtros["fecha_fin"]
        equipo_filtro = filtros.get("equipo_id")

        try:
            # Total alquileres
            filtros_alq = {"fecha_inicio": fi, "fecha_fin": ff}
            if filtros["cliente_id"]:
                filtros_alq["cliente_id"] = filtros["cliente_id"]
            if equipo_filtro:
                filtros_alq["equipo_id"] = equipo_filtro
            alquileres = self.fm.obtener_alquileres(filtros_alq) or []
            total_alquileres = sum(float(a.get("monto", 0) or 0) for a in alquileres)

            # Total abonos — filtrados según los clientes de los alquileres del período/equipo
            if filtros["cliente_id"]:
                # Filtro explícito por cliente
                abonos = self.fm.obtener_abonos(
                    cliente_id=filtros["cliente_id"],
                    fecha_inicio=fi,
                    fecha_fin=ff,
                ) or []
                total_abonos = sum(float(a.get("monto", 0) or 0) for a in abonos)
            elif equipo_filtro:
                # Filtro solo por equipo: sumar abonos de los clientes que aparecen
                # en los alquileres filtrados, para no traer abonos de otros equipos
                clientes_del_equipo = {
                    str(a.get("cliente_id", ""))
                    for a in alquileres
                    if a.get("cliente_id")
                }
                total_abonos = 0.0
                for cid in clientes_del_equipo:
                    abonos_c = self.fm.obtener_abonos(
                        cliente_id=cid,
                        fecha_inicio=fi,
                        fecha_fin=ff,
                    ) or []
                    total_abonos += sum(float(a.get("monto", 0) or 0) for a in abonos_c)
            else:
                # Sin filtros específicos: todos los abonos del período
                abonos = self.fm.obtener_abonos(fecha_inicio=fi, fecha_fin=ff) or []
                total_abonos = sum(float(a.get("monto", 0) or 0) for a in abonos)

            # Gastos
            filtros_gastos = {"fecha_inicio": fi, "fecha_fin": ff}
            if equipo_filtro:
                filtros_gastos["equipo_id"] = equipo_filtro
            gastos_list = self.fm.obtener_gastos(filtros_gastos) or []
            total_gastos = sum(
                float(g.get("monto", 0) or 0)
                for g in gastos_list
                if str(g.get("equipo_id") or "")
            )

            # Pagos operadores
            filtros_pagos = {"fecha_inicio": fi, "fecha_fin": ff}
            pagos_op_list = self.fm.obtener_pagos_operadores(filtros_pagos) or []
            total_pagos_op = 0.0
            for p in pagos_op_list:
                eid = str(p.get("equipo_id") or "")
                if not eid:
                    continue
                if equipo_filtro and eid != equipo_filtro:
                    continue
                total_pagos_op += float(p.get("monto", 0) or 0)

            total_gastos_globales = total_gastos + total_pagos_op
            rendimiento_global = total_alquileres - total_gastos_globales

            self._totales_data = {
                "total_alquileres": total_alquileres,
                "total_abonos": total_abonos,
                "total_gastos_globales": total_gastos_globales,
                "rendimiento_global": rendimiento_global,
            }

            # Llenar tabla
            self.table_totales.setRowCount(4)
            conceptos = [
                ("Total Alquileres (Facturado)", total_alquileres, "#1565C0"),
                ("Total Abonos (Cobrado)", total_abonos, "#F59E0B"),
                ("Total Gastos Globales (Gastos + Pagos Op.)", total_gastos_globales, "#D32F2F"),
                ("Rendimiento Global", rendimiento_global, None),
            ]
            for row, (concepto, valor, color) in enumerate(conceptos):
                item_concepto = QTableWidgetItem(concepto)
                item_concepto.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                self.table_totales.setItem(row, 0, item_concepto)

                item_valor = QTableWidgetItem(f"{self.moneda} {valor:,.2f}")
                item_valor.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                item_valor.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))

                if row == 3:  # Rendimiento
                    rend_color = "#2E7D32" if valor >= 0 else "#D32F2F"
                    item_valor.setForeground(QColor(rend_color))
                    item_concepto.setForeground(QColor(rend_color))
                elif color:
                    item_valor.setForeground(QColor(color))

                self.table_totales.setItem(row, 1, item_valor)

        except Exception as e:
            logger.error(f"Error cargando totales: {e}", exc_info=True)

    # ════════════════════════════════════════════════════════════
    # EXPORTAR
    # ════════════════════════════════════════════════════════════

    def _construir_dataset(self):
        """Construye el dataset completo para ReportGenerator."""
        filtros = self._obtener_filtros()

        filtros_alq = {
            "fecha_inicio": filtros["fecha_inicio"],
            "fecha_fin": filtros["fecha_fin"],
        }
        if filtros["cliente_id"]:
            filtros_alq["cliente_id"] = filtros["cliente_id"]
        if filtros["equipo_id"]:
            filtros_alq["equipo_id"] = filtros["equipo_id"]

        alquileres = self.fm.obtener_alquileres(filtros_alq) or []

        try:
            if hasattr(self.app, "_enriquecer_facturas_con_nombres"):
                self.app._enriquecer_facturas_con_nombres(alquileres)
        except Exception as e:
            logger.error(f"Error enriqueciendo nombres (export): {e}", exc_info=True)

        datos = []
        for row in alquileres:
            horas = float(row.get("horas", 0) or 0)
            monto = float(row.get("monto", 0) or 0)

            datos.append({
                "fecha": str(row.get("fecha", "")),
                "cliente": row.get("cliente_nombre", ""),
                "equipo": row.get("equipo_nombre", ""),
                "operador": row.get("operador_nombre", ""),
                "ubicacion": row.get("ubicacion", ""),
                "conduce": row.get("conduce", ""),
                "horas": f"{horas:,.2f}",
                "monto": f"{self.moneda} {monto:,.2f}",
                # Raw values para gráficos
                "horas_raw": horas,
                "monto_raw": monto,
                "equipo_id": str(row.get("equipo_id", "")),
            })

        return datos, filtros

    def exportar(self, formato: str):
        """Exporta a PDF o Excel usando ReportGenerator."""
        try:
            datos, filtros = self._construir_dataset()
            if not datos:
                QMessageBox.information(self, "Sin datos", "No hay datos para exportar.")
                return

            ext = "PDF (*.pdf)" if formato == "pdf" else "Excel (*.xlsx)"
            sugerido = (
                f"Reporte_Detallado_Equipos_{filtros['fecha_inicio']}_a_{filtros['fecha_fin']}"
            ).replace(" ", "_")
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Guardar Reporte Detallado de Equipos", sugerido, ext,
            )
            if not file_path:
                return

            # Obtener gastos del período para incluirlos en el reporte
            try:
                filtros_gastos = {
                    "fecha_inicio": filtros["fecha_inicio"],
                    "fecha_fin": filtros["fecha_fin"],
                }
                if filtros.get("equipo_id"):
                    filtros_gastos["equipo_id"] = filtros["equipo_id"]
                gastos_list = self.fm.obtener_gastos(filtros_gastos) or []
            except Exception as e:
                logger.error(f"Error obteniendo gastos para exportar: {e}", exc_info=True)
                gastos_list = []

            # Obtener pagos de operadores del período para incluirlos en el reporte
            try:
                filtros_pagos = {
                    "fecha_inicio": filtros["fecha_inicio"],
                    "fecha_fin": filtros["fecha_fin"],
                }
                pagos_op_list = self.fm.obtener_pagos_operadores(filtros_pagos) or []
                # Filtrar por equipo si aplica
                if filtros.get("equipo_id"):
                    pagos_op_list = [
                        p for p in pagos_op_list
                        if str(p.get("equipo_id") or "") == filtros["equipo_id"]
                    ]
            except Exception as e:
                logger.error(f"Error obteniendo pagos operadores para exportar: {e}", exc_info=True)
                pagos_op_list = []

            column_map = {
                "fecha": "Fecha",
                "cliente": "Cliente",
                "equipo": "Equipo",
                "operador": "Operador",
                "ubicacion": "Ubicación",
                "conduce": "Conduce",
                "horas": "Horas",
                "monto": f"Monto ({self.moneda})",
            }

            title = "REPORTE DETALLADO DE EQUIPOS"
            date_range = f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"

            rg = ReportGenerator(
                data=datos,
                title=title,
                cliente="",
                date_range=date_range,
                currency_symbol=self.moneda,
                storage_manager=self.sm,
                column_map=column_map,
            )

            # Pasar datos de rendimientos, totales, gastos y pagos al generador
            rg.rendimientos_por_equipo = getattr(self, "_rendimientos_data", [])
            rg.totales_globales = getattr(self, "_totales_data", {})
            rg.equipos_mapa = self.equipos_mapa
            rg.operadores_mapa = self.operadores_mapa
            rg.gastos_list = gastos_list
            rg.pagos_op_list = pagos_op_list

            if formato == "pdf":
                ok, error = rg.to_pdf_reporte_detallado(file_path)
            else:
                ok, error = rg.to_excel(file_path)

            if ok:
                QMessageBox.information(
                    self, "Éxito",
                    f"Reporte detallado generado exitosamente:\n{file_path}",
                )
            else:
                QMessageBox.critical(
                    self, "Error",
                    f"No se pudo generar el reporte detallado:\n{error}",
                )

        except Exception as e:
            logger.error(f"Error exportando reporte detallado: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Ocurrió un error al exportar:\n{e}")