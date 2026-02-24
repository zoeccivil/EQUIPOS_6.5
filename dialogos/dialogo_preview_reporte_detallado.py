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
)
from PyQt6.QtCore import QDate
import logging

from firebase_manager import FirebaseManager
from report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class DialogoPreviewReporteDetallado(QDialog):
    """
    Vista previa del Reporte Detallado de Equipos.

    Permite:
      - Filtrar por cliente (o todos) y rango de fechas
      - Ver el detalle de alquileres en una tabla
      - Exportar a PDF / Excel usando ReportGenerator
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
        self.clientes_mapa = clientes_mapa or {}  # {id_str: nombre}
        self.config = config or {}
        self.sm = storage_manager
        self.app = app_gui  # referencia a AppGUI para usar _enriquecer_facturas_con_nombres

        self.moneda = self.config.get("app", {}).get("moneda", "RD$")

        self.setWindowTitle("Preview - Reporte Detallado de Equipos")
        self.resize(1100, 600)

        layout = QVBoxLayout(self)

        # ---------------- Filtros ----------------
        filtros_layout = QHBoxLayout()

        # Cliente
        filtros_layout.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.addItem("Todos", None)
        # clientes_mapa viene como {id: nombre}; lo ordenamos por nombre
        for cid, nombre in sorted(self.clientes_mapa.items(), key=lambda x: x[1]):
            self.combo_cliente.addItem(nombre, str(cid))
        filtros_layout.addWidget(self.combo_cliente)

        # Fechas
        filtros_layout.addWidget(QLabel("Desde:"))
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        filtros_layout.addWidget(self.fecha_inicio)

        filtros_layout.addWidget(QLabel("Hasta:"))
        self.fecha_fin = QDateEdit(calendarPopup=True)
        self.fecha_fin.setDisplayFormat("yyyy-MM-dd")
        filtros_layout.addWidget(self.fecha_fin)

        # Botón actualizar
        self.btn_actualizar = QPushButton("Actualizar")
        filtros_layout.addWidget(self.btn_actualizar)

        layout.addLayout(filtros_layout)

        # ---------------- Tabla preview ----------------
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Fecha",
                "Cliente",
                "Equipo",
                "Operador",
                "Ubicación",
                "Conduce",
                "Horas",
                f"Monto ({self.moneda})",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)

        # ---------------- Botones exportar/cerrar ----------------
        botones_layout = QHBoxLayout()
        self.btn_pdf = QPushButton("Exportar PDF")
        self.btn_excel = QPushButton("Exportar Excel")
        self.btn_cerrar = QPushButton("Cerrar")

        botones_layout.addWidget(self.btn_pdf)
        botones_layout.addWidget(self.btn_excel)
        botones_layout.addStretch()
        botones_layout.addWidget(self.btn_cerrar)

        layout.addLayout(botones_layout)

        # Conexiones
        self.btn_actualizar.clicked.connect(self.cargar_datos)
        self.btn_pdf.clicked.connect(lambda: self.exportar("pdf"))
        self.btn_excel.clicked.connect(lambda: self.exportar("excel"))
        self.btn_cerrar.clicked.connect(self.reject)

        # Filtro dinámico: recargar al cambiar cualquier filtro
        self.combo_cliente.currentIndexChanged.connect(self.cargar_datos)
        self.fecha_inicio.dateChanged.connect(lambda _d: self.cargar_datos())
        self.fecha_fin.dateChanged.connect(lambda _d: self.cargar_datos())

        # Inicializar fechas y cargar datos
        self._init_fechas()
        self.cargar_datos()

    # ------------------------------------------------------------

    def _init_fechas(self):
        """Rango inicial: desde primera transacción hasta hoy."""
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
        if cliente_id is not None:
            cliente_id = str(cliente_id)

        return {
            "cliente_id": cliente_id,
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
        }

    # ---------------- Carga de datos ----------------

    def cargar_datos(self):
        """Carga los alquileres desde Firebase y los muestra en la tabla."""
        filtros = self._obtener_filtros()
        try:
            filtros_alq = {
                "fecha_inicio": filtros["fecha_inicio"],
                "fecha_fin": filtros["fecha_fin"],
            }
            if filtros["cliente_id"]:
                filtros_alq["cliente_id"] = filtros["cliente_id"]

            alquileres = self.fm.obtener_alquileres(filtros_alq) or []
        except Exception as e:
            logger.error(
                f"Error obteniendo alquileres para reporte detallado: {e}",
                exc_info=True,
            )
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar los alquileres:\n{e}",
            )
            return

        self.table.setRowCount(0)

        if not alquileres:
            return

        # Enriquecer con nombres legibles usando la lógica de AppGUI
        try:
            if hasattr(self.app, "_enriquecer_facturas_con_nombres"):
                self.app._enriquecer_facturas_con_nombres(alquileres)
        except Exception as e:
            logger.error(
                f"Error enriqueciendo alquileres con nombres: {e}", exc_info=True
            )

        for row_data in alquileres:
            horas = float(row_data.get("horas", 0) or 0)
            monto = float(row_data.get("monto", 0) or 0)

            horas_fmt = f"{round(horas, 2):,.2f}"
            monto_fmt = f"{self.moneda} {round(monto, 2):,.2f}"

            fila = self.table.rowCount()
            self.table.insertRow(fila)

            valores = [
                str(row_data.get("fecha", "")),
                row_data.get("cliente_nombre", ""),
                row_data.get("equipo_nombre", ""),
                row_data.get("operador_nombre", ""),
                row_data.get("ubicacion", ""),
                row_data.get("conduce", ""),
                horas_fmt,
                monto_fmt,
            ]
            for col, val in enumerate(valores):
                self.table.setItem(fila, col, QTableWidgetItem(str(val)))

    # ---------------- Exportar ----------------

    def _construir_dataset(self):
        """Construye el dataset para ReportGenerator (mismo formato que en AppGUI)."""
        filtros = self._obtener_filtros()

        filtros_alq = {
            "fecha_inicio": filtros["fecha_inicio"],
            "fecha_fin": filtros["fecha_fin"],
        }
        if filtros["cliente_id"]:
            filtros_alq["cliente_id"] = filtros["cliente_id"]

        alquileres = self.fm.obtener_alquileres(filtros_alq) or []

        # Enriquecer con nombres igual que en la app
        try:
            if hasattr(self.app, "_enriquecer_facturas_con_nombres"):
                self.app._enriquecer_facturas_con_nombres(alquileres)
        except Exception as e:
            logger.error(
                f"Error enriqueciendo alquileres con nombres (export): {e}",
                exc_info=True,
            )

        datos = []
        for row in alquileres:
            horas = float(row.get("horas", 0) or 0)
            monto = float(row.get("monto", 0) or 0)

            horas_fmt = f"{round(horas, 2):,.2f}"
            monto_fmt = f"{self.moneda} {round(monto, 2):,.2f}"

            datos.append(
                {
                    "fecha": str(row.get("fecha", "")),
                    "cliente": row.get("cliente_nombre", ""),
                    "equipo": row.get("equipo_nombre", ""),
                    "operador": row.get("operador_nombre", ""),
                    "ubicacion": row.get("ubicacion", ""),
                    "conduce": row.get("conduce", ""),
                    "horas": horas_fmt,
                    "monto": monto_fmt,
                }
            )

        return datos, filtros

    def exportar(self, formato: str):
        """Exporta a PDF o Excel usando ReportGenerator."""
        try:
            datos, filtros = self._construir_dataset()
            if not datos:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No hay datos para exportar en el rango seleccionado.",
                )
                return

            ext = "PDF (*.pdf)" if formato == "pdf" else "Excel (*.xlsx)"
            sugerido = (
                f"Reporte_Detallado_Equipos_{filtros['fecha_inicio']}_a_{filtros['fecha_fin']}"
            ).replace(" ", "_")
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte Detallado de Equipos",
                sugerido,
                ext,
            )
            if not file_path:
                return

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

            if formato == "pdf":
                ok, error = rg.to_pdf(file_path)
            else:
                ok, error = rg.to_excel(file_path)

            if ok:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Reporte detallado generado exitosamente:\n{file_path}",
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo generar el reporte detallado:\n{error}",
                )

        except Exception as e:
            logger.error(f"Error exportando reporte detallado: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Ocurrió un error al exportar el reporte:\n{e}",
            )