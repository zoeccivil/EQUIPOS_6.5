# rendimientos.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QPushButton
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont

from firebase_manager import FirebaseManager


class DialogoReporteRendimientosFirebase(QDialog):
    """
    Filtros para el Reporte de Rendimientos:

      - Equipo: Todos / uno.
      - Rango de fechas.
    """

    def __init__(self, fm: FirebaseManager, equipos_mapa: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reporte de Rendimientos - Filtros")
        self.fm = fm
        self.equipos_mapa = equipos_mapa or {}
        self.formato = "pdf"

        # Aplicar tema consistente
        self.setStyleSheet("""
            QDialog {
                background-color: #F3F4F6;
                font-family: 'Segoe UI';
            }
            QLabel {
                color: #374151;
                font-size: 11pt;
                font-weight: 500;
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
            QPushButton {
                background-color: #F59E0B;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
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
            QPushButton#btn_cancel {
                background-color: #E5E7EB;
                color: #374151;
            }
            QPushButton#btn_cancel:hover {
                background-color: #D1D5DB;
            }
            QPushButton#btn_cancel:pressed {
                background-color: #9CA3AF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Título del diálogo
        titulo = QLabel("Filtros de Reporte")
        titulo.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1F2937; margin-bottom: 10px;")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)

        # Equipo
        hlayout_eq = QHBoxLayout()
        hlayout_eq.setSpacing(10)
        lbl_equipo = QLabel("Equipo:")
        lbl_equipo.setFixedWidth(80)
        hlayout_eq.addWidget(lbl_equipo)
        self.combo_equipo = QComboBox()
        self.combo_equipo.addItem("Todos", None)
        for eid, nom in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
            self.combo_equipo.addItem(nom, str(eid))
        hlayout_eq.addWidget(self.combo_equipo)
        layout.addLayout(hlayout_eq)

        # Fechas
        hlayout_fechas = QHBoxLayout()
        hlayout_fechas.setSpacing(10)
        
        lbl_desde = QLabel("Desde:")
        lbl_desde.setFixedWidth(80)
        hlayout_fechas.addWidget(lbl_desde)
        
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        self.fecha_inicio.setCalendarPopup(True)
        hlayout_fechas.addWidget(self.fecha_inicio)

        hlayout_fechas.addSpacing(15)

        lbl_hasta = QLabel("Hasta:")
        lbl_hasta.setFixedWidth(60)
        hlayout_fechas.addWidget(lbl_hasta)
        
        self.fecha_fin = QDateEdit(calendarPopup=True)
        self.fecha_fin.setDisplayFormat("yyyy-MM-dd")
        self.fecha_fin.setCalendarPopup(True)
        hlayout_fechas.addWidget(self.fecha_fin)
        
        layout.addLayout(hlayout_fechas)

        layout.addSpacing(10)

        # Botones
        btns = QHBoxLayout()
        btns.setSpacing(10)
        
        self.btn_pdf = QPushButton("📄 Exportar PDF")
        self.btn_pdf.clicked.connect(self.exportar_pdf)
        btns.addWidget(self.btn_pdf)

        self.btn_excel = QPushButton("📊 Exportar Excel")
        self.btn_excel.clicked.connect(self.exportar_excel)
        btns.addWidget(self.btn_excel)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)

        layout.addLayout(btns)

        # Inicializar fechas
        self._init_fechas()
        
        # Tamaño mínimo del diálogo
        self.setMinimumWidth(550)

    def _init_fechas(self):
        """
        Rango inicial: desde la primera transacción global hasta hoy.
        Usa FirebaseManager.obtener_fecha_primera_transaccion().
        """
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

    def get_filtros(self) -> dict:
        equipo_id = self.combo_equipo.currentData()
        if equipo_id is not None:
            equipo_id = str(equipo_id)

        return {
            "equipo_id": equipo_id,
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
        }

    def exportar_pdf(self):
        self.formato = "pdf"
        self.accept()

    def exportar_excel(self):
        self.formato = "excel"
        self.accept()