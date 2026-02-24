from __future__ import annotations

import os
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QDateEdit, QLineEdit, QTextEdit, QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import QDate

logger = logging.getLogger(__name__)

METODOS_DEFECTO = ["Efectivo", "Transferencia", "Cheque", "Tarjeta", "Otro"]


class PagoOperadorDialog(QDialog):
    """
    Diálogo crear/editar pagos a operadores.
    Adaptado a Firebase, pero manteniendo comportamiento del sistema anterior:
      - Campos: cuenta, operador, equipo, horas, monto, fecha, método, descripción, comentario, adjunto.
      - Autocompletado de descripción/comentario.
      - Asegura categoría 'PAGO HRS OPERADOR' y subcategoría = equipo en Firebase si tienes esa lógica.
    """

    def __init__(
        self,
        firebase_manager,
        storage_manager,
        operadores_mapa: dict,
        cuentas_mapa: Optional[dict] = None,
        equipos_mapa: Optional[dict] = None,
        pago: Optional[dict] = None,
        parent=None,
        moneda_symbol: str = "RD$",
        metodos_sugeridos=None,
    ):
        super().__init__(parent)
        self.fm = firebase_manager
        self.sm = storage_manager
        self.operadores_mapa = operadores_mapa or {}
        self.cuentas_mapa = cuentas_mapa or {}
        self.equipos_mapa = equipos_mapa or {}
        self.moneda_symbol = moneda_symbol
        self.metodos = metodos_sugeridos or METODOS_DEFECTO

        # Si viene un dict de pago, estamos en modo edición
        self.pago_actual = pago or {}
        self.pago_id = self.pago_actual.get("id")

        self.ruta_local_adjunto: Optional[str] = None

        self.setWindowTitle(
            "Registrar Pago a Operador" if not self.pago_id else f"Editar Pago {self.pago_id}"
        )
        self.setMinimumWidth(620)

        self._build_ui()
        self._populate_combos()
        self._connect_autofill()

        if self.pago_actual:
            self._load_data_into_form()
        else:
            self._autocompletar_textos()

    # UI ----------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Cuenta
        self.combo_cuenta = QComboBox()
        form.addRow("Cuenta:", self.combo_cuenta)

        # Operador
        self.combo_operador = QComboBox()
        form.addRow("Operador:", self.combo_operador)

        # Equipo
        self.combo_equipo = QComboBox()
        form.addRow("Equipo:", self.combo_equipo)

        # Horas
        self.txt_horas = QLineEdit()
        self.txt_horas.setPlaceholderText("Ej: 6.5")
        form.addRow("Horas:", self.txt_horas)

        # Monto
        self.txt_monto = QLineEdit()
        self.txt_monto.setPlaceholderText("Ej: 14500.00")
        form.addRow(f"Monto ({self.moneda_symbol}):", self.txt_monto)

        # Fecha
        self.date_fecha = QDateEdit(calendarPopup=True)
        self.date_fecha.setDisplayFormat("yyyy-MM-dd")
        self.date_fecha.setDate(QDate.currentDate())
        form.addRow("Fecha:", self.date_fecha)

        # Método de pago
        self.combo_metodo = QComboBox()
        form.addRow("Método:", self.combo_metodo)

        # Descripción
        self.txt_descripcion = QLineEdit()
        form.addRow("Descripción:", self.txt_descripcion)

        # Comentario
        self.txt_comentario = QTextEdit()
        form.addRow("Comentario:", self.txt_comentario)

        # Adjunto
        adj_l = QHBoxLayout()
        self.lbl_adjunto = QLabel("No seleccionado")
        self.btn_sel_adjunto = QPushButton("Seleccionar Archivo")
        self.btn_sel_adjunto.clicked.connect(self._seleccionar_archivo)
        adj_l.addWidget(self.lbl_adjunto)
        adj_l.addWidget(self.btn_sel_adjunto)
        form.addRow("Adjunto:", adj_l)

        layout.addLayout(form)

        # Botones
        btns = QHBoxLayout()
        self.btn_guardar = QPushButton("Guardar")
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar.clicked.connect(self._guardar)
        self.btn_cancelar.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(self.btn_guardar)
        btns.addWidget(self.btn_cancelar)
        layout.addLayout(btns)

    def _populate_combos(self):
        # Cuenta
        self.combo_cuenta.clear()
        self.combo_cuenta.addItem("-- Seleccione --", None)
        for cid, nom in sorted(self.cuentas_mapa.items(), key=lambda x: x[1]):
            self.combo_cuenta.addItem(nom, str(cid))

        # Operador
        self.combo_operador.clear()
        self.combo_operador.addItem("-- Seleccione --", None)
        for oid, nom in sorted(self.operadores_mapa.items(), key=lambda x: x[1]):
            self.combo_operador.addItem(nom, str(oid))

        # Equipo
        self.combo_equipo.clear()
        self.combo_equipo.addItem("-- Seleccione --", None)
        for eid, nom in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
            self.combo_equipo.addItem(nom, str(eid))

        # Método
        self.combo_metodo.clear()
        self.combo_metodo.addItems(self.metodos)

    def _connect_autofill(self):
        self.combo_operador.currentIndexChanged.connect(self._autocompletar_textos)
        self.combo_equipo.currentIndexChanged.connect(self._autocompletar_textos)
        self.txt_horas.textChanged.connect(self._autocompletar_textos)

    def _load_data_into_form(self):
        p = self.pago_actual or {}

        # Helpers para seleccionar item por data
        def set_by_data(combo: QComboBox, value):
            sval = str(value) if value not in (None, "") else None
            if sval is None:
                return
            for i in range(combo.count()):
                if combo.itemData(i) == sval:
                    combo.setCurrentIndex(i)
                    return

        set_by_data(self.combo_cuenta, p.get("cuenta_id"))
        set_by_data(self.combo_operador, p.get("operador_id"))
        set_by_data(self.combo_equipo, p.get("equipo_id"))

        # Horas/Monto
        self.txt_horas.setText(
            "" if p.get("horas") in (None, "") else str(p.get("horas"))
        )
        self.txt_monto.setText(
            "" if p.get("monto") in (None, "") else str(p.get("monto"))
        )

        # Fecha
        f = p.get("fecha")
        if f:
            qd = QDate.fromString(f, "yyyy-MM-dd")
            if qd.isValid():
                self.date_fecha.setDate(qd)

        # Método
        if p.get("metodo_pago"):
            idx = self.combo_metodo.findText(p["metodo_pago"])
            if idx >= 0:
                self.combo_metodo.setCurrentIndex(idx)

        # Descripción/Comentario
        self.txt_descripcion.setText(
            p.get("descripcion", "") or p.get("concepto", "")
        )
        self.txt_comentario.setText(
            p.get("comentario", "") or p.get("nota", "")
        )

        # Adjunto
        if p.get("archivo_storage_path"):
            self.lbl_adjunto.setText(
                f"(adjunto existente) {p['archivo_storage_path']}"
            )

    # Autocompletar como el sistema anterior ---------------------------------
    def _autocompletar_textos(self):
        operador = self.combo_operador.currentText()
        equipo = self.combo_equipo.currentText()
        horas = (self.txt_horas.text() or "").strip()

        cliente, ubicacion = "", ""
        try:
            eid = self.combo_equipo.currentData()
            if eid:
                # Debes implementar esto en FirebaseManager:
                # obtener_cliente_y_ubicacion_equipo_actual(equipo_id)
                info = self.fm.obtener_cliente_y_ubicacion_equipo_actual(str(eid))
                if info:
                    cliente = info.get("cliente", "") or ""
                    ubicacion = info.get("ubicacion", "") or ""
        except Exception:
            pass

        desc = f"Pago {horas} Horas Operador {operador}".strip()
        comm = (
            f"Pago {horas} Horas, Operador {operador}, "
            f"Cliente {cliente}, Ubicacion {ubicacion}"
        ).strip()

        if (
            not self.pago_actual
            or self.txt_descripcion.text().strip() == ""
            or horas
        ):
            self.txt_descripcion.setText(desc)
        if (
            not self.pago_actual
            or self.txt_comentario.toPlainText().strip() == ""
            or horas
        ):
            self.txt_comentario.setText(comm)

    # Guardar -----------------------------------------------------------------
    def _guardar(self):
        errs = []
        if self.combo_cuenta.currentData() is None:
            errs.append("Seleccione una cuenta.")
        if self.combo_operador.currentData() is None:
            errs.append("Seleccione un operador.")
        if self.combo_equipo.currentData() is None:
            errs.append("Seleccione un equipo.")
        if not self.txt_monto.text().strip():
            errs.append("Ingrese un monto.")

        # Horas/monto numéricos
        try:
            horas = float(
                self.txt_horas.text().strip().replace(",", ".")
            ) if self.txt_horas.text().strip() else 0.0
        except Exception:
            errs.append("Las horas deben ser numéricas.")
            horas = 0.0
        try:
            monto = float(self.txt_monto.text().strip().replace(",", ""))
        except Exception:
            errs.append("El monto debe ser numérico.")
            monto = 0.0

        if errs:
            QMessageBox.warning(self, "Validación", "\n".join(errs))
            return

        fecha = self.date_fecha.date().toString("yyyy-MM-dd")

        # (Opcional) asegurar categoría/subcategoría en la colección de gastos
        categoria_id = None
        subcategoria_id = None
        try:
            eq_id = self.combo_equipo.currentData()
            if hasattr(self.fm, "ensure_categoria_y_subcategoria_pago_operador"):
                categoria_id, subcategoria_id = self.fm.ensure_categoria_y_subcategoria_pago_operador(
                    str(eq_id)
                )
        except Exception as e:
            logger.warning(f"No se pudo asegurar categoría/subcategoría: {e}")

        data = {
            "fecha": fecha,
            "cuenta_id": self.combo_cuenta.currentData(),
            "operador_id": self.combo_operador.currentData(),
            "equipo_id": self.combo_equipo.currentData(),
            "horas": horas,
            "monto": monto,
            "metodo_pago": self.combo_metodo.currentText().strip(),
            "descripcion": self.txt_descripcion.text().strip(),
            "comentario": self.txt_comentario.toPlainText().strip(),
            "categoria_id": categoria_id,
            "subcategoria_id": subcategoria_id,
        }

        try:
            if not self.pago_id:
                # Debes implementar en FirebaseManager:
                # crear_pago_operador(data) -> nuevo_id
                nuevo_id = self.fm.crear_pago_operador(data)
                if self.ruta_local_adjunto and nuevo_id:
                    # Debes implementar en FirebaseManager:
                    # subir_archivo_pago_operador(pago_id, fecha, ruta_local)
                    ok, sp = self.fm.subir_archivo_pago_operador(
                        nuevo_id, fecha, self.ruta_local_adjunto
                    )
                    if ok:
                        self.fm.actualizar_pago_operador(
                            nuevo_id, {"archivo_storage_path": sp}
                        )
                QMessageBox.information(self, "Éxito", "Pago registrado.")
            else:
                self.fm.actualizar_pago_operador(self.pago_id, data)
                if self.ruta_local_adjunto:
                    ok, sp = self.fm.subir_archivo_pago_operador(
                        self.pago_id, fecha, self.ruta_local_adjunto
                    )
                    if ok:
                        self.fm.actualizar_pago_operador(
                            self.pago_id, {"archivo_storage_path": sp}
                        )
                QMessageBox.information(self, "Éxito", "Pago actualizado.")
            self.accept()
        except Exception as e:
            logger.error(f"Error guardando pago operador: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")

    def _seleccionar_archivo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar comprobante", "", "Todos (*.*)"
        )
        if path:
            self.ruta_local_adjunto = path
            self.lbl_adjunto.setText(os.path.basename(path))