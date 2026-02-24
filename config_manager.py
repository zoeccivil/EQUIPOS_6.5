"""
Gestor de configuración para EQUIPOS 4.0
Maneja la carga y guardado del archivo config_equipos.json
"""

import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

CONFIG_FILE = "config_equipos.json"
CONFIG_EXAMPLE_FILE = "config_equipos.example.json"


def cargar_configuracion() -> Dict[str, Any]:
    """
    Carga la configuración desde el archivo JSON.
    Si no existe, crea uno basado en el ejemplo o en valores por defecto.

    Además, se asegura de que siempre existan las claves mínimas
    (incluyendo firebase.storage_bucket) incluso si el archivo viene de
    una versión anterior sin ese campo.
    """
    if not os.path.exists(CONFIG_FILE):
        logger.warning(f"No se encontró {CONFIG_FILE}, creando desde ejemplo...")
        if os.path.exists(CONFIG_EXAMPLE_FILE):
            # Copiar el archivo de ejemplo
            with open(CONFIG_EXAMPLE_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # Completar con valores por defecto si faltan claves nuevas
            config = _completar_config_con_defecto(config)
            guardar_configuracion(config)
            logger.info(f"Configuración creada desde {CONFIG_EXAMPLE_FILE}")
        else:
            # Crear configuración por defecto (incluye storage_bucket)
            config = crear_configuracion_defecto()
            guardar_configuracion(config)
            logger.info("Configuración creada con valores por defecto")
        return config

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Rellenar claves nuevas (como firebase.storage_bucket) si el archivo
        # fue creado con una versión anterior
        config = _completar_config_con_defecto(config)

        logger.info(f"Configuración cargada desde {CONFIG_FILE}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Error al parsear {CONFIG_FILE}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error al cargar configuración: {e}")
        raise


def guardar_configuracion(config: Dict[str, Any]) -> bool:
    """
    Guarda la configuración en el archivo JSON.
    
    Args:
        config: Diccionario con la configuración a guardar
        
    Returns:
        True si se guardó correctamente, False en caso contrario
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Configuración guardada en {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar configuración: {e}")
        return False


def crear_configuracion_defecto() -> Dict[str, Any]:
    return {
        "firebase": {
            "credentials_path": "firebase_credentials.json",
            "project_id": "equipos-zoec",
            "storage_bucket": "equipos-zoec.firebasestorage.app",  # <--- TU BUCKET REAL
        },
        "backup": {
            "ruta_backup_sqlite": "./backups/equipos_backup.db",
            "frecuencia": "diario",
            "hora_ejecucion": "02:00",
            "ultimo_backup": None
        },
        "app": {
            "tema": "claro",
            "idioma": "es",
            "ventana_maximizada": False
        }
    }


def _completar_config_con_defecto(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Toma una configuración existente (posiblemente creada con una versión
    anterior) y completa cualquier clave faltante usando la configuración
    por defecto (incluyendo firebase.storage_bucket).

    Esto permite que:
      - Un config viejo sin storage_bucket se actualice automáticamente.
      - El exe genere un config completo desde cero si no existía.
    """
    defecto = crear_configuracion_defecto()

    # firebase
    if "firebase" not in config or not isinstance(config["firebase"], dict):
        config["firebase"] = {}
    for k, v in defecto["firebase"].items():
        config["firebase"].setdefault(k, v)

    # backup
    if "backup" not in config or not isinstance(config["backup"], dict):
        config["backup"] = {}
    for k, v in defecto["backup"].items():
        config["backup"].setdefault(k, v)

    # app
    if "app" not in config or not isinstance(config["app"], dict):
        config["app"] = {}
    for k, v in defecto["app"].items():
        config["app"].setdefault(k, v)

    return config


def obtener_valor_config(config: Dict[str, Any], clave: str, defecto: Any = None) -> Any:
    """
    Obtiene un valor de la configuración usando notación de punto.
    
    Args:
        config: Diccionario de configuración
        clave: Clave en notación de punto (ej: "firebase.project_id")
        defecto: Valor por defecto si no se encuentra la clave
        
    Returns:
        El valor encontrado o el valor por defecto
    """
    partes = clave.split('.')
    valor = config
    
    for parte in partes:
        if isinstance(valor, dict) and parte in valor:
            valor = valor[parte]
        else:
            return defecto
    
    return valor


def establecer_valor_config(config: Dict[str, Any], clave: str, valor: Any) -> Dict[str, Any]:
    """
    Establece un valor en la configuración usando notación de punto.
    
    Args:
        config: Diccionario de configuración
        clave: Clave en notación de punto (ej: "firebase.project_id")
        valor: Valor a establecer
        
    Returns:
        El diccionario de configuración actualizado
    """
    partes = clave.split('.')
    actual = config
    
    # Navegar hasta el penúltimo nivel
    for parte in partes[:-1]:
        if parte not in actual or not isinstance(actual[parte], dict):
            actual[parte] = {}
        actual = actual[parte]
    
    # Establecer el valor en el último nivel
    actual[partes[-1]] = valor
    
    return config


def validar_configuracion(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Valida que la configuración tenga los campos requeridos.
    
    Args:
        config: Diccionario de configuración a validar
        
    Returns:
        Tupla (es_valida, mensaje_error)
        es_valida: True si la configuración es válida
        mensaje_error: Descripción del error si no es válida, None si es válida
    """
    campos_requeridos = [
        "firebase.credentials_path",
        "firebase.project_id",
        # Opcional pero recomendado: si quieres exigir el bucket, descomenta:
        # "firebase.storage_bucket",
        "backup.ruta_backup_sqlite",
        "backup.frecuencia",
        "backup.hora_ejecucion"
    ]
    
    for campo in campos_requeridos:
        valor = obtener_valor_config(config, campo)
        if valor is None or valor == "":
            return False, f"Falta el campo requerido: {campo}"
    
    # Validar que el archivo de credenciales existe
    credentials_path = obtener_valor_config(config, "firebase.credentials_path")
    if not os.path.exists(credentials_path):
        return False, f"No se encuentra el archivo de credenciales de Firebase: {credentials_path}"
    
    return True, None


if __name__ == "__main__":
    # Pruebas básicas
    logging.basicConfig(level=logging.INFO)
    
    try:
        config = cargar_configuracion()
        print("Configuración cargada:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        
        es_valida, error = validar_configuracion(config)
        if es_valida:
            print("\n✓ La configuración es válida")
        else:
            print(f"\n✗ Error en configuración: {error}")
    except Exception as e:
        print(f"Error: {e}")