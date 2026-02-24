"""
Diálogo para gestión de equipos en Firebase
Permite crear, editar y eliminar equipos
"""
import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QLineEdit, QFormLayout, QCheckBox, QLabel, QStyle
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from firebase_manager import FirebaseManager

logger = logging.getLogger(__name__)

# Estilos CSS
DIALOG_STYLE = """
QDialog {
    background-color: #F3F4F6;
    font-family: 'Segoe UI';
}
QLabel {
    color: #374151;
    font-size: 11pt;
}
QLabel[class="title"] {
    font-size: 18pt;
    font-weight: bold;
    color: #1F2937;
}
QPushButton {
    background-color: #F59E0B;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 18px;
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
QPushButton[class="secondary"] {
    background-color: #E5E7EB;
    color: #374151;
}
QPushButton[class="secondary"]:hover {
    background-color: #D1D5DB;
}
QPushButton[class="secondary"]:pressed {
    background-color: #9CA3AF;
}
QPushButton[class="danger"] {
    background-color: #DC2626;
    color: white;
}
QPushButton[class="danger"]:hover {
    background-color: #B91C1C;
}
QPushButton[class="danger"]:pressed {
    background-color: #991B1B;
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
    padding: 8px;
    color: #1F2937;
}
QTableWidget::item:selected {
    background-color: #FEF3C7;
    color: #1F2937;
}
QHeaderView::section {
    background-color: #1F2937;
    color: #FFFFFF;
    padding: 10px;
    border: none;
    font-weight: 600;
    font-size: 10pt;
}
QLineEdit {
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 6px;
    padding: 8px 12px;
    color: #1F2937;
    font-size: 10pt;
    min-height: 25px;
}
QLineEdit:hover {
    border: 2px solid #F59E0B;
}
QLineEdit:focus {
    border: 2px solid #F59E0B;
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
"""


