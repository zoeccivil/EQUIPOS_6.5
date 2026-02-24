"""
Diálogo de Preview de Rendimientos - VERSIÓN MEJORADA
------------------------------------------------------
Cambios V2.0:
- Dividido en 2 bloques:  Facturación y Rendimientos
- Nueva columna: Gastos del Equipo
- Recálculo correcto:  Rendimiento = Facturado - Pagado Op - Gastos
- Frame de resumen inferior con totales
- Exportación mejorada a PDF/Excel (bloques separados)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QFrame, QGroupBox, QGridLayout,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from firebase_manager import FirebaseManager
from report_generator import ReportGenerator
import logging

logger = logging.getLogger(__name__)

APP_QSS = """
QDialog {
    background-color: #F3F4F6;
    font-family: 'Segoe UI';
}
QWidget {
    background-color: transparent;
    color: #1F2937;
    font-family: 'Segoe UI';
    font-size: 10pt;
}
QLabel {
    color: #374151;
    font-size: 10pt;
}
QGroupBox {
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 8px;
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
    color: #1F2937;
    background-color: #FFFFFF;
}
QComboBox {
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 6px;
    padding: 8px 12px;
    color: #1F2937;
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
    border: 2px solid #E5E7EB;
    selection-background-color: #FEF3C7;
    selection-color: #1F2937;
    color: #1F2937;
}
QDateEdit {
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 6px;
    padding: 8px 12px;
    color: #1F2937;
    font-size: 10pt;
    min-height: 25px;
}
QDateEdit:hover {
    border: 2px solid #F59E0B;
}
QDateEdit:focus {
    border: 2px solid #F59E0B;
}
QDateEdit::drop-down {
    border: none;
    padding-right: 10px;
}
QDateEdit::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #6B7280;
    margin-right: 8px;
}
QCalendarWidget {
    background-color: #FFFFFF;
}
QCalendarWidget QWidget {
    alternate-background-color: #F9FAFB;
    background-color: #FFFFFF;
}
QCalendarWidget QAbstractItemView:enabled {
    color: #1F2937;
    background-color: #FFFFFF;
    selection-background-color: #F59E0B;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background-color: #1F2937;
    color: #FFFFFF;
    padding: 8px;
    border: none;
    font-weight: 600;
    font-size: 10pt;
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
    padding: 6px 8px;
    color: #1F2937;
}
QTableWidget::item:selected {
    background-color: #FEF3C7;
    color: #1F2937;
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
QFrame#resumenFrame {
    background-color: #FFFFFF;
    border: 2px solid #F59E0B;
    border-radius: 8px;
    padding: 18px;
}
QPushButton {
    background-color: #F59E0B;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 10px 16px;
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
QPushButton[class~="primary"] {
    background-color: #F59E0B;
    color: #FFFFFF;
}
QPushButton[class~="primary"]:hover {
    background-color: #D97706;
}
QPushButton[class~="primary"]:pressed {
    background-color: #B45309;
}
QPushButton[class~="danger"] {
    background-color: #E5E7EB;
    color: #374151;
}
QPushButton[class~="danger"]:hover {
    background-color: #D1D5DB;
}
QPushButton[class~="danger"]:pressed {
    background-color: #9CA3AF;
}
"""

class DialogoPreviewRendimientos(QDialog):
    """
    Vista previa del Reporte de Rendimientos por equipo - MEJORADO.
    """

    def __init__(self, fm: FirebaseManager, equipos_mapa: dict, config: dict, storage_manager, parent=None):
        super().__init__(parent)
        self.fm = fm
        self.equipos_mapa = equipos_mapa or {}
        self.config = config or {}
        self.sm = storage_manager
        self.setWindowTitle("Reporte de Rendimientos por Equipo - Mejorado")
        self.resize(1400, 750)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.moneda = self.config.get("app", {}).get("moneda", "RD$")

        # Datos calculados
        self.datos_facturacion = []
        self.datos_rendimientos = []
        self.resumen = {}

        self._init_ui()
        self._init_fechas()
        self.cargar_datos()

    def _init_ui(self):
        """Inicializa la interfaz mejorada."""
        self.setStyleSheet(APP_QSS)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- Filtros ---
        filtros_layout = QHBoxLayout()
        filtros_layout.setSpacing(10)
        
        lbl_equipo = QLabel("Equipo:")
        lbl_equipo.setStyleSheet("font-weight: 600;")
        filtros_layout.addWidget(lbl_equipo)
        
        self.combo_equipo = QComboBox()
        self.combo_equipo.addItem("Todos", None)
        for eid, nombre in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
            self.combo_equipo.addItem(nombre, str(eid))
        filtros_layout.addWidget(self.combo_equipo)

        filtros_layout.addSpacing(15)

        lbl_desde = QLabel("Desde:")
        lbl_desde.setStyleSheet("font-weight: 600;")
        filtros_layout.addWidget(lbl_desde)
        
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        self.fecha_inicio.setCalendarPopup(True)
        filtros_layout.addWidget(self.fecha_inicio)

        lbl_hasta = QLabel("Hasta:")
        lbl_hasta.setStyleSheet("font-weight: 600;")
        filtros_layout.addWidget(lbl_hasta)
        
        self.fecha_fin = QDateEdit(calendarPopup=True)
        self.fecha_fin.setDisplayFormat("yyyy-MM-dd")
        self.fecha_fin.setCalendarPopup(True)
        filtros_layout.addWidget(self.fecha_fin)

        filtros_layout.addSpacing(15)

        self.btn_actualizar = QPushButton("🔄 Actualizar")
        filtros_layout.addWidget(self.btn_actualizar)
        filtros_layout.addStretch()
        layout.addLayout(filtros_layout)

        # --- BLOQUE 1: FACTURACIÓN ---
        grupo_fact = QGroupBox("📊 FACTURACIÓN")
        layout_fact = QVBoxLayout(grupo_fact)
        layout_fact.setContentsMargins(10, 25, 10, 10)
        layout_fact.setSpacing(8)

        self.tabla_facturacion = QTableWidget(0, 7)
        self.tabla_facturacion.setHorizontalHeaderLabels([
            "Equipo", "Horas Fact.", "Volumen Fact.", "Monto Facturado",
            "Precio/h", "Precio/u", "Modalidad(s)"
        ])
        hh1 = self.tabla_facturacion.horizontalHeader()
        hh1.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh1.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabla_facturacion.verticalHeader().setVisible(False)
        self.tabla_facturacion.setAlternatingRowColors(True)
        self.tabla_facturacion.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_facturacion.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_facturacion.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_facturacion.setWordWrap(False)
        self.tabla_facturacion.setShowGrid(True)
        self.tabla_facturacion.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabla_facturacion.horizontalHeader().setMinimumSectionSize(90)
        self.tabla_facturacion.verticalHeader().setDefaultSectionSize(32)
        layout_fact.addWidget(self.tabla_facturacion)
        layout.addWidget(grupo_fact)

        # --- BLOQUE 2: RENDIMIENTOS ---
        grupo_rend = QGroupBox("💰 RENDIMIENTOS")
        layout_rend = QVBoxLayout(grupo_rend)
        layout_rend.setContentsMargins(10, 25, 10, 10)
        layout_rend.setSpacing(8)

        self.tabla_rendimientos = QTableWidget(0, 6)
        self.tabla_rendimientos.setHorizontalHeaderLabels([
            "Equipo", "Horas Pag.", "Pagado Op.", "Gastos Equipo",
            "Rendimiento Neto", "% Margen"
        ])
        hh2 = self.tabla_rendimientos.horizontalHeader()
        hh2.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh2.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabla_rendimientos.verticalHeader().setVisible(False)
        self.tabla_rendimientos.setAlternatingRowColors(True)
        self.tabla_rendimientos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_rendimientos.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_rendimientos.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_rendimientos.setWordWrap(False)
        self.tabla_rendimientos.setShowGrid(True)
        self.tabla_rendimientos.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabla_rendimientos.horizontalHeader().setMinimumSectionSize(90)
        self.tabla_rendimientos.verticalHeader().setDefaultSectionSize(32)
        layout_rend.addWidget(self.tabla_rendimientos)
        layout.addWidget(grupo_rend)

        # --- FRAME RESUMEN ---
        frame_resumen = QFrame()
        frame_resumen.setObjectName("resumenFrame")
        frame_resumen.setFrameShape(QFrame.Shape.StyledPanel)
        resumen_layout = QVBoxLayout(frame_resumen)
        resumen_layout.setContentsMargins(15, 15, 15, 15)
        resumen_layout.setSpacing(12)

        titulo_resumen = QLabel("📈 RESUMEN GENERAL")
        titulo_resumen.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        titulo_resumen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo_resumen.setStyleSheet("background: transparent; border: none; padding: 8px; color: #1F2937;")
        resumen_layout.addWidget(titulo_resumen)

        grid_resumen = QGridLayout()
        grid_resumen.setSpacing(12)
        grid_resumen.setContentsMargins(10, 10, 10, 10)

        self.lbl_total_horas = QLabel("Total Horas Facturadas: 0.00 h")
        self.lbl_total_facturado = QLabel(f"Total Facturado: {self.moneda} 0.00")
        self.lbl_total_pagado = QLabel(f"Total Pagado Op: {self.moneda} 0.00")
        self.lbl_total_gastos = QLabel(f"Total Gastos: {self.moneda} 0.00")
        self.lbl_rendimiento_neto = QLabel(f"Rendimiento Neto: {self.moneda} 0.00")
        self.lbl_margen_prom = QLabel("Margen Promedio: 0.00%")

        base_style = "background: transparent; border: none; color: #6B7280; font-size: 11pt; font-weight: 500;"
        for lbl in [self.lbl_total_horas, self.lbl_total_facturado, self.lbl_total_pagado, self.lbl_total_gastos]:
            lbl.setStyleSheet(base_style)

        self.lbl_rendimiento_neto.setStyleSheet(
            "background: transparent; border: none; color: #059669; font-weight: 700; font-size: 12pt;"
        )
        self.lbl_margen_prom.setStyleSheet(
            "background: transparent; border: none; color: #F59E0B; font-weight: 700; font-size: 12pt;"
        )

        grid_resumen.addWidget(self.lbl_total_horas,     0, 0)
        grid_resumen.addWidget(self.lbl_total_gastos,    0, 1)
        grid_resumen.addWidget(self.lbl_total_facturado, 1, 0)
        grid_resumen.addWidget(self.lbl_rendimiento_neto,1, 1)
        grid_resumen.addWidget(self.lbl_total_pagado,    2, 0)
        grid_resumen.addWidget(self.lbl_margen_prom,     2, 1)

        resumen_layout.addLayout(grid_resumen)
        layout.addWidget(frame_resumen)

        # --- Botones de exportación ---
        botones_layout = QHBoxLayout()
        botones_layout.setSpacing(10)
        
        self.btn_pdf = QPushButton("📄 Exportar PDF")
        self.btn_excel = QPushButton("📊 Exportar Excel")
        self.btn_cerrar = QPushButton("❌ Cerrar")
        
        self.btn_pdf.setProperty("class", "primary")
        self.btn_excel.setProperty("class", "primary")
        self.btn_cerrar.setProperty("class", "danger")
        
        for b in (self.btn_pdf, self.btn_excel, self.btn_cerrar):
            b.setStyleSheet("QPushButton { padding: 10px 18px; }")

        botones_layout.addWidget(self.btn_pdf)
        botones_layout.addWidget(self.btn_excel)
        botones_layout.addStretch()
        botones_layout.addWidget(self.btn_cerrar)
        layout.addLayout(botones_layout)

        # Estiramientos por orden de inserción:
        layout.setStretch(0, 0)  # filtros
        layout.setStretch(1, 3)  # facturación
        layout.setStretch(2, 3)  # rendimientos
        layout.setStretch(3, 2)  # resumen
        layout.setStretch(4, 0)  # botones

        # Conexiones
        self.btn_actualizar.clicked.connect(self.cargar_datos)
        self.btn_pdf.clicked.connect(lambda: self.exportar("pdf"))
        self.btn_excel.clicked.connect(lambda: self.exportar("excel"))
        self.btn_cerrar.clicked.connect(self.reject)
        self.combo_equipo.currentIndexChanged.connect(self.cargar_datos)
        self.fecha_inicio.dateChanged.connect(lambda: self.cargar_datos())
        self.fecha_fin.dateChanged.connect(lambda: self.cargar_datos())

    def _init_fechas(self):
        """Inicializa rango de fechas."""
        try:
            fecha_str = self.fm.obtener_fecha_primera_transaccion()
        except Exception:
            fecha_str = None

        if fecha_str:
            qd = QDate.fromString(fecha_str, "yyyy-MM-dd")
            if qd.isValid():
                self.fecha_inicio.setDate(qd)
            else:
                self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
        else:
            self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))

        self.fecha_fin.setDate(QDate.currentDate())

    def _obtener_filtros(self) -> dict:
        """Obtiene filtros actuales."""
        equipo_id = self.combo_equipo.currentData()
        if equipo_id is not None:
            equipo_id = str(equipo_id)

        fi = self.fecha_inicio.date()
        ff = self.fecha_fin.date()

        if fi > ff:
            fi, ff = ff, fi
            self.fecha_inicio.setDate(fi)
            self.fecha_fin.setDate(ff)

        return {
            "equipo_id": equipo_id,
            "fecha_inicio": fi.toString("yyyy-MM-dd"),
            "fecha_fin": ff.toString("yyyy-MM-dd"),
        }

    def cargar_datos(self):
        """Carga y calcula los datos para ambos bloques."""
        try:
            filtros = self._obtener_filtros()

            rendimiento = self.fm.obtener_rendimiento_por_equipo(
                fecha_inicio=filtros["fecha_inicio"],
                fecha_fin=filtros["fecha_fin"],
                equipo_id=filtros["equipo_id"],
            )

            gastos_por_equipo = self.fm.obtener_gastos_por_equipo(
                fecha_inicio=filtros["fecha_inicio"],
                fecha_fin=filtros["fecha_fin"],
                equipo_id=filtros["equipo_id"],
            )

            self.datos_facturacion = []
            self.datos_rendimientos = []

            total_horas = 0.0
            total_facturado = 0.0
            total_pagado = 0.0
            total_gastos = 0.0
            total_rendimiento = 0.0

            for r in rendimiento or []:
                eid = str(r.get("equipo_id", "") or "")
                nombre = self.equipos_mapa.get(eid, r.get("equipo_nombre") or f"ID:{eid}")

                horas_fact = float(r.get("horas_facturadas", 0) or 0)
                vol_fact = float(r.get("volumen_facturado", 0) or 0)
                monto_fact = float(r.get("monto_facturado", 0) or 0)
                horas_pag = float(r.get("horas_pagadas_operador", 0) or 0)
                monto_pag = float(r.get("monto_pagado_operador", 0) or 0)
                gastos_equipo = float(gastos_por_equipo.get(eid, 0.0))

                precio_hora_fact = (monto_fact / horas_fact) if horas_fact > 0 else 0.0
                precio_unidad_fact = (monto_fact / vol_fact) if vol_fact > 0 else 0.0

                rendimiento_neto = monto_fact - monto_pag - gastos_equipo
                margen_pct = (rendimiento_neto / monto_fact * 100.0) if monto_fact > 0 else 0.0

                modalidades = []
                if horas_fact > 0:
                    modalidades.append("Horas")
                if vol_fact > 0:
                    modalidades.append("Volumen")
                if horas_fact == 0 and vol_fact == 0 and monto_fact > 0:
                    modalidades.append("Fijo")
                modalidades_txt = ", ".join(modalidades) if modalidades else "-"

                self.datos_facturacion.append({
                    "equipo": nombre,
                    "horas_facturadas": horas_fact,
                    "volumen_facturado": vol_fact,
                    "monto_facturado": monto_fact,
                    "precio_hora_facturado": precio_hora_fact,
                    "precio_unidad_facturado": precio_unidad_fact,
                    "modalidades": modalidades_txt,
                })

                self.datos_rendimientos.append({
                    "equipo": nombre,
                    "horas_pagadas": horas_pag,
                    "monto_pagado_operador": monto_pag,
                    "gastos_equipo": gastos_equipo,
                    "rendimiento_neto": rendimiento_neto,
                    "margen_porcentaje": margen_pct,
                })

                total_horas += horas_fact
                total_facturado += monto_fact
                total_pagado += monto_pag
                total_gastos += gastos_equipo
                total_rendimiento += rendimiento_neto

            margen_promedio = (total_rendimiento / total_facturado * 100.0) if total_facturado > 0 else 0.0

            self.resumen = {
                "total_horas_facturadas": total_horas,
                "total_facturado": total_facturado,
                "total_pagado_operador": total_pagado,
                "total_gastos": total_gastos,
                "rendimiento_neto": total_rendimiento,
                "margen_promedio": margen_promedio,
            }

            self._actualizar_tablas()
            self._actualizar_resumen()

        except Exception as e:
            logger.error(f"Error cargando datos de rendimientos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los rendimientos:\n{e}")

    def _actualizar_tablas(self):
        """Actualiza ambas tablas con los datos procesados."""
        try:
            # TABLA 1: Facturación
            self.tabla_facturacion.setRowCount(0)
            for row, d in enumerate(self.datos_facturacion):
                self.tabla_facturacion.insertRow(row)
                self.tabla_facturacion.setItem(row, 0, QTableWidgetItem(d["equipo"]))
                self.tabla_facturacion.setItem(row, 1, QTableWidgetItem(f"{float(d['horas_facturadas']):.2f} h"))
                self.tabla_facturacion.setItem(row, 2, QTableWidgetItem(f"{float(d['volumen_facturado']):.2f}"))
                self.tabla_facturacion.setItem(row, 3, QTableWidgetItem(f"{self.moneda} {float(d['monto_facturado']):,.2f}"))
                self.tabla_facturacion.setItem(row, 4, QTableWidgetItem(f"{self.moneda} {float(d['precio_hora_facturado']):,.2f}"))
                self.tabla_facturacion.setItem(row, 5, QTableWidgetItem(f"{self.moneda} {float(d['precio_unidad_facturado']):,.2f}"))
                self.tabla_facturacion.setItem(row, 6, QTableWidgetItem(d["modalidades"]))

            for r in range(self.tabla_facturacion.rowCount()):
                for c in [1, 2, 3, 4, 5]:
                    item = self.tabla_facturacion.item(r, c)
                    if item:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # TABLA 2: Rendimientos
            self.tabla_rendimientos.setRowCount(0)
            for row, d in enumerate(self.datos_rendimientos):
                self.tabla_rendimientos.insertRow(row)
                self.tabla_rendimientos.setItem(row, 0, QTableWidgetItem(d["equipo"]))
                self.tabla_rendimientos.setItem(row, 1, QTableWidgetItem(f"{float(d['horas_pagadas']):.2f} h"))
                self.tabla_rendimientos.setItem(row, 2, QTableWidgetItem(f"{self.moneda} {float(d['monto_pagado_operador']):,.2f}"))
                self.tabla_rendimientos.setItem(row, 3, QTableWidgetItem(f"{self.moneda} {float(d['gastos_equipo']):,.2f}"))
                rend_val = float(d["rendimiento_neto"])
                item_rend = QTableWidgetItem(f"{self.moneda} {rend_val:,.2f}")
                item_rend.setForeground(QColor("#059669") if rend_val >= 0 else QColor("#DC2626"))
                self.tabla_rendimientos.setItem(row, 4, item_rend)
                self.tabla_rendimientos.setItem(row, 5, QTableWidgetItem(f"{float(d['margen_porcentaje']):.2f}%"))

            for r in range(self.tabla_rendimientos.rowCount()):
                for c in [1, 2, 3, 4, 5]:
                    item = self.tabla_rendimientos.item(r, c)
                    if item:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise

    def _actualizar_resumen(self):
        """Actualiza el frame de resumen."""
        try:
            r = self.resumen
            self.lbl_total_horas.setText(f"Total Horas Facturadas: {r['total_horas_facturadas']:,.2f} h")
            self.lbl_total_facturado.setText(f"Total Facturado: {self.moneda} {r['total_facturado']:,.2f}")
            self.lbl_total_pagado.setText(f"Total Pagado Op: {self.moneda} {r['total_pagado_operador']:,.2f}")
            self.lbl_total_gastos.setText(f"Total Gastos: {self.moneda} {r['total_gastos']:,.2f}")
            self.lbl_rendimiento_neto.setText(f"Rendimiento Neto: {self.moneda} {r['rendimiento_neto']:,.2f}")
            self.lbl_margen_prom.setText(f"Margen Promedio: {r['margen_promedio']:.2f}%")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise

    def exportar(self, formato: str):
        """Exporta el reporte usando ReportGenerator mejorado."""
        try:
            if not self.datos_facturacion:
                QMessageBox.information(self, "Sin datos", "No hay datos para exportar.")
                return

            filtros = self._obtener_filtros()
            ext = "PDF (*.pdf)" if formato == "pdf" else "Excel (*.xlsx)"
            sugerido = f"Rendimientos_{filtros['fecha_inicio']}_a_{filtros['fecha_fin']}"

            file_path, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte", sugerido, ext)
            if not file_path:
                return

            title = "REPORTE DE RENDIMIENTOS POR EQUIPO"
            date_range = f"{filtros['fecha_inicio']} a {filtros['fecha_fin']}"

            rg = ReportGenerator(
                data=[],
                title=title,
                date_range=date_range,
                currency_symbol=self.moneda,
                storage_manager=self.sm,
            )

            ok, error = rg.generar_reporte_rendimientos_bloques(
                file_path=file_path,
                formato=formato,
                datos_facturacion=self.datos_facturacion,
                datos_rendimientos=self.datos_rendimientos,
                resumen=self.resumen,
                moneda=self.moneda,
                titulo=title,
                rango_fechas=date_range,
            )

            if ok:
                QMessageBox.information(self, "Éxito", f"Reporte generado:\n{file_path}")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo generar:\n{error}")

        except Exception as e:
            logger.error(f"Error exportando: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al exportar:\n{e}")