"""
backfill_galones.py
===================
Calcula y rellena el campo `galones` en los gastos de COMBUSTIBLE que no lo tengan,
usando la tabla oficial de precios del GASOIL REGULAR publicada por el Ministerio
de Industria, Comercio y MIPYMES de la República Dominicana.

Precio usado: "Gasoil Regular" → columna "PRECIO OFICIAL A PAGAR POR EL PUBLICO (RD$/GL)"
  - Q1 2025 (Ene–Mar):  RD$ 221.60  (congelado)
  - Q2 2025 (Abr–Jun):  RD$ 221.60  (congelado)
  - Q3 2025 (Jul–Sep):  RD$ 224.80  (congelado, subió Jun 28)
  - Q4 2025 (Oct–Dic):  RD$ 224.80  (congelado)
  - Ene–Mar 20, 2026:   Interpolación lineal 224.80 → 242.30 (prorateo 12 pasos)
  - Mar 21–27, 2026:    RD$ 242.30  (aviso oficial MICM)
  - Posteriores:        RD$ 242.30  (último precio conocido)

Uso:
    python backfill_galones.py            # dry-run (no escribe nada)
    python backfill_galones.py --apply    # aplica los cambios en Firestore

Lógica:
    galones = monto / precio_galon_vigente_en_fecha_del_gasto
"""

import sys
import os
import json
import argparse
import logging
from datetime import date, datetime

# ── Agregar el directorio del proyecto al path ───────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backfill_galones")

# ─────────────────────────────────────────────────────────────────────────────
# TABLA DE PRECIOS
# Fuente: Histórico oficial MICM – columna "GASOIL REGULAR"
#         Precio Oficial al Público (RD$/galón)
#
# Nota sobre precios congelados:
#   El gobierno dominicano congela el precio de la gasolina/gasoil regular
#   en períodos específicos. Las celdas azules en las tablas históricas
#   indican precio congelado = mismo valor toda la semana/período.
#
# Interpolación 2026:
#   Desde el último precio conocido (224.80, hasta Jan 2) hasta el primer
#   aviso oficial de 2026 disponible (242.30, semana Mar 21-27) se hace
#   una interpolación lineal de 12 pasos (≈ RD$ 1.46/semana).
# ─────────────────────────────────────────────────────────────────────────────

# step = (242.30 - 224.80) / 12 = 1.4583...
_STEP_2026 = round((242.30 - 224.80) / 12, 4)  # 1.4583

