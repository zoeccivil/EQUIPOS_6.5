"""
Delegates de edición inline para tablas de Gastos y Alquileres.

Uso: hacer doble-click en una celda para editar en sitio.
Antes de guardar se muestra un diálogo de confirmación.
"""

import logging
from PyQt6.QtWidgets import (
    QStyledItemDelegate, QDateEdit, QComboBox, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from app_theme_modern import ModernTheme

logger = logging.getLogger(__name__)

_C = ModernTheme.COLORS

_EDITOR_STYLE = f"""
    QLineEdit, QDateEdit {{
        background-color: {_C['bg_input']};
        border: 2px solid {_C['primary']};
        border-radius: 4px;
        padding: 4px 8px;
        color: {_C['text_main']};
        font-size: 13px;
    }}
    QComboBox {{
        background-color: {_C['bg_input']};
        border: 2px solid {_C['primary']};
        border-radius: 4px;
        padding: 4px 8px;
        color: {_C['text_main']};
        font-size: 13px;
    }}
    QComboBox::drop-down {{
        border: none;
        padding-right: 6px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {_C['text_muted']};
        margin-right: 6px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {_C['bg_card']};
        color: {_C['text_main']};
        selection-background-color: {_C['primary']};
        selection-color: {_C['primary_text']};
        border: 1px solid {_C['border']};
        border-radius: 4px;
        padding: 4px;
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 28px;
        padding: 4px 8px;
        color: {_C['text_main']};
        background-color: transparent;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background-color: {_C['bg_hover']};
        color: {_C['text_main']};
    }}
    QComboBox QAbstractItemView::item:selected {{
        background-color: {_C['primary']};
        color: {_C['primary_text']};
    }}
"""


# ──────────────────────────────────────────────────────────────────────────────
# Utilidad: diálogo de confirmación compacto
# ──────────────────────────────────────────────────────────────────────────────

def _confirmar(parent, antes: str, despues: str) -> bool:
    """Muestra diálogo de confirmación y devuelve True si el usuario acepta."""
    reply = QMessageBox.question(
        parent,
        "Confirmar cambio",
        f"¿Guardar este cambio?\n\n  Antes:    {antes}\n  Después:  {despues}",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    return reply == QMessageBox.StandardButton.Yes


# ──────────────────────────────────────────────────────────────────────────────
# Delegate de texto libre
# ──────────────────────────────────────────────────────────────────────────────

class TextDelegate(QStyledItemDelegate):
    """Edición inline de texto con confirmación."""

    def __init__(self, on_save, parent=None):
        """
        on_save: callable(row: int, col: int, new_value: str)
        """
        super().__init__(parent)
        self._on_save = on_save

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setStyleSheet(_EDITOR_STYLE)
        return editor

    def setEditorData(self, editor, index):
        editor.setText(index.data(Qt.ItemDataRole.DisplayRole) or "")

    def setModelData(self, editor, model, index):
        new_val = editor.text().strip()
        old_val = (model.data(index, Qt.ItemDataRole.DisplayRole) or "").strip()
        if new_val == old_val:
            return
        if not _confirmar(editor.parent(), old_val, new_val):
            return
        model.setData(index, new_val, Qt.ItemDataRole.DisplayRole)
        try:
            self._on_save(index.row(), index.column(), new_val)
        except Exception as e:
            logger.error(f"Error guardando inline texto: {e}", exc_info=True)
            QMessageBox.critical(editor.parent(), "Error", f"No se pudo guardar:\n{e}")


# ──────────────────────────────────────────────────────────────────────────────
# Delegate de fecha
# ──────────────────────────────────────────────────────────────────────────────

class DateDelegate(QStyledItemDelegate):
    """Edición inline de fecha (yyyy-MM-dd) con confirmación."""

    def __init__(self, on_save, parent=None):
        super().__init__(parent)
        self._on_save = on_save

    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent, calendarPopup=True)
        editor.setDisplayFormat("yyyy-MM-dd")
        editor.setStyleSheet(_EDITOR_STYLE)
        return editor

    def setEditorData(self, editor, index):
        date_str = index.data(Qt.ItemDataRole.DisplayRole) or ""
        qd = QDate.fromString(date_str, "yyyy-MM-dd")
        editor.setDate(qd if qd.isValid() else QDate.currentDate())

    def setModelData(self, editor, model, index):
        new_date = editor.date().toString("yyyy-MM-dd")
        old_date = (model.data(index, Qt.ItemDataRole.DisplayRole) or "").strip()
        if new_date == old_date:
            return
        if not _confirmar(editor.parent(), old_date, new_date):
            return
        model.setData(index, new_date, Qt.ItemDataRole.DisplayRole)
        try:
            self._on_save(index.row(), index.column(), new_date)
        except Exception as e:
            logger.error(f"Error guardando inline fecha: {e}", exc_info=True)
            QMessageBox.critical(editor.parent(), "Error", f"No se pudo guardar:\n{e}")


# ──────────────────────────────────────────────────────────────────────────────
# Delegate de combo (FK)
# ──────────────────────────────────────────────────────────────────────────────

class ComboDelegate(QStyledItemDelegate):
    """
    Edición inline de campos FK (equipo, cliente, etc.) con confirmación.

    on_save: callable(row: int, col: int, new_id: str)
    """

    def __init__(self, items_map: dict, on_save, parent=None):
        """
        items_map: {id: display_name}
        """
        super().__init__(parent)
        self._items_map = items_map
        self._on_save = on_save

    def update_map(self, new_map: dict):
        self._items_map = new_map

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.setStyleSheet(_EDITOR_STYLE)
        for item_id, name in sorted(self._items_map.items(), key=lambda x: x[1]):
            editor.addItem(name, item_id)
        return editor

    def setEditorData(self, editor, index):
        current_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        idx = editor.findText(current_text)
        if idx >= 0:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):
        new_name = editor.currentText()
        new_id = editor.currentData()
        old_name = (model.data(index, Qt.ItemDataRole.DisplayRole) or "").strip()
        if new_name == old_name:
            return
        if not _confirmar(editor.parent(), old_name, new_name):
            return
        model.setData(index, new_name, Qt.ItemDataRole.DisplayRole)
        try:
            self._on_save(index.row(), index.column(), new_id)
        except Exception as e:
            logger.error(f"Error guardando inline combo: {e}", exc_info=True)
            QMessageBox.critical(editor.parent(), "Error", f"No se pudo guardar:\n{e}")


