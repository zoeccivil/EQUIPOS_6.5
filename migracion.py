import sqlite3
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import logging
from datetime import datetime

# --- CONFIGURACIÓN ---
DB_PATH = "progain_database.db"
SERVICE_ACCOUNT_KEY = "firebase_credentials.json" 
BATCH_SIZE = 499

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- INICIALIZACIÓN ---
try:
    if not firebase_admin._apps: # Evitar inicializar dos veces
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
        firebase_admin.initialize_app(cred)
    
    db_firestore = firestore.client()
    logging.info(f"Conexión a Firestore exitosa.")

    conn_sql = sqlite3.connect(DB_PATH)
    logging.info(f"Conexión a SQLite exitosa ({DB_PATH})")
except Exception as e:
    logging.error(f"Error al inicializar las conexiones: {e}")
    exit()


def cometer_lote(batch, doc_count, coleccion):
    """Función ayudante para enviar el lote y reiniciarlo."""
    if doc_count > 0:
        logging.info(f"Enviando lote de {doc_count} documentos a [{coleccion}]...")
        batch.commit()
    return db_firestore.batch(), 0


def migrar_coleccion_simple(coleccion_fs, tabla_sql):
    """Migra tablas simples de SQL a Firestore (Equipos, Entidades, Mantenimientos)"""
    logging.info(f"--- Iniciando migración de [{tabla_sql}] a [{coleccion_fs}] ---")
    try:
        df = pd.read_sql(f"SELECT * FROM {tabla_sql}", conn_sql)
        if df.empty:
            logging.warning(f"No se encontraron datos en [{tabla_sql}]. Omitiendo.")
            return

        batch = db_firestore.batch()
        doc_count = 0
        total_migrados = 0
        for index, row in df.iterrows():
            datos = row.to_dict()
            datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
            doc_id = str(datos_limpios['id'])
            doc_ref = db_firestore.collection(coleccion_fs).document(doc_id)
            batch.set(doc_ref, datos_limpios)
            doc_count += 1
            total_migrados += 1
            
            if doc_count >= BATCH_SIZE:
                batch, doc_count = cometer_lote(batch, doc_count, coleccion_fs)
        
        cometer_lote(batch, doc_count, coleccion_fs)
        logging.info(f"--- Migración de [{coleccion_fs}] completada. Total: {total_migrados} docs. ---")
    except Exception as e:
        logging.error(f"Error durante la migración de [{coleccion_fs}]: {e}")


