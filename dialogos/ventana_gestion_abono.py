from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QComboBox, QDateEdit,
    QMessageBox, QLineEdit, QAbstractItemView, QFormLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from typing import Dict, Any, Optional, List


class VentanaGestionAbonos(QDialog):
    """
    Ventana principal para gestionar abonos registrados (adaptada a Firebase).
    UI y comportamiento prácticamente idénticos a la versión SQLite:
    - Filtros por cliente y fecha
    - Tabla con columnas: ID, Fecha, Cliente, Monto Abono, Aplicado a Factura, Comentario
    - Registrar / Editar / Eliminar abonos
    """
    def __init__(self, firebase_manager, moneda: str, clientes_mapa: Dict[str, str], parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.moneda = moneda or ""
        # clientes_mapa: {id_str -> nombre}
        self.clientes_mapa = clientes_mapa or {}

        self.setWindowTitle("Gestión de Abonos Registrados")
        self.resize(1050, 650)
        self.total_abonos_var = "Monto Total Filtrado: 0.00"

        layout = QVBoxLayout(self)

        # --- Filtros ---
        filtros_box = QGroupBox("Filtros")
        filtros_layout = QHBoxLayout(filtros_box)

        self.combo_cliente = QComboBox()
        self.combo_cliente.addItem("Todos", None)
        for cl_id, nombre in sorted(self.clientes_mapa.items(), key=lambda item: item[1]):
            self.combo_cliente.addItem(nombre, cl_id)
        filtros_layout.addWidget(QLabel("Cliente:"))
        filtros_layout.addWidget(self.combo_cliente)

        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_fin = QDateEdit()
        self.fecha_fin.setCalendarPopup(True)

        primera_fecha = self._obtener_fecha_primera_transaccion_abonos()
        if primera_fecha:
            self.fecha_inicio.setDate(QDate.fromString(primera_fecha, "yyyy-MM-dd"))
        else:
            self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_fin.setDate(QDate.currentDate())

        filtros_layout.addWidget(QLabel("Desde:"))
        filtros_layout.addWidget(self.fecha_inicio)
        filtros_layout.addWidget(QLabel("Hasta:"))
        filtros_layout.addWidget(self.fecha_fin)

        layout.addWidget(filtros_box)

        # --- Tabla de abonos ---
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Fecha", "Cliente", "Monto Abono", "Aplicado a Factura", "Comentario"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # --- Total y acciones ---
        acciones_layout = QHBoxLayout()
        self.lbl_total = QLabel(self.total_abonos_var)
        self.lbl_total.setStyleSheet("font-weight:bold;")
        acciones_layout.addWidget(self.lbl_total)

        btn_nuevo = QPushButton("Registrar Abono")
        btn_editar = QPushButton("Editar Abono")
        btn_eliminar = QPushButton("Eliminar Abono(s)")
        btn_cerrar = QPushButton("Cerrar")
        acciones_layout.addWidget(btn_nuevo)
        acciones_layout.addWidget(btn_editar)
        acciones_layout.addWidget(btn_eliminar)
        acciones_layout.addWidget(btn_cerrar)

        layout.addLayout(acciones_layout)

        # --- Conexiones ---
        self.combo_cliente.currentIndexChanged.connect(self.cargar_abonos)
        self.fecha_inicio.dateChanged.connect(self.cargar_abonos)
        self.fecha_fin.dateChanged.connect(self.cargar_abonos)
        btn_nuevo.clicked.connect(self.abrir_dialogo_nuevo_abono)
        btn_editar.clicked.connect(self.abrir_dialogo_editar_abono)
        btn_eliminar.clicked.connect(self.eliminar_abonos)
        btn_cerrar.clicked.connect(self.close)
        self.table.itemDoubleClicked.connect(self.abrir_dialogo_editar_abono)

        self.cargar_abonos()

    # --------------------- UTILIDADES ---------------------

    def _obtener_fecha_primera_transaccion_abonos(self) -> Optional[str]:
        try:
            docs = (
                self.fm.db.collection("abonos")
                .order_by("fecha")
                .limit(1)
                .stream()
            )
            docs = list(docs)
            if not docs:
                return None
            datos = docs[0].to_dict()
            return datos.get("fecha")
        except Exception:
            return None

    def _nombre_cliente_por_id(self, cliente_id: Any) -> str:
        if cliente_id is None or cliente_id == "":
            return ""
        cid_str = str(cliente_id)
        return self.clientes_mapa.get(cid_str, f"ID:{cid_str}")

    # --------------------- CARGA DE DATOS ---------------------

    def cargar_abonos(self):
        """Carga y muestra los abonos filtrados en la tabla (desde Firebase)."""
        self.table.setRowCount(0)
        filtros = {
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
        }

        cliente_id = self.combo_cliente.currentData()
        if cliente_id:
            filtros["cliente_id"] = cliente_id

        try:
            abonos = self.fm.obtener_abonos(
                cliente_id=filtros.get("cliente_id"),
                fecha_inicio=filtros.get("fecha_inicio"),
                fecha_fin=filtros.get("fecha_fin"),
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron obtener abonos:\n{e}")
            return

        total = 0.0
        for abono in abonos:
            row = self.table.rowCount()
            self.table.insertRow(row)

            abono_id = abono.get("id", "")
            fecha = abono.get("fecha", "")
            monto = float(abono.get("monto", 0) or 0)
            comentario = abono.get("comentario") or ""
            cliente_id_abono = abono.get("cliente_id")
            cliente_nombre = self._nombre_cliente_por_id(cliente_id_abono)
            trans_desc = abono.get("transaccion_descripcion") or ""

            self.table.setItem(row, 0, QTableWidgetItem(str(abono_id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(fecha)))
            self.table.setItem(row, 2, QTableWidgetItem(str(cliente_nombre)))
            self.table.setItem(row, 3, QTableWidgetItem(f"{self.moneda} {monto:,.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(str(trans_desc)))
            self.table.setItem(row, 5, QTableWidgetItem(str(comentario)))

            total += monto

        self.lbl_total.setText(f"Monto Total Filtrado: {self.moneda} {total:,.2f}")

    # --------------------- ACCIONES ---------------------

    def abrir_dialogo_nuevo_abono(self):
        dlg = DialogoRegistroAbono(self.fm, self.moneda, self.clientes_mapa, parent=self)
        if dlg.exec():
            self.cargar_abonos()

    def abrir_dialogo_editar_abono(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección requerida", "Seleccione un abono para editar.")
            return
        if len(selected_rows) > 1:
            QMessageBox.warning(self, "Selección múltiple", "Seleccione solo un abono para editar.")
            return

        abono_id = self.table.item(selected_rows[0].row(), 0).text()

        try:
            doc = self.fm.db.collection("abonos").document(abono_id).get()
            if not doc.exists:
                QMessageBox.warning(self, "Error", "No se pudo cargar el abono.")
                return
            datos = doc.to_dict()
            datos["id"] = doc.id
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el abono:\n{e}")
            return

        dlg = DialogoEditarAbono(self.fm, self.moneda, datos, parent=self)
        if dlg.exec():
            self.cargar_abonos()

    def eliminar_abonos(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección requerida", "Seleccione uno o más abonos para eliminar.")
            return

        abono_ids = [self.table.item(row.row(), 0).text() for row in selected_rows]
        msg = ("¿Está seguro de que desea eliminar el abono seleccionado?" if len(abono_ids) == 1
               else f"¿Está seguro de que desea eliminar los {len(abono_ids)} abonos seleccionados?")
        if QMessageBox.question(
            self, "Confirmar Eliminación", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return

        errores = 0
        for abono_id in abono_ids:
            ok = self.fm.eliminar_abono(abono_id)
            if not ok:
                errores += 1

        if errores == 0:
            QMessageBox.information(self, "Éxito", "Abono(s) eliminado(s) correctamente.")
        else:
            QMessageBox.warning(self, "Error", "No se pudieron eliminar algunos abonos.")
        self.cargar_abonos()


class DialogoEditarAbono(QDialog):
    def __init__(self, firebase_manager, moneda: str, datos: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.moneda = moneda or ""
        self.datos = datos

        self.setWindowTitle("Editar Abono")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.fecha_edit = QDateEdit()
        self.fecha_edit.setCalendarPopup(True)
        self.fecha_edit.setDate(QDate.fromString(self.datos.get("fecha", ""), "yyyy-MM-dd"))
        self.monto_edit = QLineEdit(str(self.datos.get("monto", "")))
        comentario_val = self.datos.get("comentario") or ""
        self.comentario_edit = QLineEdit(comentario_val)

        layout.addRow("Fecha:", self.fecha_edit)
        layout.addRow(f"Monto ({self.moneda}):", self.monto_edit)
        layout.addRow("Comentario:", self.comentario_edit)

        btns = QHBoxLayout()
        btn_guardar = QPushButton("Guardar Cambios")
        btn_cancelar = QPushButton("Cancelar")
        btns.addWidget(btn_guardar)
        btns.addWidget(btn_cancelar)
        layout.addRow(btns)

        btn_guardar.clicked.connect(self.guardar)
        btn_cancelar.clicked.connect(self.reject)

    def guardar(self):
        try:
            nuevo_monto = float(self.monto_edit.text())
            nueva_fecha = self.fecha_edit.date().toString("yyyy-MM-dd")
            nuevo_comentario = self.comentario_edit.text().strip()

            datos_update = {
                "fecha": nueva_fecha,
                "monto": nuevo_monto,
                "comentario": nuevo_comentario,
            }

            if self.fm.editar_abono(self.datos["id"], datos_update):
                QMessageBox.information(self, "Éxito", "Abono actualizado correctamente.")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "No se pudo actualizar el abono.")
        except ValueError:
            QMessageBox.warning(self, "Dato Inválido", "El monto debe ser un número válido.")
        except Exception as ex:
            QMessageBox.critical(self, "Error", f"Ocurrió un error: {ex}")


class DialogoRegistroAbono(QDialog):
    """
    Diálogo para registrar un abono general a un cliente, mostrando facturas pendientes y
    aplicando el monto a las facturas más antiguas primero (versión Firebase).
    """
    abono_registrado = pyqtSignal()

    def __init__(self, firebase_manager, moneda: str, clientes_mapa: Dict[str, str], parent=None):
        super().__init__(parent)
        self.fm = firebase_manager
        self.moneda = moneda or ""
        # clientes_mapa: {id_str -> nombre}
        self.clientes_mapa = clientes_mapa

        self.setWindowTitle("Registrar Abono a Cliente")
        self.resize(600, 500)

        self.clientes_nombre_a_id: Dict[str, str] = {}
        self.cuentas_nombre_a_id: Dict[str, str] = {}

        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Clientes
        self.combo_cliente = QComboBox()
        # construir mapa nombre->id a partir de clientes_mapa {id->nombre}
        for cid, nombre in sorted(self.clientes_mapa.items(), key=lambda x: x[1]):
            self.clientes_nombre_a_id[nombre] = cid
            self.combo_cliente.addItem(nombre)
        form.addRow("Cliente:", self.combo_cliente)

        # Fecha
        self.fecha_edit = QDateEdit()
        self.fecha_edit.setCalendarPopup(True)
        self.fecha_edit.setDate(QDate.currentDate())
        form.addRow("Fecha del Abono:", self.fecha_edit)

        # Monto
        self.monto_edit = QLineEdit()
        form.addRow(f"Monto a Abonar ({self.moneda}):", self.monto_edit)

        # Cuentas desde Firebase
        cuentas = self.fm.obtener_cuentas() or []
        self.combo_cuenta = QComboBox()
        for c in cuentas:
            nombre = c.get("nombre", "")
            cid = c.get("id")
            if nombre and cid:
                self.cuentas_nombre_a_id[nombre] = cid
                self.combo_cuenta.addItem(nombre)
        form.addRow("Depositar en Cuenta:", self.combo_cuenta)

        # Comentario
        self.comentario_edit = QLineEdit()
        form.addRow("Comentario:", self.comentario_edit)

        layout.addLayout(form)

        # Facturas pendientes
        self.tree_pendientes = QTableWidget(0, 3)
        self.tree_pendientes.setHorizontalHeaderLabels(["Fecha", "Descripción", "Monto"])
        self.tree_pendientes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(QLabel("Facturas Pendientes de Pago"))
        layout.addWidget(self.tree_pendientes)
        self.lbl_total_pendiente = QLabel("Total Pendiente: 0.00")
        self.lbl_total_pendiente.setStyleSheet("font-weight:bold;color:red")
        layout.addWidget(self.lbl_total_pendiente)

        # Botones
        btns = QHBoxLayout()
        btn_guardar = QPushButton("Guardar Abono")
        btn_cancelar = QPushButton("Cancelar")
        btns.addWidget(btn_guardar)
        btns.addWidget(btn_cancelar)
        layout.addLayout(btns)

        # Conexiones
        self.combo_cliente.currentIndexChanged.connect(self.actualizar_facturas_pendientes)
        btn_guardar.clicked.connect(self.guardar_abono)
        btn_cancelar.clicked.connect(self.reject)

        # Cargar pendientes iniciales
        self.actualizar_facturas_pendientes()

    # ----------------- FACTURAS PENDIENTES -----------------

    def actualizar_facturas_pendientes(self):
        """Carga las facturas pendientes para el cliente seleccionado desde Firebase."""
        self.tree_pendientes.setRowCount(0)

        cliente_nombre = self.combo_cliente.currentText()
        cliente_id = self.clientes_nombre_a_id.get(cliente_nombre)
        if not cliente_id:
            self.lbl_total_pendiente.setText("Total Pendiente: 0.00")
            return

        pendientes = self.fm.obtener_facturas_pendientes_cliente(cliente_id)
        total = 0.0
        for trans in pendientes:
            row = self.tree_pendientes.rowCount()
            self.tree_pendientes.insertRow(row)
            fecha = trans.get("fecha", "")
            descripcion = trans.get("descripcion") or trans.get("observacion") or ""
            monto = float(trans.get("monto", 0) or 0)
            self.tree_pendientes.setItem(row, 0, QTableWidgetItem(str(fecha)))
            self.tree_pendientes.setItem(row, 1, QTableWidgetItem(str(descripcion)))
            self.tree_pendientes.setItem(row, 2, QTableWidgetItem(f"{self.moneda} {monto:,.2f}"))
            total += monto

        self.lbl_total_pendiente.setText(f"Total Pendiente: {self.moneda} {total:,.2f}")

    # ----------------- GUARDAR ABONO GENERAL -----------------

    def guardar_abono(self):
        try:
            cliente_nombre = self.combo_cliente.currentText()
            cliente_id = self.clientes_nombre_a_id.get(cliente_nombre)
            cuenta_nombre = self.combo_cuenta.currentText()
            cuenta_id = self.cuentas_nombre_a_id.get(cuenta_nombre)

            if not cliente_id:
                raise ValueError("Debe seleccionar un cliente válido.")
            if not cuenta_id:
                raise ValueError("Debe seleccionar una cuenta de destino válida.")

            monto = float(self.monto_edit.text())
            if monto <= 0:
                raise ValueError("El monto debe ser mayor que cero.")

            datos_pago = {
                "cliente_id": cliente_id,
                "fecha": self.fecha_edit.date().toString("yyyy-MM-dd"),
                "monto": monto,
                "cuenta_id": cuenta_id,
                "comentario": self.comentario_edit.text().strip(),
            }

            resultado = self.fm.registrar_abono_general_cliente(datos_pago)
            if resultado is True:
                QMessageBox.information(self, "Éxito", "Abono registrado y aplicado correctamente.")
                self.abono_registrado.emit()
                self.accept()
            elif isinstance(resultado, str):
                QMessageBox.warning(self, "Aviso", resultado)
            else:
                QMessageBox.warning(self, "Error", "No se pudo registrar el abono general. Revise el log.")
        except ValueError as e:
            QMessageBox.warning(self, "Error de Validación", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error: {e}")