#!/usr/bin/env python3
"""
herramientas/backfill_subcats_combustible.py
─────────────────────────────────────────────
Para cada gasto de COMBUSTIBLE que tenga subcategoria_id vacío/nulo,
busca el equipo del gasto y le asigna la subcategoría correspondiente
(cuyo nombre coincide con el nombre del equipo).

Ejecución directa (aplica en Firebase sin preguntar).
"""

import sys, os, logging

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

logging.basicConfig(level=logging.WARNING)   # silenciar logs de firebase
SEP = "-" * 60


def main():
    from config_manager import cargar_configuracion
    from firebase_manager import FirebaseManager

    config = cargar_configuracion()
    fb = config["firebase"]
    fm = FirebaseManager(fb["credentials_path"], fb["project_id"])

    print(SEP)
    print("  BACKFILL SUBCATEGORIA EN GASTOS DE COMBUSTIBLE")
    print(SEP)

    # ── Categoría COMBUSTIBLE ─────────────────────────────────────────────────
    categorias = fm.obtener_categorias()
    cat = next((c for c in categorias if c["nombre"].upper() == "COMBUSTIBLE"), None)
    if not cat:
        print("ERROR: Categoria COMBUSTIBLE no encontrada.")
        sys.exit(1)
    cat_id = cat["id"]
    print(f"  Categoria COMBUSTIBLE  id={cat_id}")

    # ── Subcategorías de COMBUSTIBLE (nombre -> id) ───────────────────────────
    subcats = fm.obtener_subcategorias(categoria_id=cat_id)
    subcat_por_nombre = {s["nombre"].upper(): s["id"] for s in subcats}
    print(f"  Subcategorias disponibles: {len(subcat_por_nombre)}")
    for nombre in sorted(subcat_por_nombre):
        print(f"    {nombre}")
    print()

    # ── Equipos (id -> nombre) ────────────────────────────────────────────────
    equipos = fm.obtener_equipos()
    equipo_nombre = {str(e["id"]): e.get("nombre", "").strip().upper() for e in equipos}

    # ── Gastos de COMBUSTIBLE sin subcategoría ────────────────────────────────
    todos = fm.obtener_gastos({"categoria_id": cat_id})
    print(f"  Gastos COMBUSTIBLE total        : {len(todos)}")
    print()

    if not todos:
        print("  No hay gastos de COMBUSTIBLE.")
        print(SEP)
        return

    # ── Actualizar TODOS (sobreescribe referencias rotas también) ─────────────
    actualizados = 0
    sin_equipo   = 0
    sin_match    = 0

    for g in todos:
        raw = g.get("equipo_id")
        # Normalizar: '3.0' → '3', 3 → '3', '' → ''
        try:
            eq_id = str(int(float(raw))) if raw not in (None, "", "None") else ""
        except (ValueError, TypeError):
            eq_id = str(raw or "")
        eq_nombre = equipo_nombre.get(eq_id, "")

        if not eq_nombre:
            print(f"  [SIN EQUIPO]  gasto {g['id']}  fecha={g.get('fecha')}  equipo_id={eq_id!r}")
            sin_equipo += 1
            continue

        sub_id = subcat_por_nombre.get(eq_nombre)
        if not sub_id:
            print(f"  [SIN MATCH]   gasto {g['id']}  equipo='{eq_nombre}'  (no hay subcategoria con ese nombre)")
            sin_match += 1
            continue

        fm.actualizar_gasto(g["id"], {"subcategoria_id": sub_id})
        print(f"  OK  {g.get('fecha')}  {eq_nombre:<30}  subcat_id={sub_id}")
        actualizados += 1

    print()
    print(SEP)
    print(f"  Actualizados  : {actualizados}")
    print(f"  Sin equipo    : {sin_equipo}")
    print(f"  Sin match     : {sin_match}")
    print(SEP)


if __name__ == "__main__":
    main()
