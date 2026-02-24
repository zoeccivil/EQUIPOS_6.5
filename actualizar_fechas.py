import firebase_admin
from firebase_admin import credentials, firestore
import logging
from datetime import datetime

# --- CONFIGURACIÓN ---
SERVICE_ACCOUNT_KEY = "firebase_credentials.json" 
COLECCION_A_ACTUALIZAR = "alquileres"
CAMPO_FECHA_ORIGEN = "fecha" # El campo string que tiene la fecha
BATCH_SIZE = 499

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- INICIALIZACIÓN ---
try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
    firebase_admin.initialize_app(cred)
    db_firestore = firestore.client()
    logging.info(f"Conexión a Firestore exitosa. Proyecto: {cred.project_id}")
except Exception as e:
    logging.error(f"Error al inicializar la conexión: {e}")
    exit()

def actualizar_documentos_fechas():
    """
    Lee la colección, extrae el año y mes del campo 'fecha',
    y actualiza el documento con los nuevos campos 'ano' y 'mes'.
    """
    logging.info(f"--- Iniciando actualización de fechas en [{COLECCION_A_ACTUALIZAR}] ---")
    
    try:
        # Obtenemos TODOS los documentos de la colección
        docs_stream = db_firestore.collection(COLECCION_A_ACTUALIZAR).stream()
        
        batch = db_firestore.batch()
        doc_count_lote = 0
        total_actualizados = 0

        for doc in docs_stream:
            datos = doc.to_dict()
            
            # Revisa si el campo de fecha existe y si 'ano' no existe ya
            if CAMPO_FECHA_ORIGEN in datos and 'ano' not in datos:
                fecha_str = datos[CAMPO_FECHA_ORIGEN]
                
                try:
                    # Intenta convertir la fecha (asumimos formato YYYY-MM-DD)
                    fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d")
                    ano_num = fecha_obj.year
                    mes_num = fecha_obj.month
                    
                    # Prepara la actualización
                    doc_ref = doc.reference
                    batch.update(doc_ref, {
                        'ano': ano_num,
                        'mes': mes_num
                    })
                    
                    doc_count_lote += 1
                    total_actualizados += 1
                    
                    if doc_count_lote >= BATCH_SIZE:
                        logging.info(f"Enviando lote de {doc_count_lote} actualizaciones...")
                        batch.commit()
                        batch = db_firestore.batch()
                        doc_count_lote = 0

                except ValueError:
                    logging.warning(f"Documento {doc.id} tiene formato de fecha inválido: {fecha_str}. Omitiendo.")
                except Exception as e_inner:
                    logging.warning(f"Error procesando doc {doc.id}: {e_inner}. Omitiendo.")
            
            elif 'ano' in datos:
                # Si 'ano' ya existe, lo saltamos.
                pass
            else:
                logging.warning(f"Documento {doc.id} no tiene el campo '{CAMPO_FECHA_ORIGEN}'. Omitiendo.")

        # Enviar el último lote
        if doc_count_lote > 0:
            logging.info(f"Enviando lote final de {doc_count_lote} actualizaciones...")
            batch.commit()
            
        if total_actualizados == 0:
            logging.info("No se encontraron documentos que necesitaran actualización. (Quizás ya se ejecutó)")
        else:
            logging.info(f"--- Actualización completada. Total: {total_actualizados} documentos actualizados. ---")

    except Exception as e:
        logging.error(f"Error durante la actualización de fechas: {e}")

if __name__ == "__main__":
    actualizar_documentos_fechas()