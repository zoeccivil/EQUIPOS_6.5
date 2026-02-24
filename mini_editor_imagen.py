"""
MiniEditorImagen - editor de imágenes robusto con crop funcional.

Esta versión:
- Mantiene la carga robusta (Pillow o fallback QImage).
- Añade un CropRectItem interactivo (handles) que permite mover y redimensionar.
- Implementa toggle_crop() y apply_crop() correctamente, mapeando coordenadas de escena
  a coordenadas de la imagen original (PIL).
- Maneja casos límite y evita errores si el rectángulo está fuera de la imagen.
- Devuelve PIL.Image desde get_final_image cuando es posible.

Uso:
    editor = MiniEditorImagen(path, width=1200, height=800)
    if editor.exec():
        img = editor.get_final_image()
"""

from __future__ import annotations
import io
import logging
import warnings
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
    QGraphicsView, QGraphicsScene, QSizePolicy, QLabel, QFrame,
    QGraphicsPixmapItem, QGraphicsRectItem
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QWheelEvent, QPen, QColor, QBrush
from PyQt6.QtCore import Qt, QRectF, QBuffer, QPointF, QSizeF

# Pillow (import en tiempo de ejecución)
try:
    from PIL import Image, ImageEnhance, ImageOps
    _HAS_PIL = True
except Exception:
    Image = None
    ImageEnhance = None
    ImageOps = None
    _HAS_PIL = False

# Typing-only import for PIL Image to satisfy linters/Pylance
if TYPE_CHECKING and _HAS_PIL:
    from PIL.Image import Image as PILImage  # type: ignore

# Allow very large images (avoid DecompressionBombError)
if _HAS_PIL:
    try:
        Image.MAX_IMAGE_PIXELS = None
    except Exception:
        pass

warnings.filterwarnings("ignore", category=UserWarning)

logger = logging.getLogger(__name__)


