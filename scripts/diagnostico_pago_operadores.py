import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path

SERVICE_ACCOUNT_KEY = "firebase_credentials.json"

def init_db():
    cred_file = str(Path(SERVICE_ACCOUNT_KEY).expanduser().resolve())
    if not Path(cred_file).exists():
        raise FileNotFoundError(cred_file)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(cred_file))
    return firestore.client()

def main():
    db = init_db()
    col = db.collection("pagos_operadores")
    docs = list(col.stream())
    total = len(docs)
    sin_fecha = 0
    no_string = 0
    ejemplos_sin = []
    ejemplos_tipo = []
    for d in docs:
        data = d.to_dict() or {}
        f = data.get("fecha")
        if f is None:
            sin_fecha += 1
            if len(ejemplos_sin) < 5:
                ejemplos_sin.append(d.id)
        elif not isinstance(f, str):
            no_string += 1
            if len(ejemplos_tipo) < 5:
                ejemplos_tipo.append((d.id, type(f).__name__, f))
    print(f"Total pagos: {total}")
    print(f"Sin fecha: {sin_fecha}, ejemplos: {ejemplos_sin}")
    print(f"Fecha no-string: {no_string}, ejemplos: {ejemplos_tipo}")

if __name__ == "__main__":
    main()