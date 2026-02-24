#!/usr/bin/env python3
"""
Script para eliminar el campo obsoleto 'conduce_url' de alquileres. 
Solo mantiene 'conduce_storage_path' (URLs se generan dinámicamente).
"""

import firebase_admin
from firebase_admin import credentials, firestore
from tkinter import Tk, filedialog
import sys

def seleccionar_credenciales():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    archivo_credenciales = filedialog.askopenfilename(
        title="Selecciona las credenciales de Firebase",
        filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]
    )
    
    root.destroy()
    
    if not archivo_credenciales:
        print("❌ No se seleccionó ningún archivo.")
        sys.exit(1)
    
    print(f"✓ Credenciales:   {archivo_credenciales}\n")
    return archivo_credenciales

def inicializar_firebase(ruta_credenciales):
    try:
        cred = credentials. Certificate(ruta_credenciales)
        firebase_admin.initialize_app(cred)
        print("✓ Firebase inicializado\n")
        return True
    except Exception as e:
        print(f"❌ Error:   {e}")
        return False

def limpiar_conduce_url(db, hacer_commit=True):
    """
    Elimina el campo 'conduce_url' de todos los alquileres.
    Solo mantiene 'conduce_storage_path'. 
    """
    print("="*60)
    print("LIMPIEZA DE CAMPO 'conduce_url' OBSOLETO")
    print("="*60)
    print()
    
    if not hacer_commit:
        print("⚠️  MODO SIMULACIÓN (no se modificará Firestore)\n")
    
    total_procesados = 0
    total_limpiados = 0
    total_sin_campo = 0
    total_sin_storage_path = 0
    
    docs = db.collection('alquileres').stream()
    
    for doc in docs:
        total_procesados += 1
        data = doc.to_dict()
        
        tiene_conduce_url = 'conduce_url' in data
        tiene_storage_path = 'conduce_storage_path' in data and data['conduce_storage_path']
        
        # Mostrar primeros 10
        if total_procesados <= 10:
            print(f"[{total_procesados}] {doc.id}")
            print(f"   conduce_storage_path: {data.get('conduce_storage_path', '(vacío)')}")
            print(f"   conduce_url:  {'SÍ' if tiene_conduce_url else 'NO'}")
        
        # Caso 1: Tiene storage_path pero NO tiene conduce_url → Ya está bien
        if tiene_storage_path and not tiene_conduce_url:
            total_sin_campo += 1
            if total_procesados <= 10:
                print(f"   ✓ Ya limpio")
            continue
        
        # Caso 2: NO tiene storage_path → Advertencia
        if not tiene_storage_path:
            total_sin_storage_path += 1
            if total_procesados <= 10:
                print(f"   ⚠️  Sin conduce_storage_path")
            continue
        
        # Caso 3: Tiene ambos → Eliminar conduce_url
        if tiene_storage_path and tiene_conduce_url:
            if hacer_commit:
                try:
                    db.collection('alquileres').document(doc.id).update({
                        'conduce_url': firestore.DELETE_FIELD
                    })
                    total_limpiados += 1
                    if total_procesados <= 10:
                        print(f"   ✅ conduce_url eliminado")
                except Exception as e:
                    print(f"   ❌ Error:  {e}")
            else:
                total_limpiados += 1
                if total_procesados <= 10:
                    print(f"   🔄 Se eliminará conduce_url")
        
        if total_procesados <= 10:
            print()
    
    # Resumen
    print(f"{'='*60}")
    print(f"RESUMEN")
    print(f"{'='*60}")
    print(f"📊 Total documentos:  {total_procesados}")
    print(f"✅ Limpiados: {total_limpiados}")
    print(f"✓ Ya limpios: {total_sin_campo}")
    print(f"⚠️  Sin storage_path: {total_sin_storage_path}")
    
    if hacer_commit:
        print(f"\n✅ Limpieza completada")
    else:
        print(f"\n💡 Ejecuta con opción 2 para aplicar cambios")

def main():
    print("="*60)
    print("LIMPIEZA DE CAMPOS OBSOLETOS - ALQUILERES")
    print("="*60)
    print()
    
    ruta_credenciales = seleccionar_credenciales()
    
    if not inicializar_firebase(ruta_credenciales):
        sys.exit(1)
    
    db = firestore.client()
    
    print("OPCIONES:")
    print("1. Simulación (ver qué se va a cambiar)")
    print("2. Limpieza real (ELIMINA 'conduce_url')")
    print()
    
    opcion = input("Selecciona (1 o 2): ").strip()
    
    if opcion == '1':
        limpiar_conduce_url(db, hacer_commit=False)
    elif opcion == '2':
        print("\n⚠️  Se ELIMINARÁ el campo 'conduce_url' de todos los alquileres")
        print("Solo se mantendrá 'conduce_storage_path'")
        print("Las URLs se generarán dinámicamente en la app")
        print()
        respuesta = input("¿Continuar? (s/n): ").lower().strip()
        
        if respuesta == 's': 
            limpiar_conduce_url(db, hacer_commit=True)
        else:
            print("❌ Cancelado")
    else:
        print("❌ Opción inválida")

if __name__ == "__main__":
    main()