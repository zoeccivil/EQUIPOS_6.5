from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit,
    QPushButton, QMessageBox
)
from PyQt6.QtCore import QDate

from firebase_manager import FirebaseManager


class DialogoReporteDetalladoFirebase(QDialog):
    """
    Diálogo de filtros para el Reporte Detallado de Equipos (versión Firebase).

    Filtros:
      - Cliente (Todos / uno específico)
      - Rango de fechas (desde primera transacción de alquiler/cliente hasta hoy)
    """

    def __init__(self, fm: FirebaseManager, clientes_mapa: dict, proyecto_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filtros Reporte Detallado de Equipos")
        self.fm = fm
        self.proyecto_id = proyecto_id  # reservado por si más adelante filtras por proyecto
        self.formato = "pdf"

        self.clientes_mapa = clientes_mapa or {}  # {id_str: nombre}

        layout = QVBoxLayout(self)

        # --- Cliente ---
        hlayout_cliente = QHBoxLayout()
        hlayout_cliente.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        # "Todos" -> data=None
        self.combo_cliente.addItem("Todos", None)
        # Ordenar nombres
        for cid, nombre in sorted(self.clientes_mapa.items(), key=lambda x: x[1]):
            self.combo_cliente.addItem(nombre, str(cid))
        hlayout_cliente.addWidget(self.combo_cliente)
        layout.addLayout(hlayout_cliente)

        # --- Fechas ---
        hlayout_fechas = QHBoxLayout()
        hlayout_fechas.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        hlayout_fechas.addWidget(self.fecha_inicio)
        hlayout_fechas.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit(calendarPopup=True)
        self.fecha_fin.setDisplayFormat("yyyy-MM-dd")
        hlayout_fechas.addWidget(self.fecha_fin)
        layout.addLayout(hlayout_fechas)

        # --- Botones ---
        btns = QHBoxLayout()
        self.btn_pdf = QPushButton("Exportar PDF")
        self.btn_pdf.clicked.connect(self.exportar_pdf)
        btns.addWidget(self.btn_pdf)

        self.btn_excel = QPushButton("Exportar Excel")
        self.btn_excel.clicked.connect(self.exportar_excel)
        btns.addWidget(self.btn_excel)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)

        layout.addLayout(btns)

        # Eventos
        self.combo_cliente.currentIndexChanged.connect(self.actualizar_rango_fechas)

        # Inicializar fechas
        self.actualizar_rango_fechas()

    # ------------------------------------------------------------------ Lógica

    def actualizar_rango_fechas(self):
        """
        Usa FirebaseManager para obtener la primera fecha de transacción:
        - Global (si cliente=None)
        - Filtrada por cliente (si cliente_id != None)

        Debes implementar en FirebaseManager:
          - obtener_fecha_primera_transaccion()
          - obtener_fecha_primera_transaccion_cliente(cliente_id)
        """
        cliente_id = self.combo_cliente.currentData()
        try:
            if cliente_id:
                fecha_str = self.fm.obtener_fecha_primera_transaccion_cliente(str(cliente_id))
            else:
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
        """
        Devuelve un dict con los filtros seleccionados.

        {
           "cliente_id": str | None,
           "fecha_inicio": "YYYY-MM-DD",
           "fecha_fin": "YYYY-MM-DD",
        }
        """
        cliente_id = self.combo_cliente.currentData()
        if cliente_id is not None:
            cliente_id = str(cliente_id)

        return {
            "cliente_id": cliente_id,
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
        }

    def exportar_pdf(self):
        self.formato = "pdf"
        self.accept()

    def exportar_excel(self):
        self.formato = "excel"
        self.accept()