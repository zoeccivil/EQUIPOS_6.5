# dialogos/categorias_dialog.py
"""
Gestor de Categorías y Subcategorías — v2
==========================================
Tab 1 · Gestión
  - Multi-selección (Ctrl/Shift/Selec. Todo / Ninguno)
  - Eliminación con reasignación: elige a qué categoría mover los gastos
  - Mover subcategorías entre categorías

Tab 2 · Auditoría
  - Detecta gastos con referencias rotas (cat/subcat inexistente)
  - Detecta subcategorías huérfanas (su categoría fue eliminada)
  - Repara en bloque: reasigna o limpia las referencias rotas
"""

import logging
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QGroupBox,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
    QLineEdit, QMessageBox, QInputDialog, QComboBox,
    QFrame, QSplitter, QAbstractItemView, QApplication,
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialogButtonBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPalette, QColor

logger = logging.getLogger(__name__)


# ── Helpers de estilo ─────────────────────────────────────────────────────────

def _es_oscuro() -> bool:
    base = QApplication.instance().palette().color(QPalette.ColorRole.Base)
    return (0.299 * base.red() + 0.587 * base.green() + 0.114 * base.blue()) < 128


def _list_css(accent: str) -> str:
    if _es_oscuro():
        bg, txt, hover, sep = "#1E1E1E", "#FFFFFF", "#2C2C2C", "#2C2C2C"
    else:
        bg, txt, hover, sep = "#FFFFFF", "#1F2937", "#F3F4F6", "#E5E7EB"
    return f"""
        QListWidget {{
            background:{bg}; color:{txt};
            border:1px solid {sep}; border-radius:6px; outline:none;
        }}
        QListWidget::item {{
            padding:7px 12px; border-bottom:1px solid {sep};
            color:{txt}; background:{bg};
        }}
        QListWidget::item:hover    {{ background:{hover}; }}
        QListWidget::item:selected {{ background:{accent}; color:#fff;
                                      border-bottom:1px solid {accent}; }}
    """


def _table_css() -> str:
    if _es_oscuro():
        bg, txt, hdr, sel, grid = "#1E1E1E","#FFFFFF","#2C2C2C","#0F62FE","#333333"
    else:
        bg, txt, hdr, sel, grid = "#FFFFFF","#1F2937","#374151","#3B82F6","#E5E7EB"
    return f"""
        QTableWidget {{
            background:{bg}; color:{txt}; gridline-color:{grid};
            border:1px solid {grid}; border-radius:6px;
        }}
        QTableWidget::item {{ padding:6px; color:{txt}; background:{bg}; }}
        QTableWidget::item:selected {{ background:{sel}; color:#fff; }}
        QHeaderView::section {{
            background:{hdr}; color:#fff; padding:8px;
            border:none; font-weight:600;
        }}
    """


def _btn(text: str, color: str, slot, icon: str = "") -> QPushButton:
    b = QPushButton(f"{icon} {text}".strip())
    b.setStyleSheet(
        f"QPushButton{{background:{color};color:#fff;border:none;"
        f"border-radius:5px;padding:6px 14px;font-weight:600;}}"
        f"QPushButton:hover{{filter:brightness(1.1);}}"
        f"QPushButton:disabled{{background:#6B7280;}}"
    )
    b.clicked.connect(slot)
    return b


# ── Diálogo de reasignación ───────────────────────────────────────────────────