class CropRectItem(QGraphicsRectItem):
    """Rectángulo de recorte con 'handles' para redimensionar y mover."""

    HANDLE_SIZE = 10.0

    def __init__(self, rect: QRectF, parent=None):
        super().__init__(rect, parent)
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.handle_selected = None
        self.mouse_press_pos = None
        self.mouse_press_rect = None
        self.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine))
        self.setBrush(QBrush(QColor(255, 0, 0, 40)))

    def boundingRect(self) -> QRectF:
        o = self.HANDLE_SIZE / 2.0
        return self.rect().adjusted(-o, -o, o, o)

    def hoverMoveEvent(self, event):
        handle = self._get_handle_at(event.pos())
        cursor = Qt.CursorShape.ArrowCursor
        if handle in ("tl", "br"):
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif handle in ("tr", "bl"):
            cursor = Qt.CursorShape.SizeBDiagCursor
        elif handle in ("l", "r"):
            cursor = Qt.CursorShape.SizeHorCursor
        elif handle in ("t", "b"):
            cursor = Qt.CursorShape.SizeVerCursor
        elif handle == "move":
            cursor = Qt.CursorShape.SizeAllCursor
        self.setCursor(cursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        self.handle_selected = self._get_handle_at(event.pos())
        self.mouse_press_pos = event.pos()
        self.mouse_press_rect = QRectF(self.rect())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.handle_selected and self.handle_selected != "move":
            self._interactive_resize(self.handle_selected, event.pos())
        elif self.handle_selected == "move":
            diff = event.pos() - self.mouse_press_pos
            new_rect = QRectF(self.mouse_press_rect)
            new_rect.translate(diff)
            self.setRect(new_rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.handle_selected = None
        super().mouseReleaseEvent(event)

    def _get_handle_at(self, pos: QPointF) -> Optional[str]:
        """Devuelve el handle en el que está pos (o 'move' si está dentro del rect)."""
        rect = self.rect()
        o = self.HANDLE_SIZE
        handles = {
            "tl": QRectF(rect.topLeft() - QPointF(o / 2, o / 2), QSizeF(o, o)),
            "tr": QRectF(rect.topRight() - QPointF(o / 2, o / 2), QSizeF(o, o)),
            "bl": QRectF(rect.bottomLeft() - QPointF(o / 2, o / 2), QSizeF(o, o)),
            "br": QRectF(rect.bottomRight() - QPointF(o / 2, o / 2), QSizeF(o, o)),
            "t": QRectF(rect.center().x() - o / 2, rect.top() - o / 2, o, o),
            "b": QRectF(rect.center().x() - o / 2, rect.bottom() - o / 2, o, o),
            "l": QRectF(rect.left() - o / 2, rect.center().y() - o / 2, o, o),
            "r": QRectF(rect.right() - o / 2, rect.center().y() - o / 2, o, o),
        }
        for k, v in handles.items():
            if v.contains(pos):
                return k
        if rect.contains(pos):
            return "move"
        return None

    def _interactive_resize(self, handle: str, mouse_pos: QPointF):
        r = QRectF(self.mouse_press_rect)
        diff = mouse_pos - self.mouse_press_pos
        if handle == "tl":
            r.setTopLeft(r.topLeft() + diff)
        elif handle == "tr":
            r.setTopRight(r.topRight() + diff)
        elif handle == "bl":
            r.setBottomLeft(r.bottomLeft() + diff)
        elif handle == "br":
            r.setBottomRight(r.bottomRight() + diff)
        elif handle == "t":
            r.setTop(r.top() + diff.y())
        elif handle == "b":
            r.setBottom(r.bottom() + diff.y())
        elif handle == "l":
            r.setLeft(r.left() + diff.x())
        elif handle == "r":
            r.setRight(r.right() + diff.x())
        self.setRect(r.normalized())

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        # draw handles
        o = self.HANDLE_SIZE
        rect = self.rect()
        pts = [
            rect.topLeft(),
            rect.topRight(),
            rect.bottomLeft(),
            rect.bottomRight(),
            QPointF(rect.center().x(), rect.top()),
            QPointF(rect.center().x(), rect.bottom()),
            QPointF(rect.left(), rect.center().y()),
            QPointF(rect.right(), rect.center().y()),
        ]
        for pt in pts:
            painter.setBrush(QColor(255, 255, 255))
            painter.setPen(QPen(QColor(255, 0, 0), 1))
            painter.drawRect(QRectF(pt.x() - o / 2, pt.y() - o / 2, o, o))


class MiniEditorImagen(QDialog):
    def __init__(self, image_path: str | Path, width: int = 1200, height: int = 800, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editor de imagen")
        self.resize(min(1000, width), min(700, height))

        self.image_path = str(image_path)
        self._max_width = int(width)
        self._max_height = int(height)

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._current_image = None  # PIL.Image or None
        self._qimage_cache: Optional[QImage] = None
        self.crop_item: Optional[CropRectItem] = None

        # Scene + View (crear primero para evitar AttributeError)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setRenderHints(self.view.renderHints() | QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view.setFrameShape(QFrame.Shape.NoFrame)

        self._build_ui()

        loaded = self._load_image_robust()
        if not loaded:
            try:
                self.reject()
            except Exception:
                pass
            return

        self._update_scene_from_current_image()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setToolTip("Acercar")
        btn_zoom_in.clicked.connect(self.zoom_in)

        btn_zoom_out = QPushButton("-")
        btn_zoom_out.setToolTip("Alejar")
        btn_zoom_out.clicked.connect(self.zoom_out)

        btn_fit = QPushButton("Ajustar")
        btn_fit.clicked.connect(self.fit_to_view)

        btn_rotate = QPushButton("Rotar 90°")
        btn_rotate.clicked.connect(lambda: self.rotate_image(90))

        btn_contrast = QPushButton("Contraste +")
        btn_contrast.clicked.connect(lambda: self.enhance_contrast(1.25))

        self.btn_crop = QPushButton("Recortar")
        self.btn_crop.clicked.connect(self.toggle_crop)

        btn_ok = QPushButton("Aceptar")
        btn_ok.clicked.connect(self.accept)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for w in (btn_zoom_in, btn_zoom_out, btn_fit, btn_rotate, btn_contrast, self.btn_crop):
            toolbar.addWidget(w)
        toolbar.addStretch()
        toolbar.addWidget(self.info_label)
        toolbar.addWidget(btn_ok)
        toolbar.addWidget(btn_cancel)

        main_layout.addLayout(toolbar)
        main_layout.addWidget(self.view)

    def _load_image_robust(self) -> bool:
        p = Path(self.image_path)
        if not p.exists():
            QMessageBox.critical(self, "Error al cargar imagen", f"No se encontró el archivo: {self.image_path}")
            logger.error("Archivo no encontrado: %s", self.image_path)
            return False

        # Try PIL
        if _HAS_PIL:
            try:
                pil_img = Image.open(str(p))
                pil_img.load()
                try:
                    pil_img = ImageOps.exif_transpose(pil_img)
                except Exception:
                    pass
                pil_img = pil_img.convert("RGB")
                self._current_image = pil_img
                logger.debug("Imagen cargada con PIL: %s (%sx%s)", self.image_path, pil_img.width, pil_img.height)
                return True
            except Exception as e_pil:
                logger.exception("PIL no pudo cargar %s: %s", self.image_path, e_pil)
        # Fallback QImage
        try:
            qimg = QImage(self.image_path)
            if qimg.isNull():
                raise RuntimeError("QImage no pudo cargar la imagen.")
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.ReadWrite)
            ok = qimg.save(buffer, "PNG")
            if not ok:
                buffer.close()
                raise RuntimeError("No se pudo guardar QImage a buffer PNG.")
            data = bytes(buffer.data())
            buffer.close()
            if _HAS_PIL:
                pil_img = Image.open(io.BytesIO(data))
                pil_img.load()
                pil_img = pil_img.convert("RGB")
                self._current_image = pil_img
                logger.debug("Imagen cargada vía QImage->PIL: %s (%sx%s)", self.image_path, pil_img.width, pil_img.height)
                return True
            else:
                self._qimage_cache = qimg
                logger.debug("Imagen cargada como QImage (Pillow no disponible): %s", self.image_path)
                return True
        except Exception as e_qt:
            logger.exception("QImage fallback falló para %s: %s", self.image_path, e_qt)

        QMessageBox.critical(self, "Error al Cargar Imagen",
                             "No se pudo abrir o procesar la imagen. El archivo podría estar corrupto o ser un formato no soportado.")
        return False

    def _pil_to_qpixmap(self, pil_image) -> QPixmap:
        try:
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            buf.seek(0)
            qimg = QImage.fromData(buf.getvalue())
            pix = QPixmap.fromImage(qimg)
            return pix
        except Exception as e:
            logger.exception("Error convirtiendo PIL->QPixmap: %s", e)
            return QPixmap()

    def _update_scene_from_current_image(self):
        self.scene.clear()
        self._pixmap_item = None
        try:
            if self._current_image is not None:
                pix = self._pil_to_qpixmap(self._current_image)
            elif self._qimage_cache is not None:
                pix = QPixmap.fromImage(self._qimage_cache)
            else:
                pix = QPixmap()

            if not pix.isNull():
                self._pixmap_item = QGraphicsPixmapItem(pix)
                self.scene.addItem(self._pixmap_item)
                self.scene.setSceneRect(QRectF(self._pixmap_item.pixmap().rect()))
                self.fit_to_view()
                self._update_info()
            else:
                logger.warning("Pixmap nulo al actualizar escena para %s", self.image_path)
        except Exception as e:
            logger.exception("Error actualizando scene desde imagen: %s", e)

    def fit_to_view(self):
        try:
            if self._pixmap_item:
                self.view.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            else:
                self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        except Exception:
            logger.exception("fit_to_view fallo")

    def zoom_in(self):
        try:
            self.view.scale(1.2, 1.2)
            self._update_info()
        except Exception:
            logger.exception("zoom_in fallo")

    def zoom_out(self):
        try:
            self.view.scale(1 / 1.2, 1 / 1.2)
            self._update_info()
        except Exception:
            logger.exception("zoom_out fallo")

    def rotate_image(self, degrees: int = 90):
        try:
            if self._current_image is not None:
                self._current_image = self._current_image.rotate(-degrees, expand=True)
                self._update_scene_from_current_image()
            elif self._qimage_cache is not None and _HAS_PIL:
                buf = QBuffer()
                buf.open(QBuffer.OpenModeFlag.ReadWrite)
                self._qimage_cache.save(buf, "PNG")
                pil = Image.open(io.BytesIO(bytes(buf.data())))
                pil = pil.rotate(-degrees, expand=True).convert("RGB")
                buf.close()
                self._current_image = pil
                self._qimage_cache = None
                self._update_scene_from_current_image()
        except Exception:
            logger.exception("rotate_image fallo")

    def enhance_contrast(self, factor: float = 1.25):
        try:
            if _HAS_PIL and self._current_image is not None:
                enhancer = ImageEnhance.Contrast(self._current_image)
                self._current_image = enhancer.enhance(factor)
                self._update_scene_from_current_image()
            else:
                logger.debug("No hay PIL o imagen PIL para enhance_contrast")
        except Exception:
            logger.exception("enhance_contrast fallo")

    def toggle_crop(self):
        """Activa/desactiva el modo crop. Si hay crop activo, aplica el recorte."""
        try:
            if self.crop_item is None:
                if not self._pixmap_item:
                    return
                pix_rect = self._pixmap_item.boundingRect()
                w = pix_rect.width() * 0.6
                h = pix_rect.height() * 0.6
                x = pix_rect.x() + (pix_rect.width() - w) / 2
                y = pix_rect.y() + (pix_rect.height() - h) / 2
                crop_rect = QRectF(x, y, w, h)
                self.crop_item = CropRectItem(crop_rect)
                self.scene.addItem(self.crop_item)
                self.btn_crop.setText("Aplicar Recorte")
            else:
                # aplicar crop
                self.apply_crop()
                self.btn_crop.setText("Recortar")
        except Exception as e:
            logger.exception("toggle_crop fallo: %s", e)
            QMessageBox.warning(self, "Error", f"No se pudo activar/aplicar recorte: {e}")

    def apply_crop(self):
        """Aplica el recorte seleccionado en crop_item a self._current_image (PIL)."""
        if not self.crop_item or not self._pixmap_item:
            QMessageBox.warning(self, "Sin selección", "No hay selección de recorte activa.")
            return
        try:
            # crop_rect en coordenadas locales del crop_item
            crop_rect_local = self.crop_item.rect()
            # mapear a coordenadas de escena
            tl_scene = self.crop_item.mapToScene(crop_rect_local.topLeft())
            br_scene = self.crop_item.mapToScene(crop_rect_local.bottomRight())
            # bounding rect del pixmap en escena
            pixmap_scene_rect = self._pixmap_item.sceneBoundingRect()

            # Si no hay PIL image (ej. solo QImage cache), intentar convertir QImage->PIL
            if self._current_image is None and self._qimage_cache is not None and _HAS_PIL:
                try:
                    buf = QBuffer()
                    buf.open(QBuffer.OpenModeFlag.ReadWrite)
                    self._qimage_cache.save(buf, "PNG")
                    pil = Image.open(io.BytesIO(bytes(buf.data())))
                    pil.load()
                    self._current_image = pil.convert("RGB")
                    buf.close()
                except Exception:
                    logger.exception("Fallo convertir QImage->PIL para recorte")

            if self._current_image is None:
                QMessageBox.critical(self, "Error", "No hay imagen PIL para recortar.")
                return

            # Ratio entre tamaño original (PIL) y tamaño mostrado (pixmap)
            displayed_w = pixmap_scene_rect.width()
            displayed_h = pixmap_scene_rect.height()
            orig_w = self._current_image.width
            orig_h = self._current_image.height
            if displayed_w <= 0 or displayed_h <= 0:
                QMessageBox.critical(self, "Error", "Dimensiones inválidas para recorte.")
                return

            w_ratio = orig_w / displayed_w
            h_ratio = orig_h / displayed_h

            # Coordenadas relativas dentro del pixmap (en escena)
            x1_scene = tl_scene.x() - pixmap_scene_rect.left()
            y1_scene = tl_scene.y() - pixmap_scene_rect.top()
            x2_scene = br_scene.x() - pixmap_scene_rect.left()
            y2_scene = br_scene.y() - pixmap_scene_rect.top()

            # Convertir a coordenadas de imagen original
            x1 = int(round(x1_scene * w_ratio))
            y1 = int(round(y1_scene * h_ratio))
            x2 = int(round(x2_scene * w_ratio))
            y2 = int(round(y2_scene * h_ratio))

            # Clamp
            x1 = max(0, min(orig_w - 1, x1))
            x2 = max(0, min(orig_w, x2))
            y1 = max(0, min(orig_h - 1, y1))
            y2 = max(0, min(orig_h, y2))

            if x2 <= x1 or y2 <= y1 or (x2 - x1) < 5 or (y2 - y1) < 5:
                QMessageBox.warning(self, "Recorte inválido", "El área seleccionada es demasiado pequeña o inválida.")
                return

            # Aplicar recorte a la imagen PIL
            self._current_image = self._current_image.crop((x1, y1, x2, y2))
            # Eliminar crop_item de la escena
            try:
                self.scene.removeItem(self.crop_item)
            except Exception:
                pass
            self.crop_item = None
            self._update_scene_from_current_image()
        except Exception as e:
            logger.exception("apply_crop fallo: %s", e)
            QMessageBox.critical(self, "Error al recortar", f"No se pudo aplicar el recorte: {e}")

    def wheelEvent(self, event: QWheelEvent):
        try:
            if hasattr(self, "view") and isinstance(event, QWheelEvent):
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                event.accept()
            else:
                super().wheelEvent(event)
        except Exception:
            logger.exception("wheelEvent fallo")
            try:
                super().wheelEvent(event)
            except Exception:
                pass

    def _update_info(self):
        try:
            if self._current_image is not None:
                self.info_label.setText(f"{self._current_image.width}×{self._current_image.height}")
            elif self._qimage_cache is not None:
                self.info_label.setText(f"{self._qimage_cache.width()}×{self._qimage_cache.height()}")
            else:
                self.info_label.setText("")
        except Exception:
            pass

    def get_final_image(self):
        """
        Retorna la imagen final procesada y optimizada.
        Aplica thumbnail para reducir tamaño si es necesario.
        """
        try:
            if _HAS_PIL and self._current_image is not None:
                img = self._current_image.copy()
                
                # Reducir tamaño si excede los límites
                original_size = img.size
                img.thumbnail((self._max_width, self._max_height), Image.Resampling.LANCZOS)
                
                if img.size != original_size:
                    logger.info(f"Imagen redimensionada de {original_size} a {img.size}")
                
                return img
            elif self._qimage_cache is not None:
                return self._qimage_cache
            else:
                raise RuntimeError("No hay imagen disponible para devolver")
        except Exception as e:
            logger.exception("get_final_image fallo: %s", e)
            raise

    def save_changes(self, save_path: Optional[str] = None) -> bool:
        try:
            final = self.get_final_image()
            target = save_path or self.image_path
            if _HAS_PIL and hasattr(final, "save"):
                final.save(target, quality=95, optimize=True)
            elif isinstance(final, QImage):
                final.save(target)
            else:
                raise RuntimeError("Tipo de imagen no soportado para guardar")
            return True
        except Exception as e:
            logger.exception("save_changes fallo: %s", e)
            QMessageBox.critical(self, "Error al guardar", f"No se pudo guardar la imagen: {e}")
            return False

    def closeEvent(self, event):
        try:
            if self.scene:
                self.scene.clear()
        except Exception:
            pass
        super().closeEvent(event)