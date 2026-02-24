#!/usr/bin/env python3
"""
Script para migrar conduces de alquileres al formato de gastos: 
- Lee la colección 'alquileres'
- Convierte 'archivoUrl' (del conduce) a 'archivo_storage_path'
- Backup opcional
"""

import firebase_admin
from firebase_admin import credentials, firestore, storage
from tkinter import Tk, filedialog, messagebox
import sys
from pathlib import Path
import urllib.parse

def seleccionar_credenciales():
    """Abre un diálogo para seleccionar el archivo de credenciales JSON."""
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    print("Selecciona el archivo de credenciales de Firebase...")
    
    archivo_credenciales = filedialog.askopenfilename(
        title="Selecciona las credenciales de Firebase",
        filetypes=[
            ("Archivos JSON", "*.json"),
            ("Todos los archivos", "*.*")
        ]
    )
    
    root.destroy()
    
    if not archivo_credenciales:
        print("❌ No se seleccionó ningún archivo.")
        sys.exit(1)
    
    print(f"✓ Credenciales:  {archivo_credenciales}\n")
    return archivo_credenciales

def seleccionar_carpeta_backup():
    """Selecciona carpeta para backup (opcional)."""
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    hacer_backup = messagebox.askyesno(
        "Backup",
        "¿Deseas hacer un backup local de los archivos antes de migrar?\n\n" +
        "Recomendado por seguridad."
    )
    
    carpeta = None
    if hacer_backup: 
        carpeta = filedialog. askdirectory(title="Selecciona carpeta para backup")
    
    root.destroy()
    return carpeta

def inicializar_firebase(ruta_credenciales):
    """Inicializa Firebase."""
    try:
        cred = credentials.Certificate(ruta_credenciales)
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'equipos-zoec. firebasestorage.app'
        })
        print("✓ Firebase inicializado\n")
        return True
    except Exception as e:
        print(f"❌ Error:  {e}")
        return False

def hacer_backup(bucket, carpeta_destino):
    """Descarga backup de todos los archivos de conduces/."""
    print("\n" + "="*60)
    print("BACKUP DE ARCHIVOS")
    print("="*60)
    print()
    
    blobs = list(bucket.list_blobs(prefix="conduces/"))
    
    if not blobs:
        print("⚠️  No se encontraron archivos")
        return
    
    print(f"✓ Encontrados {len(blobs)} archivos\n")
    
    total_descargados = 0
    
    for i, blob in enumerate(blobs, 1):
        try:
            # conduces/2025/11/00620.jpeg
            partes = blob.name.split('/')
            
            if len(partes) < 4:
                continue
            
            year = partes[1]
            month = partes[2]
            filename = partes[3]
            
            # Crear estructura de carpetas
            carpeta_archivo = Path(carpeta_destino) / "conduces" / year / month
            carpeta_archivo.mkdir(parents=True, exist_ok=True)
            
            ruta_archivo = carpeta_archivo / filename
            
            print(f"[{i}/{len(blobs)}] {blob.name}")
            blob.download_to_filename(str(ruta_archivo))
            
            total_descargados += 1
            
        except Exception as e:
            print(f"   ❌ Error:  {e}")
    
    print(f"\n✅ {total_descargados} archivos descargados")
    print(f"📁 Guardados en: {carpeta_destino}/conduces/\n")

def extraer_storage_path_de_url(url:  str) -> str | None:
    """
    Extrae el storage_path de una URL antigua.
    
    De: https://firebasestorage.googleapis.com/v0/b/. ../o/conduces%2F2025%2F11%2F00620.jpeg?alt=media&token=... 
    A: conduces/2025/11/00620.jpeg
    """
    try:
        if '/o/' in url:
            # Extraer la parte después de /o/ y antes de ? 
            parte = url.split('/o/')[1].split('?')[0]
            # Decodificar URL encoding
            decoded = urllib.parse.unquote(parte)
            return decoded
        elif '/conduces/' in url:
            # Ya está en formato simple
            parte = url.split('/conduces/', 1)[1].split('?')[0]
            return f"conduces/{parte}"
        return None
    except Exception as e: 
        print(f"   ⚠️  Error extrayendo path de URL: {e}")
        return None

