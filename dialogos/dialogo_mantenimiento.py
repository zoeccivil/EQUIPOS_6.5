from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QDateEdit, QMessageBox
)
from PyQt6.QtCore import QDate


class DialogoMantenimiento(QDialog):
    """
    Diálogo para registrar o editar un mantenimiento de equipo.
    Adaptado para usar FirebaseManager como `db`.
    """
    def __init__(self, db, proyecto_actual, equipo_id, datos=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.proyecto_actual = proyecto_actual  # puede ser dict o id, según tu app
        self.equipo_id = equipo_id
        self.datos = datos if datos else {}

        self.setWindowTitle("Editar Mantenimiento" if self.datos else "Nuevo Mantenimiento")
        layout = QVBoxLayout(self)

        self.fecha_edit = QDateEdit()
        self.fecha_edit.setCalendarPopup(True)
        if "fecha_servicio" in self.datos:
            try:
                partes = [int(x) for x in str(self.datos["fecha_servicio"]).split("-")]
                self.fecha_edit.setDate(QDate(partes[0], partes[1], partes[2]))
            except Exception:
                self.fecha_edit.setDate(QDate.currentDate())
        else:
            self.fecha_edit.setDate(QDate.currentDate())

        self.edit_costo = QLineEdit(str(self.datos.get("costo", "")))
        self.edit_descripcion = QTextEdit(self.datos.get("descripcion", ""))
        self.edit_horas = QLineEdit(str(self.datos.get("horas_totales_equipo", "")))
        self.edit_km = QLineEdit(str(self.datos.get("km_totales_equipo", "")))

        layout.addWidget(QLabel("Fecha Servicio:"))
        layout.addWidget(self.fecha_edit)
        layout.addWidget(QLabel("Costo:"))
        layout.addWidget(self.edit_costo)
        layout.addWidget(QLabel("Descripción:"))
        layout.addWidget(self.edit_descripcion)
        layout.addWidget(QLabel("Horas Totales Equipo:"))
        layout.addWidget(self.edit_horas)
        layout.addWidget(QLabel("KM Totales Equipo:"))
        layout.addWidget(self.edit_km)

        btns = QHBoxLayout()
        btn_guardar = QPushButton("Guardar")
        btn_cancelar = QPushButton("Cancelar")
        btns.addWidget(btn_guardar)
        btns.addWidget(btn_cancelar)
        layout.addLayout(btns)

        btn_guardar.clicked.connect(self.guardar)
        btn_cancelar.clicked.connect(self.reject)

    def guardar(self):
        try:
            if self.equipo_id is None:
                raise ValueError("No se seleccionó un equipo para el mantenimiento.")

            def get_float(txt):
                try:
                    return float(txt.strip().replace(",", ".")) if txt.strip() else 0.0
                except Exception:
                    return 0.0

            datos = {
                "id": self.datos.get("id"),
                "equipo_id": self.equipo_id,
                "fecha": self.fecha_edit.date().toString("yyyy-MM-dd"),
                "descripcion": self.edit_descripcion.toPlainText().strip(),
                "tipo": None,
                "valor": get_float(self.edit_costo.text()),
                "odometro_horas": get_float(self.edit_horas.text()),
                "odometro_km": get_float(self.edit_km.text()),
                "lectura_es_horas": True,
            }
            # si proyecto_actual es un dict con 'id':
            if isinstance(self.proyecto_actual, dict) and "id" in self.proyecto_actual:
                datos["proyecto_id"] = self.proyecto_actual["id"]

            if datos["id"]:
                self.db.actualizar_mantenimiento(datos)
                QMessageBox.information(self, "Éxito", "Mantenimiento actualizado correctamente.")
            else:
                self.db.registrar_mantenimiento(datos)
                QMessageBox.information(self, "Éxito", "Mantenimiento registrado correctamente.")

            self.accept()
        except Exception as ex:
            QMessageBox.warning(self, "Error", f"Error al guardar: {ex}")