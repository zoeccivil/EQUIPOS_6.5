"""
Punto de entrada principal para EQUIPOS 6.0
Adaptado para trabajar con Firebase en lugar de SQLite
Diseño moderno "Tierra & Asfalto"

Comportamiento específico:
- Busca credenciales de Firebase en:
    1) config["firebase"]["credentials_path"] si existe y el archivo está presente
    2) Carpeta raíz (firebase_equipos_key.json o firebase_equipos_key)
    3) Diálogo de archivo para que el usuario seleccione el JSON; se guarda en config_equipos.json
- Inicializa firebase_admin tempranamente (si hay credenciales) antes de crear StorageManager.
- Usa resource_path(...) para soportar PyInstaller.
"""

import sys
import os
import logging
import traceback
import json
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt6.QtCore import QTimer
from dashboard_ejecutivo import DashboardEjecutivo
from gestor_combustible import GestorCombustible
from cuentas_por_cobrar import CuentasPorCobrar
from whatsapp_integration import WhatsAppIntegration

# Importaciones internas
from firebase_manager import FirebaseManager
from backup_manager import BackupManager
from storage_manager import StorageManager
from config_manager import cargar_configuracion, guardar_configuracion
from app_gui_qt import AppGUI
from theme_manager import ThemeManager

# Intentar importar helpers de firebase_admin (si están instalados)
try:
    from firebase_admin import credentials as fb_credentials  # type: ignore
    from firebase_admin import initialize_app as fb_initialize_app  # type: ignore
    from firebase_admin import _apps as fb_apps  # type: ignore
except Exception:
    fb_credentials = None
    fb_initialize_app = None
    fb_apps = None

# Configurar logging global
LOG_FILE = "equipos.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def excepthook(exc_type, exc_value, exc_tb):
    """
    Manejador global de excepciones: registra la traza completa en el log
    y muestra un QMessageBox si es posible.
    """
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.exception("Excepción no controlada:\n%s", msg)

    try:
        app = QApplication.instance()
        created_temp_app = False
        if app is None:
            app = QApplication([])
            created_temp_app = True

        QMessageBox.critical(
            None,
            "Error inesperado",
            "Se produjo un error inesperado y la aplicación debe cerrarse.\n\n"
            f"{exc_value}",
        )

        if created_temp_app:
            app.quit()
    except Exception as show_err:
        logger.exception("No se pudo mostrar QMessageBox en excepthook: %s", show_err)
        try:
            print("Error inesperado:", exc_value, file=sys.stderr)
        except Exception:
            pass

    try:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    except Exception:
        pass

    sys.exit(1)


# Helpers de rutas (soporta PyInstaller)
def resource_path(rel_path: str) -> str:
    """
    Devuelve la ruta absoluta a rel_path, soportando ejecución desde PyInstaller.
    Si el archivo se pasa como ruta absoluta se devuelve tal cual.
    """
    if os.path.isabs(rel_path):
        return rel_path
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, rel_path)


def root_credentials_candidates() -> list:
    """
    Rutas candidatas en la carpeta raíz para firebase_equipos_key(.json)
    """
    base = os.path.abspath(os.path.dirname(__file__))
    return [
        os.path.join(base, "firebase_equipos_key.json"),
        os.path.join(base, "firebase_equipos_key"),
    ]


def ensure_credentials(app, config: dict) -> str:
    """
    Busca credenciales en:
      1) config["firebase"]["credentials_path"] (si existe y el archivo existe)
      2) Carpeta raíz (firebase_equipos_key.json / firebase_equipos_key)
      3) Diálogo de archivo: el usuario elige un JSON; se guarda en config y se persiste.
    Retorna la ruta absoluta al JSON seleccionado.
    """
    # 1) Desde config
    cfg_path = config.get("firebase", {}).get("credentials_path")
    if cfg_path:
        cfg_abs = resource_path(cfg_path)
        if os.path.exists(cfg_abs):
            return cfg_abs

    # 2) En raíz
    for c in root_credentials_candidates():
        if os.path.exists(c):
            config.setdefault("firebase", {})["credentials_path"] = c
            guardar_configuracion(config)
            return c

    # 3) Diálogo para elegir
    file_path, _ = QFileDialog.getOpenFileName(
        None,
        "Seleccionar credenciales de Firebase (Service Account JSON)",
        os.path.expanduser("~"),
        "JSON Files (*.json);;All Files (*)",
    )
    if not file_path:
        QMessageBox.critical(
            None,
            "Credenciales de Firebase no encontradas",
            "No se seleccionó ningún archivo de credenciales. La aplicación se cerrará."
        )
        sys.exit(1)

    if not os.path.exists(file_path):
        QMessageBox.critical(
            None,
            "Archivo inválido",
            f"El archivo seleccionado no existe:\n{file_path}"
        )
        sys.exit(1)

    # Guardar en config y persistir
    config.setdefault("firebase", {})["credentials_path"] = file_path
    guardar_configuracion(config)
    return file_path


