from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QDateEdit, QLineEdit, QTextEdit, QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import QDate
import os
import logging

logger = logging.getLogger(__name__)

class GastoDialog(QDialog):
    """
    Diálogo para registrar o editar un gasto de equipo.
    Modo:
      - nuevo: gasto_id=None
      - edición: gasto_id != None (se carga el gasto existente)
    Campos:
      fecha, equipo, cuenta, categoría, subcategoría, descripción, monto, comentario, adjunto (archivo)
    Al guardar:
      - Sube (opcional) el archivo a Storage: gastos/YYYY/MM/<gastoID_o_temp>.<ext>
    """
    def __init__(self, firebase_manager, storage_manager,
                 equipos_mapa, cuentas_mapa, categorias_mapa, subcategorias_mapa,
                 gasto_id=None, parent=None, moneda_symbol="RD$"):
        super().__init__(parent)
        self.setWindowTitle("Registrar Gasto" if not gasto_id else f"Editar Gasto {gasto_id}")
        self.setMinimumWidth(600)
        self.fm = firebase_manager
        self.sm = storage_manager
        self.gasto_id = gasto_id
        self.moneda_symbol = moneda_symbol

        # Mapas (id -> nombre)
        self.equipos_mapa = equipos_mapa
        self.cuentas_mapa = cuentas_mapa
        self.categorias_mapa = categorias_mapa
        self.subcategorias_mapa = subcategorias_mapa

        # Valores actuales si es edición
        self.gasto_actual = None
        if self.gasto_id:
            try:
                self.gasto_actual = self.fm.obtener_gasto_por_id(self.gasto_id)
            except Exception as e:
                logger.error(f"No se pudo obtener gasto {self.gasto_id}: {e}", exc_info=True)

        # Archivo adjunto (ruta local elegida antes de subir)
        self.ruta_local_adjunto = None

        self._build_ui()
        self._populate_combos()
        if self.gasto_actual:
            self._load_data_into_form()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Fecha
        self.date_fecha = QDateEdit(calendarPopup=True)
        self.date_fecha.setDisplayFormat("yyyy-MM-dd")
        self.date_fecha.setDate(QDate.currentDate())
        form.addRow("Fecha:", self.date_fecha)

        # Equipo
        self.combo_equipo = QComboBox()
        form.addRow("Equipo:", self.combo_equipo)

        # Cuenta
        self.combo_cuenta = QComboBox()
        form.addRow("Cuenta:", self.combo_cuenta)

        # Categoría
        self.combo_categoria = QComboBox()
        self.combo_categoria.currentIndexChanged.connect(self._filtrar_subcategorias)
        form.addRow("Categoría:", self.combo_categoria)

        # Subcategoría
        self.combo_subcategoria = QComboBox()
        form.addRow("Subcategoría:", self.combo_subcategoria)

        # Descripción (linea corta)
        self.txt_descripcion = QLineEdit()
        form.addRow("Descripción:", self.txt_descripcion)

        # Monto
        self.txt_monto = QLineEdit()
        self.txt_monto.setPlaceholderText("Ej: 1500.00")
        form.addRow(f"Monto ({self.moneda_symbol}):", self.txt_monto)

        # Comentario (largo)
        self.txt_comentario = QTextEdit()
        self.txt_comentario.setPlaceholderText("Comentario adicional / notas...")
        form.addRow("Comentario:", self.txt_comentario)

        # Adjunto
        adj_layout = QHBoxLayout()
        self.lbl_adjunto = QLabel("No seleccionado")
        self.btn_seleccionar_adjunto = QPushButton("Seleccionar Archivo")
        self.btn_seleccionar_adjunto.clicked.connect(self._seleccionar_archivo)
        adj_layout.addWidget(self.lbl_adjunto)
        adj_layout.addWidget(self.btn_seleccionar_adjunto)
        form.addRow("Adjunto (opcional):", adj_layout)

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
        # Equipo
        self.combo_equipo.clear()
        self.combo_equipo.addItem("-- Seleccione --", None)
        for eq_id, nombre in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
            self.combo_equipo.addItem(nombre, eq_id)

        # Cuenta
        self.combo_cuenta.clear()
        self.combo_cuenta.addItem("-- Seleccione --", None)
        for c_id, nombre in sorted(self.cuentas_mapa.items(), key=lambda x: x[1]):
            self.combo_cuenta.addItem(nombre, c_id)

        # Categoría
        self.combo_categoria.clear()
        self.combo_categoria.addItem("-- Seleccione --", None)
        for cat_id, nombre in sorted(self.categorias_mapa.items(), key=lambda x: x[1]):
            self.combo_categoria.addItem(nombre, cat_id)

        # Subcategoría (se llena luego en _filtrar_subcategorias)
        self.combo_subcategoria.clear()
        self.combo_subcategoria.addItem("-- Seleccione --", None)

    def _filtrar_subcategorias(self):
        """
        Filtra subcategorías por la categoría seleccionada (si tu mapa lo permite).
        Si el mapa no tiene agrupación por categoría, las muestra todas.
        """
        seleccion_cat_id = self.combo_categoria.currentData()
        self.combo_subcategoria.blockSignals(True)
        self.combo_subcategoria.clear()
        self.combo_subcategoria.addItem("-- Seleccione --", None)

        # Asumimos que subcategorias_mapa = {subcat_id: nombre}. No hay agrupación.
        # Si en el futuro guardas relación categoría->subcategoría, aquí aplicas el filtro.
        for sub_id, nombre in sorted(self.subcategorias_mapa.items(), key=lambda x: x[1]):
            self.combo_subcategoria.addItem(nombre, sub_id)

        self.combo_subcategoria.blockSignals(False)

    def _load_data_into_form(self):
        g = self.gasto_actual
        if not g:
            return
        # fecha
        fecha_str = g.get("fecha")
        if fecha_str:
            qd = QDate.fromString(fecha_str, "yyyy-MM-dd")
            if qd.isValid():
                self.date_fecha.setDate(qd)

        # IDs como string
        eq_id = str(g.get("equipo_id")) if g.get("equipo_id") not in (None, "") else None
        self._set_combo_by_data(self.combo_equipo, eq_id)

        ct_id = str(g.get("cuenta_id")) if g.get("cuenta_id") not in (None, "") else None
        self._set_combo_by_data(self.combo_cuenta, ct_id)

        cat_id = str(g.get("categoria_id")) if g.get("categoria_id") not in (None, "") else None
        self._set_combo_by_data(self.combo_categoria, cat_id)
        self._filtrar_subcategorias()
        sub_id = str(g.get("subcategoria_id")) if g.get("subcategoria_id") not in (None, "") else None
        self._set_combo_by_data(self.combo_subcategoria, sub_id)

        self.txt_descripcion.setText(g.get("descripcion", "") or "")
        self.txt_monto.setText(str(g.get("monto", "") or ""))
        self.txt_comentario.setText(g.get("comentario", "") or "")

        if g.get("archivo_storage_path"):
            self.lbl_adjunto.setText(f"(adjunto existente) {g.get('archivo_storage_path')}")


    def _guardar(self):
        errores = self._validar()
        if errores:
            QMessageBox.warning(self, "Validación", "\n".join(errores))
            return

        data = {
            "fecha": self.date_fecha.date().toString("yyyy-MM-dd"),
            "equipo_id": self.combo_equipo.currentData() or None,
            "cuenta_id": self.combo_cuenta.currentData() or None,
            "categoria_id": self.combo_categoria.currentData() or None,
            "subcategoria_id": self.combo_subcategoria.currentData() or None,
            "descripcion": self.txt_descripcion.text().strip(),
            "monto": float(self.txt_monto.text().strip().replace(",", "")),
            "comentario": self.txt_comentario.toPlainText().strip(),
        }

        try:
            if not self.gasto_id:
                # Crear
                nuevo_id = self.fm.crear_gasto(data)
                logger.info(f"Gasto creado ID={nuevo_id}")
                if self.ruta_local_adjunto and nuevo_id:
                    ok, storage_path = self.fm.subir_archivo_gasto(nuevo_id, data["fecha"], self.ruta_local_adjunto)
                    if ok:
                        self.fm.actualizar_gasto(nuevo_id, {"archivo_storage_path": storage_path})
                QMessageBox.information(self, "Éxito", "Gasto registrado correctamente.")
            else:
                # Actualizar
                self.fm.actualizar_gasto(self.gasto_id, data)
                if self.ruta_local_adjunto:
                    ok, storage_path = self.fm.subir_archivo_gasto(self.gasto_id, data["fecha"], self.ruta_local_adjunto)
                    if ok:
                        self.fm.actualizar_gasto(self.gasto_id, {"archivo_storage_path": storage_path})
                QMessageBox.information(self, "Éxito", "Gasto actualizado correctamente.")
            self.accept()
        except Exception as e:
            logger.error(f"Error guardando gasto: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudo guardar el gasto:\n{e}")
            

    def _set_combo_by_data(self, combo: QComboBox, data_value):
        if data_value is None:
            return
        for i in range(combo.count()):
            if combo.itemData(i) == data_value:
                combo.setCurrentIndex(i)
                break

    def _seleccionar_archivo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo de gasto",
                                                   "", "Todos (*.*)")
        if file_path:
            self.ruta_local_adjunto = file_path
            base = os.path.basename(file_path)
            self.lbl_adjunto.setText(base)

    def _validar(self):
        errores = []
        if not self.date_fecha.date().isValid():
            errores.append("Fecha inválida.")
        if self.combo_equipo.currentData() is None:
            errores.append("Debe seleccionar un equipo.")
        if self.combo_cuenta.currentData() is None:
            errores.append("Debe seleccionar una cuenta.")
        if self.combo_categoria.currentData() is None:
            errores.append("Debe seleccionar una categoría.")
        if not self.txt_monto.text().strip():
            errores.append("Debe ingresar un monto.")

        # Validar monto numérico
        try:
            float(self.txt_monto.text().strip().replace(",", ""))
        except Exception:
            errores.append("Monto inválido. Debe ser numérico.")

        return errores

