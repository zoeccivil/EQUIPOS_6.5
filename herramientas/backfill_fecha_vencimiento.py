"""
Script: backfill_fecha_vencimiento.py
=======================================
Pone fecha_vencimiento_pago = fecha_alquiler + 45 días a todos los
alquileres que aún no tienen ese campo (o lo tienen vacío/nulo).

Uso:
    python herramientas/backfill_fecha_vencimiento.py
    python herramientas/backfill_fecha_vencimiento.py --solo-listar
    python herramientas/backfill_fecha_vencimiento.py --dry-run
    python herramientas/backfill_fecha_vencimiento.py --dias 30
"""

import sys, os, argparse, json
from datetime import datetime, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import firebase_admin
from firebase_admin import credentials, firestore

DIAS_DEFAULT = 45


def _load_config() -> dict:
    with open(os.path.join(ROOT, "config_equipos.json"), encoding="utf-8") as f:
        return json.load(f)


def _init_firebase(cfg: dict):
    if not firebase_admin._apps:
        cred = credentials.Certificate(cfg["firebase"]["credentials_path"])
        firebase_admin.initialize_app(cred, {"projectId": cfg["firebase"]["project_id"]})
    return firestore.client()


def _fecha_str(fecha: str, dias: int) -> str:
    """Devuelve fecha + dias días en formato YYYY-MM-DD."""
    dt = datetime.strptime(fecha, "%Y-%m-%d")
    return (dt + timedelta(days=dias)).strftime("%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill fecha_vencimiento_pago en alquileres.")
    parser.add_argument("--solo-listar", action="store_true",
                        help="Muestra los alquileres sin vencimiento, sin modificar nada.")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Calcula los cambios pero no los aplica.")
    parser.add_argument("--dias",        type=int, default=DIAS_DEFAULT,
                        help=f"Días de plazo (default: {DIAS_DEFAULT}).")
    args = parser.parse_args()

    cfg = _load_config()
    db  = _init_firebase(cfg)

    print("\n══════════════════════════════════════════════════")
    print("  Backfill fecha_vencimiento_pago — EQUIPOS 6.5")
    print(f"  Plazo: {args.dias} días desde fecha del alquiler")
    print("══════════════════════════════════════════════════\n")

    docs = list(db.collection("alquileres").stream())
    print(f"  Total alquileres en Firebase: {len(docs)}\n")

    # Filtrar los que NO tienen fecha_vencimiento_pago válida
    pendientes = []
    for doc in docs:
        d = doc.to_dict() or {}
        fv = (d.get("fecha_vencimiento_pago") or "").strip()
        if not fv:
            fecha_reg = (d.get("fecha") or "").strip()
            if fecha_reg:
                pendientes.append((doc.id, fecha_reg))
            else:
                print(f"  AVISO: alquiler {doc.id} sin campo 'fecha' — omitido.")

    print(f"  Sin vencimiento asignado: {len(pendientes)}\n")

    if not pendientes:
        print("  Todos los alquileres ya tienen fecha_vencimiento_pago. ✓\n")
        return

    # Mostrar lista
    for alq_id, fecha_reg in sorted(pendientes, key=lambda x: x[1]):
        nuevo_venc = _fecha_str(fecha_reg, args.dias)
        print(f"  {alq_id[:20]:<22}  fecha={fecha_reg}  →  vencimiento={nuevo_venc}")

    print()

    if args.solo_listar:
        print("  Modo --solo-listar. Sin cambios.\n")
        return

    if args.dry_run:
        print("  Modo --dry-run. Sin cambios.\n")
        return

    resp = input(f"  ¿Confirmas aplicar fecha_vencimiento_pago a {len(pendientes)} alquiler(es)?\n"
                 "  Escribe APLICAR para continuar: ").strip()
    if resp != "APLICAR":
        print("  Cancelado.\n")
        return

    # Aplicar en batches de 400
    batch       = db.batch()
    count_batch = 0
    actualizados = 0

    for alq_id, fecha_reg in pendientes:
        nuevo_venc = _fecha_str(fecha_reg, args.dias)
        ref = db.collection("alquileres").document(alq_id)
        batch.update(ref, {"fecha_vencimiento_pago": nuevo_venc})
        count_batch += 1
        actualizados += 1
        if count_batch >= 400:
            batch.commit()
            batch       = db.batch()
            count_batch = 0

    if count_batch > 0:
        batch.commit()

    print(f"\n  ✅  {actualizados} alquiler(es) actualizados con fecha_vencimiento_pago.\n")


if __name__ == "__main__":
    main()
