"""
Test: Verificar si las URLs firmadas funcionan
"""
import requests

# Tomar una URL firmada real de Firestore
URL_FIRMADA = "https://storage.googleapis.com/equipos-zoec.firebasestorage.app/gastos/2025/01/gasto_21aa0e3a-bbb9-4958-84ba-c64d1daa3f97.jpg?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=firebase-adminsdk-fbsvc%40equipos-zoec.iam.gserviceaccount.com%2F20260204%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20260204T040806Z&X-Goog-Expires=604800&X-Goog-SignedHeaders=host&X-Goog-Signature=96e5008e8291d9aee54145c75c1a1e7f9470bd5bb1f09be889944d6d6e561c48f1c7b4fc77d952503c51bd40ff06a3bc0e5f4c9d50704565b0087bce5412c6b00defd4fb4ae29ebac30595060a86974fa97594f216ffd6b448cb80d7858e6403102c7975000a4888b25c4cb2d924f92c0fe21f7c7323dd0e011a748ae9bcf8a22d78aeca3c28045ff6a55390b3ea9d4e9dedcbcb1284d51f3df8872074e41bc82cfcb71ac57bf20e947e7bb0df3ab38054e998aa097f23898824cc236e37788dd3533a0b173189b5d8b406706340c2b2e870fd9da1e59b107c56f5d828333e40534de039f330958f9ce6a50bb7b14704e338a40cf99e887390c00261296d422f"

print("=" * 80)
print("🧪 TEST: URL FIRMADA DE GASTO")
print("=" * 80)
print(f"URL: {URL_FIRMADA[:100]}...")
print()

try:
    response = requests.get(URL_FIRMADA, timeout=10)
    
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
    print(f"Content-Length: {response.headers.get('Content-Length', 'N/A')} bytes")
    print()
    
    if response.status_code == 200:
        print("✅ ¡ÉXITO! La URL firmada FUNCIONA")
        print("✅ El archivo es accesible")
    elif response.status_code == 403:
        print("❌ ERROR 403: Acceso denegado")
        print("❌ La cuenta de servicio NO tiene permisos en Storage")
        print()
        print("SOLUCIÓN:")
        print("1. Ve a https://console.cloud.google.com/iam-admin/iam?project=equipos-zoec")
        print("2. Busca: firebase-adminsdk-fbsvc@equipos-zoec.iam.gserviceaccount.com")
        print("3. Asigna rol: Storage Object Admin")
    elif response.status_code == 404:
        print("❌ ERROR 404: Archivo no encontrado")
    else:
        print(f"⚠️ Código inesperado: {response.status_code}")
        print(response.text[:500])
        
except Exception as e:
    print(f"❌ ERROR: {e}")

print("=" * 80)