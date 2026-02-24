"""
Script de migración de datos desde PROGAIN a EQUIPOS 4.0
Migra todos los datos de equipos desde la base de datos compartida de PROGAIN
hacia Firebase (Firestore) y crea un backup inicial en SQLite.
"""

import sys
import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Agregar el directorio padre al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase_manager import FirebaseManager
from backup_manager import BackupManager
from config_manager import cargar_configuracion

# Configurar logging
LOG_FILE = f"migracion_equipos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MigradorEquipos:
    """
    Migra datos de equipos desde la base de datos compartida de PROGAIN
    hacia Firebase (EQUIPOS 4.0).
    """
    
    def __init__(self, ruta_bd_progain: str, firebase_manager: FirebaseManager):
        """
        Inicializa el migrador.
        
        Args:
            ruta_bd_progain: Ruta a la base de datos SQLite de PROGAIN
            firebase_manager: Instancia del FirebaseManager para Firebase
        """
        self.ruta_bd_progain = ruta_bd_progain
        self.firebase_manager = firebase_manager
        self.mapeo_ids = {
            'equipos': {},        # {id_sqlite: id_firebase}
            'entidades': {},      # {id_sqlite: id_firebase}
        }
        self.estadisticas = {
            'equipos_migrados': 0,
            'entidades_migradas': 0,
            'transacciones_migradas': 0,
            'mantenimientos_migrados': 0,
            'pagos_migrados': 0,
            'errores': []
        }
    
    def conectar_bd_progain(self) -> sqlite3.Connection:
        """Conecta a la base de datos de PROGAIN."""
        try:
            conn = sqlite3.connect(self.ruta_bd_progain)
            conn.row_factory = sqlite3.Row
            logger.info(f"Conectado a BD de PROGAIN: {self.ruta_bd_progain}")
            return conn
        except Exception as e:
            logger.error(f"Error al conectar a BD de PROGAIN: {e}")
            raise
    
    def migrar_todo(self, proyecto_id: int = 8) -> bool:
        """
        Ejecuta la migración completa.
        
        Args:
            proyecto_id: ID del proyecto "EQUIPOS PESADOS ZOEC" en PROGAIN (default: 8)
            
        Returns:
            True si la migración fue exitosa, False en caso contrario
        """
        try:
            logger.info("="*80)
            logger.info("INICIANDO MIGRACIÓN DE EQUIPOS DESDE PROGAIN A FIREBASE")
            logger.info("="*80)
            logger.info(f"Proyecto ID: {proyecto_id}")
            logger.info(f"Base de datos origen: {self.ruta_bd_progain}")
            logger.info(f"Timestamp: {datetime.now().isoformat()}")
            logger.info("")
            
            conn = self.conectar_bd_progain()
            
            # Paso 1: Migrar equipos
            logger.info("Paso 1: Migrando equipos...")
            self._migrar_equipos(conn, proyecto_id)
            
            # Paso 2: Migrar entidades (clientes y operadores)
            logger.info("\nPaso 2: Migrando entidades (clientes y operadores)...")
            self._migrar_entidades(conn, proyecto_id)
            
            # Paso 3: Migrar transacciones (alquileres)
            logger.info("\nPaso 3: Migrando transacciones (alquileres)...")
            self._migrar_transacciones(conn, proyecto_id)
            
            # Paso 4: Migrar mantenimientos
            logger.info("\nPaso 4: Migrando mantenimientos...")
            self._migrar_mantenimientos(conn)
            
            # Paso 5: Migrar pagos a operadores
            logger.info("\nPaso 5: Migrando pagos a operadores...")
            self._migrar_pagos_operadores(conn, proyecto_id)
            
            conn.close()
            
            # Mostrar resumen
            self._mostrar_resumen()
            
            logger.info("\n" + "="*80)
            logger.info("MIGRACIÓN COMPLETADA")
            logger.info("="*80)
            
            return len(self.estadisticas['errores']) == 0
            
        except Exception as e:
            logger.error(f"Error durante la migración: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _migrar_equipos(self, conn: sqlite3.Connection, proyecto_id: int):
        """Migra los equipos desde PROGAIN a Firebase."""
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, nombre, marca, modelo, categoria, activo
                FROM equipos
                WHERE proyecto_id = ?
            """, (proyecto_id,))
            
            equipos = cur.fetchall()
            logger.info(f"Encontrados {len(equipos)} equipos en PROGAIN")
            
            for equipo in equipos:
                try:
                    datos_equipo = {
                        'nombre': equipo['nombre'],
                        'marca': equipo['marca'] or '',
                        'modelo': equipo['modelo'] or '',
                        'categoria': equipo['categoria'] or '',
                        'activo': bool(equipo['activo']),
                        'placa': '',  # No existe en PROGAIN
                        'ficha': '',  # No existe en PROGAIN
                    }
                    
                    firebase_id = self.firebase_manager.agregar_equipo(datos_equipo)
                    
                    if firebase_id:
                        self.mapeo_ids['equipos'][equipo['id']] = firebase_id
                        self.estadisticas['equipos_migrados'] += 1
                        logger.info(f"  ✓ Equipo migrado: {equipo['nombre']} (SQLite ID: {equipo['id']} → Firebase ID: {firebase_id})")
                    else:
                        error_msg = f"Error al migrar equipo ID {equipo['id']}: {equipo['nombre']}"
                        logger.error(f"  ✗ {error_msg}")
                        self.estadisticas['errores'].append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Excepción al migrar equipo ID {equipo['id']}: {e}"
                    logger.error(f"  ✗ {error_msg}")
                    self.estadisticas['errores'].append(error_msg)
            
            logger.info(f"Equipos migrados: {self.estadisticas['equipos_migrados']}/{len(equipos)}")
            
        except Exception as e:
            logger.error(f"Error al migrar equipos: {e}")
            raise
    
    def _migrar_entidades(self, conn: sqlite3.Connection, proyecto_id: int):
        """Migra clientes y operadores desde PROGAIN a Firebase."""
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, nombre, tipo, activo, telefono, cedula
                FROM equipos_entidades
                WHERE proyecto_id = ?
            """, (proyecto_id,))
            
            entidades = cur.fetchall()
            logger.info(f"Encontradas {len(entidades)} entidades en PROGAIN")
            
            for entidad in entidades:
                try:
                    datos_entidad = {
                        'nombre': entidad['nombre'],
                        'tipo': entidad['tipo'],  # 'Cliente' o 'Operador'
                        'activo': bool(entidad['activo']),
                        'telefono': entidad['telefono'] or '',
                        'cedula': entidad['cedula'] or '',
                    }
                    
                    firebase_id = self.firebase_manager.agregar_entidad(datos_entidad)
                    
                    if firebase_id:
                        self.mapeo_ids['entidades'][entidad['id']] = firebase_id
                        self.estadisticas['entidades_migradas'] += 1
                        logger.info(f"  ✓ Entidad migrada: {entidad['nombre']} ({entidad['tipo']}) (SQLite ID: {entidad['id']} → Firebase ID: {firebase_id})")
                    else:
                        error_msg = f"Error al migrar entidad ID {entidad['id']}: {entidad['nombre']}"
                        logger.error(f"  ✗ {error_msg}")
                        self.estadisticas['errores'].append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Excepción al migrar entidad ID {entidad['id']}: {e}"
                    logger.error(f"  ✗ {error_msg}")
                    self.estadisticas['errores'].append(error_msg)
            
            logger.info(f"Entidades migradas: {self.estadisticas['entidades_migradas']}/{len(entidades)}")
            
        except Exception as e:
            logger.error(f"Error al migrar entidades: {e}")
            raise
    
    def _migrar_transacciones(self, conn: sqlite3.Connection, proyecto_id: int):
        """Migra transacciones (alquileres) desde PROGAIN a Firebase."""
        try:
            cur = conn.cursor()
            # Solo migramos transacciones de tipo 'Ingreso' que tienen equipo_id
            cur.execute("""
                SELECT id, tipo, equipo_id, cliente_id, operador_id, fecha, monto,
                       descripcion, comentario, horas, precio_por_hora, conduce,
                       ubicacion, pagado
                FROM transacciones
                WHERE proyecto_id = ? AND tipo = 'Ingreso' AND equipo_id IS NOT NULL
            """, (proyecto_id,))
            
            transacciones = cur.fetchall()
            logger.info(f"Encontradas {len(transacciones)} transacciones de alquiler en PROGAIN")
            
            for trans in transacciones:
                try:
                    # Mapear IDs de SQLite a Firebase
                    equipo_id_firebase = self.mapeo_ids['equipos'].get(trans['equipo_id'])
                    cliente_id_firebase = self.mapeo_ids['entidades'].get(trans['cliente_id']) if trans['cliente_id'] else None
                    operador_id_firebase = self.mapeo_ids['entidades'].get(trans['operador_id']) if trans['operador_id'] else None
                    
                    if not equipo_id_firebase:
                        error_msg = f"No se encontró equipo Firebase para equipo SQLite ID {trans['equipo_id']} (transacción {trans['id']})"
                        logger.warning(f"  ⚠ {error_msg}")
                        self.estadisticas['errores'].append(error_msg)
                        continue
                    
                    datos_trans = {
                        'tipo': 'Ingreso',
                        'equipo_id': equipo_id_firebase,
                        'cliente_id': cliente_id_firebase,
                        'operador_id': operador_id_firebase,
                        'fecha': trans['fecha'],
                        'monto': float(trans['monto']) if trans['monto'] else 0.0,
                        'descripcion': trans['descripcion'] or '',
                        'comentario': trans['comentario'] or '',
                        'horas': float(trans['horas']) if trans['horas'] else None,
                        'precio_por_hora': float(trans['precio_por_hora']) if trans['precio_por_hora'] else None,
                        'conduce': trans['conduce'] or '',
                        'ubicacion': trans['ubicacion'] or '',
                        'pagado': bool(trans['pagado']),
                    }
                    
                    firebase_id = self.firebase_manager.registrar_alquiler(datos_trans)
                    
                    if firebase_id:
                        self.estadisticas['transacciones_migradas'] += 1
                        if self.estadisticas['transacciones_migradas'] % 50 == 0:
                            logger.info(f"  → {self.estadisticas['transacciones_migradas']} transacciones migradas...")
                    else:
                        error_msg = f"Error al migrar transacción ID {trans['id']}"
                        logger.error(f"  ✗ {error_msg}")
                        self.estadisticas['errores'].append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Excepción al migrar transacción ID {trans['id']}: {e}"
                    logger.error(f"  ✗ {error_msg}")
                    self.estadisticas['errores'].append(error_msg)
            
            logger.info(f"Transacciones migradas: {self.estadisticas['transacciones_migradas']}/{len(transacciones)}")
            
        except Exception as e:
            logger.error(f"Error al migrar transacciones: {e}")
            raise
    
    def _migrar_mantenimientos(self, conn: sqlite3.Connection):
        """Migra mantenimientos desde PROGAIN a Firebase."""
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, equipo_id, fecha, descripcion, tipo, valor as costo,
                       odometro_horas, odometro_km, notas, proximo_tipo,
                       proximo_valor, proximo_fecha
                FROM mantenimientos
            """)
            
            mantenimientos = cur.fetchall()
            logger.info(f"Encontrados {len(mantenimientos)} mantenimientos en PROGAIN")
            
            for mant in mantenimientos:
                try:
                    # Mapear ID del equipo
                    equipo_id_firebase = self.mapeo_ids['equipos'].get(mant['equipo_id'])
                    
                    if not equipo_id_firebase:
                        error_msg = f"No se encontró equipo Firebase para mantenimiento (equipo SQLite ID {mant['equipo_id']})"
                        logger.warning(f"  ⚠ {error_msg}")
                        self.estadisticas['errores'].append(error_msg)
                        continue
                    
                    datos_mant = {
                        'equipo_id': equipo_id_firebase,
                        'fecha': mant['fecha'] or '',
                        'descripcion': mant['descripcion'] or '',
                        'tipo': mant['tipo'] or '',
                        'costo': float(mant['costo']) if mant['costo'] else None,
                        'odometro_horas': float(mant['odometro_horas']) if mant['odometro_horas'] else None,
                        'odometro_km': float(mant['odometro_km']) if mant['odometro_km'] else None,
                        'notas': mant['notas'] or '',
                        'proximo_tipo': mant['proximo_tipo'] or '',
                        'proximo_valor': float(mant['proximo_valor']) if mant['proximo_valor'] else None,
                        'proximo_fecha': mant['proximo_fecha'] or '',
                    }
                    
                    firebase_id = self.firebase_manager.registrar_mantenimiento(datos_mant)
                    
                    if firebase_id:
                        self.estadisticas['mantenimientos_migrados'] += 1
                        if self.estadisticas['mantenimientos_migrados'] % 20 == 0:
                            logger.info(f"  → {self.estadisticas['mantenimientos_migrados']} mantenimientos migrados...")
                    else:
                        error_msg = f"Error al migrar mantenimiento ID {mant['id']}"
                        logger.error(f"  ✗ {error_msg}")
                        self.estadisticas['errores'].append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Excepción al migrar mantenimiento ID {mant['id']}: {e}"
                    logger.error(f"  ✗ {error_msg}")
                    self.estadisticas['errores'].append(error_msg)
            
            logger.info(f"Mantenimientos migrados: {self.estadisticas['mantenimientos_migrados']}/{len(mantenimientos)}")
            
        except Exception as e:
            logger.error(f"Error al migrar mantenimientos: {e}")
            raise
    
    def _migrar_pagos_operadores(self, conn: sqlite3.Connection, proyecto_id: int):
        """Migra pagos a operadores desde PROGAIN a Firebase."""
        try:
            cur = conn.cursor()
            # Buscamos transacciones de tipo 'Gasto' con operador_id
            cur.execute("""
                SELECT id, operador_id, equipo_id, fecha, monto, horas,
                       descripcion, comentario
                FROM transacciones
                WHERE proyecto_id = ? AND tipo = 'Gasto' AND operador_id IS NOT NULL
            """, (proyecto_id,))
            
            pagos = cur.fetchall()
            logger.info(f"Encontrados {len(pagos)} pagos a operadores en PROGAIN")
            
            for pago in pagos:
                try:
                    # Mapear IDs
                    operador_id_firebase = self.mapeo_ids['entidades'].get(pago['operador_id'])
                    equipo_id_firebase = self.mapeo_ids['equipos'].get(pago['equipo_id']) if pago['equipo_id'] else None
                    
                    if not operador_id_firebase:
                        error_msg = f"No se encontró operador Firebase para pago (operador SQLite ID {pago['operador_id']})"
                        logger.warning(f"  ⚠ {error_msg}")
                        self.estadisticas['errores'].append(error_msg)
                        continue
                    
                    datos_pago = {
                        'operador_id': operador_id_firebase,
                        'equipo_id': equipo_id_firebase,
                        'fecha': pago['fecha'],
                        'monto': float(pago['monto']) if pago['monto'] else 0.0,
                        'horas': float(pago['horas']) if pago['horas'] else None,
                        'descripcion': pago['descripcion'] or '',
                        'comentario': pago['comentario'] or '',
                    }
                    
                    firebase_id = self.firebase_manager.registrar_pago_operador(datos_pago)
                    
                    if firebase_id:
                        self.estadisticas['pagos_migrados'] += 1
                        if self.estadisticas['pagos_migrados'] % 20 == 0:
                            logger.info(f"  → {self.estadisticas['pagos_migrados']} pagos migrados...")
                    else:
                        error_msg = f"Error al migrar pago ID {pago['id']}"
                        logger.error(f"  ✗ {error_msg}")
                        self.estadisticas['errores'].append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Excepción al migrar pago ID {pago['id']}: {e}"
                    logger.error(f"  ✗ {error_msg}")
                    self.estadisticas['errores'].append(error_msg)
            
            logger.info(f"Pagos a operadores migrados: {self.estadisticas['pagos_migrados']}/{len(pagos)}")
            
        except Exception as e:
            logger.error(f"Error al migrar pagos a operadores: {e}")
            raise
    
    def _mostrar_resumen(self):
        """Muestra un resumen de la migración."""
        logger.info("\n" + "="*80)
        logger.info("RESUMEN DE LA MIGRACIÓN")
        logger.info("="*80)
        logger.info(f"✓ Equipos migrados:              {self.estadisticas['equipos_migrados']}")
        logger.info(f"✓ Entidades migradas:            {self.estadisticas['entidades_migradas']}")
        logger.info(f"✓ Transacciones migradas:        {self.estadisticas['transacciones_migradas']}")
        logger.info(f"✓ Mantenimientos migrados:       {self.estadisticas['mantenimientos_migrados']}")
        logger.info(f"✓ Pagos a operadores migrados:   {self.estadisticas['pagos_migrados']}")
        logger.info(f"")
        logger.info(f"Total de registros migrados:     {sum([
            self.estadisticas['equipos_migrados'],
            self.estadisticas['entidades_migradas'],
            self.estadisticas['transacciones_migradas'],
            self.estadisticas['mantenimientos_migrados'],
            self.estadisticas['pagos_migrados']
        ])}")
        logger.info(f"")
        logger.info(f"Errores encontrados:             {len(self.estadisticas['errores'])}")
        
        if self.estadisticas['errores']:
            logger.info("\nLista de errores:")
            for i, error in enumerate(self.estadisticas['errores'][:10], 1):
                logger.info(f"  {i}. {error}")
            if len(self.estadisticas['errores']) > 10:
                logger.info(f"  ... y {len(self.estadisticas['errores']) - 10} errores más")


def main():
    """Función principal del script de migración."""
    print("="*80)
    print("MIGRACIÓN DE EQUIPOS DESDE PROGAIN A FIREBASE (EQUIPOS 4.0)")
    print("="*80)
    print("")
    
    # Solicitar ruta de la BD de PROGAIN
    ruta_bd_progain = input("Ingrese la ruta completa a la base de datos de PROGAIN (progain_database.db): ").strip()
    
    if not os.path.exists(ruta_bd_progain):
        print(f"\n✗ Error: No se encontró el archivo: {ruta_bd_progain}")
        return
    
    print(f"\n✓ Base de datos encontrada: {ruta_bd_progain}")
    
    # Cargar configuración de EQUIPOS 4.0
    try:
        config = cargar_configuracion()
        print("✓ Configuración de EQUIPOS 4.0 cargada")
    except Exception as e:
        print(f"\n✗ Error al cargar configuración: {e}")
        return
    
    # Inicializar Firebase Manager
    try:
        firebase_manager = FirebaseManager(
            credentials_path=config['firebase']['credentials_path'],
            project_id=config['firebase']['project_id']
        )
        print("✓ Conexión a Firebase establecida")
    except Exception as e:
        print(f"\n✗ Error al conectar con Firebase: {e}")
        print("  Asegúrese de que el archivo de credenciales existe y es válido.")
        return
    
    # Confirmar antes de continuar
    print("\n⚠ ADVERTENCIA: Este proceso migrará todos los datos de equipos desde PROGAIN a Firebase.")
    print("  - Se crearán nuevos documentos en Firestore")
    print("  - NO se modificará la base de datos de PROGAIN")
    print("  - El proceso puede tomar varios minutos")
    print("")
    confirmacion = input("¿Desea continuar? (sí/no): ").strip().lower()
    
    if confirmacion not in ['sí', 'si', 's', 'yes', 'y']:
        print("\nMigración cancelada por el usuario.")
        return
    
    print("\n" + "="*80)
    print("INICIANDO MIGRACIÓN...")
    print("="*80 + "\n")
    
    # Ejecutar migración
    migrador = MigradorEquipos(ruta_bd_progain, firebase_manager)
    exito = migrador.migrar_todo()
    
    if exito:
        print("\n✓ Migración completada exitosamente")
        print(f"  Log guardado en: {LOG_FILE}")
        
        # Crear backup inicial
        print("\nCreando backup inicial en SQLite...")
        try:
            backup_manager = BackupManager(
                ruta_backup=config['backup']['ruta_backup_sqlite'],
                firebase_manager=firebase_manager
            )
            if backup_manager.crear_backup():
                print(f"✓ Backup inicial creado en: {config['backup']['ruta_backup_sqlite']}")
            else:
                print("✗ Error al crear backup inicial")
        except Exception as e:
            print(f"✗ Error al crear backup: {e}")
    else:
        print("\n✗ La migración completó con errores")
        print(f"  Revise el log para más detalles: {LOG_FILE}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Migración interrumpida por el usuario")
    except Exception as e:
        logger.exception("Error fatal durante la migración")
        print(f"\n✗ Error fatal: {e}")
