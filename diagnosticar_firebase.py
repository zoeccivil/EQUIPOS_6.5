#!/usr/bin/env python3
"""
Script de diagnóstico para verificar acceso a Firestore. 
"""

import firebase_admin
from firebase_admin import credentials, firestore
from tkinter import Tk, filedialog
import sys

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

def inicializar_firebase(ruta_credenciales):
    """Inicializa Firebase."""
    try:
        cred = credentials.Certificate(ruta_credenciales)
        firebase_admin. initialize_app(cred)
        print("✓ Firebase inicializado\n")
        return True
    except Exception as e:
        print(f"❌ Error:  {e}")
        import traceback
        traceback.print_exc()
        return False

def diagnosticar_firestore(db):
    """Diagnostica acceso a Firestore."""
    
    print("="*60)
    print("DIAGNÓSTICO DE FIRESTORE")
    print("="*60)
    print()
    
    # 1. Listar todas las colecciones
    print("1️⃣  COLECCIONES DISPONIBLES:")
    print("-" * 60)
    try:
        colecciones = db.collections()
        nombres_col = [col.id for col in colecciones]
        
        if nombres_col:
            print(f"✓ Encontradas {len(nombres_col)} colecciones:\n")
            for i, nombre in enumerate(nombres_col, 1):
                print(f"   {i}. {nombre}")
        else:
            print("⚠️  No se encontraron colecciones")
            print("\n💡 Posibles causas:")
            print("   - Firestore no tiene datos")
            print("   - Las reglas de seguridad bloquean el acceso")
    except Exception as e:
        print(f"❌ Error listando colecciones: {e}")
        import traceback
        traceback.print_exc()
    
    # 2. Verificar colección 'conduces'
    print("\n2️⃣  COLECCIÓN 'conduces':")
    print("-" * 60)
    try:
        conduces_ref = db.collection('conduces')
        docs = list(conduces_ref.limit(5).stream())
        
        if docs: 
            print(f"✓ Encontrados documentos ({len(docs)} primeros):\n")
            for i, doc in enumerate(docs, 1):
                data = doc.to_dict()
                print(f"   {i}. ID: {doc.id}")
                print(f"      Campos: {list(data.keys())}")
                
                # Verificar campos relevantes
                if 'archivoUrl' in data: 
                    print(f"      ✓ Tiene 'archivoUrl': {data['archivoUrl'][: 80]}...")
                if 'archivo_storage_path' in data:
                    print(f"      ✓ Tiene 'archivo_storage_path': {data['archivo_storage_path']}")
                
                print()
        else:
            print("❌ No se encontraron documentos en 'conduces'")
            print("\n💡 Verifica:")
            print("   1. ¿El nombre de la colección es correcto? ")
            print("   2. ¿Hay datos en Firestore?")
            print("   3. ¿Las reglas de seguridad permiten lectura?")
    except Exception as e:
        print(f"❌ Error consultando 'conduces': {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Contar documentos
    print("\n3️⃣  CONTEO DE DOCUMENTOS:")
    print("-" * 60)
    try:
        # Intentar diferentes métodos de conteo
        print("Método 1: stream() completo...")
        docs_stream = list(db.collection('conduces').stream())
        print(f"   Total documentos: {len(docs_stream)}")
        
        if len(docs_stream) > 0:
            print(f"\n✓ La colección 'conduces' tiene {len(docs_stream)} documentos")
        else:
            print("\n⚠️  La colección 'conduces' está vacía o no existe")
    except Exception as e:
        print(f"❌ Error contando documentos: {e}")
    
    # 4. Intentar otras colecciones comunes
    print("\n4️⃣  OTRAS COLECCIONES COMUNES:")
    print("-" * 60)
    for col_name in ['Conduces', 'CONDUCES', 'conduce', 'equipos', 'gastos']:
        try:
            docs = list(db.collection(col_name).limit(1).stream())
            if docs:
                print(f"   ✓ '{col_name}':  {len(list(db.collection(col_name).stream()))} documentos")
        except Exception: 
            pass

def main():
    print("="*60)
    print("DIAGNÓSTICO DE FIRESTORE")
    print("="*60)
    print()
    
    ruta_credenciales = seleccionar_credenciales()
    
    if not inicializar_firebase(ruta_credenciales):
        sys.exit(1)
    
    db = firestore.client()
    diagnosticar_firestore(db)
    
    print("\n" + "="*60)
    print("DIAGNÓSTICO COMPLETADO")
    print("="*60)

if __name__ == "__main__":
    main()