def migrar_firestore_alquileres(db, hacer_commit=True):
    """
    Actualiza Firestore (colección 'alquileres'):
    Convierte archivoUrl (del conduce) a archivo_storage_path. 
    
    Args:
        db: Cliente de Firestore
        hacer_commit: Si True, actualiza Firestore.  Si False, solo simula.
    """
    print("\n" + "="*60)
    print("MIGRACIÓN DE FIRESTORE - ALQUILERES (CONDUCES)")
    print("="*60)
    print()
    
    if not hacer_commit:
        print("⚠️  MODO SIMULACIÓN (no se modificará Firestore)\n")
    
    total_procesados = 0
    total_actualizados = 0
    total_sin_url = 0
    total_errores = 0
    total_ya_migrados = 0
    
    # Obtener TODOS los documentos de alquileres
    docs = db.collection('alquileres').stream()
    
    for doc in docs:
        total_procesados += 1
        data = doc.to_dict()
        
        # Verificar si ya tiene conduce_storage_path (ya migrado)
        if 'conduce_storage_path' in data and data['conduce_storage_path']:
            if total_procesados <= 5: 
                print(f"[{total_procesados}] {doc.id}:  Ya migrado ✓")
            total_ya_migrados += 1
            continue
        
        # Buscar URL del conduce (puede estar en diferentes campos)
        # Común: 'conducUrl', 'archivoUrl', 'conduce_url', etc.
        url_antigua = None
        campo_url = None
        
        for posible_campo in ['conducUrl', 'conduce_url', 'archivoUrl', 'archivo_url', 'url_conduce']:
            if posible_campo in data and data[posible_campo]: 
                url_antigua = data[posible_campo]
                campo_url = posible_campo
                break
        
        if not url_antigua:
            total_sin_url += 1
            if total_procesados <= 5:
                print(f"[{total_procesados}] {doc.id}:  Sin URL de conduce")
            continue
        
        # Verificar que la URL sea de conduces (no de otro tipo)
        if 'conduces/' not in url_antigua:
            if total_procesados <= 5:
                print(f"[{total_procesados}] {doc.id}: URL no es de conduces")
            continue
        
        # Extraer storage_path
        storage_path = extraer_storage_path_de_url(url_antigua)
        
        if not storage_path: 
            print(f"[{total_procesados}] {doc.id}:  No se pudo extraer storage_path")
            total_errores += 1
            continue
        
        # Mostrar primeros 10
        if total_procesados <= 10:
            print(f"\n[{total_procesados}] {doc.id}")
            print(f"   Campo original: {campo_url}")
            print(f"   URL antigua: {url_antigua[: 80]}...")
            print(f"   Storage path: {storage_path}")
        
        # Actualizar Firestore
        if hacer_commit:
            try: 
                actualizacion = {
                    'conduce_storage_path': storage_path
                }
                
                # Opcional: eliminar campo antiguo
                # actualizacion[campo_url] = firestore.DELETE_FIELD
                
                db.collection('alquileres').document(doc.id).update(actualizacion)
                total_actualizados += 1
                
                if total_procesados <= 10:
                    print(f"   ✅ Actualizado")
            except Exception as e:
                print(f"   ❌ Error actualizando:  {e}")
                total_errores += 1
        else: 
            total_actualizados += 1
    
    # Resumen
    print(f"\n{'='*60}")
    print(f"RESUMEN")
    print(f"{'='*60}")
    print(f"📊 Total documentos procesados: {total_procesados}")
    print(f"✅ Actualizados: {total_actualizados}")
    print(f"🔄 Ya migrados: {total_ya_migrados}")
    print(f"⚠️  Sin URL de conduce: {total_sin_url}")
    print(f"❌ Errores: {total_errores}")
    
    if hacer_commit:
        print(f"\n✅ Firestore actualizado exitosamente")
    else:
        print(f"\n💡 Modo simulación: ejecuta de nuevo con opción 2 para aplicar cambios")

def main():
    print("="*60)
    print("MIGRACIÓN DE CONDUCES EN ALQUILERES")
    print("Formato: igual que gastos (storage_path + URLs dinámicas)")
    print("="*60)
    print()
    
    # Paso 1: Seleccionar credenciales
    ruta_credenciales = seleccionar_credenciales()
    
    # Paso 2: ¿Hacer backup?
    carpeta_backup = seleccionar_carpeta_backup()
    
    # Paso 3: Inicializar Firebase
    if not inicializar_firebase(ruta_credenciales):
        sys.exit(1)
    
    bucket = storage.bucket()
    db = firestore.client()
    
    # Paso 4: Backup (si se solicitó)
    if carpeta_backup:
        print("\n⚠️  ¿Iniciar backup? ")
        if input("Continuar (s/n): ").lower().strip() == 's':
            hacer_backup(bucket, carpeta_backup)
        else:
            print("❌ Backup cancelado")
    
    # Paso 5: Migración de Firestore
    print("\n" + "="*60)
    print("OPCIONES DE MIGRACIÓN")
    print("="*60)
    print("1. Simulación (ver qué se va a cambiar, NO modifica Firestore)")
    print("2. Migración real (ACTUALIZA Firestore)")
    print()
    
    opcion = input("Selecciona (1 o 2): ").strip()
    
    if opcion == '1':
        migrar_firestore_alquileres(db, hacer_commit=False)
    elif opcion == '2': 
        print("\n⚠️  ⚠️  ⚠️  ADVERTENCIA ⚠️  ⚠️  ⚠️")
        print("Se MODIFICARÁN todos los documentos de alquileres en Firestore")
        print("Cambios:")
        print("  - Se agregará campo 'conduce_storage_path'")
        print("  - Se MANTENDRÁ el campo original (para compatibilidad)")
        print()
        respuesta = input("¿Estás SEGURO?  Escribe 'MIGRAR' para confirmar: ").strip()
        
        if respuesta == 'MIGRAR':
            migrar_firestore_alquileres(db, hacer_commit=True)
            print("\n✅ Migración completada exitosamente")
        else:
            print("❌ Migración cancelada")
    else:
        print("❌ Opción inválida")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("PROCESO COMPLETADO")
    print("="*60)
    print()
    print("📝 Próximos pasos:")
    print("   1. Actualiza tu app para usar 'conduce_storage_path'")
    print("   2. Las URLs se generarán dinámicamente (como gastos)")
    print("   3. No más URLs expiradas ✅")

if __name__ == "__main__":
    main()