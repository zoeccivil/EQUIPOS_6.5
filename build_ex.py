import PyInstaller.__main__
import os
from pathlib import Path

# Ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent

# Archivo principal
MAIN_SCRIPT = BASE_DIR / "main_qt.py"

# Nombre del ejecutable
APP_NAME = "EQUIPOS_4_0"

# Carpetas/archivos de datos que quieras incluir en el exe
# Formato PyInstaller: "origen;destino_relativo_dentro_del_pkg"
extra_datas = []

# Config
config_file = BASE_DIR / "config_equipos.json"
if config_file.exists():
    extra_datas.append(f"{config_file};.")

# Carpeta de diálogos
dialogos_dir = BASE_DIR / "dialogos"
if dialogos_dir.exists():
    extra_datas.append(f"{dialogos_dir};dialogos")

# Otros recursos opcionales (ajusta según tu proyecto)
for folder_name in ["icons", "images", "themes", "docs"]:
    folder = BASE_DIR / folder_name
    if folder.exists():
        extra_datas.append(f"{folder};{folder_name}")

# Archivo .ico opcional para el exe
icon_path = BASE_DIR / "icono_equipos.ico"  # cambia si tienes otro nombre
icon_arg = []
if icon_path.exists():
    icon_arg = ["--icon", str(icon_path)]


def build():
    args = [
        str(MAIN_SCRIPT),
        "--name", APP_NAME,
        "--onefile",           # un solo .exe
        "--noconsole",         # sin ventana de consola
        "--clean",             # limpia temporales de PyInstaller
        "--log-level", "WARN", # menos ruido
    ]

    # Añadir datos
    for d in extra_datas:
        args += ["--add-data", d]

    # Añadir icono si existe
    args += icon_arg

    # Opcional: excluir módulos que no uses para reducir tamaño
    # args += ["--exclude-module", "tkinter"]

    print("Ejecutando PyInstaller con argumentos:")
    for a in args:
        print(" ", a)

    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    build()