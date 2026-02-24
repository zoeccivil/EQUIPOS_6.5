"""
Gestor de almacenamiento en Firebase Cloud Storage para EQUIPOS 4.0
Maneja la subida y descarga de archivos (conduces, facturas, etc.)

CAMBIOS IMPORTANTES:
- generate_signed_url ahora genera URLs con 7 días de expiración por defecto (evita error ExpiredToken)
- Verificación de existencia del blob antes de generar URL firmada
- Método generar_url_firmada (alias en español) para compatibilidad
- Logging mejorado para debug de URLs expiradas
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple
import tempfile
from firebase_admin import storage

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False
    logger.warning("PIL/Pillow no disponible.  Las imágenes no se procesarán.")


class StorageManager:
    def __init__(self, bucket_name: str | None = None, service_account_json: str | None = None):
        """
        Constructor tolerante:  intenta usar firebase_admin si ya está inicializado,
        o inicializarlo si se le pasa service_account_json.  Si falla, deja self.bucket = None.
        """
        from firebase_admin import storage as fb_storage, credentials as fb_credentials, initialize_app as fb_initialize_app, _apps as fb_apps
        import logging

        self.logger = logging.getLogger(__name__)
        self.bucket = None

        try:
            # Si no hay app y nos dieron credenciales, intentamos inicializar
            if not fb_apps: 
                if service_account_json:
                    try:
                        cred = fb_credentials.Certificate(service_account_json)
                        fb_initialize_app(cred, {'storageBucket': bucket_name} if bucket_name else None)
                        self.logger. info("firebase_admin inicializado desde StorageManager.")
                    except Exception as init_err:
                        self.logger. warning(f"No se pudo inicializar firebase_admin desde StorageManager: {init_err}")
                else:
                    self.logger.debug("firebase_admin no inicializado y no se proporcionaron credenciales a StorageManager.")

            # Si ahora hay apps, intentar obtener bucket
            if fb_apps:
                try: 
                    self.bucket = fb_storage.bucket()
                    self.logger.info(f"StorageManager:  bucket inicializado:  {getattr(self. bucket, 'name', None)}")
                except Exception as e:
                    self.logger. warning(f"No se pudo obtener bucket desde firebase_admin: {e}")
                    self.bucket = None
            else:
                self.bucket = None

        except Exception as e:
            self.logger.error(f"Error inicializando StorageManager: {e}", exc_info=True)
            self.bucket = None

    def is_available(self) -> bool:
        """Verifica si StorageManager está disponible (bucket inicializado)."""
        return self.bucket is not None
    
    def _process_image(self, origen_path: str, width: int = 1200, height: int = 800) -> Optional[str]:
        """
        Procesa una imagen:  redimensiona manteniendo aspecto y convierte a JPEG con compresión optimizada.
        Retorna la ruta del archivo temporal procesado o None si falla.
        
        Para archivos muy grandes, usa compresión más agresiva. 
        """
        if not _HAS_PIL:
            logger.warning("PIL no disponible, no se procesará la imagen")
            return None
        
        try:
            with Image.open(origen_path) as img:
                # Obtener tamaño original
                original_size = img.size
                original_pixels = original_size[0] * original_size[1]
                
                # Convertir a RGB
                img = img.convert("RGB")
                
                # Redimensionar manteniendo aspecto
                img. thumbnail((width, height), Image.Resampling.LANCZOS)
                new_size = img.size
                
                logger.info(f"Redimensionando imagen de {original_size} a {new_size}")
                
                # Determinar calidad de JPEG basada en el tamaño
                # Más píxeles en la imagen original = más compresión
                if original_pixels > 3000000:  # >3 megapixels
                    quality = 70
                elif original_pixels > 1500000:  # >1.5 megapixels
                    quality = 80
                else:
                    quality = 85
                
                # Guardar en archivo temporal
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpeg')
                temp_path = temp_file.name
                temp_file.close()
                
                img.save(temp_path, format="JPEG", quality=quality, optimize=True)
                
                # Verificar tamaño final
                final_size = os. path.getsize(temp_path)
                final_size_mb = final_size / 1024 / 1024
                logger.info(f"Imagen procesada y guardada: {temp_path} ({final_size_mb:.2f} MB, calidad={quality})")
                
                return temp_path
                
        except Exception as e:
            logger. error(f"Error al procesar imagen {origen_path}: {e}", exc_info=True)
            return None
    
    def guardar_conduce(self, 
                    file_path: str,
                    alquiler: dict,
                    procesar_imagen: bool = True) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Sube un archivo de conduce a Firebase Storage como archivo PÚBLICO.
        La URL resultante es permanente y no expira.
        
        Args:
            file_path: Ruta local al archivo
            alquiler: Datos del alquiler
            procesar_imagen: Si True, optimiza imágenes
        
        Returns: 
            (éxito, url_publica_permanente, storage_path, error)
        """
        try:
            logger.info(f"=== Subiendo conduce (público) ===")
            logger.info(f"Archivo: {file_path}")
            
            # Validar existencia
            if not os.path.exists(file_path):
                return False, None, None, f"Archivo no encontrado: {file_path}"
            
            # Construir storage_path (igual que antes)
            fecha_str = alquiler.get('fecha', '')
            try:
                fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                anio, mes = str(fecha_dt.year), f"{fecha_dt.month:02d}"
            except: 
                now = datetime.now()
                anio, mes = str(now.year), f"{now.month:02d}"
            
            conduce_num = alquiler.get('conduce') or alquiler.get('id', 'temp')
            ext = Path(file_path).suffix.lower()
            
            # Procesar imagen si aplica
            archivo_a_subir = file_path
            archivo_temporal = None
            if procesar_imagen and ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
                procesado = self._process_image(file_path)
                if procesado:
                    archivo_a_subir = procesado
                    archivo_temporal = procesado
                    ext = '.jpeg'
            
            storage_path = f"conduces/{anio}/{mes}/{conduce_num}{ext}"
            logger.info(f"Storage path: {storage_path}")
            
            # Subir archivo
            blob = self. bucket.blob(storage_path)
            blob.upload_from_filename(archivo_a_subir)
            logger.info("✓ Archivo subido a Storage")
            
            # Hacer público (CRÍTICO)
            try:
                blob.make_public()
                url_publica = blob.public_url
                logger.info(f"✓ Archivo hecho público: {url_publica}")
            except Exception as e_public:
                # Si make_public falla, loguear pero intentar obtener la URL pública de todas formas
                logger.warning(f"make_public() falló: {e_public}")
                # Construir URL pública manualmente (formato estándar de GCS)
                bucket_name = self.bucket.name
                # URL pública de Google Cloud Storage
                url_publica = f"https://storage.googleapis.com/{bucket_name}/{storage_path}"
                logger.info(f"Usando URL pública construida manualmente: {url_publica}")
            
            # Limpiar temporal
            if archivo_temporal and os.path.exists(archivo_temporal):
                try:
                    os.unlink(archivo_temporal)
                except:
                    pass
            
            logger.info(f"✓ Conduce guardado exitosamente")
            return True, url_publica, storage_path, None
            
        except Exception as e:
            logger.error(f"Error guardando conduce: {e}", exc_info=True)
            return False, None, None, str(e)
    
    def descargar_conduce(self, storage_path: str, destino_local: Optional[str] = None) -> Optional[str]:
        """
        Descarga un archivo desde Storage. 
        
        Args:
            storage_path: Ruta del archivo en Storage
            destino_local: Ruta local donde guardar (si None, usa temp)
        
        Returns:
            Ruta local del archivo descargado o None si falla
        """
        try: 
            blob = self.bucket.blob(storage_path)
            
            if not destino_local:
                # Crear archivo temporal
                ext = Path(storage_path).suffix
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                destino_local = temp_file. name
                temp_file.close()
            
            blob.download_to_filename(destino_local)
            logger. info(f"Archivo descargado:  {storage_path} -> {destino_local}")
            return destino_local
            
        except Exception as e:
            logger.error(f"Error al descargar archivo {storage_path}: {e}")
            return None
    
    def eliminar_conduce(self, storage_path: str) -> bool:
        """
        Elimina un archivo de Storage.
        
        Args:
            storage_path: Ruta del archivo en Storage
        
        Returns: 
            True si se eliminó correctamente
        """
        try:
            blob = self.bucket.blob(storage_path)
            blob.delete()
            logger.info(f"Archivo eliminado de Storage: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar archivo {storage_path}: {e}")
            return False
    
    def obtener_url_publica(self, storage_path: str) -> Optional[str]:
        """
        Obtiene la URL pública de un archivo en Storage. 
        
        Args:
            storage_path: Ruta del archivo en Storage
        
        Returns: 
            URL pública o None si falla
        """
        try:
            blob = self.bucket.blob(storage_path)
            # Hacer público si no lo está
            if not blob.public_url:
                blob.make_public()
            return blob.public_url
        except Exception as e: 
            logger.error(f"Error al obtener URL pública de {storage_path}: {e}")
            return None
    
    def obtener_url_firmada(self, storage_path: str, expiracion_minutos:  int = 60) -> Optional[str]:
        """
        Genera una URL firmada temporal para acceder a un archivo privado.
        
        DEPRECADO:  Usar generate_signed_url en su lugar (usa días en vez de minutos).
        
        Args:
            storage_path: Ruta del archivo en Storage
            expiracion_minutos: Minutos hasta que expire la URL
        
        Returns: 
            URL firmada o None si falla
        """
        try:
            from datetime import timedelta
            blob = self.bucket. blob(storage_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiracion_minutos),
                method="GET"
            )
            return url
        except Exception as e: 
            logger.error(f"Error al generar URL firmada de {storage_path}: {e}")
            return None

    def generate_signed_url(self, storage_path: str, expiration_days: int = 7) -> str | None:
        """
        Genera una URL firmada para acceder al archivo en storage_path.
        
        Esta es la versión CORREGIDA que evita el error "ExpiredToken" al: 
        - Usar expiración de 7 días por defecto (en lugar de 1 hora)
        - Verificar que el archivo existe antes de generar la URL
        - Usar version="v4" para máxima compatibilidad
        
        Args: 
            storage_path: Ruta del archivo en Storage (ej: "gastos/2025/archivo.pdf")
            expiration_days:  Días de validez de la URL (default: 7)
        
        Returns:
            URL firmada (str) o None si falla
        """
        try:
            if not self.bucket:
                self.logger.warning("Bucket no disponible para generar URL firmada.")
                return None
            
            from datetime import timedelta
            blob = self.bucket.blob(storage_path)
            
            # Verificar que el archivo existe antes de generar URL
            # Esto evita generar URLs para archivos que no existen
            if not blob.exists():
                self.logger.warning(f"El archivo {storage_path} no existe en Storage.")
                return None
            
            # Generar URL firmada con expiración en días (7 días por defecto)
            # version="v4" es la versión más reciente y compatible
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=expiration_days),
                method="GET",
            )
            
            self.logger.info(f"URL firmada generada para {storage_path} (válida {expiration_days} días)")
            return url
            
        except Exception as e: 
            self.logger.error(f"Error generando URL firmada para {storage_path}: {e}", exc_info=True)
            return None

    def generar_url_firmada(self, storage_path: str, dias:  int = 7) -> str | None:
        """
        Alias en español de generate_signed_url para compatibilidad.
        
        Args:
            storage_path:  Ruta del archivo en Storage
            dias: Días de validez de la URL (default: 7)
        
        Returns: 
            URL firmada (str) o None si falla
        """
        return self.generate_signed_url(storage_path, expiration_days=dias)

    def get_download_url(self, storage_path: str, prefer_firmada: bool = True, expiracion_minutos: int = 120) -> Optional[str]:
        """
        Devuelve una URL de descarga usable para un objeto en Storage. 
        
        IMPORTANTE: Este método está DEPRECADO para evitar problemas de URLs expiradas.
        Se recomienda usar generate_signed_url directamente, que genera URLs con 7 días de validez.
        
        - Si storage_path ya es una URL http(s), se retorna tal cual.
        - Si prefer_firmada=True (por defecto), intenta generar URL firmada;
          si falla, intenta pública.
        - Si prefer_firmada=False, intenta hacer público; si falla, genera firmada.
        
        NOTA: expiracion_minutos es ignorado si se usa el nuevo método generate_signed_url
        """
        if not storage_path:
            return None
        if isinstance(storage_path, str) and storage_path.startswith(("http://", "https://")):
            return storage_path
        try:
            if prefer_firmada:
                # Usar el nuevo método con 7 días de expiración en lugar de minutos
                url = self.generate_signed_url(storage_path, expiration_days=7)
                if url:
                    return url
                return self.obtener_url_publica(storage_path)
            else:
                url = self. obtener_url_publica(storage_path)
                if url:
                    return url
                return self.generate_signed_url(storage_path, expiration_days=7)
        except Exception as e:
            logger.warning(f"get_download_url: error con {storage_path}: {e}")
            return None
        
    def subir_archivo_publico(self, 
                            file_path: str, 
                            carpeta: str,
                            nombre_archivo: str,
                            procesar_imagen: bool = True) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Sube un archivo a Storage como público (URL permanente).
        
        Args:
            file_path:  Ruta local del archivo
            carpeta: Carpeta destino en Storage (ej: "gastos/2025/11")
            nombre_archivo: Nombre del archivo en Storage (ej: "factura_123.pdf")
            procesar_imagen: Si True, optimiza imágenes
        
        Returns: 
            (éxito, url_publica, storage_path, error)
        """
        try:
            if not os.path.exists(file_path):
                return False, None, None, f"Archivo no encontrado: {file_path}"
            
            ext = Path(file_path).suffix.lower()
            archivo_a_subir = file_path
            archivo_temporal = None
            
            # Procesar imagen si aplica
            if procesar_imagen and ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
                procesado = self._process_image(file_path)
                if procesado: 
                    archivo_a_subir = procesado
                    archivo_temporal = procesado
                    # Actualizar nombre con extensión . jpeg
                    nombre_base = Path(nombre_archivo).stem
                    nombre_archivo = f"{nombre_base}.jpeg"
            
            # Construir path completo
            storage_path = f"{carpeta. rstrip('/')}/{nombre_archivo}"
            
            # Subir
            blob = self.bucket.blob(storage_path)
            blob.upload_from_filename(archivo_a_subir)
            
            # Hacer público
            try:
                blob.make_public()
                url = blob.public_url
            except Exception as e:
                logger.warning(f"make_public falló: {e}, usando URL construida")
                url = f"https://storage.googleapis.com/{self.bucket.name}/{storage_path}"
            
            # Limpiar temporal
            if archivo_temporal and os. path.exists(archivo_temporal):
                try:
                    os. unlink(archivo_temporal)
                except:
                    pass
            
            logger.info(f"✓ Archivo público subido:  {storage_path}")
            return True, url, storage_path, None
            
        except Exception as e: 
            logger.error(f"Error subiendo archivo público: {e}", exc_info=True)
            return False, None, None, str(e)
        
def guardar_pago_operador(self, 
                          file_path: str,
                          pago_data: dict,
                          procesar_imagen: bool = True) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Sube un comprobante de pago a operador a Storage.
    SIEMPRE usa URLs firmadas (compatible con UBLA).
    
    Args:
        file_path: Ruta local al archivo
        pago_data: Dict con 'id' y 'fecha' del pago
        procesar_imagen: Si True, optimiza imágenes
    
    Returns:
        (éxito, url_firmada, storage_path, error)
    """
    try:
        logger.info(f"=== Subiendo comprobante de pago a operador ===")
        logger.info(f"Archivo: {file_path}")
        
        if not os.path.exists(file_path):
            return False, None, None, f"Archivo no encontrado: {file_path}"
        
        # Construir storage_path
        fecha_str = pago_data.get('fecha', '')
        try:
            fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
            anio, mes = str(fecha_dt.year), f"{fecha_dt.month:02d}"
        except:
            now = datetime.now()
            anio, mes = str(now.year), f"{now.month:02d}"
        
        pago_id = pago_data.get('id', 'temp')
        ext = Path(file_path).suffix.lower()
        
        # Procesar imagen si aplica
        archivo_a_subir = file_path
        archivo_temporal = None
        if procesar_imagen and ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
            procesado = self._process_image(file_path)
            if procesado:
                archivo_a_subir = procesado
                archivo_temporal = procesado
                ext = '.jpeg'
        
        storage_path = f"pagos_operadores/{anio}/{mes}/pago_{pago_id}{ext}"
        logger.info(f"Storage path: {storage_path}")
        
        # Subir archivo
        blob = self.bucket.blob(storage_path)
        blob.upload_from_filename(archivo_a_subir)
        logger.info("✓ Archivo subido a Storage")
        
        # ✅ Generar URL firmada (NO intentar hacer público)
        url_firmada = self.generate_signed_url(storage_path, expiration_days=7)
        
        if not url_firmada:
            return False, None, None, "No se pudo generar URL firmada"
        
        logger.info(f"✓ URL firmada generada (válida 7 días)")
        
        # Limpiar temporal
        if archivo_temporal and os.path.exists(archivo_temporal):
            try:
                os.unlink(archivo_temporal)
            except:
                pass
        
        logger.info(f"✓ Comprobante de pago guardado exitosamente")
        return True, url_firmada, storage_path, None
        
    except Exception as e:
        logger.error(f"Error guardando comprobante de pago: {e}", exc_info=True)
        return False, None, None, str(e)
    
    def guardar_pago_operador(self, 
                            file_path: str,
                            pago_data: dict,
                            procesar_imagen: bool = True) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Sube un comprobante de pago a operador a Storage.
        SIEMPRE usa URLs firmadas (compatible con UBLA).
        
        Args:
            file_path: Ruta local al archivo
            pago_data: Dict con 'id' y 'fecha' del pago
            procesar_imagen: Si True, optimiza imágenes
        
        Returns:
            (éxito, url_firmada, storage_path, error)
        """
        try:
            logger.info(f"=== Subiendo comprobante de pago a operador ===")
            logger.info(f"Archivo: {file_path}")
            
            if not os.path.exists(file_path):
                return False, None, None, f"Archivo no encontrado: {file_path}"
            
            # Construir storage_path
            fecha_str = pago_data.get('fecha', '')
            try:
                fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                anio, mes = str(fecha_dt.year), f"{fecha_dt.month:02d}"
            except:
                now = datetime.now()
                anio, mes = str(now.year), f"{now.month:02d}"
            
            pago_id = pago_data.get('id', 'temp')
            ext = Path(file_path).suffix.lower()
            
            # Procesar imagen si aplica
            archivo_a_subir = file_path
            archivo_temporal = None
            if procesar_imagen and ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
                procesado = self._process_image(file_path)
                if procesado:
                    archivo_a_subir = procesado
                    archivo_temporal = procesado
                    ext = '.jpeg'
            
            storage_path = f"pagos_operadores/{anio}/{mes}/pago_{pago_id}{ext}"
            logger.info(f"Storage path: {storage_path}")
            
            # Subir archivo
            blob = self.bucket.blob(storage_path)
            blob.upload_from_filename(archivo_a_subir)
            logger.info("✓ Archivo subido a Storage")
            
            # ✅ Generar URL firmada (NO intentar hacer público)
            url_firmada = self.generate_signed_url(storage_path, expiration_days=7)
            
            if not url_firmada:
                return False, None, None, "No se pudo generar URL firmada"
            
            logger.info(f"✓ URL firmada generada (válida 7 días)")
            
            # Limpiar temporal
            if archivo_temporal and os.path.exists(archivo_temporal):
                try:
                    os.unlink(archivo_temporal)
                except:
                    pass
            
            logger.info(f"✓ Comprobante de pago guardado exitosamente")
            return True, url_firmada, storage_path, None
            
        except Exception as e:
            logger.error(f"Error guardando comprobante de pago: {e}", exc_info=True)
            return False, None, None, str(e)