PRECIO_POR_SEMANA = [
    # ── PRIMER TRIMESTRE 2025 ─────────────────────────────────────────────────
    # GASOIL REGULAR congelado en RD$ 221.60 todo el trimestre
    ("2025-01-04", "2025-01-10", 221.60),
    ("2025-01-11", "2025-01-17", 221.60),
    ("2025-01-18", "2025-01-24", 221.60),
    ("2025-01-25", "2025-01-31", 221.60),
    ("2025-02-01", "2025-02-07", 221.60),
    ("2025-02-08", "2025-02-14", 221.60),
    ("2025-02-15", "2025-02-21", 221.60),
    ("2025-02-22", "2025-02-28", 221.60),
    ("2025-03-01", "2025-03-07", 221.60),
    ("2025-03-08", "2025-03-14", 221.60),
    ("2025-03-15", "2025-03-21", 221.60),
    ("2025-03-22", "2025-03-28", 221.60),
    # ── SEGUNDO TRIMESTRE 2025 ────────────────────────────────────────────────
    # GASOIL REGULAR congelado en RD$ 221.60 todo el trimestre
    ("2025-03-29", "2025-04-04", 221.60),
    ("2025-04-05", "2025-04-11", 221.60),
    ("2025-04-12", "2025-04-18", 221.60),
    ("2025-04-19", "2025-04-25", 221.60),
    ("2025-04-26", "2025-05-02", 221.60),
    ("2025-05-03", "2025-05-09", 221.60),
    ("2025-05-10", "2025-05-16", 221.60),
    ("2025-05-17", "2025-05-23", 221.60),
    ("2025-05-24", "2025-05-30", 221.60),
    ("2025-05-31", "2025-06-06", 221.60),
    ("2025-06-07", "2025-06-13", 221.60),
    ("2025-06-14", "2025-06-20", 221.60),
    ("2025-06-21", "2025-06-27", 221.60),
    # ── TERCER TRIMESTRE 2025 ─────────────────────────────────────────────────
    # GASOIL REGULAR sube a RD$ 224.80 a partir del 28 de junio
    ("2025-06-28", "2025-07-04", 224.80),
    ("2025-07-05", "2025-07-11", 224.80),
    ("2025-07-12", "2025-07-18", 224.80),
    ("2025-07-19", "2025-07-25", 224.80),
    ("2025-07-26", "2025-08-01", 224.80),
    ("2025-08-02", "2025-08-08", 224.80),
    ("2025-08-09", "2025-08-15", 224.80),
    ("2025-08-16", "2025-08-22", 224.80),
    ("2025-08-23", "2025-08-29", 224.80),
    ("2025-08-30", "2025-09-05", 224.80),
    ("2025-09-06", "2025-09-12", 224.80),
    ("2025-09-13", "2025-09-19", 224.80),
    ("2025-09-20", "2025-09-26", 224.80),
    ("2025-09-27", "2025-10-03", 224.80),
    # ── CUARTO TRIMESTRE 2025 ─────────────────────────────────────────────────
    # GASOIL REGULAR congelado en RD$ 224.80 todo el trimestre
    ("2025-10-04", "2025-10-10", 224.80),
    ("2025-10-11", "2025-10-17", 224.80),
    ("2025-10-18", "2025-10-24", 224.80),
    ("2025-10-25", "2025-10-31", 224.80),
    ("2025-11-01", "2025-11-07", 224.80),
    ("2025-11-08", "2025-11-14", 224.80),
    ("2025-11-15", "2025-11-21", 224.80),
    ("2025-11-22", "2025-11-28", 224.80),
    ("2025-11-29", "2025-12-05", 224.80),
    ("2025-12-06", "2025-12-12", 224.80),
    ("2025-12-13", "2025-12-19", 224.80),
    ("2025-12-20", "2025-12-26", 224.80),
    ("2025-12-27", "2026-01-02", 224.80),
    # ── 2026: interpolación lineal 224.80 → 242.30 en 12 pasos ──────────────
    # Paso = (242.30 - 224.80) / 12 ≈ RD$ 1.46/semana
    ("2026-01-03", "2026-01-09",  round(224.80 + _STEP_2026 *  1, 2)),  # ≈ 226.26
    ("2026-01-10", "2026-01-16",  round(224.80 + _STEP_2026 *  2, 2)),  # ≈ 227.72
    ("2026-01-17", "2026-01-23",  round(224.80 + _STEP_2026 *  3, 2)),  # ≈ 229.17
    ("2026-01-24", "2026-01-30",  round(224.80 + _STEP_2026 *  4, 2)),  # ≈ 230.63
    ("2026-01-31", "2026-02-06",  round(224.80 + _STEP_2026 *  5, 2)),  # ≈ 232.09
    ("2026-02-07", "2026-02-13",  round(224.80 + _STEP_2026 *  6, 2)),  # ≈ 233.55
    ("2026-02-14", "2026-02-20",  round(224.80 + _STEP_2026 *  7, 2)),  # ≈ 235.01
    ("2026-02-21", "2026-02-27",  round(224.80 + _STEP_2026 *  8, 2)),  # ≈ 236.46
    ("2026-02-28", "2026-03-06",  round(224.80 + _STEP_2026 *  9, 2)),  # ≈ 237.92
    ("2026-03-07", "2026-03-13",  round(224.80 + _STEP_2026 * 10, 2)),  # ≈ 239.38
    ("2026-03-14", "2026-03-20",  round(224.80 + _STEP_2026 * 11, 2)),  # ≈ 240.84
    # ── Aviso oficial MICM: semana 21-27 Mar 2026 ────────────────────────────
    ("2026-03-21", "2026-03-27", 242.30),
    # ── Prorateo Mar 28 → Abr 10 (brecha 2 sem, paso = (249.30-242.30)/3 = 2.33) ──
    ("2026-03-28", "2026-04-03", 244.63),   # 242.30 + 1×2.33
    ("2026-04-04", "2026-04-10", 246.97),   # 242.30 + 2×2.33
    # ── Aviso oficial MICM: semana 11-17 Abr 2026 ────────────────────────────
    ("2026-04-11", "2026-04-17", 249.30),
    # ── A partir de aquí: agregar nuevos avisos cuando se publiquen ───────────
    # ("2026-04-18", "2026-04-24", XXX.XX),
]

# Precio fallback: el último de la tabla (más reciente disponible)
PRECIO_FALLBACK = PRECIO_POR_SEMANA[-1][2]  # 249.30

# ── Compilar tabla a objetos date ─────────────────────────────────────────────
_TABLA: list[tuple[date, date, float]] = [
    (
        datetime.strptime(ini, "%Y-%m-%d").date(),
        datetime.strptime(fin, "%Y-%m-%d").date(),
        precio,
    )
    for ini, fin, precio in PRECIO_POR_SEMANA
]