def migrar_transacciones_unificadas_y_pagos_operador():
    """
    Migra 'Ingresos' y 'Gastos' a la colección 'transacciones'.
    Migra 'Pagos a Operadores' a su propia colección 'pagos_operadores'.
    Añade los campos 'ano' y 'mes' automáticamente.
    """
    logging.info("--- Iniciando migración de transacciones (unificada) ---")
    try:
        # 1. OBTENER ID DE CATEGORÍA DE PAGO A OPERADOR
        cat_id_pago_operador = None
        try:
            cat_id_pago_operador = pd.read_sql(
                "SELECT id FROM categorias WHERE nombre = 'PAGO HRS OPERADOR'", 
                conn_sql
            ).iloc[0]['id']
            logging.info(f"ID de categoría 'PAGO HRS OPERADOR' encontrado: {cat_id_pago_operador}")
        except Exception:
            logging.warning("No se encontró la categoría 'PAGO HRS OPERADOR' en SQL.")

        # 2. MIGRAR 'pagos_operadores' (LOS QUE SÍ VAN SEPARADOS)
        if cat_id_pago_operador:
            coleccion_pagos_op = "pagos_operadores"
            query_pagos_op = "SELECT * FROM transacciones WHERE tipo = 'Gasto' AND categoria_id = ?"
            df_pagos_op = pd.read_sql(query_pagos_op, conn_sql, params=(cat_id_pago_operador,))
            
            if not df_pagos_op.empty:
                batch_pagos = db_firestore.batch()
                count_pagos = 0
                total_pagos = 0
                for index, row in df_pagos_op.iterrows():
                    datos = row.to_dict()
                    datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
                    # Añadir campos 'ano' y 'mes'
                    try:
                        fecha_obj = datetime.strptime(datos_limpios['fecha'], "%Y-%m-%d")
                        datos_limpios['ano'] = fecha_obj.year
                        datos_limpios['mes'] = fecha_obj.month
                    except Exception:
                        pass # Ignorar si la fecha es inválida

                    doc_id = str(datos_limpios['id'])
                    doc_ref = db_firestore.collection(coleccion_pagos_op).document(doc_id)
                    batch_pagos.set(doc_ref, datos_limpios)
                    count_pagos += 1
                    total_pagos += 1
                    
                    if count_pagos >= BATCH_SIZE:
                        batch_pagos, count_pagos = cometer_lote(batch_pagos, count_pagos, coleccion_pagos_op)
                
                cometer_lote(batch_pagos, count_pagos, coleccion_pagos_op)
                logging.info(f"Migración de [{coleccion_pagos_op}] completada. Total: {total_pagos} docs.")
            else:
                logging.info("No se encontraron 'Pagos a Operadores' para migrar.")
        
        # 3. MIGRAR TODO LO DEMÁS A 'transacciones'
        coleccion_trans = "transacciones"
        query_trans = "SELECT * FROM transacciones"
        params_trans = ()
        if cat_id_pago_operador:
            # Excluir los pagos a operadores que ya migramos
            query_trans += " WHERE (categoria_id != ? OR categoria_id IS NULL OR tipo != 'Gasto')"
            params_trans = (cat_id_pago_operador,)
        
        df_trans = pd.read_sql(query_trans, conn_sql, params=params_trans)
        
        if df_trans.empty:
            logging.warning("No se encontraron 'Ingresos' o 'Gastos' en [transacciones].")
            return

        batch_trans = db_firestore.batch()
        count_trans = 0
        total_trans = 0
        
        for index, row in df_trans.iterrows():
            datos = row.to_dict()
            datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
            
            # Convertir 0/1 de SQL a boolean para Firestore
            if 'pagado' in datos_limpios:
                datos_limpios['pagado'] = bool(datos_limpios.get('pagado', 0))

            # Añadir campos 'ano' y 'mes'
            try:
                fecha_obj = datetime.strptime(datos_limpios['fecha'], "%Y-%m-%d")
                datos_limpios['ano'] = fecha_obj.year
                datos_limpios['mes'] = fecha_obj.month
            except Exception:
                pass # Ignorar si la fecha es inválida
                
            doc_id = str(datos_limpios['id'])
            doc_ref = db_firestore.collection(coleccion_trans).document(doc_id)
            
            batch_trans.set(doc_ref, datos_limpios)
            count_trans += 1
            total_trans += 1
            
            if count_trans >= BATCH_SIZE:
                batch_trans, count_trans = cometer_lote(batch_trans, count_trans, coleccion_trans)
        
        cometer_lote(batch_trans, count_trans, coleccion_trans)
        logging.info(f"--- Migración de [{coleccion_trans}] completada. Total: {total_trans} docs. ---")
        
        # 4. MIGRAR LOS ABONOS (PAGOS) como subcolección
        logging.info("--- Iniciando migración de Abonos (pagos) a subcolecciones ---")
        df_abonos = pd.read_sql("SELECT * FROM pagos", conn_sql)
        if not df_abonos.empty:
            batch_abonos = db_firestore.batch()
            count_abonos = 0
            total_abonos = 0
            for index, row in df_abonos.iterrows():
                datos = row.to_dict()
                datos_limpios = {k: v for k, v in datos.items() if pd.notna(v)}
                
                trans_id = str(datos_limpios['transaccion_id'])
                pago_id = str(datos_limpios['id'])
                
                # Referencia a la subcolección
                doc_ref = db_firestore.collection(coleccion_trans).document(trans_id).collection("pagos").document(pago_id)
                batch_abonos.set(doc_ref, datos_limpios)
                count_abonos += 1
                total_abonos += 1

                if count_abonos >= BATCH_SIZE:
                    batch_abonos, count_abonos = cometer_lote(batch_abonos, count_abonos, "pagos (subcolección)")

            cometer_lote(batch_abonos, count_abonos, "pagos (subcolección)")
            logging.info(f"--- Migración de Abonos (pagos) completada. Total: {total_abonos} docs. ---")

    except Exception as e:
        logging.error(f"Error durante la migración unificada: {e}")


def main():
    logging.info("========= INICIANDO SCRIPT DE MIGRACIÓN V2 (UNIFICADO) =========")
    
    migrar_coleccion_simple(coleccion_fs="equipos", tabla_sql="equipos")
    migrar_coleccion_simple(coleccion_fs="entidades", tabla_sql="equipos_entidades")
    migrar_coleccion_simple(coleccion_fs="mantenimientos", tabla_sql="mantenimientos")
    
    # Migra 'transacciones', 'pagos_operadores', y 'pagos' (subcolección)
    migrar_transacciones_unificadas_y_pagos_operador()
    
    conn_sql.close()
    logging.info("========= MIGRACIÓN V2 FINALIZADA =========")

if __name__ == "__main__":
    main()