#!/usr/bin/env python3
"""
herramientas/subcats_mecanica_por_equipo.py
───────────────────────────────────────────
Script automático que:
  1. Encuentra la categoría MECANICA en Firebase.
  2. Borra TODAS sus subcategorías actuales.
  3. Crea una subcategoría nueva por cada equipo activo.

Uso:
    # Ver qué haría sin tocar nada (dry-run):
    python herramientas/subcats_mecanica_por_equipo.py

    # Aplicar los cambios:
    python herramientas/subcats_mecanica_por_equipo.py --apply

Requiere config_equipos.json en el directorio raíz del proyecto.
"""

import sys
import os
import argparse
import logging

# ── Path al raíz del proyecto ─────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

SEP = "-" * 60

CATEGORIA_OBJETIVO = "MECANICA"


def conectar():
    from config_manager import cargar_configuracion
    from firebase_manager import FirebaseManager

    config = cargar_configuracion()
    fb = config["firebase"]
    return FirebaseManager(fb["credentials_path"], fb["project_id"])


def main(apply: bool):
    print(SEP)
    print(f"  SUBCATEGORIAS {CATEGORIA_OBJETIVO} => EQUIPOS")
    print(f"  Modo: {'APLICAR (--apply)' if apply else 'DRY-RUN (solo lectura)'}")
    print(SEP)

    fm = conectar()
    print("  Firebase conectado OK")
    print()

    # ── 1. Encontrar categoría MECANICA ───────────────────────────────────────
    categorias = fm.obtener_categorias()
    cat = next(
        (c for c in categorias if c["nombre"].strip().upper() == CATEGORIA_OBJETIVO),
        None,
    )
    if not cat:
        print(f"ERROR: No se encontro la categoria '{CATEGORIA_OBJETIVO}' en Firebase.")
        print("       Crea la categoria primero desde el gestor de la app.")
        sys.exit(1)

    cat_id = cat["id"]
    print(f"  Categoria {CATEGORIA_OBJETIVO} encontrada  (id={cat_id})")
    print()

    # ── 2. Subcategorías actuales ─────────────────────────────────────────────
    subcats_actuales = fm.obtener_subcategorias(categoria_id=cat_id)
    print(f"  Subcategorias actuales ({len(subcats_actuales)}):")
    for s in subcats_actuales:
        print(f"    - [{s['id']}]  {s['nombre']}")
    print()

    # ── 3. Equipos activos ────────────────────────────────────────────────────
    equipos = fm.obtener_equipos(activo=True)
    equipos_sorted = sorted(equipos, key=lambda e: e.get("nombre", "").upper())
    print(f"  Equipos activos a crear como subcategorias ({len(equipos_sorted)}):")
    for e in equipos_sorted:
        print(f"    + {e.get('nombre', '(sin nombre)')}")
    print()

    if not equipos_sorted:
        print("ERROR: No se encontraron equipos activos.")
        sys.exit(1)

    # ── Resumen dry-run ───────────────────────────────────────────────────────
    if not apply:
        print(SEP)
        print("  DRY-RUN: no se realizaron cambios.")
        print(f"  Se eliminarian {len(subcats_actuales)} subcategorias.")
        print(f"  Se crearian    {len(equipos_sorted)} subcategorias.")
        print()
        print(f"  Para aplicar: python herramientas/subcats_mecanica_por_equipo.py --apply")
        print(SEP)
        return

    # ── 4. Borrar subcategorías actuales ──────────────────────────────────────
    print(SEP)
    print(f"  BORRANDO subcategorias existentes de {CATEGORIA_OBJETIVO}...")
    eliminadas = 0
    for s in subcats_actuales:
        try:
            fm.eliminar_subcategoria(s["id"])
            print(f"    Eliminada: {s['nombre']}")
            eliminadas += 1
        except Exception as exc:
            print(f"    ERROR eliminando [{s['id']}] {s['nombre']}: {exc}")
    print(f"  {eliminadas}/{len(subcats_actuales)} eliminadas")
    print()

    # ── 5. Crear una subcategoría por equipo ──────────────────────────────────
    print(f"  CREANDO subcategorias por equipo en {CATEGORIA_OBJETIVO}...")
    creadas = 0
    errores = 0
    for e in equipos_sorted:
        nombre = e.get("nombre", "").strip().upper()
        if not nombre:
            print(f"    OMITIDO: equipo sin nombre (id={e['id']})")
            continue
        try:
            nuevo_id = fm.crear_subcategoria(nombre, cat_id)
            print(f"    Creada:  {nombre}  (id={nuevo_id})")
            creadas += 1
        except Exception as exc:
            print(f"    ERROR creando '{nombre}': {exc}")
            errores += 1

    print()
    print(SEP)
    print(f"  RESULTADO FINAL")
    print(f"    Subcategorias eliminadas : {eliminadas}")
    print(f"    Subcategorias creadas    : {creadas}")
    print(f"    Errores                  : {errores}")
    print(SEP)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"Reemplaza subcategorias de {CATEGORIA_OBJETIVO} con los equipos activos."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar cambios en Firebase (sin este flag solo muestra lo que haría).",
    )
    args = parser.parse_args()
    main(apply=args.apply)
