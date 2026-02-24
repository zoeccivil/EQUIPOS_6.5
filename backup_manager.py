"""
Gestor de backups SQLite para EQUIPOS 4.0
Crea backups automáticos de los datos de Firebase en SQLite local
"""

import sqlite3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from firebase_manager import FirebaseManager

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Gestiona backups automáticos de Firestore a SQLite.
    """

    def __init__(self, ruta_backup: str, firebase_manager: FirebaseManager):
        """
        Inicializa el gestor de backups.

        Args:
            ruta_backup: Ruta completa al archivo SQLite de backup
            firebase_manager: Instancia del FirebaseManager para leer datos
        """
        self.ruta_backup = ruta_backup
        self.firebase_manager = firebase_manager

        # Crear directorio si no existe
        directorio = os.path.dirname(ruta_backup)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio)
            logger.info(f"Directorio de backup creado: {directorio}")

        # Crear o verificar estructura de BD
        self._crear_estructura_bd()

    def _crear_estructura_bd(self):
        """Crea la estructura de tablas en la BD de backup."""
        try:
            conn = sqlite3.connect(self.ruta_backup)
            cur = conn.cursor()

            # Tabla de equipos
            cur.execute("""
                CREATE TABLE IF NOT EXISTS equipos (
                    id TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    marca TEXT,
                    modelo TEXT,
                    categoria TEXT,
                    placa TEXT,
                    ficha TEXT,
                    activo INTEGER DEFAULT 1,
                    fecha_creacion TEXT,
                    fecha_modificacion TEXT
                )
            """)

            # Tabla de transacciones (unifica alquileres como 'Ingreso' y gastos como 'Gasto')
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transacciones (
                    id TEXT PRIMARY KEY,
                    tipo TEXT NOT NULL CHECK(tipo IN ('Ingreso', 'Gasto')),
                    equipo_id TEXT,
                    cliente_id TEXT,
                    operador_id TEXT,
                    fecha TEXT NOT NULL,
                    monto REAL NOT NULL,
                    descripcion TEXT,
                    comentario TEXT,
                    horas REAL,
                    precio_por_hora REAL,
                    conduce TEXT,
                    ubicacion TEXT,
                    pagado INTEGER DEFAULT 0,
                    categoria TEXT,
                    subcategoria TEXT,
                    fecha_creacion TEXT,
                    fecha_modificacion TEXT
                )
            """)

            # Tabla de entidades (clientes y operadores)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS entidades (
                    id TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    tipo TEXT NOT NULL CHECK(tipo IN ('Cliente', 'Operador')),
                    telefono TEXT,
                    cedula TEXT,
                    activo INTEGER DEFAULT 1,
                    fecha_creacion TEXT,
                    fecha_modificacion TEXT
                )
            """)

            # Tabla de mantenimientos
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mantenimientos (
                    id TEXT PRIMARY KEY,
                    equipo_id TEXT NOT NULL,
                    fecha TEXT,
                    descripcion TEXT,
                    tipo TEXT,
                    costo REAL,
                    odometro_horas REAL,
                    odometro_km REAL,
                    notas TEXT,
                    proximo_tipo TEXT,
                    proximo_valor REAL,
                    proximo_fecha TEXT,
                    fecha_creacion TEXT,
                    fecha_modificacion TEXT
                )
            """)

            # Tabla de pagos a operadores
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pagos_operadores (
                    id TEXT PRIMARY KEY,
                    operador_id TEXT NOT NULL,
                    equipo_id TEXT,
                    fecha TEXT NOT NULL,
                    monto REAL NOT NULL,
                    horas REAL,
                    descripcion TEXT,
                    comentario TEXT,
                    fecha_creacion TEXT,
                    fecha_modificacion TEXT
                )
            """)

            # Tabla de metadata del backup
            cur.execute("""
                CREATE TABLE IF NOT EXISTS backup_metadata (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    fecha_backup TEXT NOT NULL,
                    version TEXT,
                    registros_equipos INTEGER,
                    registros_transacciones INTEGER,
                    registros_entidades INTEGER,
                    registros_mantenimientos INTEGER,
                    registros_pagos_operadores INTEGER
                )
            """)

            # Índices para mejorar rendimiento
            cur.execute("CREATE INDEX IF NOT EXISTS idx_transacciones_fecha ON transacciones(fecha)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_transacciones_equipo ON transacciones(equipo_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_mantenimientos_equipo ON mantenimientos(equipo_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pagos_operador ON pagos_operadores(operador_id)")

            conn.commit()
            conn.close()
            logger.info(f"Estructura de BD de backup creada en: {self.ruta_backup}")

        except Exception as e:
            logger.error(f"Error al crear estructura de BD: {e}")
            raise

    def crear_backup(self) -> bool:
        """
        Crea un backup completo de todos los datos de Firebase.

        Returns:
            True si el backup se creó exitosamente, False en caso contrario
        """
        try:
            logger.info("Iniciando proceso de backup...")

            conn = sqlite3.connect(self.ruta_backup)
            cur = conn.cursor()

            # Limpiar tablas existentes
            cur.execute("DELETE FROM equipos")
            cur.execute("DELETE FROM transacciones")
            cur.execute("DELETE FROM entidades")
            cur.execute("DELETE FROM mantenimientos")
            cur.execute("DELETE FROM pagos_operadores")

            # Backup de equipos
            equipos = self.firebase_manager.obtener_equipos(activo=None)  # Todos los equipos
            count_equipos = 0
            for equipo in equipos:
                cur.execute("""
                    INSERT INTO equipos 
                    (id, nombre, marca, modelo, categoria, placa, ficha, activo, fecha_creacion, fecha_modificacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    equipo.get('id'),
                    equipo.get('nombre'),
                    equipo.get('marca'),
                    equipo.get('modelo'),
                    equipo.get('categoria'),
                    equipo.get('placa'),
                    equipo.get('ficha'),
                    1 if equipo.get('activo', True) else 0,
                    self._datetime_to_str(equipo.get('fecha_creacion')),
                    self._datetime_to_str(equipo.get('fecha_modificacion'))
                ))
                count_equipos += 1

            logger.info(f"Backup de {count_equipos} equipos completado")

            # Backup de transacciones = alquileres (Ingreso) + gastos (Gasto)
            count_transacciones = 0

            # a) Alquileres -> tipo 'Ingreso'
            try:
                alquileres = self.firebase_manager.obtener_alquileres()  # todos
            except TypeError:
                # por compatibilidad si requiere dict de filtros
                alquileres = self.firebase_manager.obtener_alquileres({}) or []
            for alq in (alquileres or []):
                cur.execute("""
                    INSERT INTO transacciones 
                    (id, tipo, equipo_id, cliente_id, operador_id, fecha, monto, descripcion, 
                     comentario, horas, precio_por_hora, conduce, ubicacion, pagado, 
                     categoria, subcategoria, fecha_creacion, fecha_modificacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alq.get('id') or alq.get('transaccion_id'),
                    'Ingreso',
                    alq.get('equipo_id'),
                    alq.get('cliente_id'),
                    alq.get('operador_id'),
                    alq.get('fecha'),
                    float(alq.get('monto', 0) or 0),
                    alq.get('descripcion'),
                    alq.get('comentario'),
                    alq.get('horas'),
                    alq.get('precio_por_hora'),
                    alq.get('conduce'),
                    alq.get('ubicacion'),
                    1 if alq.get('pagado', False) else 0,
                    None,
                    None,
                    self._datetime_to_str(alq.get('fecha_creacion')),
                    self._datetime_to_str(alq.get('fecha_modificacion')),
                ))
                count_transacciones += 1

            # b) Gastos -> tipo 'Gasto'
            try:
                gastos = self.firebase_manager.obtener_gastos({}) or []
            except TypeError:
                # si la firma difiere, intenta sin argumentos
                gastos = self.firebase_manager.obtener_gastos({}) or []
            for g in (gastos or []):
                cur.execute("""
                    INSERT INTO transacciones 
                    (id, tipo, equipo_id, cliente_id, operador_id, fecha, monto, descripcion, 
                     comentario, horas, precio_por_hora, conduce, ubicacion, pagado, 
                     categoria, subcategoria, fecha_creacion, fecha_modificacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    g.get('id'),
                    'Gasto',
                    g.get('equipo_id'),
                    None,
                    None,
                    g.get('fecha'),
                    float(g.get('monto', 0) or 0),
                    g.get('descripcion'),
                    g.get('comentario'),
                    None,
                    None,
                    None,
                    None,
                    0,
                    str(g.get('categoria_id')) if g.get('categoria_id') not in (None, "") else None,
                    str(g.get('subcategoria_id')) if g.get('subcategoria_id') not in (None, "") else None,
                    self._datetime_to_str(g.get('created_at')) or self._datetime_to_str(g.get('fecha_creacion')),
                    self._datetime_to_str(g.get('updated_at')) or self._datetime_to_str(g.get('fecha_modificacion')),
                ))
                count_transacciones += 1

            logger.info(f"Backup de {count_transacciones} transacciones (ingresos+gastos) completado")

            # Backup de entidades
            entidades = self.firebase_manager.obtener_entidades(activo=None)  # Todas las entidades
            count_entidades = 0
            for entidad in entidades:
                cur.execute("""
                    INSERT INTO entidades 
                    (id, nombre, tipo, telefono, cedula, activo, fecha_creacion, fecha_modificacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entidad.get('id'),
                    entidad.get('nombre'),
                    entidad.get('tipo'),
                    entidad.get('telefono'),
                    entidad.get('cedula'),
                    1 if entidad.get('activo', True) else 0,
                    self._datetime_to_str(entidad.get('fecha_creacion')),
                    self._datetime_to_str(entidad.get('fecha_modificacion'))
                ))
                count_entidades += 1

            logger.info(f"Backup de {count_entidades} entidades completado")

            # Backup de mantenimientos
            try:
                mantenimientos = self.firebase_manager.obtener_mantenimientos()
            except TypeError:
                # si firma exige parámetro opcional, llamar sin filtro
                mantenimientos = self.firebase_manager.obtener_mantenimientos(None)
            count_mantenimientos = 0
            for mant in (mantenimientos or []):
                cur.execute("""
                    INSERT INTO mantenimientos 
                    (id, equipo_id, fecha, descripcion, tipo, costo, odometro_horas, 
                     odometro_km, notas, proximo_tipo, proximo_valor, proximo_fecha,
                     fecha_creacion, fecha_modificacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mant.get('id'),
                    mant.get('equipo_id'),
                    mant.get('fecha') or self._datetime_to_str(mant.get('fecha')),
                    mant.get('descripcion'),
                    mant.get('tipo'),
                    mant.get('costo') or mant.get('valor'),
                    mant.get('odometro_horas'),
                    mant.get('odometro_km'),
                    mant.get('notas'),
                    mant.get('proximo_tipo'),
                    mant.get('proximo_valor'),
                    self._datetime_to_str(mant.get('proximo_fecha')),
                    self._datetime_to_str(mant.get('fecha_creacion')),
                    self._datetime_to_str(mant.get('fecha_modificacion'))
                ))
                count_mantenimientos += 1

            logger.info(f"Backup de {count_mantenimientos} mantenimientos completado")

            # Backup de pagos a operadores
            try:
                pagos = self.firebase_manager.obtener_pagos_operadores({})  # sin filtro
            except TypeError:
                pagos = self.firebase_manager.obtener_pagos_operadores({})  # firma actual requiere dict
            count_pagos = 0
            for pago in (pagos or []):
                cur.execute("""
                    INSERT INTO pagos_operadores 
                    (id, operador_id, equipo_id, fecha, monto, horas, descripcion, 
                     comentario, fecha_creacion, fecha_modificacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pago.get('id'),
                    pago.get('operador_id'),
                    pago.get('equipo_id'),
                    pago.get('fecha'),
                    float(pago.get('monto', 0) or 0),
                    pago.get('horas'),
                    pago.get('descripcion'),
                    pago.get('comentario'),
                    self._datetime_to_str(pago.get('fecha_creacion')),
                    self._datetime_to_str(pago.get('fecha_modificacion'))
                ))
                count_pagos += 1

            logger.info(f"Backup de {count_pagos} pagos a operadores completado")

            # Guardar metadata del backup
            cur.execute("DELETE FROM backup_metadata")
            cur.execute("""
                INSERT INTO backup_metadata 
                (id, fecha_backup, version, registros_equipos, registros_transacciones,
                 registros_entidades, registros_mantenimientos, registros_pagos_operadores)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                "4.0.0",
                count_equipos,
                count_transacciones,
                count_entidades,
                count_mantenimientos,
                count_pagos
            ))

            conn.commit()
            conn.close()

            logger.info(f"Backup completado exitosamente en: {self.ruta_backup}")
            logger.info(f"Total de registros: {count_equipos + count_transacciones + count_entidades + count_mantenimientos + count_pagos}")

            return True

        except Exception as e:
            logger.error(f"Error al crear backup: {e}", exc_info=True)
            return False

    def _datetime_to_str(self, dt: Any) -> Optional[str]:
        """
        Convierte un datetime a string ISO 8601.
        Maneja objetos datetime de Python y timestamps de Firestore.
        """
        if dt is None:
            return None

        if isinstance(dt, datetime):
            return dt.isoformat()

        # Si es un timestamp de Firestore (objeto con isoformat)
        if hasattr(dt, 'isoformat'):
            try:
                return dt.isoformat()
            except Exception:
                pass

        # Si ya es string
        if isinstance(dt, str):
            return dt

        return None

    def obtener_info_backup(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene información sobre el último backup realizado.

        Returns:
            Diccionario con información del backup o None si no existe
        """
        try:
            if not os.path.exists(self.ruta_backup):
                return None

            conn = sqlite3.connect(self.ruta_backup)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("SELECT * FROM backup_metadata WHERE id = 1")
            row = cur.fetchone()
            conn.close()

            if row:
                return {
                    'fecha_backup': row['fecha_backup'],
                    'version': row['version'],
                    'registros_equipos': row['registros_equipos'],
                    'registros_transacciones': row['registros_transacciones'],
                    'registros_entidades': row['registros_entidades'],
                    'registros_mantenimientos': row['registros_mantenimientos'],
                    'registros_pagos_operadores': row['registros_pagos_operadores'],
                    'tamanio_archivo': os.path.getsize(self.ruta_backup)
                }

            return None

        except Exception as e:
            logger.error(f"Error al obtener info de backup: {e}")
            return None

    def debe_crear_backup(self, frecuencia: str, hora_ejecucion: str, ultimo_backup: Optional[str]) -> bool:
        """
        Determina si es momento de crear un backup automático.

        Args:
            frecuencia: 'diario', 'semanal', etc.
            hora_ejecucion: Hora en formato HH:MM
            ultimo_backup: Timestamp del último backup (ISO format) o None

        Returns:
            True si debe crear backup, False en caso contrario
        """
        try:
            ahora = datetime.now()
            hora_actual = ahora.strftime("%H:%M")

            # Si no hay backup previo, crear uno
            if not ultimo_backup:
                return True

            ultimo_backup_dt = datetime.fromisoformat(ultimo_backup)

            # Si la frecuencia es diaria
            if frecuencia.lower() == "diario":
                # Verificar que haya pasado al menos un día
                if (ahora - ultimo_backup_dt).days >= 1:
                    # Verificar que sea la hora programada (con margen de 1 hora)
                    if self._es_hora_aproximada(hora_actual, hora_ejecucion, margen_minutos=60):
                        return True

            # TODO: Implementar otras frecuencias (semanal, mensual, etc.)

            return False

        except Exception as e:
            logger.error(f"Error al verificar si debe crear backup: {e}")
            return False

    def _es_hora_aproximada(self, hora_actual: str, hora_objetivo: str, margen_minutos: int = 60) -> bool:
        """
        Verifica si la hora actual está dentro del margen de la hora objetivo.

        Args:
            hora_actual: Hora actual en formato HH:MM
            hora_objetivo: Hora objetivo en formato HH:MM
            margen_minutos: Margen de tiempo en minutos

        Returns:
            True si está dentro del margen, False en caso contrario
        """
        try:
            # Convertir a minutos desde medianoche
            h_actual, m_actual = map(int, hora_actual.split(':'))
            minutos_actual = h_actual * 60 + m_actual

            h_objetivo, m_objetivo = map(int, hora_objetivo.split(':'))
            minutos_objetivo = h_objetivo * 60 + m_objetivo

            diferencia = abs(minutos_actual - minutos_objetivo)

            return diferencia <= margen_minutos

        except Exception as e:
            logger.error(f"Error al comparar horas: {e}")
            return False


if __name__ == "__main__":
    # Pruebas básicas
    logging.basicConfig(level=logging.INFO)
    print("BackupManager - Módulo de backups SQLite para EQUIPOS 4.0")