def obtener_precio(fecha_str: str) -> tuple[float, str]:
    """
    Retorna (precio_galon, fuente) para una fecha dada (formato yyyy-MM-dd).
    fuente: 'tabla_exacta' | 'fallback_futuro' | 'fallback_pasado'
    """
    try:
        d = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return PRECIO_FALLBACK, "fallback_pasado"

    # Búsqueda exacta en tabla
    for ini, fin, precio in _TABLA:
        if ini <= d <= fin:
            return precio, "tabla_exacta"

    # Fecha posterior al último registro → usar el más reciente
    ultimo_fin = _TABLA[-1][1]
    if d > ultimo_fin:
        return PRECIO_FALLBACK, "fallback_futuro"

    # Fecha anterior al primer registro → usar el más cercano hacia adelante
    return _TABLA[0][2], "fallback_pasado"


# ── Conexión a Firebase ────────────────────────────────────────────────────────
def cargar_config() -> dict:
    config_path = os.path.join(PROJECT_DIR, "config_equipos.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def conectar_firestore(config: dict):
    """Inicializa Firebase Admin SDK y retorna el cliente Firestore."""
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        cred_path = config["firebase"]["credentials_path"]
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

    return firestore.client()


# ── Lógica principal ──────────────────────────────────────────────────────────
def main(apply: bool):
    config  = cargar_config()
    db      = conectar_firestore(config)

    # 1. Resolver ID de la categoría COMBUSTIBLE
    cat_id = None
    for doc in db.collection("categorias").stream():
        if doc.to_dict().get("nombre", "").upper() == "COMBUSTIBLE":
            cat_id = doc.id
            break

    if not cat_id:
        logger.error("No se encontró la categoría COMBUSTIBLE en Firestore.")
        sys.exit(1)

    logger.info(f"Categoría COMBUSTIBLE → ID = {cat_id}")

    # 2. Obtener todos los gastos y filtrar por categoría (tolerante a tipo int/str)
    todos  = list(db.collection("gastos").stream())
    comb   = [
        {**d.to_dict(), "id": d.id}
        for d in todos
        if str(d.to_dict().get("categoria_id", "")) == str(cat_id)
    ]

    logger.info(f"Gastos COMBUSTIBLE encontrados: {len(comb)}")

    con_galones = [g for g in comb if float(g.get("galones") or 0) > 0]
    sin_galones = [g for g in comb if float(g.get("galones") or 0) <= 0]

    logger.info(f"  Ya tienen galones        : {len(con_galones)}")
    logger.info(f"  Sin galones (pendientes) : {len(sin_galones)}")

    if not sin_galones:
        logger.info("Nada que hacer. Todos los registros ya tienen galones.")
        return

    # 3. Mostrar / aplicar
    COL = "{:<28}  {:<12}  {:>11}  {:>11}  {:>10}  {}"
    SEP = "-" * 88
    print()
    print(SEP)
    print(COL.format("ID", "Fecha", "Monto RD$", "Precio/Gal", "Galones", "Fuente"))
    print(SEP)

    actualizados = 0
    omitidos     = 0
    fallbacks    = 0

    for g in sorted(sin_galones, key=lambda x: x.get("fecha", "")):
        gid   = g["id"]
        fecha = g.get("fecha", "")
        monto = g.get("monto")

        if not monto or float(monto) <= 0:
            logger.warning(f"  OMITIDO {gid} — monto inválido ({monto})")
            omitidos += 1
            continue

        monto_f        = float(monto)
        precio, fuente = obtener_precio(fecha)
        galones        = monto_f / precio

        if "fallback" in fuente:
            fallbacks += 1
            fuente_tag = f"! {fuente}"
        else:
            fuente_tag = "* oficial"

        print(COL.format(
            gid[:28],
            fecha,
            f"{monto_f:,.2f}",
            f"{precio:.2f}",
            f"{galones:.3f}",
            fuente_tag,
        ))

        if apply:
            db.collection("gastos").document(gid).update({"galones": round(galones, 3)})
            actualizados += 1

    print(SEP)
    print()

    if apply:
        logger.info(f"OK Galones actualizados: {actualizados}")
    else:
        pendientes = len(sin_galones) - omitidos
        logger.info(f"DRY-RUN — se actualizarían {pendientes} registros.")
        logger.info("Ejecuta con --apply para escribir en Firestore.")

    if fallbacks:
        logger.warning(
            f"  {fallbacks} registro(s) usaron precio interpolado/estimado "
            f"(fuera de tabla oficial). Recalcular cuando se publique el aviso."
        )
    if omitidos:
        logger.warning(f"  {omitidos} registro(s) omitidos por monto inválido o cero.")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill 'galones' en gastos de COMBUSTIBLE usando precios oficiales MICM"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica los cambios en Firestore (sin este flag es solo simulación)",
    )
    args = parser.parse_args()

    modo = "APLICANDO CAMBIOS EN FIRESTORE" if args.apply else "DRY-RUN (sin cambios)"
    logger.info(f"═══ Modo: {modo} ═══")
    main(apply=args.apply)
