"""
Script: deduplicar_subcategorias.py
=====================================
Elimina subcategorías duplicadas (mismo nombre, sin importar la categoría),
conservando UN documento por nombre y redirigiendo los gastos que
apuntaban a los duplicados eliminados hacia el que se conserva.

Uso:
    python herramientas/deduplicar_subcategorias.py
    python herramientas/deduplicar_subcategorias.py --solo-listar
    python herramientas/deduplicar_subcategorias.py --debug
    python herramientas/deduplicar_subcategorias.py --dry-run
"""

import sys
import os
import argparse
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import json
import firebase_admin
from firebase_admin import credentials, firestore


# ── config ─────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    path = os.path.join(ROOT, "config_equipos.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _init_firebase(cfg: dict):
    if not firebase_admin._apps:
        cred = credentials.Certificate(cfg["firebase"]["credentials_path"])
        firebase_admin.initialize_app(cred, {
            "projectId": cfg["firebase"]["project_id"],
        })
    return firestore.client()


# ── helpers ────────────────────────────────────────────────────────────────────

def _cargar_categorias(db) -> dict:
    """Devuelve {cat_id: nombre}."""
    return {
        doc.id: (doc.to_dict() or {}).get("nombre", doc.id)
        for doc in db.collection("categorias").stream()
    }


def _cargar_subcategorias(db) -> list[dict]:
    """Devuelve lista de {id, nombre, categoria_id}."""
    result = []
    for doc in db.collection("subcategorias").stream():
        d = doc.to_dict() or {}
        result.append({
            "id":           doc.id,
            "nombre":       (d.get("nombre") or "").strip(),
            "categoria_id": str(d.get("categoria_id") or ""),
        })
    return result


def _detectar_duplicados(subs: list[dict]) -> dict:
    """
    Agrupa subcategorías por nombre (sin distinguir categoría).
    Devuelve sólo los grupos con más de un elemento.
    La clave es nombre.upper().
    """
    grupos: dict[str, list] = defaultdict(list)
    for s in subs:
        grupos[s["nombre"].upper()].append(s)

    return {k: v for k, v in grupos.items() if len(v) > 1}


# ── acciones ───────────────────────────────────────────────────────────────────

def debug_dump(db):
    """Muestra todos los documentos crudos de la colección subcategorias."""
    cats = _cargar_categorias(db)
    print("\n  ── RAW subcategorias ────────────────────────────────────────")
    total = 0
    for doc in db.collection("subcategorias").stream():
        d = doc.to_dict() or {}
        cat_id  = str(d.get("categoria_id") or "")
        cat_nom = cats.get(cat_id, f"[?{cat_id}]")
        nombre  = d.get("nombre", "<sin nombre>")
        print(f"  id={doc.id:<28}  cat={cat_nom:<20}  nombre={nombre}")
        total += 1
    print(f"\n  Total: {total} documentos\n")


def listar_duplicados(db) -> dict:
    cats = _cargar_categorias(db)
    subs = _cargar_subcategorias(db)
    duplicados = _detectar_duplicados(subs)

    if not duplicados:
        print("\n  No se encontraron subcategorías duplicadas. ✓\n")
        return {}

    total_a_borrar = 0
    print(f"\n  Se encontraron {len(duplicados)} grupo(s) con duplicados:\n")
    for nombre, grupo in sorted(duplicados.items()):
        conservar = grupo[0]
        borrar    = grupo[1:]
        cat_nom   = cats.get(conservar["categoria_id"], f"[{conservar['categoria_id']}]")
        print(f"  {nombre}  (cat conservada: {cat_nom})")
        print(f"       CONSERVAR  → id={conservar['id']}  cat={cat_nom}")
        for s in borrar:
            cn = cats.get(s["categoria_id"], f"[{s['categoria_id']}]")
            print(f"       ELIMINAR   → id={s['id']}  cat={cn}")
        print()
        total_a_borrar += len(borrar)

    print(f"  Total duplicados a eliminar: {total_a_borrar}\n")
    return duplicados