# ──────────────────────────────────────────────────────────────────────────────
# Delegate numérico (monto, horas, precio…)
# ──────────────────────────────────────────────────────────────────────────────

class NumericDelegate(QStyledItemDelegate):
    """
    Edición inline de campos numéricos con confirmación.

    prefix: prefijo visual a ignorar al parsear (ej. "RD$ ")
    on_save: callable(row: int, col: int, new_value: float)
    """

    def __init__(self, on_save, prefix: str = "", parent=None):
        super().__init__(parent)
        self._prefix = prefix
        self._on_save = on_save

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setPlaceholderText("0.00")
        editor.setStyleSheet(_EDITOR_STYLE)
        return editor

    def setEditorData(self, editor, index):
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        val = text.replace(self._prefix, "").replace(",", "").strip()
        editor.setText(val)

    def setModelData(self, editor, model, index):
        raw = editor.text().strip().replace(",", "")
        try:
            new_val = float(raw)
        except ValueError:
            return  # Valor inválido: ignorar

        old_text = (model.data(index, Qt.ItemDataRole.DisplayRole) or "").strip()
        old_raw = old_text.replace(self._prefix, "").replace(",", "").strip()
        try:
            old_val = float(old_raw)
        except ValueError:
            old_val = None

        if new_val == old_val:
            return

        prefix_clean = self._prefix.strip()
        antes_str = old_text or f"{prefix_clean} {old_val:,.2f}" if old_val is not None else old_text
        despues_str = f"{prefix_clean} {new_val:,.2f}" if prefix_clean else f"{new_val:,.2f}"

        if not _confirmar(editor.parent(), antes_str, despues_str):
            return

        display = f"{prefix_clean} {new_val:,.2f}" if prefix_clean else f"{new_val:,.2f}"
        model.setData(index, display, Qt.ItemDataRole.DisplayRole)
        try:
            self._on_save(index.row(), index.column(), new_val)
        except Exception as e:
            logger.error(f"Error guardando inline numérico: {e}", exc_info=True)
            QMessageBox.critical(editor.parent(), "Error", f"No se pudo guardar:\n{e}")
