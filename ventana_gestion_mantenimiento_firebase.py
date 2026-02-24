import logging
from typing import Any, Dict, List

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QHeaderView,
)
from PyQt6.QtCore import Qt

from firebase_manager import FirebaseManager
from dialogos.dialogo_mantenimiento import DialogoMantenimiento

logger = logging.getLogger(__name__)


class VentanaGestionMantenimientosFirebase(QDialog):
    """
    Gestión de Mantenimiento de Equipos usando Firebase (Firestore).
    Versión adaptada de VentanaGestionMantenimientos que usaba SQLite.
    """

    def __init__(self, firebase_manager: FirebaseManager, proyecto_actual: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.proyecto_actual = proyecto_actual  # se espera dict con al menos 'id'
        self.setWindowTitle("Gestión y Estado de Mantenimiento de Equipos")
        self.resize(1100, 700)

        layout = QVBoxLayout(self)

        # --- Tabla de estado de equipos (resumen) ---
        self.table_estado = QTableWidget(0, 6)
        self.table_estado.setHorizontalHeaderLabels(
            [
                "Equipo",
                "Intervalo de Servicio",
                "Uso desde Servicio",
                "Uso Restante",
                "Progreso de Uso",
                "ID",
            ]
        )
        self.table_estado.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_estado.setColumnHidden(5, True)
        layout.addWidget(QLabel("Estado Actual de Equipos (Mantenimiento)"))
        layout.addWidget(self.table_estado)

        # --- Botones de acción ---
        btns = QHBoxLayout()
        self.btn_registrar = QPushButton("Registrar Nuevo Mantenimiento")
        self.btn_editar = QPushButton("Editar Mantenimiento")
        self.btn_eliminar = QPushButton("Eliminar Mantenimiento")
        self.btn_configurar_intervalo = QPushButton("Configurar Intervalo")
        btns.addWidget(self.btn_registrar)
        btns.addWidget(self.btn_editar)
        btns.addWidget(self.btn_eliminar)
        btns.addWidget(self.btn_configurar_intervalo)
        layout.addLayout(btns)

        # Mientras no exista DialogoIntervaloEquipo en 4.0, deshabilitamos este botón
        self.btn_configurar_intervalo.setEnabled(False)
        self.btn_configurar_intervalo.setToolTip(
            "Configuración de intervalos pendiente de migrar a Firebase"
        )

        # --- Historial de mantenimiento ---
        # Cambiamos columnas: la primera será Equipo, y el ID lo guardaremos en UserRole
        self.table_historial = QTableWidget(0, 6)
        self.table_historial.setHorizontalHeaderLabels(
            [
                "Equipo",              # 0
                "Fecha Servicio",      # 1
                "Costo",               # 2
                "Descripción",         # 3
                "Horas Totales Equipo",# 4
                "KM Totales Equipo",   # 5
            ]
        )
        self.table_historial.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(QLabel("Historial de Mantenimiento del Equipo Seleccionado"))
        layout.addWidget(self.table_historial)

        # --- Conexiones ---
        self.btn_registrar.clicked.connect(self.abrir_dialogo_registro)
        self.btn_editar.clicked.connect(self.editar_mantenimiento_seleccionado)
        self.btn_eliminar.clicked.connect(self.eliminar_mantenimiento_seleccionado)

        self.table_estado.itemSelectionChanged.connect(self.cargar_historial_equipo)
        self.table_historial.itemDoubleClicked.connect(self.editar_mantenimiento_seleccionado)

        # Cargar datos iniciales
        self.refrescar_estado_equipos()

    # ------------------------------------------------------------------ Datos

    def refrescar_estado_equipos(self):
        """
        Carga el estado general de mantenimiento de equipos desde Firebase.
        Depende de FirebaseManager.obtener_estado_mantenimiento_equipos.
        """
        self.table_estado.setRowCount(0)

        try:
            proyecto_id = (
                self.proyecto_actual.get("id")
                if isinstance(self.proyecto_actual, dict)
                else self.proyecto_actual
            )
            estado_equipos: List[Dict[str, Any]] = self.fm.obtener_estado_mantenimiento_equipos(
                proyecto_id
            )
        except Exception as e:
            logger.error(
                f"Error al obtener estado de mantenimiento de equipos: {e}", exc_info=True
            )
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cargar el estado de mantenimiento:\n{e}",
            )
            return

        for eq in estado_equipos:
            row = self.table_estado.rowCount()
            self.table_estado.insertRow(row)
            self.table_estado.setItem(row, 0, QTableWidgetItem(eq.get("nombre", "")))
            self.table_estado.setItem(row, 1, QTableWidgetItem(eq.get("intervalo_txt", "")))
            self.table_estado.setItem(row, 2, QTableWidgetItem(eq.get("uso_txt", "")))
            self.table_estado.setItem(row, 3, QTableWidgetItem(eq.get("restante_txt", "")))

            progreso_item = QTableWidgetItem(eq.get("progreso_txt", ""))
            if eq.get("critico"):
                progreso_item.setBackground(Qt.GlobalColor.red)
            elif eq.get("alerta"):
                progreso_item.setBackground(Qt.GlobalColor.yellow)
            self.table_estado.setItem(row, 4, progreso_item)

            self.table_estado.setItem(row, 5, QTableWidgetItem(str(eq.get("id", ""))))

    def cargar_historial_equipo(self):
        """
        Carga el historial de mantenimientos para el equipo seleccionado en table_estado.
        Usa FirebaseManager.obtener_mantenimientos_por_equipo.
        """
        selected = self.table_estado.currentRow()
        if selected == -1:
            self.table_historial.setRowCount(0)
            return

        equipo_id_item = self.table_estado.item(selected, 5)
        if not equipo_id_item:
            self.table_historial.setRowCount(0)
            return

        equipo_id = equipo_id_item.text()
        # Nombre visible en la tabla de estado
        equipo_nombre_item = self.table_estado.item(selected, 0)
        equipo_nombre = equipo_nombre_item.text() if equipo_nombre_item else ""

        try:
            lista = self.fm.obtener_mantenimientos_por_equipo(equipo_id)
        except Exception as e:
            logger.error(
                f"Error al obtener mantenimientos para equipo {equipo_id}: {e}", exc_info=True
            )
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cargar el historial del equipo:\n{e}",
            )
            return

        self.table_historial.setRowCount(0)
        for m in lista:
            row = self.table_historial.rowCount()
            self.table_historial.insertRow(row)

            # Columna 0: nombre de equipo, y en UserRole guardamos el ID del mantenimiento
            it_equipo = QTableWidgetItem(equipo_nombre)
            it_equipo.setData(Qt.ItemDataRole.UserRole, str(m.get("id", "")))
            self.table_historial.setItem(row, 0, it_equipo)

            self.table_historial.setItem(
                row,
                1,
                QTableWidgetItem(str(m.get("fecha_servicio", m.get("fecha", "")))),
            )
            self.table_historial.setItem(
                row,
                2,
                QTableWidgetItem(str(m.get("costo", m.get("valor", "")))),
            )
            self.table_historial.setItem(
                row,
                3,
                QTableWidgetItem(str(m.get("descripcion", ""))),
            )
            self.table_historial.setItem(
                row,
                4,
                QTableWidgetItem(
                    str(m.get("horas_totales_equipo", m.get("odometro_horas", "")))
                ),
            )
            self.table_historial.setItem(
                row,
                5,
                QTableWidgetItem(
                    str(m.get("km_totales_equipo", m.get("odometro_km", "")))
                ),
            )

    # ------------------------------------------------------------- Acciones UI

    def _id_historial_actual(self) -> str | None:
        """Devuelve el id del mantenimiento seleccionado en la tabla de historial (desde UserRole)."""
        row = self.table_historial.currentRow()
        if row < 0:
            return None
        it = self.table_historial.item(row, 0)
        if not it:
            return None
        mid = it.data(Qt.ItemDataRole.UserRole)
        return str(mid) if mid else None

    def abrir_dialogo_registro(self):
        selected = self.table_estado.currentRow()
        if selected == -1:
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Seleccione un equipo primero.",
            )
            return

        equipo_id_item = self.table_estado.item(selected, 5)
        if not equipo_id_item:
            QMessageBox.warning(self, "Error", "No se pudo determinar el ID del equipo.")
            return

        equipo_id = equipo_id_item.text()

        dlg = DialogoMantenimiento(
            db=self.fm,
            proyecto_actual=self.proyecto_actual,
            equipo_id=equipo_id,
            datos=None,
            parent=self,
        )
        if dlg.exec():
            self.refrescar_estado_equipos()
            self.cargar_historial_equipo()

    def editar_mantenimiento_seleccionado(self):
        selected_estado = self.table_estado.currentRow()
        if selected_estado == -1:
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Seleccione un equipo.",
            )
            return

        mid = self._id_historial_actual()
        if not mid:
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Seleccione un mantenimiento.",
            )
            return

        equipo_id_item = self.table_estado.item(selected_estado, 5)
        if not equipo_id_item:
            QMessageBox.warning(self, "Error", "No se pudo determinar el equipo.")
            return
        equipo_id = equipo_id_item.text()

        try:
            lista = self.fm.obtener_mantenimientos_por_equipo(equipo_id)
        except Exception as e:
            logger.error(
                f"Error obteniendo mantenimientos para edición (equipo {equipo_id}): {e}",
                exc_info=True,
            )
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cargar el historial del equipo:\n{e}",
            )
            return

        mantenimiento = next((m for m in lista if str(m.get("id")) == str(mid)), None)
        if not mantenimiento:
            QMessageBox.warning(
                self,
                "Error",
                "No se encontró el mantenimiento seleccionado.",
            )
            return

        dlg = DialogoMantenimiento(
            db=self.fm,
            proyecto_actual=self.proyecto_actual,
            equipo_id=equipo_id,
            datos=mantenimiento,
            parent=self,
        )
        if dlg.exec():
            self.refrescar_estado_equipos()
            self.cargar_historial_equipo()

    def eliminar_mantenimiento_seleccionado(self):
        mid = self._id_historial_actual()
        if not mid:
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Seleccione un mantenimiento a eliminar.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirmar",
            "¿Eliminar este mantenimiento?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            exito = self.fm.eliminar_mantenimiento(mid)
        except Exception as e:
            logger.error(f"Error eliminando mantenimiento {mid}: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo eliminar el mantenimiento:\n{e}",
            )
            return

        if exito:
            QMessageBox.information(self, "Éxito", "Mantenimiento eliminado.")
            self.refrescar_estado_equipos()
            self.cargar_historial_equipo()
        else:
            QMessageBox.warning(self, "Error", "No se pudo eliminar el mantenimiento.")