def main():
    """Función principal de la aplicación"""
    sys.excepthook = excepthook
    app = QApplication(sys.argv)

    # Cargar configuración
    try:
        config = cargar_configuracion()
    except Exception as e:
        logger.exception("No se pudo cargar la configuración: %s", e)
        QMessageBox.critical(
            None,
            "Error de Configuración",
            "No se pudo cargar la configuración:\n"
            f"{e}\n\n"
            "Asegúrese de que existe el archivo config_equipos.json",
        )
        sys.exit(1)

    # Aplicar tema
    theme_name = config.get("app", {}).get("tema", "Oscuro")
    try:
        ThemeManager.apply_theme(app, theme_name)
        logger.info(f"Tema aplicado: {theme_name}")
    except Exception as e:
        logger.warning(f"No se pudo aplicar el tema {theme_name}: {e}")
        try:
            ThemeManager.apply_theme(app, "Oscuro")
        except Exception:
            logger.exception("Fallo aplicando tema de fallback 'Oscuro'")

    # Credenciales (con diálogo si faltan)
    selected_cred = ensure_credentials(app, config)
    selected_cred = os.path.abspath(selected_cred)
    logger.info("Usando credenciales de Firebase en: %s", selected_cred)

    storage_manager = None
    storage_bucket = config.get("firebase", {}).get("storage_bucket")

    # Inicializar firebase_admin tempranamente
    if fb_initialize_app is not None and fb_credentials is not None and fb_apps is not None:
        try:
            if not fb_apps:
                cred = fb_credentials.Certificate(selected_cred)
                init_kwargs = {}
                if storage_bucket:
                    init_kwargs["storageBucket"] = storage_bucket
                fb_initialize_app(cred, init_kwargs) if init_kwargs else fb_initialize_app(cred)
                logger.info("firebase_admin inicializado tempranamente.")
        except Exception as e:
            logger.warning("No se pudo inicializar firebase_admin tempranamente: %s", e)

    # StorageManager
    if storage_bucket:
        try:
            storage_manager = StorageManager(bucket_name=storage_bucket)
            logger.info("Storage Manager inicializado con bucket: %s", storage_bucket)
        except Exception as e:
            logger.warning("No se pudo inicializar Storage Manager: %s", e)
            storage_manager = None
    else:
        logger.info("Storage bucket no configurado")

    # FirebaseManager
    try:
        firebase_manager = FirebaseManager(
            credentials_path=selected_cred,
            project_id=config["firebase"]["project_id"],
            storage_manager=storage_manager,
        )
        logger.info("Firebase Manager inicializado correctamente")
    except Exception as e:
        logger.exception("No se pudo inicializar Firebase Manager: %s", e)
        QMessageBox.critical(
            None,
            "Error de Firebase",
            "No se pudo conectar con Firebase:\n"
            f"{e}\n\n"
            "Verifique:\n"
            "1. Las credenciales son correctas\n"
            "2. Tiene conexión a Internet\n"
            "3. El proyecto de Firebase está activo",
        )
        sys.exit(1)

    # Backup Manager
    try:
        backup_manager = BackupManager(
            ruta_backup=config["backup"]["ruta_backup_sqlite"],
            firebase_manager=firebase_manager,
        )
        logger.info("Backup Manager inicializado correctamente")
    except Exception as e:
        logger.warning(f"No se pudo inicializar Backup Manager: {e}")
        backup_manager = None

    # Ventana principal
    try:
        window = AppGUI(
            firebase_manager=firebase_manager,
            storage_manager=storage_manager,
            backup_manager=backup_manager,
            config=config,
        )
        window.show()
        logger.info("Ventana principal creada y mostrada")
    except Exception as e:
        logger.exception("Error creando ventana principal AppGUI: %s", e)
        QMessageBox.critical(
            None,
            "Error al iniciar",
            f"No se pudo iniciar la interfaz gráfica:\n{e}",
        )
        sys.exit(1)

    # Backups automáticos
    if backup_manager:
        def verificar_backup():
            try:
                debe_backup = backup_manager.debe_crear_backup(
                    frecuencia=config["backup"]["frecuencia"],
                    hora_ejecucion=config["backup"]["hora_ejecucion"],
                    ultimo_backup=config["backup"].get("ultimo_backup"),
                )
                if debe_backup:
                    logger.info("Iniciando backup automático...")
                    if backup_manager.crear_backup():
                        from datetime import datetime
                        config["backup"]["ultimo_backup"] = datetime.now().isoformat()
                        guardar_configuracion(config)
                        logger.info("Backup automático completado")
                    else:
                        logger.error("Error al crear backup automático")
            except Exception as e:
                logger.error(f"Error en verificación de backup: {e}")

        QTimer.singleShot(5000, verificar_backup)
        timer_backup = QTimer()
        timer_backup.timeout.connect(verificar_backup)
        timer_backup.start(3600000)  # cada hora

    # Ejecutar Qt
    try:
        exit_code = app.exec()
        logger.info(f"Aplicación finalizada con exit_code={exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        logger.exception("Error durante app.exec(): %s", e)
        raise


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        logger.exception("Fallo en main (capturado en __main__): %s", e)
        try:
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "Error crítico", f"Fallo crítico: {e}")
        except Exception:
            pass
        sys.exit(1)