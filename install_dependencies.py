# install_dependencies.py

"""
Script para instalar todas las dependencias necesarias
"""

import subprocess
import sys

def instalar_dependencias():
    """Instala todas las dependencias del proyecto"""
    
    dependencias = [
        'PyQt6',
        'PyQt6-Charts',
        'firebase-admin',
        'openpyxl',
        'twilio',
        'requests',
        'reportlab',  # Para generación de PDFs
    ]
    
    print("=" * 60)
    print("INSTALACIÓN DE DEPENDENCIAS - ZOEC EQUIPOS")
    print("=" * 60)
    print()
    
    for dependencia in dependencias:
        print(f"📦 Instalando {dependencia}...")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', dependencia
            ])
            print(f"✅ {dependencia} instalado correctamente\n")
        except subprocess.CalledProcessError:
            print(f"❌ Error instalando {dependencia}\n")
    
    print("=" * 60)
    print("✅ INSTALACIÓN COMPLETADA")
    print("=" * 60)
    print()
    print("Para ejecutar la aplicación, use:")
    print("  python main_integrado.py")
    print()


if __name__ == "__main__":
    instalar_dependencias()