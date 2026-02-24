import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
import logging

# --- CONFIGURACIÓN ---
DB_PATH = "progain_database.db"
SERVICE_ACCOUNT_KEY = "firebase_credentials.json"
# si tus clientes son por proyecto, puedes filtrar por proyecto_id si quieres; por ahora no filtramos
PROYECTO_ID_FILTRO = None  # o un entero si quieres limitar

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def conectar_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    logging.info(f"Conectado a SQLite: {DB_PATH}")
    return conn


def conectar_firestore():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    logging.info("Conectado a Firestore.")
    return db


def construir_mapa_sqlite_clientes(conn):
    """
    Devuelve:
      - mapa_sqlite_id_a_nombre: {id_sqlite (int) -> nombre_cliente (str)}
    """
    cur = conn.cursor()
    if PROYECTO_ID_FILTRO is not None:
        cur.execute(
            "SELECT id, nombre FROM equipos_entidades WHERE tipo='Cliente' AND proyecto_id = ?",
            (PROYECTO_ID_FILTRO,),
        )
    else:
        cur.execute("SELECT id, nombre FROM equipos_entidades WHERE tipo='Cliente'")
    filas = cur.fetchall()
    cur.close()

    mapa = {row["id"]: row["nombre"] for row in filas}
    logging.info(f"Clientes en SQLite: {len(mapa)}")
    return mapa


def construir_mapa_firestore_clientes(db):
    """
    Devuelve:
      - mapa_nombre_a_entidad_id: {nombre_cliente (str) -> firestore_id (str)}
    """
    mapa = {}
    docs = db.collection("entidades").where("tipo", "==", "Cliente").stream()
    count = 0
    for doc in docs:
        datos = doc.to_dict()
        nombre = datos.get("nombre")
        if not nombre:
            continue
        mapa[nombre] = doc.id
        count += 1
    logging.info(f"Clientes en Firestore (entidades): {count}")
    return mapa


def corregir_abonos(conn, db, mapa_sqlite_id_a_nombre, mapa_nombre_a_entidad_id):
    """
    Recorre la colección 'abonos' y corrige cliente_id:
      de id_sqlite (ej. 16) -> entidad_id Firestore (str)
    """
    coleccion = db.collection("abonos")
    docs = list(coleccion.stream())
    logging.info(f"Abonos encontrados en Firestore: {len(docs)}")

    batch = db.batch()
    count_batch = 0
    total_actualizados = 0
    sin_mapeo = 0

    for doc in docs:
        datos = doc.to_dict()
        cliente_id_actual = datos.get("cliente_id")

        if cliente_id_actual is None or cliente_id_actual == "":
            continue

        # los migradores pueden haber dejado int o str; normalizamos a int para buscar en SQLite
        try:
            sqlite_id = int(cliente_id_actual)
        except (ValueError, TypeError):
            # ya parece ser un id de Firestore (string no convertible) -> lo dejamos
            continue

        nombre_cliente = mapa_sqlite_id_a_nombre.get(sqlite_id)
        if not nombre_cliente:
            logging.warning(f"Abono {doc.id}: cliente_id={sqlite_id} no encontrado en SQLite.")
            sin_mapeo += 1
            continue

        entidad_id = mapa_nombre_a_entidad_id.get(nombre_cliente)
        if not entidad_id:
            logging.warning(
                f"Abono {doc.id}: nombre_cliente='{nombre_cliente}' no encontrado en entidades de Firestore."
            )
            sin_mapeo += 1
            continue

        # Si ya está igual, no hacemos nada
        if cliente_id_actual == entidad_id:
            continue

        # Actualizamos el documento
        batch.update(doc.reference, {"cliente_id": entidad_id})
        count_batch += 1
        total_actualizados += 1

        if count_batch >= 400:
            logging.info(f"Enviando batch de {count_batch} actualizaciones...")
            batch.commit()
            batch = db.batch()
            count_batch = 0

    if count_batch > 0:
        logging.info(f"Enviando batch final de {count_batch} actualizaciones...")
        batch.commit()

    logging.info(f"Abonos actualizados: {total_actualizados}")
    logging.info(f"Abonos sin mapeo (no pudieron corregirse): {sin_mapeo}")


def main():
    conn = conectar_sqlite()
    db = conectar_firestore()

    mapa_sqlite_id_a_nombre = construir_mapa_sqlite_clientes(conn)
    mapa_nombre_a_entidad_id = construir_mapa_firestore_clientes(db)

    corregir_abonos(conn, db, mapa_sqlite_id_a_nombre, mapa_nombre_a_entidad_id)

    conn.close()
    logging.info("Corrección finalizada.")


if __name__ == "__main__":
    main()