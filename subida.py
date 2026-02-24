
from firebase_admin import storage
import firebase_admin
from firebase_admin import credentials

# Inicializar
cred = credentials.Certificate("firebase_credentials.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'equipos-zoec.firebasestorage.app'
})

# Probar subida
bucket = storage.bucket()
blob = bucket.blob('test/prueba.txt')
blob.upload_from_string('Hola mundo')
print(f"URL: {blob.public_url}")