class ReasignarDialog(QDialog):
    """
    Pregunta a qué categoría/subcategoría reasignar los gastos
    de los elementos que van a ser eliminados.
    """
    def __init__(self, titulo: str, opciones: list[dict],
                 n_gastos: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(440)
        ly = QVBoxLayout(self)
        ly.setSpacing(12)

        if n_gastos > 0:
            lbl = QLabel(
                f"<b>{n_gastos}</b> gasto(s) usan esta(s) categoría(s).<br>"
                "Elige a dónde reasignarlos antes de eliminar:"
            )
        else:
            lbl = QLabel("No hay gastos afectados. Confirma la eliminación.")
        lbl.setWordWrap(True)
        ly.addWidget(lbl)

        self.combo = QComboBox()
        self.combo.addItem("— Dejar sin categoría (no recomendado) —", None)
        for op in opciones:
            self.combo.addItem(op["nombre"], op["id"])
        ly.addWidget(self.combo)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        ly.addWidget(btns)

    def seleccion(self):
        return self.combo.currentData()


# ── Diálogo principal ─────────────────────────────────────────────────────────

class CategoriasDialog(QDialog):
    cambios_realizados = pyqtSignal()

    def __init__(self, fm, parent=None):
        super().__init__(parent)
        self.fm = fm
        self.setWindowTitle("Gestionar Categorías y Subcategorías")
        self.setMinimumSize(960, 620)
        self.resize(1060, 680)

        self._categorias: list[dict] = []
        self._subcats:    list[dict] = []
        self._hay_cambios = False

        self._build_ui()
        self._cargar_todo()

    # ── Construcción de la UI ─────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 10)
        root.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_gestion(),   "  Gestión  ")
        self.tabs.addTab(self._tab_auditoria(), "  Auditoría y Reparación  ")
        root.addWidget(self.tabs, 1)

        # Pie
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)
        foot = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color:#9CA3AF;font-size:9pt;")
        foot.addWidget(self.lbl_status)
        foot.addStretch()
        btn_c = QPushButton("Cerrar"); btn_c.setFixedWidth(90)
        btn_c.clicked.connect(self.accept)
        foot.addWidget(btn_c)
        root.addLayout(foot)

    # ── Tab Gestión ───────────────────────────────────────────────────────────

    def _tab_gestion(self) -> QWidget:
        w = QWidget()
        ly = QHBoxLayout(w)
        ly.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._panel_categorias())
        splitter.addWidget(self._panel_subcategorias())
        splitter.setSizes([420, 520])
        ly.addWidget(splitter)
        return w

    def _panel_categorias(self) -> QGroupBox:
        grp = QGroupBox("Categorías")
        grp.setStyleSheet(
            "QGroupBox{border:2px solid #3B82F6;border-radius:8px;"
            "margin-top:12px;padding:8px;font-weight:bold;font-size:11pt;}"
            "QGroupBox::title{subcontrol-origin:margin;left:12px;"
            "padding:0 6px;color:#3B82F6;background:transparent;}"
        )
        lv = QVBoxLayout(grp); lv.setSpacing(6)

        # Toolbar selección
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Seleccionar:"))
        b_all  = QPushButton("Todo");  b_all.setFixedHeight(24)
        b_none = QPushButton("Ninguno"); b_none.setFixedHeight(24)
        b_all.clicked.connect(lambda: self.list_cats.selectAll())
        b_none.clicked.connect(lambda: self.list_cats.clearSelection())
        for b in (b_all, b_none):
            b.setStyleSheet("QPushButton{padding:2px 8px;border-radius:3px;}")
        sel_row.addWidget(b_all); sel_row.addWidget(b_none)
        sel_row.addStretch()
        self.lbl_cats_sel = QLabel("0 sel.")
        self.lbl_cats_sel.setStyleSheet("color:#9CA3AF;font-size:9pt;")
        sel_row.addWidget(self.lbl_cats_sel)
        lv.addLayout(sel_row)

        self.list_cats = QListWidget()
        self.list_cats.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_cats.setAlternatingRowColors(False)
        self.list_cats.setStyleSheet(_list_css("#3B82F6"))
        self.list_cats.currentItemChanged.connect(self._on_cat_click)
        self.list_cats.itemSelectionChanged.connect(self._on_cats_sel_changed)
        lv.addWidget(self.list_cats)

        self.search_cat = QLineEdit()
        self.search_cat.setPlaceholderText("Buscar categoría...")
        self.search_cat.textChanged.connect(lambda t: self._poblar_cats(t))
        lv.addWidget(self.search_cat)

        btn_row = QHBoxLayout()
        btn_row.addWidget(_btn("+ Agregar",  "#16A34A", self._agregar_cat))
        btn_row.addWidget(_btn("Renombrar",  "#F59E0B", self._renombrar_cat))
        btn_row.addWidget(_btn("Eliminar",   "#DC2626", self._eliminar_cats))
        lv.addLayout(btn_row)
        return grp

    def _panel_subcategorias(self) -> QGroupBox:
        grp = QGroupBox("Subcategorías")
        grp.setStyleSheet(
            "QGroupBox{border:2px solid #F59E0B;border-radius:8px;"
            "margin-top:12px;padding:8px;font-weight:bold;font-size:11pt;}"
            "QGroupBox::title{subcontrol-origin:margin;left:12px;"
            "padding:0 6px;color:#F59E0B;background:transparent;}"
        )
        rv = QVBoxLayout(grp); rv.setSpacing(6)

        self.lbl_cat_sel = QLabel("← Selecciona una categoría")
        self.lbl_cat_sel.setStyleSheet("color:#9CA3AF;font-style:italic;")
        rv.addWidget(self.lbl_cat_sel)

        # Toolbar selección
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Seleccionar:"))
        b_all  = QPushButton("Todo");   b_all.setFixedHeight(24)
        b_none = QPushButton("Ninguno"); b_none.setFixedHeight(24)
        b_all.clicked.connect(lambda: self.list_subs.selectAll())
        b_none.clicked.connect(lambda: self.list_subs.clearSelection())
        for b in (b_all, b_none):
            b.setStyleSheet("QPushButton{padding:2px 8px;border-radius:3px;}")
        sel_row.addWidget(b_all); sel_row.addWidget(b_none)
        sel_row.addStretch()
        self.lbl_subs_sel = QLabel("0 sel.")
        self.lbl_subs_sel.setStyleSheet("color:#9CA3AF;font-size:9pt;")
        sel_row.addWidget(self.lbl_subs_sel)
        rv.addLayout(sel_row)

        self.list_subs = QListWidget()
        self.list_subs.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_subs.setAlternatingRowColors(False)
        self.list_subs.setStyleSheet(_list_css("#F59E0B"))
        self.list_subs.itemSelectionChanged.connect(self._on_subs_sel_changed)
        rv.addWidget(self.list_subs)

        self.search_sub = QLineEdit()
        self.search_sub.setPlaceholderText("Buscar subcategoría...")
        self.search_sub.textChanged.connect(self._on_search_sub)
        rv.addWidget(self.search_sub)

        move_row = QHBoxLayout()
        move_row.addWidget(QLabel("Mover a:"))
        self.combo_mover = QComboBox(); self.combo_mover.setMinimumWidth(160)
        move_row.addWidget(self.combo_mover)
        move_row.addWidget(_btn("Mover", "#6366F1", self._mover_subs))
        move_row.addStretch()
        rv.addLayout(move_row)

        btn_row = QHBoxLayout()
        btn_row.addWidget(_btn("+ Agregar", "#16A34A", self._agregar_sub))
        btn_row.addWidget(_btn("Renombrar", "#F59E0B", self._renombrar_sub))
        btn_row.addWidget(_btn("Eliminar",  "#DC2626", self._eliminar_subs))
        rv.addLayout(btn_row)

        self._set_subs_enabled(False)
        return grp

    # ── Tab Auditoría ─────────────────────────────────────────────────────────

    def _tab_auditoria(self) -> QWidget:
        w = QWidget()
        ly = QVBoxLayout(w); ly.setSpacing(10)

        # Cabecera
        hdr = QHBoxLayout()
        lbl = QLabel("Detecta y repara referencias rotas entre gastos y categorías/subcategorías.")
        lbl.setWordWrap(True)
        hdr.addWidget(lbl, 1)
        self.btn_auditar = _btn("Ejecutar Auditoría", "#0F62FE", self._ejecutar_auditoria, "")
        hdr.addWidget(self.btn_auditar)
        ly.addLayout(hdr)

        # Resultados gastos
        grp_gastos = QGroupBox("Gastos con referencias rotas")
        grp_gastos.setStyleSheet(
            "QGroupBox{border:2px solid #DC2626;border-radius:6px;"
            "margin-top:10px;padding:8px;font-weight:bold;}"
            "QGroupBox::title{subcontrol-origin:margin;left:10px;"
            "padding:0 4px;color:#DC2626;background:transparent;}"
        )
        gv = QVBoxLayout(grp_gastos)

        self.tabla_audit = QTableWidget(0, 5)
        self.tabla_audit.setHorizontalHeaderLabels(
            ["ID Gasto", "Fecha", "Descripción", "Problema", "Monto"])
        self.tabla_audit.setStyleSheet(_table_css())
        self.tabla_audit.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_audit.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_audit.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.tabla_audit.verticalHeader().setVisible(False)
        gv.addWidget(self.tabla_audit)

        fix_row = QHBoxLayout()
        fix_row.addWidget(QLabel("Reasignar categoría rota a:"))
        self.combo_fix_cat = QComboBox(); self.combo_fix_cat.setMinimumWidth(180)
        fix_row.addWidget(self.combo_fix_cat)
        fix_row.addWidget(_btn("Aplicar a seleccionados", "#16A34A",
                               self._reparar_seleccionados))
        fix_row.addWidget(_btn("Limpiar referencias rotas", "#DC2626",
                               self._limpiar_seleccionados))
        fix_row.addStretch()
        gv.addLayout(fix_row)
        ly.addWidget(grp_gastos, 1)

        # Resultados subcategorías huérfanas
        grp_huerfanas = QGroupBox("Subcategorías huérfanas (su categoría fue eliminada)")
        grp_huerfanas.setStyleSheet(
            "QGroupBox{border:2px solid #F59E0B;border-radius:6px;"
            "margin-top:6px;padding:8px;font-weight:bold;}"
            "QGroupBox::title{subcontrol-origin:margin;left:10px;"
            "padding:0 4px;color:#F59E0B;background:transparent;}"
        )
        hv = QVBoxLayout(grp_huerfanas)
        self.lista_huerfanas = QListWidget()
        self.lista_huerfanas.setMaximumHeight(130)
        self.lista_huerfanas.setStyleSheet(_list_css("#F59E0B"))
        hv.addWidget(self.lista_huerfanas)

        horf_row = QHBoxLayout()
        horf_row.addWidget(QLabel("Reasignar a:"))
        self.combo_fix_horf = QComboBox(); self.combo_fix_horf.setMinimumWidth(180)
        horf_row.addWidget(self.combo_fix_horf)
        horf_row.addWidget(_btn("Reasignar seleccionadas", "#16A34A",
                                self._reasignar_huerfanas))
        horf_row.addWidget(_btn("Eliminar seleccionadas", "#DC2626",
                                self._eliminar_huerfanas))
        horf_row.addStretch()
        hv.addLayout(horf_row)
        ly.addWidget(grp_huerfanas)

        self.lbl_audit_status = QLabel("Presiona 'Ejecutar Auditoría' para comenzar.")
        self.lbl_audit_status.setStyleSheet("color:#9CA3AF;font-size:9pt;")
        ly.addWidget(self.lbl_audit_status)
        return w

    # ── Carga de datos ────────────────────────────────────────────────────────

    def _cargar_todo(self):
        try:
            self._categorias = self.fm.obtener_categorias()
            self._subcats    = self.fm.obtener_subcategorias()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los datos:\n{e}")
            return
        self._poblar_cats()
        self._poblar_combo_mover()
        self._poblar_combos_audit()
        self._status(
            f"{len(self._categorias)} categorías  ·  {len(self._subcats)} subcategorías"
        )

    def _poblar_cats(self, filtro: str = ""):
        self.list_cats.blockSignals(True)
        self.list_cats.clear()
        t = filtro.lower()
        for cat in self._categorias:
            if t and t not in cat["nombre"].lower():
                continue
            item = QListWidgetItem(cat["nombre"])
            item.setData(Qt.ItemDataRole.UserRole, cat["id"])
            self.list_cats.addItem(item)
        self.list_cats.blockSignals(False)

    def _poblar_subs(self, cat_id: str, filtro: str = ""):
        self.list_subs.clear()
        t = filtro.lower()
        for sub in self._subcats:
            if sub["categoria_id"] != str(cat_id):
                continue
            if t and t not in sub["nombre"].lower():
                continue
            item = QListWidgetItem(sub["nombre"])
            item.setData(Qt.ItemDataRole.UserRole, sub["id"])
            self.list_subs.addItem(item)

    def _poblar_combo_mover(self):
        self.combo_mover.clear()
        for cat in self._categorias:
            self.combo_mover.addItem(cat["nombre"], cat["id"])

    def _poblar_combos_audit(self):
        for combo in (self.combo_fix_cat, self.combo_fix_horf):
            combo.clear()
            for cat in self._categorias:
                combo.addItem(cat["nombre"], cat["id"])

    # ── Señales de selección ──────────────────────────────────────────────────

    def _on_cat_click(self, current, _prev):
        if not current:
            self._set_subs_enabled(False)
            self.lbl_cat_sel.setText("← Selecciona una categoría")
            return
        cat_id = current.data(Qt.ItemDataRole.UserRole)
        self.lbl_cat_sel.setText(
            f"Subcategorías de: <b>{current.text()}</b>")
        self.lbl_cat_sel.setTextFormat(Qt.TextFormat.RichText)
        self._poblar_subs(cat_id)
        self._set_subs_enabled(True)
        for i in range(self.combo_mover.count()):
            if self.combo_mover.itemData(i) == cat_id:
                self.combo_mover.setCurrentIndex(i)
                break

    def _on_cats_sel_changed(self):
        n = len(self.list_cats.selectedItems())
        self.lbl_cats_sel.setText(f"{n} sel.")

    def _on_subs_sel_changed(self):
        n = len(self.list_subs.selectedItems())
        self.lbl_subs_sel.setText(f"{n} sel.")

    def _on_search_sub(self, texto):
        cat_id = self._cat_id_actual()
        if cat_id:
            self._poblar_subs(cat_id, texto)

    def _set_subs_enabled(self, ok: bool):
        for w in (self.list_subs, self.search_sub, self.combo_mover):
            w.setEnabled(ok)

    def _cat_id_actual(self) -> str | None:
        item = self.list_cats.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _ids_cats_seleccionadas(self) -> list[str]:
        return [i.data(Qt.ItemDataRole.UserRole)
                for i in self.list_cats.selectedItems()]

    def _ids_subs_seleccionadas(self) -> list[str]:
        return [i.data(Qt.ItemDataRole.UserRole)
                for i in self.list_subs.selectedItems()]

    # ── CRUD Categorías ───────────────────────────────────────────────────────

    def _agregar_cat(self):
        nombre, ok = QInputDialog.getText(
            self, "Nueva Categoría", "Nombre:", QLineEdit.EchoMode.Normal)
        if not ok or not nombre.strip():
            return
        nombre = nombre.strip().upper()
        if any(c["nombre"].upper() == nombre for c in self._categorias):
            QMessageBox.warning(self, "Duplicado", f'"{nombre}" ya existe.')
            return
        try:
            nid = self.fm.crear_categoria(nombre)
            self._categorias.append({"id": nid, "nombre": nombre})
            self._categorias.sort(key=lambda x: x["nombre"].upper())
            self._poblar_cats(); self._poblar_combo_mover(); self._poblar_combos_audit()
            self._cambio(f'Categoría "{nombre}" creada.')
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _renombrar_cat(self):
        ids = self._ids_cats_seleccionadas()
        if len(ids) != 1:
            QMessageBox.information(self, "Selección", "Selecciona exactamente una categoría para renombrar.")
            return
        cat = next((c for c in self._categorias if c["id"] == ids[0]), None)
        nuevo, ok = QInputDialog.getText(
            self, "Renombrar", "Nuevo nombre:",
            QLineEdit.EchoMode.Normal, cat["nombre"])
        if not ok or not nuevo.strip():
            return
        nuevo = nuevo.strip().upper()
        try:
            self.fm.actualizar_categoria(cat["id"], nuevo)
            cat["nombre"] = nuevo
            self._categorias.sort(key=lambda x: x["nombre"].upper())
            self._poblar_cats(); self._poblar_combo_mover(); self._poblar_combos_audit()
            self._cambio(f'Categoría renombrada a "{nuevo}".')
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _eliminar_cats(self):
        ids = self._ids_cats_seleccionadas()
        if not ids:
            QMessageBox.information(self, "Selección", "Selecciona al menos una categoría.")
            return

        nombres = [c["nombre"] for c in self._categorias if c["id"] in ids]

        # Contar gastos afectados
        n_gastos = sum(self.fm.contar_gastos_por_categoria(cid) for cid in ids)

        # Opciones de reemplazo (todas menos las que se van a eliminar)
        opciones = [c for c in self._categorias if c["id"] not in ids]

        dlg = ReasignarDialog(
            f"Eliminar {len(ids)} categoría(s)",
            opciones, n_gastos, parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        nueva_cat_id = dlg.seleccion()

        try:
            total_reasig = 0
            for cid in ids:
                total_reasig += self.fm.reasignar_categoria_en_gastos(cid, nueva_cat_id)
                # Eliminar subcategorías huérfanas
                for sub in [s for s in self._subcats if s["categoria_id"] == cid]:
                    self.fm.eliminar_subcategoria(sub["id"])
                self.fm.eliminar_categoria(cid)

            self._categorias = [c for c in self._categorias if c["id"] not in ids]
            self._subcats    = [s for s in self._subcats if s["categoria_id"] not in ids]
            self.list_subs.clear()
            self._poblar_cats(); self._poblar_combo_mover(); self._poblar_combos_audit()
            self._set_subs_enabled(False)
            self.lbl_cat_sel.setText("← Selecciona una categoría")
            msg = f'{len(ids)} categoría(s) eliminadas.'
            if total_reasig:
                dest = next((c["nombre"] for c in self._categorias if c["id"] == nueva_cat_id), "sin categoría")
                msg += f' {total_reasig} gasto(s) reasignados a "{dest}".'
            self._cambio(msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ── CRUD Subcategorías ────────────────────────────────────────────────────

    def _agregar_sub(self):
        cat_id = self._cat_id_actual()
        if not cat_id:
            return
        cat_nom = self.list_cats.currentItem().text()
        nombre, ok = QInputDialog.getText(
            self, "Nueva Subcategoría",
            f"Nombre  [en: {cat_nom}]:", QLineEdit.EchoMode.Normal)
        if not ok or not nombre.strip():
            return
        nombre = nombre.strip().upper()
        if any(s["nombre"].upper() == nombre and s["categoria_id"] == cat_id
               for s in self._subcats):
            QMessageBox.warning(self, "Duplicado", f'"{nombre}" ya existe aquí.')
            return
        try:
            nid = self.fm.crear_subcategoria(nombre, cat_id)
            self._subcats.append({"id": nid, "nombre": nombre, "categoria_id": cat_id})
            self._poblar_subs(cat_id)
            self._cambio(f'Subcategoría "{nombre}" creada.')
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _renombrar_sub(self):
        ids = self._ids_subs_seleccionadas()
        if len(ids) != 1:
            QMessageBox.information(self, "Selección", "Selecciona exactamente una subcategoría.")
            return
        sub = next((s for s in self._subcats if s["id"] == ids[0]), None)
        nuevo, ok = QInputDialog.getText(
            self, "Renombrar", "Nuevo nombre:",
            QLineEdit.EchoMode.Normal, sub["nombre"])
        if not ok or not nuevo.strip():
            return
        nuevo = nuevo.strip().upper()
        try:
            self.fm.actualizar_subcategoria(sub["id"], nuevo, sub["categoria_id"])
            sub["nombre"] = nuevo
            self._poblar_subs(sub["categoria_id"])
            self._cambio(f'Subcategoría renombrada a "{nuevo}".')
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _eliminar_subs(self):
        ids = self._ids_subs_seleccionadas()
        if not ids:
            QMessageBox.information(self, "Selección", "Selecciona al menos una subcategoría.")
            return

        n_gastos = sum(self.fm.contar_gastos_por_subcategoria(sid) for sid in ids)

        # Opciones: otras subcategorías de la misma categoría
        cat_id  = self._cat_id_actual()
        opciones = [{"id": s["id"], "nombre": s["nombre"]}
                    for s in self._subcats
                    if s["categoria_id"] == cat_id and s["id"] not in ids]

        if n_gastos > 0 and not opciones:
            resp = QMessageBox.question(
                self, "Sin alternativas",
                f"{n_gastos} gasto(s) quedarán sin subcategoría.\n¿Continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if resp != QMessageBox.StandardButton.Yes:
                return
            nueva_sub_id = None
        elif n_gastos > 0:
            dlg = ReasignarDialog(
                f"Eliminar {len(ids)} subcategoría(s)",
                opciones, n_gastos, parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            nueva_sub_id = dlg.seleccion()
        else:
            nueva_sub_id = None

        try:
            total_reasig = 0
            for sid in ids:
                total_reasig += self.fm.reasignar_subcategoria_en_gastos(sid, nueva_sub_id)
                self.fm.eliminar_subcategoria(sid)
            self._subcats = [s for s in self._subcats if s["id"] not in ids]
            self._poblar_subs(cat_id)
            msg = f'{len(ids)} subcategoría(s) eliminadas.'
            if total_reasig:
                dest = next((s["nombre"] for s in self._subcats if s["id"] == nueva_sub_id), "sin subcat.")
                msg += f' {total_reasig} gasto(s) reasignados a "{dest}".'
            self._cambio(msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _mover_subs(self):
        ids = self._ids_subs_seleccionadas()
        if not ids:
            QMessageBox.information(self, "Selección", "Selecciona subcategorías a mover.")
            return
        nueva_cat_id  = self.combo_mover.currentData()
        nueva_cat_nom = self.combo_mover.currentText()
        cat_id_orig   = self._cat_id_actual()
        if nueva_cat_id == cat_id_orig:
            return
        try:
            for sid in ids:
                sub = next((s for s in self._subcats if s["id"] == sid), None)
                if sub:
                    self.fm.actualizar_subcategoria(sid, sub["nombre"], nueva_cat_id)
                    sub["categoria_id"] = nueva_cat_id
            self._poblar_subs(cat_id_orig)
            self._cambio(f'{len(ids)} subcategoría(s) movidas a "{nueva_cat_nom}".')
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ── Auditoría ─────────────────────────────────────────────────────────────

    def _ejecutar_auditoria(self):
        self.lbl_audit_status.setText("Analizando... espera un momento.")
        QApplication.processEvents()
        try:
            cat_ids = {c["id"] for c in self._categorias}
            sub_ids = {s["id"] for s in self._subcats}

            problemas = self.fm.auditar_gastos_categorias(cat_ids, sub_ids)
            huerfanas  = self.fm.auditar_subcategorias_huerfanas(cat_ids)

            # Poblar tabla de gastos
            self.tabla_audit.setRowCount(0)
            for p in problemas:
                row = self.tabla_audit.rowCount()
                self.tabla_audit.insertRow(row)
                issues_str = "; ".join(f"{t}: ID={cid}" for t, cid in p["issues"])
                vals = [p["id"][:20], p["fecha"], p["descripcion"][:40],
                        issues_str, f"RD$ {p['monto']:,.2f}"]
                for col, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setData(Qt.ItemDataRole.UserRole, p)
                    self.tabla_audit.setItem(row, col, item)

            # Poblar lista huérfanas
            self.lista_huerfanas.clear()
            for h in huerfanas:
                it = QListWidgetItem(
                    f'{h["nombre"]}  (cat_id rota: {h["categoria_id_rota"]})')
                it.setData(Qt.ItemDataRole.UserRole, h["id"])
                self.lista_huerfanas.addItem(it)

            self.lbl_audit_status.setText(
                f"Resultado: {len(problemas)} gasto(s) con referencias rotas  ·  "
                f"{len(huerfanas)} subcategoría(s) huérfana(s)."
            )
        except Exception as e:
            logger.error(f"_ejecutar_auditoria: {e}", exc_info=True)
            self.lbl_audit_status.setText(f"Error: {e}")

    def _reparar_seleccionados(self):
        filas = list({i.row() for i in self.tabla_audit.selectedItems()})
        if not filas:
            QMessageBox.information(self, "Sin selección", "Selecciona filas en la tabla primero.")
            return
        nueva_cat_id = self.combo_fix_cat.currentData()
        if not nueva_cat_id:
            QMessageBox.warning(self, "Categoría", "Elige una categoría destino.")
            return
        try:
            for row in filas:
                gasto = self.tabla_audit.item(row, 0).data(Qt.ItemDataRole.UserRole)
                self.fm.db.collection("gastos").document(gasto["id"]).update(
                    {"categoria_id": nueva_cat_id, "subcategoria_id": None}
                )
            self._cambio(f"{len(filas)} gasto(s) reparados.")
            self._ejecutar_auditoria()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _limpiar_seleccionados(self):
        filas = list({i.row() for i in self.tabla_audit.selectedItems()})
        if not filas:
            QMessageBox.information(self, "Sin selección", "Selecciona filas primero.")
            return
        resp = QMessageBox.question(
            self, "Confirmar",
            f"¿Dejar {len(filas)} gasto(s) sin categoría ni subcategoría?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes:
            return
        try:
            for row in filas:
                gasto = self.tabla_audit.item(row, 0).data(Qt.ItemDataRole.UserRole)
                self.fm.db.collection("gastos").document(gasto["id"]).update(
                    {"categoria_id": None, "subcategoria_id": None}
                )
            self._cambio(f"{len(filas)} gasto(s) limpiados.")
            self._ejecutar_auditoria()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _reasignar_huerfanas(self):
        items = self.lista_huerfanas.selectedItems()
        if not items:
            QMessageBox.information(self, "Sin selección", "Selecciona subcategorías huérfanas.")
            return
        nueva_cat_id = self.combo_fix_horf.currentData()
        if not nueva_cat_id:
            return
        try:
            for it in items:
                sub_id = it.data(Qt.ItemDataRole.UserRole)
                sub = next((s for s in self._subcats if s["id"] == sub_id), None)
                if sub:
                    self.fm.actualizar_subcategoria(sub_id, sub["nombre"], nueva_cat_id)
                    sub["categoria_id"] = nueva_cat_id
            self._cambio(f"{len(items)} subcategoría(s) reasignadas.")
            self._ejecutar_auditoria()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _eliminar_huerfanas(self):
        items = self.lista_huerfanas.selectedItems()
        if not items:
            QMessageBox.information(self, "Sin selección", "Selecciona subcategorías primero.")
            return
        resp = QMessageBox.question(
            self, "Confirmar",
            f"¿Eliminar {len(items)} subcategoría(s) huérfana(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes:
            return
        try:
            for it in items:
                sub_id = it.data(Qt.ItemDataRole.UserRole)
                self.fm.reasignar_subcategoria_en_gastos(sub_id, None)
                self.fm.eliminar_subcategoria(sub_id)
                self._subcats = [s for s in self._subcats if s["id"] != sub_id]
            self._cambio(f"{len(items)} subcategoría(s) huérfanas eliminadas.")
            self._ejecutar_auditoria()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ── Utilidades ────────────────────────────────────────────────────────────

    def _cambio(self, msg: str):
        self._hay_cambios = True
        self._status(msg)
        self.cambios_realizados.emit()

    def _status(self, msg: str):
        self.lbl_status.setText(msg)

    def closeEvent(self, event):
        if self._hay_cambios:
            self.cambios_realizados.emit()
        super().closeEvent(event)
