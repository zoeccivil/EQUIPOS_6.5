"""
Script de mantenimiento:  Hace públicos todos los archivos existentes en Storage. 
Ejecutar UNA SOLA VEZ después de cambiar las reglas de Storage. 

Versión con selección de credenciales mediante diálogo de archivo. 
"""

import sys
import os
import json
from pathlib import Path
from tkinter import Tk, filedialog
from firebase_admin import credentials, initialize_app, storage


def seleccionar_archivo_credenciales():
    """Abre un diálogo para seleccionar el archivo de credenciales JSON."""
    root = Tk()
    root.withdraw()  # Ocultar ventana principal de Tkinter
    root.attributes('-topmost', True)  # Traer diálogo al frente
    
    print("Selecciona el archivo de credenciales de Firebase...")
    
    archivo = filedialog.askopenfilename(
        title="Selecciona el archivo de credenciales de Firebase",
        filetypes=[
            ("Archivos JSON", "*.json"),
            ("Todos los archivos", "*.*")
        ],
        initialdir=os.getcwd()
    )
    
    root.destroy()
    
    if not archivo:
        print("❌ No se seleccionó ningún archivo.  Cancelando...")
        sys.exit(0)
    
    return archivo


def cargar_config():
    """Carga config_equipos.json si existe, o devuelve configuración vacía."""
    try:
        config_path = "config_equipos.json"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            print("⚠️  config_equipos.json no encontrado, se solicitará configuración manualmente.")
            return {}
    except Exception as e: 
        print(f"⚠️  Error cargando config_equipos.json: {e}")
        return {}


def obtener_bucket_name(config, credentials_path):
    """Obtiene el bucket name desde config o extrae del archivo de credenciales."""
    # Intentar desde config primero
    bucket_name = config.get("firebase", {}).get("storage_bucket")
    
    if bucket_name:
        return bucket_name
    
    # Si no está en config, intentar extraer el project_id de las credenciales
    # y construir el bucket name estándar
    try:
        with open(credentials_path, "r", encoding="utf-8") as f:
            creds_data = json.load(f)
            project_id = creds_data. get("project_id")
            if project_id:
                # Intentar formato nuevo (. firebasestorage.app) primero
                bucket_candidate = f"{project_id}.firebasestorage.app"
                print(f"ℹ️  Bucket inferido desde credenciales: {bucket_candidate}")
                return bucket_candidate
    except Exception as e:
        print(f"⚠️  No se pudo extraer project_id de credenciales: {e}")
    
    return None


def main():
    # Seleccionar archivo de credenciales
    credentials_path = seleccionar_archivo_credenciales()
    print(f"✓ Credenciales:  {credentials_path}\n")
    
    # Cargar configuración
    config = cargar_config()
    
    # Obtener bucket name
    bucket_name = obtener_bucket_name(config, credentials_path)
    
    if not bucket_name: 
        print("\n❌ No se pudo determinar el nombre del bucket.")
        print("   Opciones:")
        print("   1. Agrega 'storage_bucket' en config_equipos.json")
        print("   2. Ejecuta primero diagnosticar_firebase.py para encontrar tu bucket")
        sys.exit(1)
    
    print(f"📦 Bucket: {bucket_name}")
    print(f"🔑 Credenciales:  {credentials_path}\n")
    
    # Validar que el archivo de credenciales existe
    if not os.path. exists(credentials_path):
        print(f"❌ El archivo seleccionado no existe: {credentials_path}")
        sys.exit(1)
    
    # Inicializar Firebase
    try:
        cred = credentials.Certificate(credentials_path)
        initialize_app(cred, {'storageBucket': bucket_name})
        bucket = storage.bucket()
        print(f"✅ Conectado a Storage:  {bucket.name}\n")
    except Exception as e:
        print(f"❌ Error inicializando Firebase: {e}")
        print("\nPosibles causas:")
        print("  • El archivo de credenciales no es válido")
        print("  • El nombre del bucket es incorrecto")
        print("  • La cuenta de servicio no tiene permisos de Storage")
        sys.exit(1)
    
    # Confirmar antes de proceder
    print("⚠️  ADVERTENCIA: Este script hará PÚBLICOS todos los archivos en Storage.")
    print("   Carpetas afectadas: conduces/, gastos/, pagos_operadores/")
    respuesta = input("\n¿Deseas continuar? (escribe 'SI' para confirmar): ")
    
    if respuesta.strip().upper() != 'SI':
        print("\n❌ Operación cancelada por el usuario.")
        sys.exit(0)
    
    print("\nHaciendo públicos archivos existentes.. .\n")
    
    # Carpetas a procesar
    carpetas = ["conduces", "gastos", "pagos_operadores"]
    
    total_ok = 0
    total_error = 0
    total_skip = 0
    
    for carpeta in carpetas: 
        print(f"📁 Procesando: {carpeta}/")
        
        try:
            blobs = list(bucket.list_blobs(prefix=f"{carpeta}/"))
            
            if not blobs:
                print(f"   ℹ️  Carpeta vacía o no existe\n")
                continue
            
            print(f"   Archivos encontrados: {len(blobs)}")
            
            for i, blob in enumerate(blobs, 1):
                try: 
                    # Hacer público el blob
                    blob.make_public()
                    print(f"   {i: 3d}. ✅ {blob.name}")
                    total_ok += 1
                except Exception as e:
                    # Algunos errores son esperados (archivos ya públicos)
                    error_msg = str(e).lower()
                    if "already" in error_msg or "exists" in error_msg or "public" in error_msg:
                        print(f"   {i:3d}. ⏭️  {blob.name} (ya público)")
                        total_skip += 1
                        total_ok += 1  # Contar como éxito
                    else:
                        print(f"   {i:3d}. ❌ {blob. name}:  {e}")
                        total_error += 1
            
            print()  # Línea en blanco entre carpetas
                    
        except Exception as e: 
            print(f"   ❌ Error listando {carpeta}: {e}\n")
            total_error += 1
    
    print(f"{'='*60}")
    print(f"✅ Archivos procesados correctamente: {total_ok}")
    print(f"⏭️  Archivos que ya eran públicos: {total_skip}")
    print(f"❌ Errores: {total_error}")
    print(f"{'='*60}\n")
    
    if total_ok > 0:
        print("✨ Proceso completado.  Las URLs ahora son públicas y permanentes.\n")
        print("Ejemplo de URL pública:")
        print(f"https://storage.googleapis.com/{bucket_name}/conduces/[año]/[mes]/[archivo]\n")
        print("Próximos pasos:")
        print("  1. Verifica las reglas de Storage en Firebase Console")
        print("  2. Reinicia tu aplicación para que use las URLs públicas")
        print("  3. Prueba abrir un adjunto desde la app\n")
    else:
        print("⚠️  No se procesaron archivos.  Verifica que existan archivos en Storage.\n")
    
    input("Presiona Enter para salir...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada por el usuario (Ctrl+C)")
        sys.exit(0)
    except Exception as e: 
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        input("\nPresiona Enter para salir...")
        sys.exit(1)