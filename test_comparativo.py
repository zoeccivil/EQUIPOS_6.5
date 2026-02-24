"""
Comparar acceso entre conduces (funciona) y gastos (no funciona)
"""
import requests

BUCKET = "equipos-zoec.firebasestorage.app"

# Test 1: Conduce (FUNCIONA)
conduce_path = "conduces/2025/12/alquiler_0sgxoFPFVLKRDJuVhO29_conduce.pdf"  # Ejemplo
conduce_url = f"https://storage.googleapis.com/{BUCKET}/{conduce_path}"

# Test 2: Gasto (NO FUNCIONA)
gasto_path = "gastos/2026/01/gasto_goTwOLDRqjxV2MMtOO53.jpeg"
gasto_url = f"https://storage.googleapis.com/{BUCKET}/{gasto_path}"

print("=" * 80)
print("🔍 COMPARACIÓN: Conduces vs Gastos")
print("=" * 80)

print("\n1️⃣ PRUEBA: CONDUCE (debería funcionar)")
print(f"URL: {conduce_url}")
try:
    r1 = requests.head(conduce_url, timeout=5)
    print(f"   Status: {r1.status_code}")
    if r1.status_code == 200:
        print("   ✅ FUNCIONA")
    else:
        print(f"   ❌ FALLA: {r1.status_code}")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

print("\n2️⃣ PRUEBA: GASTO (no funciona)")
print(f"URL: {gasto_url}")
try:
    r2 = requests.head(gasto_url, timeout=5)
    print(f"   Status: {r2.status_code}")
    if r2.status_code == 200:
        print("   ✅ FUNCIONA")
    else:
        print(f"   ❌ FALLA: {r2.status_code}")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

print("\n" + "=" * 80)
print("🔎 ANÁLISIS:")
print("=" * 80)

# Listar algunos gastos de Firestore para verificar rutas
print("\nVERIFICANDO RUTAS EN FIRESTORE...")

try:
    from firebase_manager import FirebaseManager
    from google.cloud import firestore
    
    # Inicializar Firebase (usando credenciales actuales)
    credentials_path = "D:/Dropbox/PROGAIN/EQUIPOS-5.0/dist/firebase_equipos_key.json"
    project_id = "equipos-zoec"
    
    fm = FirebaseManager(credentials_path, project_id)
    
    # Obtener 3 gastos con adjuntos
    gastos_ref = fm.db.collection("gastos").limit(5)
    docs = gastos_ref.stream()
    
    print("\n📄 PRIMEROS 5 GASTOS CON ADJUNTOS:")
    count = 0
    for doc in docs:
        data = doc.to_dict()
        storage_path = data.get("archivo_storage_path")
        if storage_path:
            count += 1
            print(f"\n   {count}. Gasto ID: {doc.id}")
            print(f"      Storage Path: {storage_path}")
            print(f"      URL: https://storage.googleapis.com/{BUCKET}/{storage_path}")
            
            # Probar acceso
            url = f"https://storage.googleapis.com/{BUCKET}/{storage_path}"
            try:
                r = requests.head(url, timeout=3)
                if r.status_code == 200:
                    print(f"      ✅ Accesible públicamente")
                else:
                    print(f"      ❌ NO accesible (Status: {r.status_code})")
            except:
                print(f"      ❌ Error al verificar")
            
            if count >= 3:
                break
    
    if count == 0:
        print("   ⚠️ No se encontraron gastos con adjuntos")
        
except Exception as e:
    print(f"   ❌ Error accediendo a Firestore: {e}")

print("\n" + "=" * 80)