"""
Script de Migración: Adjuntos de Gastos a URLs Firmadas
Genera URLs firmadas para gastos (igual que los conduces de alquileres)

Uso:
    python migrar_adjuntos_gastos.py
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json

# FIX: Forzar UTF-8 en Windows para evitar errores de Unicode
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            f'migracion_adjuntos_gastos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            encoding='utf-8'
        ),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def seleccionar_credenciales() -> str:
    """Abre un diálogo para seleccionar el archivo de credenciales de Firebase"""
    try:
        from PyQt6.QtWidgets import QApplication, QFileDialog
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Seleccionar archivo de credenciales de Firebase",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path and os.path.exists(file_path):
            logger.info(f"✅ Credenciales seleccionadas: {file_path}")
            return file_path
        else:
            logger.error("❌ No se seleccionó archivo de credenciales")
            return None
            
    except ImportError:
        logger.error("❌ PyQt6 no está instalado. Usando modo texto.")
        return seleccionar_credenciales_texto()
    except Exception as e:
        logger.error(f"❌ Error en diálogo: {e}")
        return seleccionar_credenciales_texto()


def seleccionar_credenciales_texto() -> str:
    """Solicita la ruta de credenciales por texto (fallback)"""
    print("\n" + "=" * 80)
    print("SELECCIÓN DE CREDENCIALES DE FIREBASE")
    print("=" * 80)
    
    json_files = [f for f in os.listdir('.') if f.endswith('.json')]
    
    if json_files:
        print("\nArchivos JSON encontrados:")
        for i, archivo in enumerate(json_files, 1):
            print(f"  {i}. {archivo}")
        print(f"  {len(json_files) + 1}. Otra ruta")
        
        try:
            opcion = int(input("\nSeleccione una opción: ").strip())
            if 1 <= opcion <= len(json_files):
                return json_files[opcion - 1]
        except ValueError:
            pass
    
    ruta = input("\nIngrese la ruta completa del archivo de credenciales: ").strip()
    
    if os.path.exists(ruta):
        return ruta
    else:
        logger.error(f"❌ Archivo no encontrado: {ruta}")
        return None


def diagnosticar_credenciales(credentials_path: str):
    """Muestra información del archivo de credenciales para diagnóstico"""
    try:
        print("\n" + "=" * 80)
        print("🔍 DIAGNÓSTICO DE ARCHIVO DE CREDENCIALES")
        print("=" * 80)
        print(f"Ruta: {credentials_path}")
        print(f"Existe: {os.path.exists(credentials_path)}")
        print(f"Tamaño: {os.path.getsize(credentials_path)} bytes")
        
        with open(credentials_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"Primeros 200 caracteres:\n{content[:200]}")
            
            try:
                f.seek(0)
                data = json.load(f)
                print("\n✅ Es un JSON válido")
                print(f"Campos encontrados: {list(data.keys())}")
                
                if 'type' in data:
                    print(f"Campo 'type': {data['type']}")
                else:
                    print("❌ NO tiene campo 'type'")
                
                if 'project_id' in data:
                    print(f"Campo 'project_id': {data['project_id']}")
                else:
                    print("❌ NO tiene campo 'project_id'")
                    
            except json.JSONDecodeError as e:
                print(f"❌ NO es un JSON válido: {e}")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}")


def crear_config_temporal(credentials_path: str) -> dict:
    """Crea una configuración temporal para Firebase"""
    try:
        with open(credentials_path, 'r', encoding='utf-8') as f:
            creds = json.load(f)
        
        # Validar que sea un archivo de servicio válido
        if creds.get('type') != 'service_account':
            logger.error("❌ ERROR: El archivo no es un certificado de servicio válido")
            logger.error("   Debe contener un campo 'type' con valor 'service_account'")
            return None
        
        # Validar campos requeridos
        campos_requeridos = ['project_id', 'private_key', 'client_email']
        campos_faltantes = [c for c in campos_requeridos if not creds.get(c)]
        
        if campos_faltantes:
            logger.error(f"❌ ERROR: Faltan campos requeridos: {', '.join(campos_faltantes)}")
            return None
        
        project_id = creds.get('project_id')
        storage_bucket = f"{project_id}.firebasestorage.app"
        
        config = {
            "firebase": {
                "credentials_path": credentials_path,
                "project_id": project_id,
                "storage_bucket": storage_bucket
            },
            "app": {
                "proyecto_id": 8
            }
        }
        
        logger.info(f"✅ Credenciales válidas")
        logger.info(f"✅ Project ID: {project_id}")
        logger.info(f"✅ Storage Bucket: {storage_bucket}")
        logger.info(f"✅ Service Account: {creds.get('client_email', 'N/A')}")
        
        return config
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error: El archivo no es un JSON válido: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error leyendo credenciales: {e}")
        return None


class MigradorAdjuntosGastos:
    """Migra adjuntos de gastos generando URLs firmadas (como conduces)"""
    
    def __init__(self, config: dict):
        self.config = config
        self.fm = None
        self.sm = None
        self.gastos_procesados = 0
        self.gastos_migrados = 0
        self.gastos_sin_adjunto = 0
        self.gastos_ya_tienen_url = 0
        self.errores = []
    
    def inicializar(self) -> bool:
        """Inicializa conexión con Firebase"""
        try:
            logger.info("\n" + "=" * 80)
            logger.info("MIGRACIÓN: Generar URLs Firmadas para Gastos")
            logger.info("=" * 80)
            
            try:
                from firebase_manager import FirebaseManager
                from storage_manager import StorageManager
            except ImportError as e:
                logger.error(f"❌ Error importando módulos: {e}")
                return False
            
            logger.info("\n🔥 Conectando con Firebase...")
            credentials_path = self.config['firebase']['credentials_path']
            project_id = self.config['firebase']['project_id']
            
            self.fm = FirebaseManager(credentials_path, project_id)
            
            logger.info("☁️  Conectando con Storage...")
            self.sm = StorageManager(self.config)
            
            if not self.sm or not self.sm.bucket:
                logger.error("❌ Storage no disponible")
                return False
            
            logger.info(f"✅ Conectado a bucket: {self.sm.bucket.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando: {e}", exc_info=True)
            return False
    
    def obtener_gastos_con_adjuntos(self) -> List[Dict]:
        """Obtiene todos los gastos que tienen adjuntos"""
        try:
            logger.info("\n📋 Obteniendo gastos con adjuntos...")
            
            gastos_ref = self.fm.db.collection("gastos")
            docs = gastos_ref.stream()
            
            gastos_con_adjuntos = []
            total = 0
            
            for doc in docs:
                total += 1
                data = doc.to_dict()
                data['id'] = doc.id
                
                if data.get("archivo_storage_path"):
                    gastos_con_adjuntos.append(data)
            
            logger.info(f"✅ Total de gastos: {total}")
            logger.info(f"✅ Gastos con adjuntos: {len(gastos_con_adjuntos)}")
            
            return gastos_con_adjuntos
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo gastos: {e}", exc_info=True)
            return []
    
    def generar_url_firmada(self, storage_path: str) -> Tuple[bool, str]:
        """
        Genera URL firmada (como los conduces) con validez de 7 días
        """
        try:
            blob = self.sm.bucket.blob(storage_path)
            
            if not blob.exists():
                return False, f"Archivo no existe: {storage_path}"
            
            # ✅ Generar URL firmada de 7 días (como conduces)
            url_firmada = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=7),
                method="GET"
            )
            
            logger.info(f"   ✅ URL firmada generada (válida 7 días)")
            return True, url_firmada
            
        except Exception as e:
            error_msg = f"Error generando URL {storage_path}: {e}"
            logger.error(f"   ❌ {error_msg}")
            return False, error_msg
    
    def actualizar_firestore(self, gasto_id: str, url_firmada: str) -> bool:
        """Actualiza con URL firmada (como conduce_url)"""
        try:
            gasto_ref = self.fm.db.collection("gastos").document(gasto_id)
            
            # ✅ Guardar URL firmada (como conduce_url)
            gasto_ref.update({
                "archivo_url": url_firmada,  # ✅ Campo con URL firmada
                "archivo_url_generada": datetime.now().isoformat(),
                "archivo_url_expira_dias": 7
            })
            
            logger.info(f"   ✅ URL firmada guardada en Firestore")
            return True
            
        except Exception as e:
            logger.error(f"   ❌ Error actualizando Firestore: {e}")
            return False
    
    def migrar_gasto(self, gasto: Dict) -> bool:
        """Migra un gasto generando URL firmada (como conduces)"""
        try:
            gasto_id = gasto['id']
            storage_path = gasto.get("archivo_storage_path")
            
            if not storage_path:
                self.gastos_sin_adjunto += 1
                return True
            
            logger.info(f"\n📄 Gasto ID: {gasto_id}")
            desc = gasto.get('descripcion', 'N/A')
            if len(desc) > 50:
                desc = desc[:50] + "..."
            logger.info(f"   Descripción: {desc}")
            logger.info(f"   Storage Path: {storage_path}")
            
            # ✅ Verificar si ya tiene URL firmada
            if gasto.get("archivo_url"):
                logger.info(f"   ✓ Ya tiene URL firmada")
                self.gastos_ya_tienen_url += 1
                return True
            
            # ✅ Generar URL firmada
            exito, url_firmada = self.generar_url_firmada(storage_path)
            
            if exito:
                # ✅ Guardar en Firestore
                if self.actualizar_firestore(gasto_id, url_firmada):
                    logger.info(f"   ✅ MIGRADO EXITOSAMENTE")
                    self.gastos_migrados += 1
                    return True
                else:
                    self.errores.append(f"Gasto {gasto_id}: Error actualizando Firestore")
                    return False
            else:
                self.errores.append(f"Gasto {gasto_id}: {url_firmada}")
                return False
                
        except Exception as e:
            error_msg = f"Error migrando gasto {gasto.get('id', 'unknown')}: {e}"
            logger.error(f"   ❌ {error_msg}")
            self.errores.append(error_msg)
            return False
    
    def generar_reporte(self):
        """Genera reporte final"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 REPORTE FINAL DE MIGRACIÓN")
        logger.info("=" * 80)
        logger.info(f"✅ Gastos procesados:      {self.gastos_procesados}")
        logger.info(f"✅ Gastos migrados:        {self.gastos_migrados}")
        logger.info(f"📋 Ya tenían URL:          {self.gastos_ya_tienen_url}")
        logger.info(f"⚠️  Sin adjunto:           {self.gastos_sin_adjunto}")
        logger.info(f"❌ Errores:                {len(self.errores)}")
        
        if self.errores:
            logger.info("\n❌ ERRORES ENCONTRADOS:")
            for i, error in enumerate(self.errores, 1):
                logger.error(f"   {i}. {error}")
        
        logger.info("\n" + "=" * 80)
        
        if self.gastos_procesados > 0:
            exito = ((self.gastos_migrados + self.gastos_ya_tienen_url) / self.gastos_procesados) * 100
            logger.info(f"🎯 Tasa de éxito: {exito:.1f}%")
        
        logger.info("=" * 80)
        logger.info("\n💡 NOTA: Las URLs firmadas expiran en 7 días.")
        logger.info("   Asegúrate de que tu app regenere las URLs antes de que expiren.")
    
    def ejecutar(self):
        """Ejecuta la migración completa"""
        try:
            if not self.inicializar():
                logger.error("❌ No se pudo inicializar. Abortando.")
                return False
            
            gastos = self.obtener_gastos_con_adjuntos()
            
            if not gastos:
                logger.info("✅ No hay gastos con adjuntos para migrar")
                return True
            
            logger.info(f"\n⚠️  Se generarán URLs firmadas para {len(gastos)} gastos")
            respuesta = input("\n¿Continuar con la migración? (s/N): ").strip().lower()
            
            if respuesta != 's':
                logger.info("❌ Migración cancelada por el usuario")
                return False
            
            logger.info("\n🚀 Iniciando migración...")
            
            for i, gasto in enumerate(gastos, 1):
                logger.info(f"\n[{i}/{len(gastos)}]")
                self.migrar_gasto(gasto)
                self.gastos_procesados += 1
            
            self.generar_reporte()
            
            return True
            
        except KeyboardInterrupt:
            logger.warning("\n⚠️  Migración interrumpida")
            self.generar_reporte()
            return False
        except Exception as e:
            logger.error(f"❌ Error fatal: {e}", exc_info=True)
            return False


def main():
    """Función principal"""
    try:
        credentials_path = seleccionar_credenciales()
        
        if not credentials_path:
            logger.error("❌ No se seleccionaron credenciales. Abortando.")
            input("\nPresione ENTER para salir...")
            sys.exit(1)
        
        # Diagnóstico
        diagnosticar_credenciales(credentials_path)
        
        # Confirmar
        respuesta = input("\n¿El archivo parece correcto? ¿Continuar? (s/N): ").strip().lower()
        if respuesta != 's':
            print("Abortado por el usuario")
            sys.exit(0)
        
        config = crear_config_temporal(credentials_path)
        
        if not config:
            logger.error("❌ No se pudo crear configuración. Abortando.")
            input("\nPresione ENTER para salir...")
            sys.exit(1)
        
        migrador = MigradorAdjuntosGastos(config)
        exito = migrador.ejecutar()
        
        if exito:
            logger.info("\n✅ Migración completada exitosamente")
            input("\nPresione ENTER para salir...")
            sys.exit(0)
        else:
            logger.error("\n❌ Migración completada con errores")
            input("\nPresione ENTER para salir...")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        input("\nPresione ENTER para salir...")
        sys.exit(1)


if __name__ == "__main__":
    main()