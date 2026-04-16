# cuentas_por_cobrar.py

"""
Cuentas por Cobrar — Gestión de cobros y seguimiento de pagos pendientes.
Lee alquileres de Firestore, suma los pagos de cada subcolección
alquileres/{id}/pagos y calcula el saldo real de cada factura.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox, QDateEdit,
    QComboBox, QMessageBox, QAbstractItemView, QGroupBox, QFrame,
    QTextEdit,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush
import logging
import uuid
from datetime import datetime, timedelta
from firebase_manager import FirebaseManager

logger = logging.getLogger(__name__)

# ── Estilos ────────────────────────────────────────────────────────────────────
CUENTAS_STYLE = """
QWidget { background-color: #F3F4F6; font-family: 'Segoe UI'; }
QLabel[class="title"]       { font-size: 20pt; font-weight: bold; color: #1F2937; }
QLabel[class="deuda-label"] { font-size: 11pt; color: #6B7280; font-weight: 500; }
QLabel[class="deuda-value"] { font-size: 22pt; font-weight: bold; }
QLabel[class="deuda-vencida"]    { color: #DC2626; }
QLabel[class="deuda-por-vencer"] { color: #F59E0B; }
QLabel[class="deuda-al-dia"]     { color: #059669; }
QFrame[class="deuda-card"]           { background-color:#FFFFFF; border:2px solid #E5E7EB; border-radius:12px; padding:20px; }
QFrame[class="deuda-card-vencida"]   { background-color:#FFFFFF; border:3px solid #DC2626; border-radius:12px; padding:20px; }
QFrame[class="deuda-card-advertencia"]{ background-color:#FFFFFF; border:3px solid #F59E0B; border-radius:12px; padding:20px; }
QPushButton { background-color:#F59E0B; color:white; border:none; border-radius:6px;
              padding:10px 18px; font-size:10pt; font-weight:600; min-height:25px; }
QPushButton:hover   { background-color:#D97706; }
QPushButton:pressed { background-color:#B45309; }
QPushButton[class="secondary"] { background-color:#E5E7EB; color:#374151; }
QPushButton[class="secondary"]:hover { background-color:#D1D5DB; }
QPushButton[class="danger"]  { background-color:#DC2626; color:white; }
QPushButton[class="danger"]:hover  { background-color:#B91C1C; }
QPushButton[class="success"] { background-color:#059669; color:white; }
QPushButton[class="success"]:hover { background-color:#047857; }
QTableWidget { background-color:#FFFFFF; alternate-background-color:#F9FAFB;
               gridline-color:#E5E7EB; selection-background-color:#FEF3C7;
               selection-color:#1F2937; border:1px solid #E5E7EB; border-radius:6px; }
QTableWidget::item { padding:8px; }
QHeaderView::section { background-color:#1F2937; color:#FFFFFF; padding:10px;
                        border:none; font-weight:600; }
QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox, QTextEdit {
    background-color:#FFFFFF; border:2px solid #E5E7EB; border-radius:6px;
    padding:8px 12px; color:#1F2937; font-size:10pt; }
QLineEdit:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus { border:2px solid #F59E0B; }
QGroupBox { background-color:#FFFFFF; border:2px solid #E5E7EB; border-radius:10px;
            margin-top:14px; padding:15px; font-weight:600; font-size:12pt; color:#1F2937; }
QGroupBox::title { subcontrol-origin:margin; left:15px; padding:0 8px; background-color:#FFFFFF; }
QProgressBar { border:2px solid #E5E7EB; border-radius:6px; text-align:center;
               background-color:#F3F4F6; height:25px; }
QProgressBar::chunk { background-color:#F59E0B; border-radius:4px; }
"""

# ── Helpers de estado ──────────────────────────────────────────────────────────
ICONOS_ESTADO = {
    'al_dia':          '✅ Al Día',
    'por_vencer':      '⚠️ Por Vencer (≤45d)',
    'vencida_15':      '🟡 Vencida ≤15 días',
    'vencida_30':      '🟠 Vencida ≤30 días',
    'vencida_45':      '🔴 Vencida ≤45 días',
    'vencida_mas':     '🚨 Vencida >45 días',
    'pagada':          '💚 Pagada',
    'sin_vencimiento': '📅 Sin Venc.',
}
COLOR_ESTADO = {
    'por_vencer':   QColor("#FEF3C7"),   # amarillo claro
    'vencida_15':   QColor("#FEF9C3"),   # amarillo suave
    'vencida_30':   QColor("#FED7AA"),   # naranja claro
    'vencida_45':   QColor("#FCA5A5"),   # rojo claro
    'vencida_mas':  QColor("#F87171"),   # rojo fuerte
    'pagada':       QColor("#D1FAE5"),   # verde claro
}


def _calcular_estado(fecha_vencimiento: str, saldo: float) -> str:
    """
    Clasifica la factura según días de retraso:
      al_dia        → aún no vence
      por_vencer    → vence en ≤ 45 días
      vencida_15    → vencida entre 1 y 15 días
      vencida_30    → vencida entre 16 y 30 días
      vencida_45    → vencida entre 31 y 45 días
      vencida_mas   → vencida > 45 días
    """
    if saldo <= 0:
        return "pagada"
    if not fecha_vencimiento:
        return "sin_vencimiento"
    try:
        dias_hasta_venc = (
            datetime.strptime(fecha_vencimiento, "%Y-%m-%d") - datetime.now()
        ).days
        if dias_hasta_venc >= 0:
            # Aún no venció
            return "por_vencer" if dias_hasta_venc <= 45 else "al_dia"
        # Ya venció — dias_retraso es positivo
        dias_retraso = -dias_hasta_venc
        if dias_retraso <= 15:
            return "vencida_15"
        if dias_retraso <= 30:
            return "vencida_30"
        if dias_retraso <= 45:
            return "vencida_45"
        return "vencida_mas"
    except Exception:
        return "sin_vencimiento"


# ── DeudaCard ──────────────────────────────────────────────────────────────────
class DeudaCard(QFrame):
    """Tarjeta de resumen de deuda."""

    _VALUE_CLASS = {
        "vencida":     "deuda-value deuda-vencida",
        "advertencia": "deuda-value deuda-por-vencer",
    }

    def __init__(self, titulo, monto, moneda, tipo="normal", parent=None):
        super().__init__(parent)
        self.moneda = moneda
        frame_class = (
            "deuda-card-vencida"    if tipo == "vencida"     else
            "deuda-card-advertencia" if tipo == "advertencia" else
            "deuda-card"
        )
        self.setProperty("class", frame_class)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setProperty("class", "deuda-label")
        layout.addWidget(lbl_titulo)

        self.lbl_monto = QLabel(f"{moneda} {monto:,.2f}")
        self.lbl_monto.setProperty("class", self._VALUE_CLASS.get(tipo, "deuda-value deuda-al-dia"))
        layout.addWidget(self.lbl_monto)

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color:#6B7280; font-size:9pt;")
        layout.addWidget(self.lbl_count)

        layout.addStretch()

    def actualizar(self, monto: float, count: int = 0):
        self.lbl_monto.setText(f"{self.moneda} {monto:,.2f}")
        self.lbl_count.setText(f"{count} factura(s)" if count else "")


# ── CuentasPorCobrar ───────────────────────────────────────────────────────────
class CuentasPorCobrar(QWidget):
    """Widget principal para gestión de cuentas por cobrar."""

    def __init__(self, fm: FirebaseManager, config: dict, parent=None):
        super().__init__(parent)
        self.fm = fm
        self.config = config
        self.moneda = config.get('app', {}).get('moneda', 'RD$')

        self.cuentas: list[dict] = []
        self.clientes_mapa: dict[str, str] = {}
        self.cuentas_bancarias: dict[str, str] = {}

        self.setStyleSheet(CUENTAS_STYLE)
        self._init_ui()
        self._cargar_clientes()
        self._cargar_cuentas_bancarias()
        self._cargar_datos()

    # ── UI ─────────────────────────────────────────────────────────────────────
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(10)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        titulo = QLabel("💳 Cuentas por Cobrar")
        titulo.setProperty("class", "title")
        header.addWidget(titulo)
        header.addStretch()

        header.addWidget(self._lbl_filtro("Estado:"))
        self.combo_estado = QComboBox()
        for texto, data in [
            ("Todas",                 "todas"),
            ("Pendientes",            "pendientes"),
            ("Al Día",                "al_dia"),
            ("Por Vencer (≤45 días)", "por_vencer"),
            ("Vencida ≤15 días",      "vencida_15"),
            ("Vencida ≤30 días",      "vencida_30"),
            ("Vencida ≤45 días",      "vencida_45"),
            ("Vencida >45 días",      "vencida_mas"),
            ("Todas las vencidas",    "vencidas_todas"),
            ("Pagadas",               "pagada"),
        ]:
            self.combo_estado.addItem(texto, data)
        self.combo_estado.currentIndexChanged.connect(self._aplicar_filtros)
        header.addWidget(self.combo_estado)

        header.addWidget(self._lbl_filtro("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.setMinimumWidth(180)
        self.combo_cliente.addItem("Todos", None)
        self.combo_cliente.currentIndexChanged.connect(self._aplicar_filtros)
        header.addWidget(self.combo_cliente)

        btn_actualizar = QPushButton("🔄 Actualizar")
        btn_actualizar.clicked.connect(self._cargar_datos)
        header.addWidget(btn_actualizar)
        layout.addLayout(header)

        # ── Barra de KPIs compacta (una sola fila, altura fija) ───────────────
        kpi_frame = QFrame()
        kpi_frame.setFixedHeight(72)
        kpi_frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:8px; }")
        kpi_row = QHBoxLayout(kpi_frame)
        kpi_row.setContentsMargins(10, 6, 10, 6)
        kpi_row.setSpacing(0)

        # Definición: (attr, label, bg, border, text_color)
        kpi_defs = [
            ("card_total",      "💰 Total Pendiente",  "#F9FAFB", "#E5E7EB", "#1F2937"),
            ("card_cobrado",    "✅ Cobrado Mes",       "#F0FDF4", "#86EFAC", "#166534"),
            ("card_por_vencer", "⚠️ Por Vencer ≤45d", "#FFFBEB", "#FCD34D", "#92400E"),
            ("card_v15",        "🟡 Vencida ≤15d",    "#FEFCE8", "#FDE047", "#713F12"),
            ("card_v30",        "🟠 Vencida ≤30d",    "#FFF7ED", "#FDBA74", "#9A3412"),
            ("card_v45",        "🔴 Vencida ≤45d",    "#FEF2F2", "#FCA5A5", "#991B1B"),
            ("card_vmas",       "🚨 Vencida >45d",    "#FFF1F2", "#FB7185", "#881337"),
        ]

        for i, (attr, label, bg, border, fg) in enumerate(kpi_defs):
            # Separador vertical entre cards
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.VLine)
                sep.setStyleSheet("color:#E5E7EB;")
                kpi_row.addWidget(sep)

            cell = QFrame()
            cell.setStyleSheet(
                f"QFrame {{ background:{bg}; border:1px solid {border};"
                f" border-radius:6px; }}")
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(8, 4, 8, 4)
            cell_layout.setSpacing(1)

            lbl_titulo = QLabel(label)
            lbl_titulo.setStyleSheet("font-size:8pt; color:#6B7280; font-weight:600;")
            lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl_monto = QLabel(f"{self.moneda} 0.00")
            lbl_monto.setStyleSheet(f"font-size:11pt; font-weight:bold; color:{fg};")
            lbl_monto.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl_count = QLabel("")
            lbl_count.setStyleSheet("font-size:7pt; color:#9CA3AF;")
            lbl_count.setAlignment(Qt.AlignmentFlag.AlignCenter)

            cell_layout.addWidget(lbl_titulo)
            cell_layout.addWidget(lbl_monto)
            cell_layout.addWidget(lbl_count)

            kpi_row.addWidget(cell, stretch=1)

            # Guardar referencias para actualizar después
            setattr(self, f"_kpi_monto_{attr}", lbl_monto)
            setattr(self, f"_kpi_count_{attr}", lbl_count)

        layout.addWidget(kpi_frame)

        # ── Tabla (ocupa todo el espacio restante) ────────────────────────────
        grupo_tabla = QGroupBox("📋 Detalle de Cuentas")
        layout_tabla = QVBoxLayout(grupo_tabla)
        layout_tabla.setSpacing(6)

        botones = QHBoxLayout()
        btn_pago = QPushButton("💵 Registrar Pago")
        btn_pago.setProperty("class", "success")
        btn_pago.clicked.connect(self._registrar_pago)
        botones.addWidget(btn_pago)

        btn_abono = QPushButton("🏦 Registrar Abono")
        btn_abono.clicked.connect(self._registrar_abono_cliente)
        botones.addWidget(btn_abono)

        btn_recordatorio = QPushButton("📱 WhatsApp")
        btn_recordatorio.clicked.connect(self._enviar_recordatorio)
        botones.addWidget(btn_recordatorio)

        btn_estado_cuenta = QPushButton("📄 Estado de Cuenta")
        btn_estado_cuenta.setProperty("class", "secondary")
        btn_estado_cuenta.clicked.connect(self._generar_estado_cuenta)
        botones.addWidget(btn_estado_cuenta)

        btn_exportar = QPushButton("📊 Excel")
        btn_exportar.setProperty("class", "secondary")
        btn_exportar.clicked.connect(self._exportar_excel)
        botones.addWidget(btn_exportar)

        botones.addStretch()
        self.lbl_conteo = QLabel("0 registros")
        self.lbl_conteo.setStyleSheet("color:#6B7280; font-size:9pt;")
        botones.addWidget(self.lbl_conteo)
        layout_tabla.addLayout(botones)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(9)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Cliente", "Factura/Conduce", "Fecha Emisión",
            "Vencimiento", "Monto Total", "Pagado", "Saldo", "Estado",
        ])
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.itemDoubleClicked.connect(self._ver_detalle)
        layout_tabla.addWidget(self.tabla)

        # ── Barra de totales del filtro actual ────────────────────────────────
        totales_frame = QFrame()
        totales_frame.setFixedHeight(36)
        totales_frame.setStyleSheet(
            "QFrame { background:#1F2937; border-radius:6px; }"
            "QLabel  { color:#F9FAFB; font-size:9pt; font-weight:600; }"
        )
        totales_row = QHBoxLayout(totales_frame)
        totales_row.setContentsMargins(14, 0, 14, 0)
        totales_row.setSpacing(30)

        def _stat(icono, texto_attr):
            lbl = QLabel(f"{icono}  —")
            lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            totales_row.addWidget(lbl)
            setattr(self, texto_attr, lbl)

        _stat("📄 Facturas:",        "_tot_facturas")
        _stat("✅ Pagado:",          "_tot_pagado")
        _stat("💳 Adeudado:",        "_tot_adeudado")
        _stat("📅 Deuda más antigua:","_tot_antigua")
        totales_row.addStretch()

        layout_tabla.addWidget(totales_frame)

        # stretch=1 hace que la tabla tome todo el espacio vertical disponible
        layout.addWidget(grupo_tabla, stretch=1)

    @staticmethod
    def _lbl_filtro(texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet("font-weight:600; color:#374151;")
        return lbl

    # ── Carga de datos ─────────────────────────────────────────────────────────
    def _cargar_clientes(self):
        try:
            clientes = self.fm.obtener_entidades(tipo="Cliente", activo=True) or []
            self.clientes_mapa = {str(c['id']): c['nombre'] for c in clientes}
            self.combo_cliente.blockSignals(True)
            self.combo_cliente.clear()
            self.combo_cliente.addItem("Todos", None)
            for cid, nombre in sorted(self.clientes_mapa.items(), key=lambda x: x[1]):
                self.combo_cliente.addItem(nombre, cid)
            self.combo_cliente.blockSignals(False)
        except Exception as e:
            logger.error(f"Error cargando clientes: {e}", exc_info=True)

    def _cargar_cuentas_bancarias(self):
        try:
            mapa = self.fm.obtener_mapa_global("cuentas") or {}
            self.cuentas_bancarias = {str(k): v for k, v in mapa.items()}
        except Exception as e:
            logger.error(f"Error cargando cuentas bancarias: {e}", exc_info=True)

    def _cargar_datos(self):
        """
        Carga todos los alquileres y calcula monto_pagado sumando la
        subcolección alquileres/{id}/pagos de cada uno.
        """
        try:
            alquileres = self.fm.obtener_alquileres({}) or []

            if not alquileres:
                self.cuentas = []
                self._aplicar_filtros()
                return

            # Traer pagos de todos los alquileres en batch
            ids = [str(a.get('id', '')) for a in alquileres if a.get('id')]
            pagos_mapa = self.fm.obtener_pagos_por_alquileres(ids)  # {alq_id: total_pagado}

            # También traer abonos del mes actual para la métrica "Cobrado Este Mes"
            inicio_mes = datetime.now().replace(day=1).strftime("%Y-%m-%d")
            fin_mes    = datetime.now().strftime("%Y-%m-%d")
            try:
                abonos_mes = self.fm.obtener_abonos(
                    fecha_inicio=inicio_mes,
                    fecha_fin=fin_mes,
                ) or []
            except Exception:
                abonos_mes = []
            self._cobrado_mes = sum(float(a.get('monto', 0)) for a in abonos_mes)

            self.cuentas = []
            for alquiler in alquileres:
                alq_id      = str(alquiler.get('id', ''))
                monto_total = float(alquiler.get('monto', 0) or 0)

                if monto_total <= 0:
                    continue

                monto_pagado = float(pagos_mapa.get(alq_id, 0.0))
                saldo        = max(0.0, monto_total - monto_pagado)

                fecha_venc = (
                    alquiler.get('fecha_vencimiento_pago') or
                    alquiler.get('fecha_fin') or ''
                )
                estado = _calcular_estado(fecha_venc, saldo)

                # Identificador visible de la factura
                factura = (
                    alquiler.get('numero_factura') or
                    alquiler.get('conduce') or
                    alquiler.get('descripcion') or
                    f"ALQ-{alq_id[:8]}"
                )

                self.cuentas.append({
                    'id':               alq_id,
                    'cliente_id':       str(alquiler.get('cliente_id', '')),
                    'factura':          factura,
                    'fecha_emision':    alquiler.get('fecha') or alquiler.get('fecha_inicio', ''),
                    'fecha_vencimiento':fecha_venc,
                    'monto_total':      monto_total,
                    'monto_pagado':     monto_pagado,
                    'saldo':            saldo,
                    'estado':           estado,
                    'alquiler':         alquiler,
                })

            self._aplicar_filtros()

        except Exception as e:
            logger.error(f"Error cargando cuentas por cobrar: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al cargar datos:\n{e}")

    # ── Filtros y vista ────────────────────────────────────────────────────────
    # Estados que se consideran "vencidos" para agrupar
    _VENCIDOS = {'vencida_15', 'vencida_30', 'vencida_45', 'vencida_mas'}

    def _aplicar_filtros(self):
        try:
            estado_filtro = self.combo_estado.currentData()
            cliente_id    = self.combo_cliente.currentData()

            filtradas = self.cuentas

            if estado_filtro == "pendientes":
                filtradas = [c for c in filtradas if c['estado'] != 'pagada']
            elif estado_filtro == "vencidas_todas":
                filtradas = [c for c in filtradas if c['estado'] in self._VENCIDOS]
            elif estado_filtro != "todas":
                filtradas = [c for c in filtradas if c['estado'] == estado_filtro]

            if cliente_id:
                filtradas = [c for c in filtradas if c['cliente_id'] == cliente_id]

            self._actualizar_resumen()
            self._actualizar_tabla(filtradas)

        except Exception as e:
            logger.error(f"Error aplicando filtros: {e}", exc_info=True)

    def _kpi_set(self, attr: str, monto: float, count: int = 0):
        """Actualiza los labels del KPI compacto."""
        lbl_m = getattr(self, f"_kpi_monto_{attr}", None)
        lbl_c = getattr(self, f"_kpi_count_{attr}", None)
        if lbl_m:
            lbl_m.setText(f"{self.moneda} {monto:,.2f}")
        if lbl_c:
            lbl_c.setText(f"{count} factura(s)" if count else "")

    def _actualizar_resumen(self):
        pendientes = [c for c in self.cuentas if c['estado'] != 'pagada']
        por_vencer = [c for c in self.cuentas if c['estado'] == 'por_vencer']
        v15  = [c for c in self.cuentas if c['estado'] == 'vencida_15']
        v30  = [c for c in self.cuentas if c['estado'] == 'vencida_30']
        v45  = [c for c in self.cuentas if c['estado'] == 'vencida_45']
        vmas = [c for c in self.cuentas if c['estado'] == 'vencida_mas']

        self._kpi_set("card_total",      sum(c['saldo'] for c in pendientes), len(pendientes))
        self._kpi_set("card_cobrado",    getattr(self, '_cobrado_mes', 0.0))
        self._kpi_set("card_por_vencer", sum(c['saldo'] for c in por_vencer), len(por_vencer))
        self._kpi_set("card_v15",        sum(c['saldo'] for c in v15),  len(v15))
        self._kpi_set("card_v30",        sum(c['saldo'] for c in v30),  len(v30))
        self._kpi_set("card_v45",        sum(c['saldo'] for c in v45),  len(v45))
        self._kpi_set("card_vmas",       sum(c['saldo'] for c in vmas), len(vmas))

    def _actualizar_tabla(self, cuentas: list[dict]):
        self.tabla.setRowCount(0)

        # Orden: más vencidas primero, luego por fecha de vencimiento
        orden = {
            'vencida_mas': 0, 'vencida_45': 1, 'vencida_30': 2, 'vencida_15': 3,
            'por_vencer': 4, 'sin_vencimiento': 5, 'al_dia': 6, 'pagada': 7,
        }
        cuentas_ord = sorted(
            cuentas,
            key=lambda c: (orden.get(c['estado'], 8), c['fecha_vencimiento'] or '9999'),
        )

        for cuenta in cuentas_ord:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)

            cliente_nombre = self.clientes_mapa.get(cuenta['cliente_id'],
                                                    f"ID: {cuenta['cliente_id']}")
            estado_texto   = ICONOS_ESTADO.get(cuenta['estado'], cuenta['estado'])
            color_fondo    = COLOR_ESTADO.get(cuenta['estado'])

            items = [
                QTableWidgetItem(str(cuenta['id'])[:12]),
                QTableWidgetItem(cliente_nombre),
                QTableWidgetItem(cuenta['factura']),
                QTableWidgetItem(cuenta['fecha_emision']),
                QTableWidgetItem(cuenta['fecha_vencimiento'] or '—'),
                QTableWidgetItem(f"{self.moneda} {cuenta['monto_total']:,.2f}"),
                QTableWidgetItem(f"{self.moneda} {cuenta['monto_pagado']:,.2f}"),
                QTableWidgetItem(f"{self.moneda} {cuenta['saldo']:,.2f}"),
                QTableWidgetItem(estado_texto),
            ]

            for col, item in enumerate(items):
                if color_fondo:
                    item.setBackground(QBrush(color_fondo))
                if col in (5, 6, 7):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                elif col in (0, 3, 4, 8):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tabla.setItem(row, col, item)

        n = len(cuentas_ord)
        self.lbl_conteo.setText(f"{n} registro(s)")

        # ── Totales del filtro ─────────────────────────────────────────────────
        total_pagado  = sum(c['monto_pagado'] for c in cuentas_ord)
        total_adeudado= sum(c['saldo']        for c in cuentas_ord)
        pagadas_count = sum(1 for c in cuentas_ord if c['estado'] == 'pagada')

        # Deuda más antigua: la fecha de vencimiento más antigua entre las vencidas
        fechas_venc = [
            c['fecha_vencimiento'] for c in cuentas_ord
            if c['estado'] in self._VENCIDOS and c['fecha_vencimiento']
        ]
        if fechas_venc:
            fecha_antigua = min(fechas_venc)
            try:
                dias_atraso = (datetime.now() - datetime.strptime(fecha_antigua, "%Y-%m-%d")).days
                antigua_txt = f"{fecha_antigua}  ({dias_atraso}d atrás)"
            except Exception:
                antigua_txt = fecha_antigua
        else:
            antigua_txt = "—"

        self._tot_facturas.setText(
            f"📄 Facturas:  {n} total · {pagadas_count} pagadas · {n - pagadas_count} pendientes")
        self._tot_pagado.setText(
            f"✅ Pagado:  {self.moneda} {total_pagado:,.2f}")
        self._tot_adeudado.setText(
            f"💳 Adeudado:  {self.moneda} {total_adeudado:,.2f}")
        self._tot_antigua.setText(
            f"📅 Deuda más antigua:  {antigua_txt}")

    # ── Acciones ───────────────────────────────────────────────────────────────
    def _get_cuenta_seleccionada(self) -> dict | None:
        """Devuelve el dict de cuenta de la fila seleccionada o None."""
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Sin Selección", "Seleccione una cuenta primero.")
            return None
        alq_id = self.tabla.item(row, 0).text()
        # Buscar por prefijo (ID puede estar truncado en la tabla)
        cuenta = next(
            (c for c in self.cuentas if str(c['id']).startswith(alq_id)),
            None,
        )
        if not cuenta:
            QMessageBox.warning(self, "Error", "No se encontró la cuenta seleccionada.")
        return cuenta

    def _registrar_pago(self):
        """Registra un pago directo a una factura específica (subcolección pagos)."""
        cuenta = self._get_cuenta_seleccionada()
        if not cuenta:
            return

        if cuenta['saldo'] <= 0:
            QMessageBox.information(self, "Cuenta Pagada",
                                    "Esta factura ya está completamente pagada.")
            return

        dlg = DialogoRegistrarPago(
            cuenta, self.clientes_mapa, self.cuentas_bancarias, self.moneda, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        monto    = dlg.get_monto()
        fecha    = dlg.get_fecha()
        cuenta_b = dlg.get_cuenta_id()
        comment  = dlg.get_comentario()

        try:
            pago_data = {
                "fecha":      fecha,
                "monto":      monto,
                "cliente_id": cuenta['cliente_id'],
                "comentario": comment,
            }
            if cuenta_b:
                pago_data["cuenta_id"] = cuenta_b

            pago_id = str(uuid.uuid4())
            (self.fm.db
             .collection("alquileres")
             .document(cuenta['id'])
             .collection("pagos")
             .document(pago_id)
             .set(pago_data))

            # Recalcular flag pagado
            self.fm._recalcular_estado_pago_alquiler(cuenta['id'])

            QMessageBox.information(
                self, "Pago Registrado",
                f"Pago de {self.moneda} {monto:,.2f} registrado correctamente.")
            self._cargar_datos()

        except Exception as e:
            logger.error(f"Error registrando pago: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo registrar el pago:\n{e}")

    def _registrar_abono_cliente(self):
        """Abre la ventana de abonos para el cliente de la fila seleccionada."""
        cuenta = self._get_cuenta_seleccionada()
        if not cuenta:
            return
        from dialogos.ventana_gestion_abono import VentanaGestionAbonos
        dlg = VentanaGestionAbonos(
            self.fm, self.moneda, self.clientes_mapa, parent=self)
        dlg.exec()
        self._cargar_datos()

    def _enviar_recordatorio(self):
        """Prepara mensaje de WhatsApp para el cliente seleccionado."""
        cuenta = self._get_cuenta_seleccionada()
        if not cuenta:
            return
        if cuenta['saldo'] <= 0:
            QMessageBox.information(self, "Sin Saldo", "Esta factura no tiene saldo pendiente.")
            return

        cliente_nombre = self.clientes_mapa.get(cuenta['cliente_id'], 'Cliente')
        mensaje = (
            f"Estimado/a {cliente_nombre},\n\n"
            f"Le recordamos que tiene un saldo pendiente:\n\n"
            f"Factura: {cuenta['factura']}\n"
            f"Monto pendiente: {self.moneda} {cuenta['saldo']:,.2f}\n"
        )
        if cuenta['fecha_vencimiento']:
            mensaje += f"Fecha de vencimiento: {cuenta['fecha_vencimiento']}\n"
        mensaje += "\nPor favor, regularice su pago a la brevedad.\n\nGracias."

        dlg = DialogoRecordatorio(cliente_nombre, mensaje, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Intentar abrir WhatsApp si está integrado
            try:
                from whatsapp_integration import WhatsAppIntegration
                wa = WhatsAppIntegration(self.config)
                # Buscar teléfono del cliente
                cliente_data = next(
                    (c for c in (self.fm.obtener_entidades(tipo="Cliente") or [])
                     if str(c.get('id', '')) == cuenta['cliente_id']),
                    None,
                )
                telefono = (cliente_data or {}).get('telefono', '')
                if telefono:
                    wa.enviar_mensaje(telefono, dlg.get_mensaje())
                    QMessageBox.information(self, "Enviado", "Recordatorio enviado por WhatsApp.")
                else:
                    QMessageBox.information(
                        self, "Sin Teléfono",
                        "El cliente no tiene teléfono registrado.\n"
                        "El mensaje fue preparado pero no enviado.")
            except Exception as e:
                logger.warning(f"WhatsApp no disponible: {e}")
                QMessageBox.information(
                    self, "Recordatorio Listo",
                    "Mensaje preparado.\nIntegración con WhatsApp no disponible.")

    def _ver_detalle(self):
        cuenta = self._get_cuenta_seleccionada()
        if not cuenta:
            return
        cliente_nombre = self.clientes_mapa.get(cuenta['cliente_id'], 'Desconocido')
        alq = cuenta['alquiler']
        modalidad = alq.get('modalidad_facturacion', '—')

        detalle_modal = f"""
<h2>Detalle de Factura</h2><hr>
<p><b>Cliente:</b> {cliente_nombre}</p>
<p><b>Factura/Conduce:</b> {cuenta['factura']}</p>
<p><b>Fecha Emisión:</b> {cuenta['fecha_emision']}</p>
<p><b>Vencimiento:</b> {cuenta['fecha_vencimiento'] or 'Sin vencimiento'}</p>
<p><b>Modalidad:</b> {modalidad}</p>
<hr>
<p><b>Monto Total:</b> {self.moneda} {cuenta['monto_total']:,.2f}</p>
<p><b>Monto Pagado:</b> {self.moneda} {cuenta['monto_pagado']:,.2f}</p>
<p><b>Saldo Pendiente:</b>
   <span style="color:#DC2626; font-size:14pt;">
   <b>{self.moneda} {cuenta['saldo']:,.2f}</b></span></p>
<hr>
<p><b>Estado:</b> {ICONOS_ESTADO.get(cuenta['estado'], cuenta['estado'])}</p>
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Detalle de Factura")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(detalle_modal)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

    def _generar_estado_cuenta(self):
        """Abre el diálogo de Estado de Cuenta del sistema existente."""
        cuenta = self._get_cuenta_seleccionada()
        if not cuenta:
            return
        try:
            from dialogos.estado_cuenta_dialog import EstadoCuentaDialog
            dlg = EstadoCuentaDialog(
                fm=self.fm,
                config=self.config,
                cliente_id=cuenta['cliente_id'],
                parent=self,
            )
            dlg.exec()
        except Exception as e:
            logger.error(f"Estado de cuenta: {e}", exc_info=True)
            QMessageBox.information(
                self, "Estado de Cuenta",
                "No se pudo abrir el estado de cuenta.\n"
                f"Detalle: {e}")

    def _exportar_excel(self):
        """Exporta las cuentas visibles a Excel."""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill
            from PyQt6.QtWidgets import QFileDialog

            archivo, _ = QFileDialog.getSaveFileName(
                self, "Guardar Reporte",
                f"CuentasPorCobrar_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "Excel (*.xlsx)")
            if not archivo:
                return

            wb = Workbook()
            ws = wb.active
            ws.title = "Cuentas por Cobrar"

            headers = ["Cliente", "Factura/Conduce", "Fecha Emisión",
                       "Vencimiento", "Monto Total", "Pagado", "Saldo", "Estado"]
            for col, h in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=h)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")

            for row, c in enumerate(self.cuentas, 2):
                ws.cell(row=row, column=1, value=self.clientes_mapa.get(c['cliente_id'], c['cliente_id']))
                ws.cell(row=row, column=2, value=c['factura'])
                ws.cell(row=row, column=3, value=c['fecha_emision'])
                ws.cell(row=row, column=4, value=c['fecha_vencimiento'] or '')
                ws.cell(row=row, column=5, value=c['monto_total'])
                ws.cell(row=row, column=6, value=c['monto_pagado'])
                ws.cell(row=row, column=7, value=c['saldo'])
                ws.cell(row=row, column=8, value=c['estado'])

            wb.save(archivo)
            QMessageBox.information(self, "Exportado", f"Archivo guardado:\n{archivo}")

        except ImportError:
            QMessageBox.critical(self, "Error",
                                 "Se requiere 'openpyxl'.\nInstale con: pip install openpyxl")
        except Exception as e:
            logger.error(f"Error exportando Excel: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al exportar:\n{e}")

    def actualizar_mapas(self, mapas: dict):
        """Llamado por app_gui_qt cuando termina de cargar los mapas globales."""
        if "clientes" in mapas or "entidades" in mapas:
            self._cargar_clientes()
        if "cuentas" in mapas:
            self.cuentas_bancarias = {str(k): v for k, v in mapas["cuentas"].items()}


# ── DialogoRegistrarPago ───────────────────────────────────────────────────────
class DialogoRegistrarPago(QDialog):
    """Diálogo para registrar un pago directo a una factura."""

    def __init__(self, cuenta: dict, clientes_mapa: dict,
                 cuentas_bancarias: dict, moneda: str, parent=None):
        super().__init__(parent)
        self.moneda = moneda
        self._cuenta_id_sel: str | None = None

        cliente_nombre = clientes_mapa.get(cuenta['cliente_id'], 'Cliente')
        self.setWindowTitle("Registrar Pago")
        self.setMinimumWidth(460)
        self.setStyleSheet(CUENTAS_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(18)

        titulo = QLabel("💵 Registrar Pago")
        titulo.setStyleSheet("font-size:16pt; font-weight:bold; color:#1F2937;")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)

        # Info factura
        info = QFrame()
        info.setStyleSheet("background:#F9FAFB; border:1px solid #E5E7EB; border-radius:6px; padding:12px;")
        il = QVBoxLayout(info)
        il.addWidget(QLabel(f"<b>Cliente:</b> {cliente_nombre}"))
        il.addWidget(QLabel(f"<b>Factura:</b> {cuenta['factura']}"))
        il.addWidget(QLabel(
            f"<b>Saldo Pendiente:</b> "
            f"<span style='color:#DC2626; font-size:13pt;'>"
            f"{moneda} {cuenta['saldo']:,.2f}</span>"))
        layout.addWidget(info)

        # Formulario
        form = QFormLayout()
        form.setSpacing(14)

        self.spin_monto = QDoubleSpinBox()
        self.spin_monto.setRange(0.01, cuenta['saldo'])
        self.spin_monto.setValue(cuenta['saldo'])
        self.spin_monto.setDecimals(2)
        self.spin_monto.setPrefix(f"{moneda} ")
        form.addRow("Monto del Pago:", self.spin_monto)

        self.date_pago = QDateEdit(calendarPopup=True)
        self.date_pago.setDate(QDate.currentDate())
        self.date_pago.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Fecha de Pago:", self.date_pago)

        self.combo_cuenta = QComboBox()
        self.combo_cuenta.addItem("— Sin cuenta —", None)
        for cid, cnombre in sorted(cuentas_bancarias.items(), key=lambda x: x[1]):
            self.combo_cuenta.addItem(cnombre, cid)
        form.addRow("Cuenta Destino:", self.combo_cuenta)

        self.txt_comentario = QLineEdit()
        self.txt_comentario.setPlaceholderText("Referencia, número de transferencia, etc.")
        form.addRow("Comentario:", self.txt_comentario)

        layout.addLayout(form)

        # Botones
        btns = QHBoxLayout()
        btn_ok = QPushButton("💾 Registrar")
        btn_ok.setProperty("class", "success")
        btn_ok.setMinimumWidth(150)
        btn_ok.clicked.connect(self.accept)
        btns.addWidget(btn_ok)

        btn_cancel = QPushButton("✖️ Cancelar")
        btn_cancel.setProperty("class", "secondary")
        btn_cancel.setMinimumWidth(120)
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    def get_monto(self) -> float:
        return self.spin_monto.value()

    def get_fecha(self) -> str:
        return self.date_pago.date().toString("yyyy-MM-dd")

    def get_cuenta_id(self) -> str | None:
        return self.combo_cuenta.currentData()

    def get_comentario(self) -> str:
        return self.txt_comentario.text().strip()


# ── DialogoRecordatorio ────────────────────────────────────────────────────────
class DialogoRecordatorio(QDialog):
    """Diálogo para revisar/editar el mensaje de recordatorio antes de enviarlo."""

    def __init__(self, cliente_nombre: str, mensaje: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recordatorio de Pago")
        self.setMinimumSize(500, 380)
        self.setStyleSheet(CUENTAS_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        titulo = QLabel(f"📱 Recordatorio para {cliente_nombre}")
        titulo.setStyleSheet("font-size:14pt; font-weight:bold; color:#1F2937;")
        layout.addWidget(titulo)

        layout.addWidget(QLabel("Mensaje (puedes editarlo antes de enviar):"))
        self.txt_mensaje = QTextEdit()
        self.txt_mensaje.setPlainText(mensaje)
        layout.addWidget(self.txt_mensaje)

        btns = QHBoxLayout()
        btn_enviar = QPushButton("📱 Enviar por WhatsApp")
        btn_enviar.setProperty("class", "success")
        btn_enviar.clicked.connect(self.accept)
        btns.addWidget(btn_enviar)

        btn_cancel = QPushButton("✖️ Cancelar")
        btn_cancel.setProperty("class", "secondary")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    def get_mensaje(self) -> str:
        return self.txt_mensaje.toPlainText()
