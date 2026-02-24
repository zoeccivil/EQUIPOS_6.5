# corregir_alquileres_proyecto_tipo.py
"""
Script de corrección de alquileres sin proyecto_id y tipo
- Interfaz gráfica para seleccionar credenciales
- Diagnóstico antes de corregir
- Backup de seguridad
- Confirmación antes de modificar
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import sys

class CorrectAlquileres:
    def __init__(self):
        self.db = None
        self.proyecto_id_default = 8
        self.tipo_default = "Ingreso"
        
    def seleccionar_credenciales(self):
        """Abre diálogo para seleccionar archivo de credenciales"""
        print("\n" + "="*80)
        print("CORRECCIÓN DE ALQUILERES - Campos proyecto_id y tipo")
        print("="*80)
        print("\n📁 Selecciona el archivo de credenciales de Firebase...\n")
        
        root = tk.Tk()
        root.withdraw()  # Ocultar ventana principal
        root.lift()
        root.attributes('-topmost', True)
        
        archivo = filedialog.askopenfilename(
            title="Selecciona las credenciales de Firebase",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ],
            initialdir="E:/Dropbox/PROGAIN/EQUIPOS-5.0/dist"
        )
        
        root.destroy()
        
        if not archivo:
            print("❌ No se seleccionó ningún archivo")
            return None
        
        print(f"✅ Archivo seleccionado: {archivo}\n")
        return archivo
    
    def inicializar_firebase(self, credentials_path):
        """Inicializa conexión a Firebase"""
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            print("✅ Conexión a Firestore exitosa\n")
            return True
        except Exception as e:
            print(f"❌ Error al conectar con Firebase: {e}")
            return False
    
    def diagnosticar(self, fecha_inicio="2025-12-01"):
        """Diagnóstico de alquileres problemáticos"""
        print("\n" + "="*80)
        print("📊 FASE 1: DIAGNÓSTICO")
        print("="*80)
        print(f"\n🔍 Buscando alquileres desde {fecha_inicio}...\n")
        
        try:
            docs = list(self.db.collection('alquileres').where('fecha', '>=', fecha_inicio).stream())
            
            if not docs:
                print(f"⚠️  No se encontraron alquileres desde {fecha_inicio}")
                return None
            
            print(f"📋 Total de documentos encontrados: {len(docs)}\n")
            
            problemas = {
                'sin_proyecto_id': [],
                'sin_tipo': [],
                'sin_ambos': [],
                'correctos': []
            }
            
            for doc in docs:
                data = doc.to_dict()
                doc_id = doc.id
                fecha = data.get('fecha', 'Sin fecha')
                monto = data.get('monto', 0)
                equipo = data.get('equipo_id', '?')
                
                tiene_proyecto = 'proyecto_id' in data and data.get('proyecto_id') is not None
                tiene_tipo = 'tipo' in data and data.get('tipo') is not None
                
                info = {
                    'id': doc_id,
                    'fecha': fecha,
                    'monto': monto,
                    'equipo_id': equipo,
                    'proyecto_id_actual': data.get('proyecto_id'),
                    'tipo_actual': data.get('tipo')
                }
                
                if not tiene_proyecto and not tiene_tipo:
                    problemas['sin_ambos'].append(info)
                elif not tiene_proyecto:
                    problemas['sin_proyecto_id'].append(info)
                elif not tiene_tipo:
                    problemas['sin_tipo'].append(info)
                else:
                    problemas['correctos'].append(info)
            
            self._mostrar_diagnostico(problemas)
            return problemas
            
        except Exception as e:
            print(f"❌ Error durante el diagnóstico: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _mostrar_diagnostico(self, problemas):
        """Muestra resultados del diagnóstico"""
        print("\n" + "-"*80)
        print("📊 RESULTADOS DEL DIAGNÓSTICO:")
        print("-"*80)
        
        total_problemas = (
            len(problemas['sin_proyecto_id']) + 
            len(problemas['sin_tipo']) + 
            len(problemas['sin_ambos'])
        )
        
        print(f"\n✅ Documentos correctos: {len(problemas['correctos'])}")
        print(f"⚠️  Documentos con problemas: {total_problemas}")
        
        if problemas['sin_ambos']:
            print(f"\n🔴 Sin proyecto_id NI tipo: {len(problemas['sin_ambos'])}")
            for doc in problemas['sin_ambos'][:3]:
                print(f"   - {doc['id'][:20]}... | {doc['fecha']} | Equipo: {doc['equipo_id']} | ${doc['monto']:,.2f}")
            if len(problemas['sin_ambos']) > 3:
                print(f"   ... y {len(problemas['sin_ambos']) - 3} más")
        
        if problemas['sin_proyecto_id']:
            print(f"\n🟡 Solo sin proyecto_id: {len(problemas['sin_proyecto_id'])}")
            for doc in problemas['sin_proyecto_id'][:3]:
                print(f"   - {doc['id'][:20]}... | {doc['fecha']} | Tipo: {doc['tipo_actual']}")
            if len(problemas['sin_proyecto_id']) > 3:
                print(f"   ... y {len(problemas['sin_proyecto_id']) - 3} más")
        
        if problemas['sin_tipo']:
            print(f"\n🟡 Solo sin tipo: {len(problemas['sin_tipo'])}")
            for doc in problemas['sin_tipo'][:3]:
                print(f"   - {doc['id'][:20]}... | {doc['fecha']} | Proyecto: {doc['proyecto_id_actual']}")
            if len(problemas['sin_tipo']) > 3:
                print(f"   ... y {len(problemas['sin_tipo']) - 3} más")
    
    def crear_backup(self, problemas):
        """Crea backup de documentos que serán modificados"""
        print("\n" + "="*80)
        print("💾 FASE 2: BACKUP")
        print("="*80)
        
        try:
            # Crear carpeta de backups
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"backup_alquileres_{timestamp}.json"
            
            # Recolectar todos los documentos problemáticos
            docs_a_respaldar = []
            for categoria in ['sin_proyecto_id', 'sin_tipo', 'sin_ambos']:
                docs_a_respaldar.extend(problemas[categoria])
            
            if not docs_a_respaldar:
                print("✅ No hay documentos que respaldar")
                return None
            
            # Guardar backup
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'fecha_backup': timestamp,
                    'total_documentos': len(docs_a_respaldar),
                    'documentos': docs_a_respaldar
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Backup creado exitosamente:")
            print(f"   📁 {backup_file.absolute()}")
            print(f"   📊 {len(docs_a_respaldar)} documentos respaldados\n")
            
            return str(backup_file)
            
        except Exception as e:
            print(f"❌ Error al crear backup: {e}")
            return None
    
    def confirmar_correccion(self, problemas):
        """Solicita confirmación del usuario"""
        total_problemas = (
            len(problemas['sin_proyecto_id']) + 
            len(problemas['sin_tipo']) + 
            len(problemas['sin_ambos'])
        )
        
        if total_problemas == 0:
            print("\n✅ No hay nada que corregir. Todos los documentos están correctos.")
            return False
        
        print("\n" + "="*80)
        print("⚠️  CONFIRMACIÓN")
        print("="*80)
        print(f"\nSe modificarán {total_problemas} documentos en Firestore:")
        print(f"   - Se agregará proyecto_id = {self.proyecto_id_default} (si falta)")
        print(f"   - Se agregará tipo = '{self.tipo_default}' (si falta)")
        print("\n⚠️  Esta operación modificará la base de datos en Firebase")
        print("✅ Se ha creado un backup por seguridad\n")
        
        respuesta = input("¿Deseas CONTINUAR con la corrección? (escribe 'SI' para confirmar): ").strip()
        
        return respuesta.upper() == 'SI'
    
    def corregir(self, problemas):
        """Aplica las correcciones a los documentos"""
        print("\n" + "="*80)
        print("🔧 FASE 3: CORRECCIÓN")
        print("="*80 + "\n")
        
        try:
            corregidos = 0
            errores = 0
            
            # Procesar cada categoría
            for categoria in ['sin_proyecto_id', 'sin_tipo', 'sin_ambos']:
                for doc_info in problemas[categoria]:
                    doc_id = doc_info['id']
                    updates = {}
                    
                    # Determinar qué campos agregar
                    if doc_info['proyecto_id_actual'] is None:
                        updates['proyecto_id'] = self.proyecto_id_default
                    
                    if doc_info['tipo_actual'] is None:
                        updates['tipo'] = self.tipo_default
                    
                    if not updates:
                        continue
                    
                    # Aplicar actualización
                    try:
                        self.db.collection('alquileres').document(doc_id).update(updates)
                        corregidos += 1
                        
                        campos = ", ".join([f"{k}={v}" for k, v in updates.items()])
                        print(f"✅ {doc_id[:20]}... | {doc_info['fecha']} | Agregado: {campos}")
                        
                    except Exception as e:
                        errores += 1
                        print(f"❌ Error en {doc_id[:20]}...: {e}")
            
            print("\n" + "-"*80)
            print("📊 RESUMEN DE CORRECCIÓN:")
            print("-"*80)
            print(f"✅ Documentos corregidos: {corregidos}")
            print(f"❌ Errores: {errores}")
            print("-"*80 + "\n")
            
            return corregidos, errores
            
        except Exception as e:
            print(f"\n❌ Error durante la corrección: {e}")
            import traceback
            traceback.print_exc()
            return 0, 0
    
    def ejecutar(self):
        """Flujo principal del script"""
        # Paso 1: Seleccionar credenciales
        credentials_path = self.seleccionar_credenciales()
        if not credentials_path:
            return
        
        # Paso 2: Conectar a Firebase
        if not self.inicializar_firebase(credentials_path):
            return
        
        # Paso 3: Diagnosticar
        problemas = self.diagnosticar()
        if problemas is None:
            return
        
        # Paso 4: Crear backup
        backup_file = self.crear_backup(problemas)
        if backup_file is None and any(len(v) > 0 for k, v in problemas.items() if k != 'correctos'):
            print("⚠️  No se pudo crear el backup. Abortando por seguridad.")
            return
        
        # Paso 5: Confirmar
        if not self.confirmar_correccion(problemas):
            print("\n❌ Corrección cancelada por el usuario")
            return
        
        # Paso 6: Corregir
        corregidos, errores = self.corregir(problemas)
        
        # Paso 7: Mensaje final
        print("\n" + "="*80)
        print("✅ PROCESO COMPLETADO")
        print("="*80)
        
        if corregidos > 0:
            print(f"\n✅ {corregidos} documentos corregidos exitosamente")
            print(f"💾 Backup guardado en: {backup_file}")
            print("\n📝 PRÓXIMO PASO:")
            print("   Ejecuta la aplicación y verifica que el dashboard muestre")
            print("   las transacciones de Diciembre 2025 y 2026\n")
        else:
            print("\n✅ No se realizaron cambios\n")

if __name__ == "__main__":
    try:
        corrector = CorrectAlquileres()
        corrector.ejecutar()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPresiona ENTER para cerrar...")
    