def deduplicar(db, dry_run: bool = False):
    cats = _cargar_categorias(db)
    subs = _cargar_subcategorias(db)
    duplicados = _detectar_duplicados(subs)

    if not duplicados:
        print("\n  No hay duplicados. Nada que hacer. ✓\n")
        return

    # Construir mapa: id_a_eliminar → id_a_conservar
    remap: dict[str, str] = {}
    ids_a_eliminar: list[str] = []
    total_grupos = len(duplicados)
    total_a_borrar = sum(len(v) - 1 for v in duplicados.values())

    for nombre, grupo in sorted(duplicados.items()):
        conservar  = grupo[0]
        borrar     = grupo[1:]
        cat_nom    = cats.get(conservar["categoria_id"], f"[{conservar['categoria_id']}]")
        print(f"  {nombre}  (conserva cat: {cat_nom})")
        print(f"       CONSERVAR  → {conservar['id']}")
        for s in borrar:
            cn = cats.get(s["categoria_id"], f"[{s['categoria_id']}]")
            print(f"       ELIMINAR   → {s['id']}  (cat: {cn})")
            remap[s["id"]] = conservar["id"]
            ids_a_eliminar.append(s["id"])
        print()

    print(f"  {total_grupos} grupo(s) · {total_a_borrar} duplicado(s) a eliminar")

    if dry_run:
        print("\n  Modo --dry-run: ningún cambio aplicado.\n")
        return

    resp = input("\n  ¿Confirmas? Escribe DEDUPLICAR para continuar: ").strip()
    if resp != "DEDUPLICAR":
        print("  Cancelado.\n")
        return

    ids_set = set(ids_a_eliminar)

    # ── 1. Redirigir gastos ───────────────────────────────────────────────────
    print("\n  [1/2] Redirigiendo gastos a la subcategoría conservada...")
    gastos_col  = db.collection("gastos")
    batch       = db.batch()
    count_batch = 0
    afectados   = 0

    for doc in gastos_col.stream():
        d   = doc.to_dict() or {}
        sid = str(d.get("subcategoria_id") or "")
        if sid in ids_set:
            nuevo_id = remap[sid]
            batch.update(doc.reference, {"subcategoria_id": nuevo_id})
            count_batch += 1
            afectados   += 1
            if count_batch >= 400:
                batch.commit()
                batch       = db.batch()
                count_batch = 0

    if count_batch > 0:
        batch.commit()
    print(f"       ✓ {afectados} gasto(s) redirigidos.")

    # ── 2. Eliminar subcategorías duplicadas ──────────────────────────────────
    print("\n  [2/2] Eliminando subcategorías duplicadas...")
    batch       = db.batch()
    count_batch = 0
    borrados    = 0

    for sub_id in ids_a_eliminar:
        ref = db.collection("subcategorias").document(sub_id)
        batch.delete(ref)
        count_batch += 1
        borrados    += 1
        if count_batch >= 400:
            batch.commit()
            batch       = db.batch()
            count_batch = 0

    if count_batch > 0:
        batch.commit()
    print(f"       ✓ {borrados} subcategoría(s) duplicada(s) eliminadas.")

    print(f"\n  ✅  Listo. Conservados {total_grupos} registros únicos.\n")


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Elimina subcategorías duplicadas en Firebase."
    )
    parser.add_argument("--solo-listar", action="store_true",
                        help="Muestra los duplicados sin borrar nada.")
    parser.add_argument("--debug",       action="store_true",
                        help="Muestra todos los documentos crudos de subcategorias.")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Calcula cambios pero no los aplica.")
    args = parser.parse_args()

    cfg = _load_config()
    db  = _init_firebase(cfg)

    print("\n══════════════════════════════════════════════")
    print("  Deduplicador de Subcategorías — EQUIPOS 6.5")
    print("══════════════════════════════════════════════")

    if args.debug:
        debug_dump(db)
        return

    if args.solo_listar:
        listar_duplicados(db)
        return

    deduplicar(db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
