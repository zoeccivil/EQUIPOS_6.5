# corregir_abonos_aplicacion.py
"""
Script para agregar el campo 'transaccion_descripcion' a abonos existentes
que no lo tienen, mostrando a qué facturas se aplicaron.
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from typing import Dict, List

class CorregirAbonosAplicacion:
    def __init__(self):
        self.db = None
        
    def seleccionar_credenciales(self):
        """Abre diálogo para seleccionar archivo de credenciales"""
        print("\n" + "="*80)
        print("CORRECCIÓN DE ABONOS - Campo transaccion_descripcion")
        print("="*80)
        print("\n📁 Selecciona el archivo de credenciales de Firebase...\n")
        
        root = tk.Tk()
        root.withdraw()
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
    
    def obtener_pagos_de_alquiler(self, alquiler_id: str) -> List[Dict]:
        """Obtiene los pagos de un alquiler específico"""
        try:
            pagos_docs = self.db.collection("alquileres").document(alquiler_id).collection("pagos").stream()
            pagos = []
            for doc in pagos_docs:
                data = doc.to_dict()
                data['id'] = doc.id
                pagos.append(data)
            return pagos
        except Exception:
            return []
    
    def buscar_facturas_relacionadas(self, cliente_id: str, fecha_abono: str, monto_abono: float) -> List[Dict]:
        """
        Busca facturas a las que se aplicó un abono específico,
        buscando en la subcollection 'pagos' de cada alquiler.
        """
        try:
            facturas_aplicadas = []
            
            # Normalizar cliente_id
            cliente_id_str = str(cliente_id) if cliente_id else None
            if not cliente_id_str:
                return []
            
            # Buscar alquileres del cliente (como STRING)
            try:
                alquileres_str = self.db.collection("alquileres").where("cliente_id", "==", cliente_id_str).stream()
                for alq_doc in alquileres_str:
                    alq_data = alq_doc.to_dict()
                    alq_data['id'] = alq_doc.id
                    
                    # Buscar pagos en este alquiler que coincidan con la fecha del abono
                    pagos = self.obtener_pagos_de_alquiler(alq_doc.id)
                    for pago in pagos:
                        if pago.get('fecha') == fecha_abono:
                            # Este pago coincide con el abono
                            descripcion = (
                                alq_data.get('descripcion') or 
                                alq_data.get('conduce') or 
                                f"Factura {alq_data.get('fecha', '')}"
                            )
                            facturas_aplicadas.append({
                                'descripcion': descripcion,
                                'monto': pago.get('monto', 0),
                                'fecha_factura': alq_data.get('fecha', '')
                            })
            except Exception as e:
                print(f"    Query STRING falló: {e}")
            
            # Buscar alquileres del cliente (como INT)
            try:
                cliente_id_int = int(cliente_id_str)
                alquileres_int = self.db.collection("alquileres").where("cliente_id", "==", cliente_id_int).stream()
                for alq_doc in alquileres_int:
                    alq_data = alq_doc.to_dict()
                    alq_data['id'] = alq_doc.id
                    
                    # Evitar duplicados
                    if any(f['fecha_factura'] == alq_data.get('fecha') for f in facturas_aplicadas):
                        continue
                    
                    pagos = self.obtener_pagos_de_alquiler(alq_doc.id)
                    for pago in pagos:
                        if pago.get('fecha') == fecha_abono:
                            descripcion = (
                                alq_data.get('descripcion') or 
                                alq_data.get('conduce') or 
                                f"Factura {alq_data.get('fecha', '')}"
                            )
                            facturas_aplicadas.append({
                                'descripcion': descripcion,
                                'monto': pago.get('monto', 0),
                                'fecha_factura': alq_data.get('fecha', '')
                            })
            except (ValueError, Exception) as e:
                print(f"    Query INT falló: {e}")
            
            return facturas_aplicadas
            
        except Exception as e:
            print(f"    Error buscando facturas: {e}")
            return []
    
    def generar_descripcion(self, facturas_aplicadas: List[Dict]) -> str:
        """Genera la descripción de aplicación del abono"""
        if len(facturas_aplicadas) == 0:
            return "Sin aplicación registrada"
        
        if len(facturas_aplicadas) == 1:
            fa = facturas_aplicadas[0]
            return f"{fa['descripcion']} (RD$ {fa['monto']:,.2f})"
        
        # Múltiples facturas
        descripciones = []
        for i, fa in enumerate(facturas_aplicadas[:3]):
            desc = fa['descripcion']
            monto = fa['monto']
            descripciones.append(f"{desc} (RD$ {monto:,.2f})")
        
        if len(facturas_aplicadas) > 3:
            restantes = len(facturas_aplicadas) - 3
            monto_restantes = sum(fa['monto'] for fa in facturas_aplicadas[3:])
            descripciones.append(f"+ {restantes} más (RD$ {monto_restantes:,.2f})")
        
        return " + ".join(descripciones)
    
    def diagnosticar(self):
        """Diagnóstico de abonos sin transaccion_descripcion"""
        print("\n" + "="*80)
        print("📊 FASE 1: DIAGNÓSTICO")
        print("="*80)
        print("\n🔍 Buscando abonos sin campo 'transaccion_descripcion'...\n")
        
        try:
            abonos_docs = list(self.db.collection('abonos').stream())
            
            sin_descripcion = []
            con_descripcion = []
            
            for doc in abonos_docs:
                data = doc.to_dict()
                data['id'] = doc.id
                
                if 'transaccion_descripcion' not in data or not data.get('transaccion_descripcion'):
                    sin_descripcion.append(data)
                else:
                    con_descripcion.append(data)
            
            print(f"📋 Total de abonos: {len(abonos_docs)}")
            print(f"✅ Con descripción: {len(con_descripcion)}")
            print(f"⚠️  Sin descripción: {len(sin_descripcion)}")
            
            if sin_descripcion:
                print(f"\n📄 Ejemplos de abonos sin descripción:")
                for abono in sin_descripcion[:5]:
                    fecha = abono.get('fecha', 'Sin fecha')
                    monto = abono.get('monto', 0)
                    cliente_id = abono.get('cliente_id', '?')
                    print(f"   - ID: {abono['id'][:20]}... | Fecha: {fecha} | Cliente: {cliente_id} | Monto: RD$ {monto:,.2f}")
                
                if len(sin_descripcion) > 5:
                    print(f"   ... y {len(sin_descripcion) - 5} más")
            
            return sin_descripcion
            
        except Exception as e:
            print(f"❌ Error durante diagnóstico: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def corregir(self, abonos_sin_descripcion: List[Dict]):
        """Corrige los abonos agregando transaccion_descripcion"""
        print("\n" + "="*80)
        print("🔧 FASE 2: CORRECCIÓN")
        print("="*80)
        
        if not abonos_sin_descripcion:
            print("\n✅ No hay abonos que corregir")
            return
        
        print(f"\n📝 Se corregirán {len(abonos_sin_descripcion)} abonos\n")
        
        respuesta = input("⚠️  ¿Deseas CONTINUAR con la corrección? (escribe 'SI' para confirmar): ").strip()
        
        if respuesta.upper() != 'SI':
            print("\n❌ Corrección cancelada por el usuario")
            return
        
        corregidos = 0
        sin_facturas = 0
        errores = 0
        
        for abono in abonos_sin_descripcion:
            try:
                abono_id = abono['id']
                cliente_id = abono.get('cliente_id')
                fecha = abono.get('fecha')
                monto = abono.get('monto', 0)
                
                if not cliente_id or not fecha:
                    print(f"⚠️  Abono {abono_id[:20]}... sin cliente_id o fecha, saltando...")
                    sin_facturas += 1
                    continue
                
                # Buscar facturas relacionadas
                print(f"🔍 Procesando abono {abono_id[:20]}... (Cliente: {cliente_id}, Fecha: {fecha})")
                facturas = self.buscar_facturas_relacionadas(cliente_id, fecha, monto)
                
                # Generar descripción
                descripcion = self.generar_descripcion(facturas)
                
                # Actualizar en Firestore
                self.db.collection('abonos').document(abono_id).update({
                    'transaccion_descripcion': descripcion
                })
                
                if facturas:
                    print(f"   ✅ {descripcion}")
                else:
                    print(f"   ⚠️  Sin facturas encontradas - '{descripcion}'")
                    sin_facturas += 1
                
                corregidos += 1
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                errores += 1
        
        print("\n" + "-"*80)
        print("📊 RESUMEN DE CORRECCIÓN:")
        print("-"*80)
        print(f"✅ Abonos corregidos: {corregidos}")
        print(f"⚠️  Sin facturas relacionadas: {sin_facturas}")
        print(f"❌ Errores: {errores}")
        print("-"*80 + "\n")
    
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
        abonos_sin_desc = self.diagnosticar()
        
        # Paso 4: Corregir
        if abonos_sin_desc:
            self.corregir(abonos_sin_desc)
        
        print("\n" + "="*80)
        print("✅ PROCESO COMPLETADO")
        print("="*80)
        print("\n📝 Verifica en la aplicación que los abonos ahora")
        print("   muestren información en la columna 'APLICADO A FACTURA'\n")

if __name__ == "__main__":
    try:
        corrector = CorregirAbonosAplicacion()
        corrector.ejecutar()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPresiona ENTER para cerrar...")