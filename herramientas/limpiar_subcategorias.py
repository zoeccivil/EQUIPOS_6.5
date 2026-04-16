"""
Script: limpiar_subcategorias.py
=================================
Borra TODAS las subcategorías de Firebase y limpia las referencias
subcategoria_id en los gastos que las apuntaban.

Uso:
    python herramientas/limpiar_subcategorias.py
    python herramientas/limpiar_subcategorias.py --solo-listar
    python herramientas/limpiar_subcategorias.py --categoria COMPRA
"""

import sys
import os
import argparse

# ── ruta raíz del proyecto ─────────────────────────────────────────────────────
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
            "id":          doc.id,
            "nombre":      d.get("nombre", ""),
            "categoria_id": str(d.get("categoria_id") or ""),
        })
    return result


def _contar_gastos_con_subcat(db, sub_id: str) -> int:
    count = 0
    for doc in db.collection("gastos").stream():
        if str((doc.to_dict() or {}).get("subcategoria_id", "")) == sub_id:
            count += 1
    return count


# ── acciones principales ───────────────────────────────────────────────────────

def listar(db, filtro_cat_nombre: str | None = None):
    cats  = _cargar_categorias(db)
    subs  = _cargar_subcategorias(db)

    if filtro_cat_nombre:
        fn = filtro_cat_nombre.strip().upper()
        cat_ids_filtro = {cid for cid, nom in cats.items() if nom.upper() == fn}
        subs = [s for s in subs if s["categoria_id"] in cat_ids_filtro]

    # Agrupar por categoría
    grupos: dict[str, list] = {}
    for s in subs:
        cat_nombre = cats.get(s["categoria_id"], f"[sin cat: {s['categoria_id']}]")
        grupos.setdefault(cat_nombre, []).append(s)

    total = 0
    for cat_nombre in sorted(grupos):
        items = grupos[cat_nombre]
        print(f"\n  📁  {cat_nombre}  ({len(items)} subcats)")
        for s in sorted(items, key=lambda x: x["nombre"]):
            print(f"       - {s['nombre']:<40}  id={s['id']}")
        total += len(items)

    print(f"\n  Total: {total} subcategoría(s)\n")
    return subs


def borrar_todo(db, filtro_cat_nombre: str | None = None,
                limpiar_gastos: bool = True):
    cats = _cargar_categorias(db)
    subs = _cargar_subcategorias(db)

    if filtro_cat_nombre:
        fn = filtro_cat_nombre.strip().upper()
        cat_ids_filtro = {cid for cid, nom in cats.items() if nom.upper() == fn}
        subs = [s for s in subs if s["categoria_id"] in cat_ids_filtro]

    if not subs:
        print("  No hay subcategorías que borrar con ese filtro.")
        return

    print(f"\n  Se borrarán {len(subs)} subcategoría(s).\n")

    # ── confirmación ──────────────────────────────────────────────────────────
    resp = input("  ¿Confirmas? Escribe BORRAR para continuar: ").strip()
    if resp != "BORRAR":
        print("  Cancelado.")
        return

    ids_a_borrar = {s["id"] for s in subs}

    # ── 1. Borrar documentos de subcategorias ─────────────────────────────────
    print("\n  [1/2] Eliminando subcategorías...")
    batch = db.batch()
    count_batch = 0
    borrados = 0
    for s in subs:
        ref = db.collection("subcategorias").document(s["id"])
        batch.delete(ref)
        count_batch += 1
        borrados    += 1
        if count_batch >= 400:          # Firestore: max 500 ops por batch
            batch.commit()
            batch      = db.batch()
            count_batch = 0
    if count_batch > 0:
        batch.commit()
    print(f"       ✓ {borrados} subcategoría(s) eliminadas.")

    # ── 2. Limpiar subcategoria_id en gastos ──────────────────────────────────
    if limpiar_gastos:
        print("\n  [2/2] Limpiando referencias en gastos...")
        gastos_col = db.collection("gastos")
        batch      = db.batch()
        count_batch = 0
        afectados  = 0
        for doc in gastos_col.stream():
            d   = doc.to_dict() or {}
            sid = str(d.get("subcategoria_id") or "")
            if sid in ids_a_borrar:
                batch.update(doc.reference, {"subcategoria_id": None})
                count_batch += 1
                afectados   += 1
                if count_batch >= 400:
                    batch.commit()
                    batch       = db.batch()
                    count_batch = 0
        if count_batch > 0:
            batch.commit()
        print(f"       ✓ {afectados} gasto(s) con subcategoria_id limpiados.")
    else:
        print("\n  [2/2] Omitido (--no-limpiar-gastos).")

    print("\n  ✅  Listo. Ahora puedes crear las nuevas subcategorías desde la app.\n")


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Limpia subcategorías de Firebase."
    )
    parser.add_argument("--solo-listar",       action="store_true",
                        help="Solo muestra las subcategorías, no borra nada.")
    parser.add_argument("--categoria",         metavar="NOMBRE",
                        help="Filtra por nombre de categoría (ej. COMPRA).")
    parser.add_argument("--no-limpiar-gastos", action="store_true",
                        help="No limpia subcategoria_id en los gastos.")
    args = parser.parse_args()

    cfg = _load_config()
    db  = _init_firebase(cfg)

    print("\n══════════════════════════════════════════════")
    print("  Limpiador de Subcategorías — EQUIPOS 6.5")
    print("══════════════════════════════════════════════")

    if args.categoria:
        print(f"\n  Filtro de categoría: {args.categoria.upper()}")

    subs = listar(db, filtro_cat_nombre=args.categoria)

    if args.solo_listar:
        print("  Modo solo-listar. Saliendo.\n")
        return

    if not subs:
        return

    borrar_todo(
        db,
        filtro_cat_nombre=args.categoria,
        limpiar_gastos=not args.no_limpiar_gastos,
    )


if __name__ == "__main__":
    main()