class GestionEquiposDialog(QDialog):
    """Diálogo para gestionar equipos."""
    
    def __init__(self, firebase_manager: FirebaseManager, parent=None):
        super().__init__(parent)
        
        self.fm = firebase_manager
        self.equipos = []
        
        self.setWindowTitle("Gestión de Equipos")
        self.setMinimumSize(900, 600)
        
        # Aplicar estilos
        self.setStyleSheet(DIALOG_STYLE)
        
        self._init_ui()
        self._cargar_equipos()
    
    def _init_ui(self):
        """Inicializa la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        titulo = QLabel("Gestión de Equipos")
        titulo.setProperty("class", "title")
        titulo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(titulo)
        
        # Botones de acción
        botones_layout = QHBoxLayout()
        botones_layout.setSpacing(10)
        
        self.btn_nuevo = QPushButton("➕ Nuevo Equipo")
        self.btn_nuevo.clicked.connect(self._nuevo)
        botones_layout.addWidget(self.btn_nuevo)
        
        self.btn_editar = QPushButton("✏️ Editar")
        self.btn_editar.clicked.connect(self._editar)
        botones_layout.addWidget(self.btn_editar)
        
        self.btn_eliminar = QPushButton("🗑️ Eliminar")
        self.btn_eliminar.setProperty("class", "danger")
        self.btn_eliminar.clicked.connect(self._eliminar)
        botones_layout.addWidget(self.btn_eliminar)
        
        self.btn_activar_desactivar = QPushButton("🔄 Activar/Desactivar")
        self.btn_activar_desactivar.setProperty("class", "secondary")
        self.btn_activar_desactivar.clicked.connect(self._toggle_activo)
        botones_layout.addWidget(self.btn_activar_desactivar)
        
        botones_layout.addStretch()
        layout.addLayout(botones_layout)
        
        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre", "Modelo", "Estado"])
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(36)
        self.tabla.itemDoubleClicked.connect(self._editar)
        layout.addWidget(self.tabla)
        
        # Botón cerrar
        btn_cerrar_layout = QHBoxLayout()
        btn_cerrar_layout.addStretch()
        
        btn_cerrar = QPushButton("✖️ Cerrar")
        btn_cerrar.setProperty("class", "secondary")
        btn_cerrar.clicked.connect(self.accept)
        btn_cerrar.setMinimumWidth(120)
        btn_cerrar_layout.addWidget(btn_cerrar)
        
        layout.addLayout(btn_cerrar_layout)
    
    def _cargar_equipos(self):
        """Carga los equipos desde Firebase."""
        try:
            self.equipos = self.fm.obtener_equipos(activo=None)
            self._actualizar_tabla()
        except Exception as e:
            logger.error(f"Error al cargar equipos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al cargar equipos:\n{e}")
    
    def _actualizar_tabla(self):
        """Actualiza la tabla con los equipos."""
        self.tabla.setRowCount(0)
        
        for equipo in self.equipos:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            
            # ID
            id_item = QTableWidgetItem(str(equipo.get('id', '')))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(row, 0, id_item)
            
            # Nombre
            self.tabla.setItem(row, 1, QTableWidgetItem(equipo.get('nombre', '')))
            
            # Modelo
            self.tabla.setItem(row, 2, QTableWidgetItem(equipo.get('modelo', '')))
            
            # Estado
            activo = "✅ Activo" if equipo.get('activo', True) else "❌ Inactivo"
            estado_item = QTableWidgetItem(activo)
            estado_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(row, 3, estado_item)
    
    def _obtener_seleccionado(self) -> Optional[Dict[str, Any]]:
        """Obtiene el equipo seleccionado."""
        current_row = self.tabla.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Sin Selección", "Debe seleccionar un equipo.")
            return None
        
        equipo_id = self.tabla.item(current_row, 0).text()
        for equipo in self.equipos:
            if str(equipo.get('id')) == equipo_id:
                return equipo
        return None
    
    def _nuevo(self):
        """Crea un nuevo equipo."""
        dialog = FormularioEquipoDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            datos = dialog.get_datos()
            datos['activo'] = True
            
            try:
                nuevo_id = self.fm.agregar_equipo(datos)
                if nuevo_id:
                    QMessageBox.information(self, "Éxito", "Equipo creado correctamente.")
                    self._cargar_equipos()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo crear el equipo.")
            except Exception as e:
                logger.error(f"Error al crear equipo: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al crear equipo:\n{e}")
    
    def _editar(self):
        """Edita el equipo seleccionado."""
        equipo = self._obtener_seleccionado()
        if not equipo:
            return
        
        dialog = FormularioEquipoDialog(equipo=equipo, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            datos = dialog.get_datos()
            
            try:
                if self.fm.editar_equipo(equipo['id'], datos):
                    QMessageBox.information(self, "Éxito", "Equipo actualizado correctamente.")
                    self._cargar_equipos()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo actualizar el equipo.")
            except Exception as e:
                logger.error(f"Error al editar equipo: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al editar equipo:\n{e}")
    
    def _eliminar(self):
        """Elimina el equipo seleccionado."""
        equipo = self._obtener_seleccionado()
        if not equipo:
            return
        
        respuesta = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar '{equipo.get('nombre')}'?\n\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                if self.fm.eliminar_equipo(equipo['id']):
                    QMessageBox.information(self, "Éxito", "Equipo eliminado correctamente.")
                    self._cargar_equipos()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo eliminar el equipo.")
            except Exception as e:
                logger.error(f"Error al eliminar equipo: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Error al eliminar equipo:\n{e}")
    
    def _toggle_activo(self):
        """Activa o desactiva el equipo seleccionado."""
        equipo = self._obtener_seleccionado()
        if not equipo:
            return
        
        nuevo_estado = not equipo.get('activo', True)
        estado_texto = "activar" if nuevo_estado else "desactivar"
        
        try:
            if self.fm.editar_equipo(equipo['id'], {'activo': nuevo_estado}):
                QMessageBox.information(self, "Éxito", 
                                      f"Equipo {estado_texto}do correctamente.")
                self._cargar_equipos()
            else:
                QMessageBox.critical(self, "Error", 
                                   f"No se pudo {estado_texto} el equipo.")
        except Exception as e:
            logger.error(f"Error al cambiar estado del equipo: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error:\n{e}")


class FormularioEquipoDialog(QDialog):
    """Formulario para crear/editar un equipo."""
    
    def __init__(self, equipo: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        
        self.equipo = equipo
        
        titulo = "Editar Equipo" if equipo else "Nuevo Equipo"
        self.setWindowTitle(titulo)
        self.setMinimumWidth(450)
        
        # Aplicar estilos
        self.setStyleSheet(DIALOG_STYLE)
        
        self._init_ui()
        if equipo:
            self._cargar_datos()
    
    def _init_ui(self):
        """Inicializa la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # Título
        titulo_texto = "Editar Equipo" if self.equipo else "Nuevo Equipo"
        titulo = QLabel(titulo_texto)
        titulo.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1F2937;")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)
        
        # Formulario
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        lbl_nombre = QLabel("Nombre:")
        lbl_nombre.setStyleSheet("font-weight: 600; color: #374151;")
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre del equipo...")
        form_layout.addRow(lbl_nombre, self.txt_nombre)
        
        lbl_modelo = QLabel("Modelo:")
        lbl_modelo.setStyleSheet("font-weight: 600; color: #374151;")
        self.txt_modelo = QLineEdit()
        self.txt_modelo.setPlaceholderText("Modelo del equipo...")
        form_layout.addRow(lbl_modelo, self.txt_modelo)
        
        layout.addLayout(form_layout)
        
        layout.addSpacing(10)
        
        # Botones
        botones_layout = QHBoxLayout()
        botones_layout.setSpacing(10)
        
        btn_guardar = QPushButton("💾 Guardar")
        btn_guardar.clicked.connect(self.accept)
        btn_guardar.setMinimumWidth(120)
        botones_layout.addWidget(btn_guardar)
        
        btn_cancelar = QPushButton("✖️ Cancelar")
        btn_cancelar.setProperty("class", "secondary")
        btn_cancelar.clicked.connect(self.reject)
        btn_cancelar.setMinimumWidth(120)
        botones_layout.addWidget(btn_cancelar)
        
        layout.addLayout(botones_layout)
    
    def _cargar_datos(self):
        """Carga los datos del equipo."""
        if self.equipo:
            self.txt_nombre.setText(self.equipo.get('nombre', ''))
            self.txt_modelo.setText(self.equipo.get('modelo', ''))
    
    def get_datos(self) -> Dict[str, Any]:
        """Obtiene los datos del formulario."""
        return {
            'nombre': self.txt_nombre.text().strip(),
            'modelo': self.txt_modelo.text().strip()
        }