"""
Generador de reportes PDF para EQUIPOS 4.0
Adaptado para trabajar con Firebase y Firebase Storage
"""

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib import colors
from datetime import datetime
import os
import tempfile
import logging

import logging
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.platypus import Paragraph, Table, TableStyle, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from xml.sax.saxutils import escape
logger = logging.getLogger(__name__)




# Recomendado al inicio del archivo:
# from datetime import datetime
# try:
#     import pandas as pd  # opcional, solo para compatibilidad
# except ImportError:
#     pd = None

class ReportGenerator:
    """
    Generador de reportes PDF con soporte para conduces desde Firebase Storage.
    """

    def __init__(
        self,
        data=None,
        title: str = "",
        cliente: str = "",
        date_range: str = "",
        currency_symbol: str = "RD$",
        storage_manager=None,
        column_map: dict | None = None,
    ):
        """
        Inicializa el generador de reportes.

        Args:
            data: Lista de diccionarios con los registros (facturas) a incluir en el reporte.
            title: Título del reporte (si está vacío se usa "REPORTE DE ALQUILERES").
            cliente: Nombre del cliente (o "GENERAL" si es estado general).
            date_range: Rango de fechas a mostrar en el encabezado (ej: '2025-01-01 a 2025-11-18').
            currency_symbol: Símbolo de moneda (por defecto 'RD$').
            storage_manager: Instancia de StorageManager (para resolver links de conduces).
            column_map: Mapeo de columnas {clave_dato: 'Etiqueta en PDF'}.
        """
        # Datos base que usa to_pdf
        self.data: list[dict] = list(data or [])
        self.title: str = title or "REPORTE DE ALQUILERES"
        self.cliente: str = cliente or ""
        self.date_range: str = date_range or ""
        self.currency_symbol: str = currency_symbol or "RD$"
        self.storage_manager = storage_manager
        self.column_map: dict = dict(column_map or {})

        # Metadatos
        self.fecha_generacion: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Estado de cuenta: entradas opcionales que puede setear el llamador (AppGUI)
        # Si no las setean, to_pdf calcula/agrupa lo necesario con fallbacks.
        self.abonos: list[dict] = []                 # lista cruda de abonos (opcional)
        self.abonos_por_fecha: list[tuple] = []      # [(fecha, total_en_fecha)] opcional
        self.total_facturado: float = 0.0
        self.total_abonado: float = 0.0
        self.saldo: float = 0.0

        # Compatibilidad opcional con código legado que esperaba un DataFrame.
        # to_pdf NO depende de self.df; esto es por si lo usas en otros reportes.
        self.df = None
        try:
            if 'pd' in globals() and pd is not None and self.data:
                raw_df = pd.DataFrame([dict(r) for r in self.data])
                if self.column_map and not raw_df.empty:
                    cols_a_usar = [c for c in self.column_map.keys() if c in raw_df.columns]
                    self.df = raw_df[cols_a_usar].rename(columns=self.column_map)
                else:
                    self.df = raw_df
        except Exception:
            # Si pandas no está o falla, seguimos sin self.df
            self.df = None

        # Archivos temporales descargados (si bajas conductos para otros flujos)
        self.temp_files: list[str] = []
    
    def _group_abonos_by_date(self, abonos: list[dict]) -> list[tuple[str, float]]:
        """
        Devuelve [(fecha 'YYYY-MM-DD', total_en_fecha), ...] ordenada por fecha asc.
        """
        acum = {}
        for a in abonos or []:
            fecha = a.get("fecha")
            if not fecha:
                continue
            monto = float(a.get("monto", 0) or 0.0)
            acum[fecha] = acum.get(fecha, 0.0) + monto
        return sorted(acum.items(), key=lambda x: x[0])


    def _resolve_condstorage_url(self, value: str) -> str:
        """
        Convierte 'CondStorage' (path o URL) en una URL final:
        - Si ya es URL, la devuelve.
        - Si es path de Storage y hay storage_manager, genera URL de descarga.
        """
        if not value:
            return ""
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
        try:
            sm = getattr(self, "storage_manager", None)
            if sm:
                return sm.get_download_url(value) or value
            return value
        except Exception:
            return value


    def _make_table_abonos_por_fecha(self, abonos_por_fecha: list[tuple[str, float]], currency_symbol: str = "RD$"):
        """
        Construye una tabla ReportLab: Fecha | Total Abonado
        """
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib import colors

        data = [["Fecha", "Total Abonado"]]
        for fecha, total in abonos_por_fecha or []:
            data.append([fecha, f"{currency_symbol} {total:,.2f}"])

        tbl = Table(data, hAlign="LEFT")
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF1E0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#A35D00")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#A35D00")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ]))
        return tbl


    def _postprocess_row_for_pdf(self, row: dict, column_map: dict) -> list:
        """
        Transforma un dict 'row' en una lista de celdas según column_map.
        - Convierte CondStorage en un link "Ver" si hay URL.
        - Formatea horas y monto.
        """
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import getSampleStyleSheet

        styles = getSampleStyleSheet()
        pdf_row = []
        currency_symbol = getattr(self, "currency_symbol", "RD$")

        for key in column_map.keys():
            val = row.get(key, "")

            if key == "CondStorage":
                url = self._resolve_condstorage_url(val)
                if url and isinstance(url, str) and url.startswith(("http://", "https://")):
                    val = Paragraph(f'<link href="{url}">Ver</link>', styles["BodyText"])
                else:
                    val = ""
            else:
                if key == "horas" and val not in ("", None):
                    try:
                        val = f"{float(val):,.2f}"
                    except Exception:
                        pass
                if key == "monto" and val not in ("", None):
                    try:
                        val = f"{currency_symbol} {float(val):,.2f}"
                    except Exception:
                        pass

            pdf_row.append(val)

        return pdf_row



    def _build_facturas_table(self, column_map, data, font_size=9, page_w=None):
        """
        Construye la tabla de facturas con:
        - Wrapping en columnas flexibles
        - Anchos dinámicos ajustados a la página (self._auto_compute_col_widths)
        - repeatRows=1 para repetir encabezados en cada página
        """
        if not column_map or not data:
            return Paragraph("Sin datos de facturas.", getSampleStyleSheet()["Normal"])

        keys = list(column_map.keys())
        headers = [column_map[k] for k in keys]

        # Filas con wrapping
        rows = self._rows_with_wrapping(column_map, data, font_size=font_size)

        # Calcular anchos dinámicos
        if page_w is None:
            page_w, _ = LETTER
        col_widths = self._auto_compute_col_widths(
            column_map,
            data,
            page_w,
            margins=(36, 36),
            font_name="Helvetica",
            font_size=font_size
        )

        tbl = Table([headers] + rows,
                    hAlign="LEFT",
                    colWidths=col_widths,
                    repeatRows=1)  # <--- encabezados se repiten

        # Alinear columnas numéricas
        num_cols = [i for i, k in enumerate(keys) if k in ("horas", "monto")]

        ts = [
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6F4EA")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F7A1F")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#1F7A1F")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ]
        for idx in num_cols:
            ts.append(("ALIGN", (idx, 1), (idx, -1), "RIGHT"))

        tbl.setStyle(TableStyle(ts))
        return tbl


    def to_pdf(self, out_path: str):
        """
        Genera el PDF horizontal con:
        - Página(s) de Facturas (tabla con encabezado repetido).
        - PageBreak.
        - Página 2: Facturación por Equipo (si disponible) + Resumen de Cuenta;
          o Abonos por fecha + Totales (fallback).
        - Página 3 (opcional): KPIs con gráficos matplotlib.
        - Anexos (conduces) al final, cada uno con mini tabla de info.
        """
        try:
            import tempfile, os, shutil

            styles = getSampleStyleSheet()
            story = []

            # Datos base
            title = getattr(self, "title", "ESTADO DE CUENTA")
            cliente = getattr(self, "cliente", "")
            date_range = getattr(self, "date_range", "")
            self.currency_symbol = getattr(self, "currency_symbol", "RD$")
            column_map = getattr(self, "column_map", {}) or {}
            data = list(getattr(self, "data", []) or [])

            # --- A) Logo opcional ---
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo", "logo.png")
            has_logo = os.path.exists(logo_path)

            # Encabezado principal con logo opcional
            try:
                if has_logo:
                    logo_img = Image(logo_path, width=60, height=60)
                    title_para = Paragraph(
                        f'<b>{title}</b><br/><font size="10" color="#555555">EQUIPOS 6.5</font>',
                        ParagraphStyle("TitleLogo", parent=styles["Title"], fontSize=16, leading=20)
                    )
                    header_tbl = Table(
                        [[logo_img, title_para]],
                        colWidths=[70, None],
                        hAlign="LEFT"
                    )
                    header_tbl.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (0, 0), 0),
                        ("RIGHTPADDING", (0, 0), (0, 0), 8),
                    ]))
                    story.append(header_tbl)
                else:
                    story.append(Paragraph(title, styles["Title"]))
                    story.append(Paragraph(
                        '<font size="10" color="#555555">EQUIPOS 6.5</font>',
                        ParagraphStyle("Subtitle", parent=styles["Normal"], alignment=TA_CENTER)
                    ))
            except Exception as e:
                logger.error(f"Error al construir encabezado: {e}")
                story.append(Paragraph(title, styles["Title"]))

            if cliente:
                story.append(Paragraph(f"Cliente: {cliente}", styles["Heading3"]))
            if date_range:
                story.append(Paragraph(f"Periodo: {date_range}", styles["Normal"]))
            story.append(Spacer(1, 10))

            # Si no hay column_map pero hay datos, generar uno básico
            if not column_map and data and isinstance(data[0], dict):
                column_map = {k: k.capitalize() for k in data[0].keys()}

            # Tabla Facturas (puede paginar automáticamente) con zebra sutil
            story.append(Paragraph("Facturas", styles["Heading3"]))
            facturas_tbl = self._build_facturas_table(column_map, data, font_size=9)
            # Apply subtle zebra stripes (#FFFFFF / #F8F9FA)
            try:
                n_rows = len(data)
                zebra_cmds = []
                for i in range(1, n_rows + 1):
                    if i % 2 == 0:
                        zebra_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F8F9FA")))
                    else:
                        zebra_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FFFFFF")))
                if zebra_cmds:
                    facturas_tbl.setStyle(TableStyle(zebra_cmds))
            except Exception:
                pass
            story.append(facturas_tbl)

            # --- B) Página 2 ---
            story.append(PageBreak())

            facturacion_por_equipo = getattr(self, "facturacion_por_equipo", None) or []
            total_facturado = float(getattr(self, "total_facturado", 0) or 0)
            total_abonado = float(getattr(self, "total_abonado", 0) or 0)
            saldo = float(getattr(self, "saldo", total_facturado - total_abonado) or 0)

            if facturacion_por_equipo:
                # Página 2: Facturación por Equipo
                story.append(Paragraph("FACTURACIÓN POR EQUIPO", styles["Heading2"]))
                story.append(Spacer(1, 8))

                eq_headers = ["Equipo", "Total Facturado", "Total Abonado", "Saldo Pendiente", "Horas"]
                eq_rows = [eq_headers]
                for row in facturacion_por_equipo:
                    row_saldo = float(row.get("saldo", 0) or 0)
                    eq_rows.append([
                        str(row.get("equipo_nombre", "")),
                        f"{self.currency_symbol} {float(row.get('total_facturado', 0) or 0):,.2f}",
                        f"{self.currency_symbol} {float(row.get('total_abonado', 0) or 0):,.2f}",
                        f"{self.currency_symbol} {row_saldo:,.2f}",
                        f"{float(row.get('horas', 0) or 0):,.2f}",
                    ])
                # Fila totales
                total_horas_eq = sum(float(r.get("horas", 0) or 0) for r in facturacion_por_equipo)
                total_fact_eq = sum(float(r.get("total_facturado", 0) or 0) for r in facturacion_por_equipo)
                total_abon_eq = sum(float(r.get("total_abonado", 0) or 0) for r in facturacion_por_equipo)
                total_saldo_eq = total_fact_eq - total_abon_eq
                eq_rows.append([
                    "TOTALES",
                    f"{self.currency_symbol} {total_fact_eq:,.2f}",
                    f"{self.currency_symbol} {total_abon_eq:,.2f}",
                    f"{self.currency_symbol} {total_saldo_eq:,.2f}",
                    f"{total_horas_eq:,.2f}",
                ])

                eq_tbl = Table(eq_rows, hAlign="LEFT", colWidths=[180, 110, 110, 110, 70])
                eq_style = [
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6F4EA")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F7A1F")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#1F7A1F")),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    # Fila de totales en negrita
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8EEF9")),
                ]
                # Colorear saldo por equipo
                for i, row in enumerate(facturacion_por_equipo, start=1):
                    row_saldo = float(row.get("saldo", 0) or 0)
                    if row_saldo <= 0:
                        eq_style.append(("BACKGROUND", (3, i), (3, i), colors.HexColor("#C8E6C9")))
                    else:
                        eq_style.append(("BACKGROUND", (3, i), (3, i), colors.HexColor("#FFCCBC")))
                eq_tbl.setStyle(TableStyle(eq_style))
                story.append(eq_tbl)
                story.append(Spacer(1, 18))

                # Resumen de cuenta
                story.append(Paragraph("RESUMEN DE CUENTA", styles["Heading3"]))
                resumen_data = [
                    ["Total Alquileres", "Total Abonos", "Saldo Pendiente"],
                    [
                        f"{self.currency_symbol} {total_facturado:,.2f}",
                        f"{self.currency_symbol} {total_abonado:,.2f}",
                        f"{self.currency_symbol} {saldo:,.2f}",
                    ],
                ]
                saldo_bg = colors.HexColor("#C8E6C9") if saldo <= 0 else colors.HexColor("#FFCCBC")
                res_tbl = Table(resumen_data, hAlign="LEFT", colWidths=[150, 150, 150])
                res_tbl.setStyle(TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2A5ADF")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#2A5ADF")),
                    ("ALIGN", (0, 1), (-1, 1), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ("BACKGROUND", (2, 1), (2, 1), saldo_bg),
                ]))
                story.append(res_tbl)

                # Incluir también tabla de abonos por fecha como referencia
                abonos_por_fecha = getattr(self, "abonos_por_fecha", None)
                if not abonos_por_fecha:
                    abonos_list = getattr(self, "abonos", [])
                    abonos_por_fecha = self._group_abonos_by_date(abonos_list)
                if abonos_por_fecha:
                    story.append(Spacer(1, 18))
                    story.append(Paragraph("Abonos por fecha", styles["Heading3"]))
                    story.append(self._make_table_abonos_por_fecha(abonos_por_fecha, currency_symbol=self.currency_symbol))

            else:
                # Fallback: Abonos por fecha + Totales (comportamiento original)
                abonos_por_fecha = getattr(self, "abonos_por_fecha", None)
                if not abonos_por_fecha:
                    abonos_list = getattr(self, "abonos", [])
                    abonos_por_fecha = self._group_abonos_by_date(abonos_list)

                story.append(Paragraph("Abonos por fecha", styles["Heading3"]))
                story.append(self._make_table_abonos_por_fecha(abonos_por_fecha, currency_symbol=self.currency_symbol))
                story.append(Spacer(1, 18))

                tot_headers = ["Total Facturas", "Total Abonos", "Saldo"]
                tot_values = [
                    f"{self.currency_symbol} {total_facturado:,.2f}",
                    f"{self.currency_symbol} {total_abonado:,.2f}",
                    f"{self.currency_symbol} {saldo:,.2f}",
                ]
                tot_tbl = Table([tot_headers, tot_values], hAlign="RIGHT", colWidths=[130, 130, 130])
                tot_tbl.setStyle(TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2A5ADF")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#2A5ADF")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 1), (-1, 1), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ]))
                story.append(tot_tbl)

            # --- Siempre agregar tablas de horas y precio (fuera del if/else) ---
            horas_por_equipo = getattr(self, 'horas_por_equipo', None)
            precio_hora_equipo = getattr(self, 'precio_hora_equipo', None)

            if horas_por_equipo and len(horas_por_equipo) > 0:
                story.append(Spacer(1, 20))
                titulo_horas = Paragraph(
                    "<b>HORAS TOTALES POR EQUIPO</b>",
                    ParagraphStyle(
                        name="TituloHorasFB",
                        fontSize=12,
                        textColor=colors.HexColor("#1F7A1F"),
                        spaceAfter=8,
                        alignment=1,
                    )
                )
                story.append(titulo_horas)

                table_data_horas = [["Equipo", "Horas Totales"]]
                total_horas_tbl = 0.0
                for item in horas_por_equipo:
                    nombre = item.get("equipo_nombre", "")
                    horas = float(item.get("horas", 0))
                    total_horas_tbl += horas
                    table_data_horas.append([nombre, f"{horas:,.2f}"])
                table_data_horas.append(["TOTAL", f"{total_horas_tbl:,.2f}"])

                tbl_horas = Table(table_data_horas, hAlign="CENTER", colWidths=[200, 100])
                num_rows_h = len(table_data_horas)
                style_horas = [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6F4EA")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F7A1F")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1F7A1F")),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, num_rows_h - 1), (-1, num_rows_h - 1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, num_rows_h - 1), (-1, num_rows_h - 1), colors.HexColor("#D4EDDA")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
                tbl_horas.setStyle(TableStyle(style_horas))
                story.append(tbl_horas)

            if precio_hora_equipo and len(precio_hora_equipo) > 0:
                story.append(Spacer(1, 20))
                titulo_precio = Paragraph(
                    "<b>PRECIO POR HORA POR EQUIPO</b>",
                    ParagraphStyle(
                        name="TituloPrecioFB",
                        fontSize=12,
                        textColor=colors.HexColor("#1F7A1F"),
                        spaceAfter=8,
                        alignment=1,
                    )
                )
                story.append(titulo_precio)

                currency = self.currency_symbol
                table_data_precio = [["Equipo", "Horas Totales", "Monto Total", "Precio Promedio/Hora"]]
                total_horas_p = 0.0
                total_monto_p = 0.0

                for item in precio_hora_equipo:
                    nombre = item.get("equipo_nombre", "")
                    horas = float(item.get("horas", 0))
                    monto = float(item.get("monto", 0))
                    precio = float(item.get("precio_hora", 0))
                    total_horas_p += horas
                    total_monto_p += monto
                    precio_str = f"{currency} {precio:,.2f}" if horas > 0 else "N/A"
                    table_data_precio.append([
                        nombre,
                        f"{horas:,.2f}",
                        f"{currency} {monto:,.2f}",
                        precio_str,
                    ])

                precio_promedio_global = total_monto_p / total_horas_p if total_horas_p > 0 else 0
                precio_global_str = f"{currency} {precio_promedio_global:,.2f}" if total_horas_p > 0 else "N/A"
                table_data_precio.append([
                    "TOTALES",
                    f"{total_horas_p:,.2f}",
                    f"{currency} {total_monto_p:,.2f}",
                    precio_global_str,
                ])

                num_rows_p = len(table_data_precio)
                tbl_precio = Table(table_data_precio, hAlign="CENTER", colWidths=[160, 90, 120, 130])
                style_precio = [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6F4EA")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F7A1F")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1F7A1F")),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, num_rows_p - 1), (-1, num_rows_p - 1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, num_rows_p - 1), (-1, num_rows_p - 1), colors.HexColor("#D4EDDA")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
                tbl_precio.setStyle(TableStyle(style_precio))
                story.append(tbl_precio)

            # --- C) Página 3: KPIs con matplotlib (opcional) ---
            try:
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                HAS_MATPLOTLIB = True
            except ImportError:
                HAS_MATPLOTLIB = False

            tmp_chart_files = []
            if HAS_MATPLOTLIB and facturacion_por_equipo:
                try:
                    story.append(PageBreak())
                    story.append(Paragraph("ANÁLISIS POR EQUIPO", styles["Heading2"]))
                    story.append(Spacer(1, 10))

                    nombres = [r.get("equipo_nombre", "") for r in facturacion_por_equipo]
                    horas_list = [float(r.get("horas", 0) or 0) for r in facturacion_por_equipo]
                    fact_list = [float(r.get("total_facturado", 0) or 0) for r in facturacion_por_equipo]

                    # Gráfico 1: Horas Totales por Equipo (barras horizontales)
                    fig1, ax1 = plt.subplots(figsize=(8, max(3, len(nombres) * 0.7)))
                    bar_colors = ['#2E7D32', '#43A047', '#66BB6A', '#81C784', '#A5D6A7', '#C8E6C9']
                    colores = [bar_colors[i % len(bar_colors)] for i in range(len(nombres))]
                    bars = ax1.barh(nombres, horas_list, color=colores, edgecolor='#1B5E20', linewidth=0.5)
                    for bar_item, val in zip(bars, horas_list):
                        ax1.text(bar_item.get_width() + 0.3, bar_item.get_y() + bar_item.get_height() / 2,
                                 f'{val:,.1f} h', va='center', fontsize=9, fontweight='bold', color='#1B5E20')
                    ax1.set_xlabel('Horas', fontsize=11, fontweight='bold')
                    ax1.set_title('Horas Trabajadas por Equipo', fontsize=13, fontweight='bold',
                                  color='#1B5E20', pad=15)
                    ax1.spines['top'].set_visible(False)
                    ax1.spines['right'].set_visible(False)
                    plt.tight_layout()
                    tmp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    fig1.savefig(tmp1.name, dpi=120, bbox_inches="tight")
                    plt.close(fig1)
                    tmp1.close()
                    tmp_chart_files.append(tmp1.name)

                    # Gráfico 2: Distribución de Facturación (pie)
                    fig2, ax2 = plt.subplots(figsize=(5, 4))
                    fact_nonzero = [(n, v) for n, v in zip(nombres, fact_list) if v > 0]
                    if fact_nonzero:
                        pie_names, pie_vals = zip(*fact_nonzero)
                        ax2.pie(pie_vals, labels=pie_names, autopct="%1.1f%%", startangle=90,
                                textprops={"fontsize": 8})
                        ax2.set_title("Distribución de Facturación por Equipo")
                        plt.tight_layout()
                        tmp2 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        fig2.savefig(tmp2.name, dpi=120, bbox_inches="tight")
                        plt.close(fig2)
                        tmp2.close()
                        tmp_chart_files.append(tmp2.name)

                    # Insertar gráficos en el PDF
                    chart_row = []
                    chart_widths = []
                    for chart_path in tmp_chart_files:
                        if os.path.exists(chart_path):
                            chart_row.append(Image(chart_path, width=250, height=160))
                            chart_widths.append(270)
                    if chart_row:
                        chart_tbl = Table([chart_row], colWidths=chart_widths, hAlign="LEFT")
                        chart_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
                        story.append(chart_tbl)
                        story.append(Spacer(1, 14))

                    # KPI boxes
                    total_horas_kpi = sum(horas_list)
                    kpi_headers = ["Total Horas", "Total Facturado", "Total Abonado", "Saldo"]
                    kpi_values = [
                        f"{total_horas_kpi:,.2f}",
                        f"{self.currency_symbol} {total_facturado:,.2f}",
                        f"{self.currency_symbol} {total_abonado:,.2f}",
                        f"{self.currency_symbol} {saldo:,.2f}",
                    ]
                    kpi_tbl = Table([kpi_headers, kpi_values], hAlign="LEFT",
                                    colWidths=[100, 130, 130, 130])
                    kpi_bg = colors.HexColor("#C8E6C9") if saldo <= 0 else colors.HexColor("#FFCCBC")
                    kpi_tbl.setStyle(TableStyle([
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#37474F")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                        ("ALIGN", (0, 1), (-1, 1), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#37474F")),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BACKGROUND", (3, 1), (3, 1), kpi_bg),
                    ]))
                    story.append(kpi_tbl)
                except Exception as e:
                    logger.error(f"Error generando página KPIs: {e}", exc_info=True)

            elif HAS_MATPLOTLIB and horas_por_equipo and len(horas_por_equipo) > 0:
                # Gráfico solo de horas cuando no hay facturacion_por_equipo
                try:
                    story.append(PageBreak())
                    story.append(Paragraph("HORAS TRABAJADAS POR EQUIPO", styles["Heading2"]))
                    story.append(Spacer(1, 10))

                    nombres = [r.get("equipo_nombre", "") for r in horas_por_equipo]
                    horas_list = [float(r.get("horas", 0) or 0) for r in horas_por_equipo]

                    # Gráfico de barras horizontales
                    fig1, ax1 = plt.subplots(figsize=(8, max(3, len(nombres) * 0.7)))
                    bar_colors = ['#2E7D32', '#43A047', '#66BB6A', '#81C784', '#A5D6A7', '#C8E6C9']
                    colores = [bar_colors[i % len(bar_colors)] for i in range(len(nombres))]
                    bars = ax1.barh(nombres, horas_list, color=colores, edgecolor='#1B5E20', linewidth=0.5)
                    for bar_item, val in zip(bars, horas_list):
                        ax1.text(bar_item.get_width() + 0.3, bar_item.get_y() + bar_item.get_height() / 2,
                                 f'{val:,.1f} h', va='center', fontsize=9, fontweight='bold', color='#1B5E20')
                    ax1.set_xlabel('Horas', fontsize=11, fontweight='bold')
                    ax1.set_title('Distribución de Horas por Equipo', fontsize=13, fontweight='bold',
                                  color='#1B5E20', pad=15)
                    ax1.spines['top'].set_visible(False)
                    ax1.spines['right'].set_visible(False)
                    plt.tight_layout()
                    tmp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    fig1.savefig(tmp1.name, dpi=150, bbox_inches="tight")
                    plt.close(fig1)
                    tmp1.close()
                    tmp_chart_files.append(tmp1.name)

                    # Insertar gráfico
                    if os.path.exists(tmp1.name):
                        img = Image(tmp1.name, width=450, height=280)
                        story.append(img)
                        story.append(Spacer(1, 14))

                    # KPI resumen
                    total_horas_kpi = sum(horas_list)
                    kpi_headers = ["Total Horas", "Total Facturado", "Total Abonado", "Saldo"]
                    kpi_values = [
                        f"{total_horas_kpi:,.2f}",
                        f"{self.currency_symbol} {total_facturado:,.2f}",
                        f"{self.currency_symbol} {total_abonado:,.2f}",
                        f"{self.currency_symbol} {saldo:,.2f}",
                    ]
                    kpi_tbl = Table([kpi_headers, kpi_values], hAlign="CENTER",
                                    colWidths=[100, 130, 130, 130])
                    kpi_bg = colors.HexColor("#C8E6C9") if saldo <= 0 else colors.HexColor("#FFCCBC")
                    kpi_tbl.setStyle(TableStyle([
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#37474F")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                        ("ALIGN", (0, 1), (-1, 1), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#37474F")),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BACKGROUND", (3, 1), (3, 1), kpi_bg),
                    ]))
                    story.append(kpi_tbl)
                except Exception as e:
                    logger.error(f"Error generando gráfico de horas: {e}", exc_info=True)

            # Construir PDF principal temporal (portrait)
            tmp_main = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp_main_path = tmp_main.name
            tmp_main.close()

            doc = SimpleDocTemplate(
                tmp_main_path,
                pagesize=LETTER,
                leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
            )
            doc.build(story)

            # Limpiar archivos temporales de gráficos
            for f in tmp_chart_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass

            # Anexos (conduces) con mini tabla de info
            anexos = self._collect_conduces_to_attach()
            if not anexos:
                shutil.move(tmp_main_path, out_path)
                return True, None

            annex_pdf_paths = []
            for a in anexos:
                if a["type"] == "pdf":
                    annex_pdf_paths.append(a["path"])
                else:
                    page_pdf = self._image_to_pdf_page_with_info(
                        a["path"], a["label"], a.get("row_data")
                    )
                    if page_pdf:
                        annex_pdf_paths.append(page_pdf)

            ok, err = self._merge_main_with_annexes(tmp_main_path, annex_pdf_paths, out_path)
            if not ok:
                shutil.move(tmp_main_path, out_path)
                return False, f"No se pudieron anexar algunos conduces: {err}"

            try:
                self._limpiar_temp_files()
            except Exception:
                pass

            return True, None

        except Exception as e:
            import traceback
            print("to_pdf error:", e)
            traceback.print_exc()
            return False, str(e)

    def to_pdf_reporte_detallado(self, out_path: str):
        """
        Genera el PDF del Reporte Detallado de Equipos con:
        - Página 1: Tabla de Facturas
        - Página 2: KPIs + Tabla de Rendimientos por Equipo + Tabla de Gastos
        - Página 3 (opcional): Gráficos matplotlib (horas y rendimiento)
        - Anexos: Conduces + Adjuntos de Gastos
        """
        try:
            import tempfile, os, shutil

            styles = getSampleStyleSheet()
            story = []

            # ─── Datos base ───
            title = getattr(self, "title", "REPORTE DETALLADO DE EQUIPOS")
            date_range = getattr(self, "date_range", "")
            self.currency_symbol = getattr(self, "currency_symbol", "RD$")
            column_map = getattr(self, "column_map", {}) or {}
            data = list(getattr(self, "data", []) or [])
            cur = self.currency_symbol

            rendimientos = getattr(self, "rendimientos_por_equipo", []) or []
            totales = getattr(self, "totales_globales", {}) or {}
            gastos_list = getattr(self, "gastos_list", []) or []
            equipos_mapa = getattr(self, "equipos_mapa", {}) or {}

            # Totales desde datos
            total_horas = sum(float(d.get("horas_raw", 0) or 0) for d in data)
            total_facturado = float(totales.get("total_alquileres", 0) or 0)
            total_abonos = float(totales.get("total_abonos", 0) or 0)
            saldo = total_facturado - total_abonos

            # Horas por equipo (para gráfico)
            horas_por_equipo = {}
            for d in data:
                eid = d.get("equipo_id", "")
                nombre = d.get("equipo", "")
                h = float(d.get("horas_raw", 0) or 0)
                if eid not in horas_por_equipo:
                    horas_por_equipo[eid] = {"nombre": nombre, "horas": 0.0}
                horas_por_equipo[eid]["horas"] += h

            # ─── Logo + Encabezado ───
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo", "logo.png")
            has_logo = os.path.exists(logo_path)
            try:
                if has_logo:
                    logo_img = Image(logo_path, width=60, height=60)
                    title_para = Paragraph(
                        f'<b>{title}</b><br/><font size="10" color="#555555">EQUIPOS 6.5</font>',
                        ParagraphStyle("TitleLogo2", parent=styles["Title"], fontSize=16, leading=20)
                    )
                    header_tbl = Table([[logo_img, title_para]], colWidths=[70, None], hAlign="LEFT")
                    header_tbl.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (0, 0), 0),
                        ("RIGHTPADDING", (0, 0), (0, 0), 8),
                    ]))
                    story.append(header_tbl)
                else:
                    story.append(Paragraph(title, styles["Title"]))
            except Exception:
                story.append(Paragraph(title, styles["Title"]))

            if date_range:
                story.append(Paragraph(f"Periodo: {date_range}", styles["Normal"]))
            story.append(Spacer(1, 10))

            # ─── Página 1: Tabla de Facturas ───
            if not column_map and data and isinstance(data[0], dict):
                column_map = {k: k.capitalize() for k in data[0].keys()
                              if not k.endswith("_raw") and k != "equipo_id"}

            story.append(Paragraph("FACTURAS", styles["Heading2"]))
            facturas_tbl = self._build_facturas_table(column_map, data, font_size=9)
            try:
                zebra_cmds = []
                for i in range(1, len(data) + 1):
                    bg = "#F8F9FA" if i % 2 == 0 else "#FFFFFF"
                    zebra_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(bg)))
                if zebra_cmds:
                    facturas_tbl.setStyle(TableStyle(zebra_cmds))
            except Exception:
                pass
            story.append(facturas_tbl)

            # ─── Página 2: Resumen ───
            story.append(PageBreak())
            story.append(Paragraph("RESUMEN EJECUTIVO", styles["Heading2"]))
            story.append(Spacer(1, 8))

            # KPI box: Total Horas | Total Facturado | Total Abonos | Saldo
            saldo_bg = colors.HexColor("#C8E6C9") if saldo <= 0 else colors.HexColor("#FFCCBC")
            kpi_headers = ["Total Horas", "Total Facturado", "Total Abonos", "Saldo"]
            kpi_values = [
                f"{total_horas:,.2f}",
                f"{cur} {total_facturado:,.2f}",
                f"{cur} {total_abonos:,.2f}",
                f"{cur} {saldo:,.2f}",
            ]
            kpi_tbl = Table([kpi_headers, kpi_values], hAlign="LEFT", colWidths=[100, 130, 130, 130])
            kpi_tbl.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#37474F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("ALIGN", (0, 1), (-1, 1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#37474F")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (3, 1), (3, 1), saldo_bg),
            ]))
            story.append(kpi_tbl)
            story.append(Spacer(1, 18))

            # ─── Tabla de Rendimientos por Equipo ───
            if rendimientos:
                story.append(Paragraph("RENDIMIENTOS POR EQUIPO", styles["Heading3"]))
                story.append(Spacer(1, 6))

                rend_rows = [["Equipo", "Facturado", "Gastos", "Pagos Op.", "Rendimiento", "% Rend."]]
                tot_f = tot_g = tot_p = tot_r = 0.0

                for r in rendimientos:
                    facturado = float(r.get("facturado", 0) or 0)
                    gastos_r = float(r.get("gastos", 0) or 0)
                    pagos_op = float(r.get("pagos_op", 0) or 0)
                    rendimiento = float(r.get("rendimiento", 0) or 0)
                    pct = float(r.get("pct", 0) or 0)
                    tot_f += facturado; tot_g += gastos_r; tot_p += pagos_op; tot_r += rendimiento
                    rend_rows.append([
                        str(r.get("equipo", "")),
                        f"{cur} {facturado:,.2f}",
                        f"{cur} {gastos_r:,.2f}",
                        f"{cur} {pagos_op:,.2f}",
                        f"{cur} {rendimiento:,.2f}",
                        f"{pct:,.1f}%",
                    ])

                tot_pct = (tot_r / tot_f * 100) if tot_f > 0 else 0.0
                rend_rows.append([
                    "TOTALES",
                    f"{cur} {tot_f:,.2f}", f"{cur} {tot_g:,.2f}",
                    f"{cur} {tot_p:,.2f}", f"{cur} {tot_r:,.2f}",
                    f"{tot_pct:,.1f}%",
                ])

                num_rend = len(rend_rows)
                rend_style = [
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9CA3AF")),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("FONTNAME", (0, num_rend - 1), (-1, num_rend - 1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, num_rend - 1), (-1, num_rend - 1), colors.HexColor("#E8EEF9")),
                ]
                for i, r in enumerate(rendimientos, start=1):
                    rend_val = float(r.get("rendimiento", 0) or 0)
                    c_rend = colors.HexColor("#C8E6C9") if rend_val >= 0 else colors.HexColor("#FFCCBC")
                    rend_style.append(("BACKGROUND", (4, i), (4, i), c_rend))
                    if i % 2 == 0:
                        rend_style.append(("BACKGROUND", (0, i), (3, i), colors.HexColor("#F8F9FA")))

                rend_tbl = Table(rend_rows, hAlign="LEFT", colWidths=[155, 90, 80, 80, 95, 60])
                rend_tbl.setStyle(TableStyle(rend_style))
                story.append(rend_tbl)
                story.append(Spacer(1, 18))

            # ─── Tabla de Gastos del Período ───
            if gastos_list:
                story.append(Paragraph("GASTOS DEL PERÍODO", styles["Heading3"]))
                story.append(Spacer(1, 6))

                gastos_rows = [["Fecha", "Equipo", "Descripción", f"Monto ({cur})"]]
                total_gastos_pdf = 0.0
                for g in gastos_list:
                    eid = str(g.get("equipo_id") or "")
                    eq_nombre = equipos_mapa.get(eid, f"Equipo {eid}" if eid else "—")
                    monto_g = float(g.get("monto", 0) or 0)
                    total_gastos_pdf += monto_g
                    desc = str(g.get("descripcion", "") or g.get("concepto", "") or "")
                    gastos_rows.append([
                        str(g.get("fecha", "")),
                        eq_nombre,
                        desc,
                        f"{cur} {monto_g:,.2f}",
                    ])
                gastos_rows.append(["TOTAL", "", "", f"{cur} {total_gastos_pdf:,.2f}"])

                num_gastos = len(gastos_rows)
                gastos_style = [
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7F1D1D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9CA3AF")),
                    ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("FONTNAME", (0, num_gastos - 1), (-1, num_gastos - 1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, num_gastos - 1), (-1, num_gastos - 1), colors.HexColor("#FEE2E2")),
                ]
                for i in range(1, len(gastos_list) + 1):
                    if i % 2 == 0:
                        gastos_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FEF2F2")))
                gastos_tbl = Table(gastos_rows, hAlign="LEFT", colWidths=[70, 140, 200, 90])
                gastos_tbl.setStyle(TableStyle(gastos_style))
                story.append(gastos_tbl)
                story.append(Spacer(1, 18))

            # ─── Página 3: Gráficos ───
            try:
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                HAS_MATPLOTLIB = True
            except ImportError:
                HAS_MATPLOTLIB = False

            tmp_chart_files = []
            equipos_con_horas = {k: v for k, v in horas_por_equipo.items() if v["horas"] > 0}

            if HAS_MATPLOTLIB and (equipos_con_horas or rendimientos):
                try:
                    story.append(PageBreak())
                    story.append(Paragraph("ANÁLISIS POR EQUIPO", styles["Heading2"]))
                    story.append(Spacer(1, 10))

                    # Gráfico 1: Horas por equipo
                    if equipos_con_horas:
                        nombres_h = [v["nombre"] for v in equipos_con_horas.values()]
                        vals_h = [v["horas"] for v in equipos_con_horas.values()]
                        fig1, ax1 = plt.subplots(figsize=(8, max(3, len(nombres_h) * 0.7)))
                        bar_cols = ['#2E7D32', '#43A047', '#66BB6A', '#81C784', '#A5D6A7', '#C8E6C9']
                        colores1 = [bar_cols[i % len(bar_cols)] for i in range(len(nombres_h))]
                        bars1 = ax1.barh(nombres_h, vals_h, color=colores1, edgecolor='#1B5E20', linewidth=0.5)
                        for b, v in zip(bars1, vals_h):
                            ax1.text(b.get_width() + 0.3, b.get_y() + b.get_height() / 2,
                                     f'{v:,.1f} h', va='center', fontsize=9, fontweight='bold', color='#1B5E20')
                        ax1.set_xlabel('Horas', fontsize=11, fontweight='bold')
                        ax1.set_title('Horas Trabajadas por Equipo', fontsize=13, fontweight='bold',
                                      color='#1B5E20', pad=15)
                        ax1.spines['top'].set_visible(False)
                        ax1.spines['right'].set_visible(False)
                        plt.tight_layout()
                        tmp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        fig1.savefig(tmp1.name, dpi=120, bbox_inches="tight")
                        plt.close(fig1)
                        tmp1.close()
                        tmp_chart_files.append(tmp1.name)
                        story.append(Image(tmp1.name, width=450, height=280))
                        story.append(Spacer(1, 14))

                    # Gráfico 2: Rendimiento por equipo
                    if rendimientos:
                        rend_nombres2 = [r.get("equipo", "") for r in rendimientos]
                        rend_vals2 = [float(r.get("rendimiento", 0) or 0) for r in rendimientos]
                        if any(v != 0 for v in rend_vals2):
                            fig2, ax2 = plt.subplots(figsize=(8, max(3, len(rend_nombres2) * 0.7)))
                            bar_cols2 = ['#2E7D32' if v >= 0 else '#D32F2F' for v in rend_vals2]
                            bars2 = ax2.barh(rend_nombres2, rend_vals2, color=bar_cols2,
                                             edgecolor='#37474F', linewidth=0.5)
                            for b, v in zip(bars2, rend_vals2):
                                ax2.text(b.get_width() + 0.3, b.get_y() + b.get_height() / 2,
                                         f'{cur} {v:,.0f}', va='center', fontsize=9, fontweight='bold')
                            ax2.set_xlabel('Rendimiento', fontsize=11, fontweight='bold')
                            ax2.set_title('Rendimiento por Equipo', fontsize=13, fontweight='bold',
                                          color='#37474F', pad=15)
                            ax2.spines['top'].set_visible(False)
                            ax2.spines['right'].set_visible(False)
                            plt.tight_layout()
                            tmp2 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                            fig2.savefig(tmp2.name, dpi=120, bbox_inches="tight")
                            plt.close(fig2)
                            tmp2.close()
                            tmp_chart_files.append(tmp2.name)
                            story.append(Image(tmp2.name, width=450, height=280))
                            story.append(Spacer(1, 14))

                    # Gráfico 3: Donut — Composición de Costos y Rendimiento
                    if rendimientos:
                        tot_gastos_d   = sum(float(r.get("gastos", 0)   or 0) for r in rendimientos)
                        tot_pagos_op_d = sum(float(r.get("pagos_op", 0) or 0) for r in rendimientos)
                        tot_rend_d     = sum(float(r.get("rendimiento", 0) or 0) for r in rendimientos)
                        # Base del donut = total facturado (suma de partes positivas + pérdida si la hay)
                        base_donut = tot_gastos_d + tot_pagos_op_d + (tot_rend_d if tot_rend_d > 0 else 0)

                        if base_donut > 0:
                            story.append(PageBreak())
                            story.append(Paragraph(
                                "COMPOSICIÓN DE COSTOS Y RENDIMIENTO",
                                styles["Heading2"]
                            ))
                            story.append(Spacer(1, 10))

                            # Construir segmentos (solo valores > 0)
                            slices_labels = []
                            slices_sizes  = []
                            slices_colors = []

                            if tot_gastos_d > 0:
                                slices_labels.append(
                                    f"Gastos Generales\n{cur} {tot_gastos_d:,.2f}"
                                )
                                slices_sizes.append(tot_gastos_d)
                                slices_colors.append('#EF4444')

                            if tot_pagos_op_d > 0:
                                slices_labels.append(
                                    f"Pagos Operadores\n{cur} {tot_pagos_op_d:,.2f}"
                                )
                                slices_sizes.append(tot_pagos_op_d)
                                slices_colors.append('#F97316')

                            if tot_rend_d > 0:
                                slices_labels.append(
                                    f"Rendimiento\n{cur} {tot_rend_d:,.2f}"
                                )
                                slices_sizes.append(tot_rend_d)
                                slices_colors.append('#22C55E')
                            elif tot_rend_d < 0:
                                # Mostrar la pérdida como segmento propio
                                slices_labels.append(
                                    f"Pérdida\n{cur} {abs(tot_rend_d):,.2f}"
                                )
                                slices_sizes.append(abs(tot_rend_d))
                                slices_colors.append('#7F1D1D')

                            if slices_sizes:
                                fig3, ax3 = plt.subplots(figsize=(7, 5))
                                wedges, _, autotexts = ax3.pie(
                                    slices_sizes,
                                    labels=None,
                                    colors=slices_colors,
                                    autopct='%1.1f%%',
                                    startangle=90,
                                    pctdistance=0.75,
                                    wedgeprops=dict(width=0.5, edgecolor='white', linewidth=2),
                                )
                                for at in autotexts:
                                    at.set_fontsize(10)
                                    at.set_fontweight('bold')
                                    at.set_color('white')

                                ax3.legend(
                                    wedges, slices_labels,
                                    title="Composición",
                                    loc="center left",
                                    bbox_to_anchor=(1, 0, 0.5, 1),
                                    fontsize=9,
                                    title_fontsize=9,
                                )
                                total_mostrado = sum(slices_sizes)
                                ax3.set_title(
                                    f'Distribución del Facturado  —  Total: {cur} {total_facturado:,.2f}',
                                    fontsize=11, fontweight='bold', color='#1F2937', pad=20
                                )
                                plt.tight_layout()
                                tmp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                                fig3.savefig(tmp3.name, dpi=150, bbox_inches="tight")
                                plt.close(fig3)
                                tmp3.close()
                                tmp_chart_files.append(tmp3.name)
                                story.append(Image(tmp3.name, width=420, height=300))
                                story.append(Spacer(1, 16))

                                # Tabla resumen debajo del donut
                                pct = lambda v: f"{v / total_facturado * 100:,.1f}%" if total_facturado > 0 else "—"
                                rend_color_hex = '#22C55E' if tot_rend_d >= 0 else '#DC2626'
                                summary_rows = [
                                    ["Concepto", f"Monto ({cur})", "% Facturado"],
                                    ["Total Facturado",  f"{cur} {total_facturado:,.2f}",  "100.00%"],
                                    ["Gastos Generales", f"{cur} {tot_gastos_d:,.2f}",   pct(tot_gastos_d)],
                                    ["Pagos Operadores", f"{cur} {tot_pagos_op_d:,.2f}", pct(tot_pagos_op_d)],
                                    ["Rendimiento",      f"{cur} {tot_rend_d:,.2f}",     pct(tot_rend_d)],
                                ]
                                sum_tbl = Table(summary_rows, hAlign="CENTER",
                                                colWidths=[180, 140, 110])
                                sum_style = [
                                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#37474F")),
                                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9CA3AF")),
                                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                                    # Facturado row
                                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E8EEF9")),
                                    ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                                    # Gastos row
                                    ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#FEF2F2")),
                                    ("TEXTCOLOR", (1, 2), (1, 2), colors.HexColor("#DC2626")),
                                    # Pagos op row
                                    ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#FFF7ED")),
                                    ("TEXTCOLOR", (1, 3), (1, 3), colors.HexColor("#C2410C")),
                                    # Rendimiento row
                                    ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
                                    ("BACKGROUND", (0, 4), (-1, 4),
                                     colors.HexColor("#DCFCE7") if tot_rend_d >= 0 else colors.HexColor("#FEE2E2")),
                                    ("TEXTCOLOR", (1, 4), (2, 4), colors.HexColor(rend_color_hex)),
                                ]
                                sum_tbl.setStyle(TableStyle(sum_style))
                                story.append(sum_tbl)

                except Exception as e:
                    logger.error(f"Error generando gráficos reporte detallado: {e}", exc_info=True)

            # ─── Build PDF principal ───
            tmp_main = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp_main_path = tmp_main.name
            tmp_main.close()

            doc = SimpleDocTemplate(
                tmp_main_path,
                pagesize=LETTER,
                leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
            )
            doc.build(story)

            for f in tmp_chart_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass

            # ─── Anexos: conduces + gastos + comprobantes de pagos ───
            anexos_conduces = self._collect_conduces_to_attach()
            anexos_gastos = self._collect_gastos_to_attach()
            anexos_pagos_op = self._collect_pagos_op_to_attach()
            anexos = anexos_conduces + anexos_gastos + anexos_pagos_op

            if not anexos:
                shutil.move(tmp_main_path, out_path)
                return True, None

            annex_pdf_paths = []
            for a in anexos:
                if a["type"] == "pdf":
                    annex_pdf_paths.append(a["path"])
                else:
                    if a.get("_es_pago_op"):
                        page_pdf = self._pago_op_to_pdf_page_with_info(
                            a["path"], a["label"], a.get("row_data")
                        )
                    elif a.get("_es_gasto"):
                        page_pdf = self._gasto_to_pdf_page_with_info(
                            a["path"], a["label"], a.get("row_data")
                        )
                    else:
                        page_pdf = self._image_to_pdf_page_with_info(
                            a["path"], a["label"], a.get("row_data")
                        )
                    if page_pdf:
                        annex_pdf_paths.append(page_pdf)

            ok, err = self._merge_main_with_annexes(tmp_main_path, annex_pdf_paths, out_path)
            if not ok:
                shutil.move(tmp_main_path, out_path)
                return False, f"No se pudieron anexar algunos documentos: {err}"

            try:
                self._limpiar_temp_files()
            except Exception:
                pass

            return True, None

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, str(e)

    def _agregar_anexos_conduces(self, elementos, estilos):
        """
        Agrega una sección de anexos con las imágenes de los conduces.
        
        Args:
            elementos: Lista de elementos del PDF
            estilos: Estilos de ReportLab
        """
        try:
            # Filtrar registros que tengan conduce
            conduces_df = self.df[self.df['CondStorage'].notna() & (self.df['CondStorage'] != '')]
            
            if conduces_df.empty:
                logger.info("No hay conduces para agregar a los anexos")
                return
            
            logger.info(f"Agregando {len(conduces_df)} conduces a los anexos")
            
            # Nueva página para anexos
            elementos.append(PageBreak())
            elementos.append(Paragraph("<b>ANEXOS: Conduces de Servicios</b>", estilos['Heading1']))
            elementos.append(Spacer(1, 5*mm))
            
            # Descargar y agregar cada conduce
            for idx, row in conduces_df.iterrows():
                storage_path = row['CondStorage']
                fecha = row.get('Fecha', '')
                conduce_num = row.get('Conduce', f'Conduce {idx+1}')
                
                # Descargar conduce desde Storage
                temp_path = self._descargar_conduce(storage_path)
                
                if temp_path and os.path.exists(temp_path):
                    # Agregar etiqueta
                    elementos.append(Paragraph(
                        f"<b>Conduce:</b> {conduce_num} | <b>Fecha:</b> {fecha}",
                        estilos['Normal']
                    ))
                    elementos.append(Spacer(1, 2*mm))
                    
                    # Agregar imagen (máximo 180mm de ancho)
                    try:
                        img = Image(temp_path)
                        img._restrictSize(180*mm, 250*mm)  # Máximo ancho y alto
                        elementos.append(img)
                    except Exception as e:
                        logger.warning(f"No se pudo insertar imagen {storage_path}: {e}")
                        elementos.append(Paragraph(
                            f"<i>No se pudo cargar la imagen del conduce</i>",
                            estilos['Normal']
                        ))
                    
                    elementos.append(Spacer(1, 5*mm))
                else:
                    logger.warning(f"No se pudo descargar conduce: {storage_path}")
            
        except Exception as e:
            logger.error(f"Error al agregar anexos de conduces: {e}", exc_info=True)
    
    def _descargar_conduce(self, storage_path):
        """
        Descarga un conduce desde Firebase Storage a un archivo temporal.
        
        Args:
            storage_path: Ruta del archivo en Storage
            
        Returns:
            str: Ruta del archivo temporal o None si falla
        """
        if not self.storage_manager:
            return None
        
        try:
            # Crear archivo temporal
            ext = os.path.splitext(storage_path)[1] or '.jpg'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_path = temp_file.name
            temp_file.close()
            
            # Descargar desde Storage
            exito = self.storage_manager.descargar_conduce(storage_path, temp_path)
            
            if exito:
                self.temp_files.append(temp_path)
                return temp_path
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return None
                
        except Exception as e:
            logger.error(f"Error al descargar conduce {storage_path}: {e}")
            return None
    
    def _limpiar_temp_files(self):
        """Elimina archivos temporales descargados."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Archivo temporal eliminado: {temp_file}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo temporal {temp_file}: {e}")
        
        self.temp_files = []
    
    def _agregar_seccion_abonos(self, elementos, estilos):
        """
        Agrega sección de abonos y totales al PDF.
        """
        try:
            elementos.append(PageBreak())
            elementos.append(Paragraph("<b>ABONOS REGISTRADOS</b>", estilos['Heading2']))
            elementos.append(Spacer(1, 3*mm))
            
            # Tabla de abonos
            if self.abonos:
                abonos_cols = ['Fecha', 'Concepto', 'Monto']
                abonos_data = [abonos_cols]
                
                for abono in self.abonos:
                    fecha = abono.get('fecha', '')
                    concepto = abono.get('concepto', '') or abono.get('descripcion', 'Abono')
                    monto = float(abono.get('monto', 0))
                    
                    abonos_data.append([
                        str(fecha),
                        str(concepto),
                        f"{self.currency} {monto:,.2f}"
                    ])
                
                abonos_tabla = Table(abonos_data, colWidths=[40*mm, 90*mm, 50*mm])
                abonos_tabla.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1F6321")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
                    ('ALIGN', (0, 1), (1, -1), 'LEFT'),
                    
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")])
                ]))
                
                elementos.append(abonos_tabla)
                elementos.append(Spacer(1, 5*mm))
            else:
                elementos.append(Paragraph("No se registraron abonos en este período.", estilos['Normal']))
                elementos.append(Spacer(1, 5*mm))
            
            # Agregar totales
            self._agregar_totales(elementos, estilos)
            
        except Exception as e:
            logger.error(f"Error al agregar sección de abonos: {e}", exc_info=True)
    
    def _agregar_totales(self, elementos, estilos):
        """
        Agrega tabla de totales (Facturado, Abonado, Saldo).
        """
        try:
            elementos.append(Paragraph("<b>RESUMEN DE CUENTA</b>", estilos['Heading3']))
            elementos.append(Spacer(1, 3*mm))
            
            # Tabla de totales
            totales_data = [
                ['Total Facturado:', f"{self.currency} {self.total_facturado:,.2f}"],
                ['Total Abonado:', f"{self.currency} {self.total_abonado:,.2f}"],
                ['Saldo Pendiente:', f"{self.currency} {self.saldo:,.2f}"]
            ]
            
            totales_tabla = Table(totales_data, colWidths=[70*mm, 70*mm])
            totales_tabla.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                
                # Destacar el saldo
                ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor("#FFF4CC") if self.saldo > 0 else colors.HexColor("#E8F5E9")),
                ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor("#D32F2F") if self.saldo > 0 else colors.HexColor("#2E7D32")),
                
                ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
                ('LINEABOVE', (0, 2), (-1, 2), 2, colors.black),
                ('LINEBELOW', (0, 2), (-1, 2), 2, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elementos.append(totales_tabla)
            elementos.append(Spacer(1, 10*mm))
            
        except Exception as e:
            logger.error(f"Error al agregar totales: {e}", exc_info=True)
    
    def to_excel(self, filepath):
        """
        Genera el reporte en formato Excel.
        
        Args:
            filepath: Ruta donde guardar el Excel
            
        Returns:
            tuple: (éxito: bool, mensaje: str)
        """
        if self.df.empty:
            return False, "No hay datos para exportar."
        
        try:
            # Exportar DataFrame a Excel
            self.df.to_excel(filepath, index=False, sheet_name='Reporte')
            logger.info(f"Excel generado exitosamente: {filepath}")
            return True, f"Reporte Excel generado exitosamente en:\n{filepath}"
            
        except Exception as e:
            logger.error(f"Error al generar Excel: {e}", exc_info=True)
            return False, f"Error al generar el reporte Excel: {str(e)}"


    def _column_widths_from_keys(self, column_map: dict) -> list:
        """
        Define anchos fijos por columna (en puntos). Evita que la tabla se distorsione.
        Ajusta estos valores si quieres más espacio en alguna columna.
        """
        width_map = {
            "fecha": 70,
            "conduce": 60,
            "ubicacion": 120,
            "equipo_nombre": 100,
            "operador_nombre": 120,
            "horas": 45,
            "monto": 85,
            "cliente_nombre": 120,
        }
        return [width_map.get(k, 80) for k in column_map.keys()]


    def _collect_conduces_to_attach(self) -> list[dict]:
        """
        Recorre self.data y devuelve una lista de anexos a agregar:
        [{"label": "Conduce No. 00621", "path": "/tmp/...", "type": "image|pdf"}]
        Descarga cada conduce con storage_manager.descargar_conduce(storage_path).
        Acepta las claves 'conduce_storage_path' o 'CondStorage' como ruta en Storage.
        """
        anexos = []
        sm = getattr(self, "storage_manager", None)
        if not sm:
            return anexos

        for row in self.data or []:
            storage_path = row.get("conduce_storage_path") or row.get("CondStorage")
            if not storage_path:
                continue

            # Se guardas storage_path (conduces/YYYY/MM/file.ext), así que debería funcionar.
            try:
                local_path = sm.descargar_conduce(storage_path)
                if not local_path:
                    continue
                import os  # si no lo tienes ya importado arriba
                ext = os.path.splitext(local_path)[1].lower()
                numero = str(row.get("conduce") or row.get("id") or "")
                label = f"Conduce No. {numero}" if numero else "Conduce"
                tipo = "pdf" if ext == ".pdf" else "image"
                anexos.append({"label": label, "path": local_path, "type": tipo, "row_data": row})
            except Exception:
                continue

        return anexos

    def _collect_gastos_to_attach(self) -> list[dict]:
        """
        Recorre self.gastos_list y devuelve anexos de gastos que tengan archivo_storage_path.
        Similar a _collect_conduces_to_attach pero para gastos.
        """
        import os
        anexos = []
        sm = getattr(self, "storage_manager", None)
        if not sm:
            return anexos

        equipos_mapa = getattr(self, "equipos_mapa", {}) or {}

        for g in getattr(self, "gastos_list", []) or []:
            storage_path = g.get("archivo_storage_path")
            if not storage_path:
                continue
            try:
                local_path = sm.descargar_conduce(storage_path)
                if not local_path:
                    continue
                ext = os.path.splitext(local_path)[1].lower()
                desc = str(g.get("descripcion", "") or g.get("concepto", "") or g.get("id", "") or "")
                label = f"Gasto: {desc}" if desc else "Gasto"
                tipo = "pdf" if ext == ".pdf" else "image"
                eid = str(g.get("equipo_id") or "")
                row_data = {
                    "fecha": g.get("fecha", ""),
                    "equipo_nombre": equipos_mapa.get(eid, f"Equipo {eid}" if eid else "—"),
                    "descripcion": desc,
                    "monto": g.get("monto", ""),
                }
                anexos.append({
                    "label": label, "path": local_path, "type": tipo,
                    "row_data": row_data, "_es_gasto": True,
                })
            except Exception:
                continue

        return anexos

    def _collect_pagos_op_to_attach(self) -> list[dict]:
        """
        Recorre self.pagos_op_list y devuelve anexos de pagos de operadores
        que tengan comprobante_storage_path. Similar a _collect_gastos_to_attach.
        """
        import os
        anexos = []
        sm = getattr(self, "storage_manager", None)
        if not sm:
            return anexos

        equipos_mapa = getattr(self, "equipos_mapa", {}) or {}
        operadores_mapa = getattr(self, "operadores_mapa", {}) or {}

        for p in getattr(self, "pagos_op_list", []) or []:
            storage_path = p.get("comprobante_storage_path")
            if not storage_path:
                continue
            try:
                local_path = sm.descargar_conduce(storage_path)
                if not local_path:
                    continue
                ext = os.path.splitext(local_path)[1].lower()
                oid = str(p.get("operador_id") or "")
                op_nombre = operadores_mapa.get(oid, f"Operador {oid}" if oid else "—")
                concepto = str(p.get("concepto", "") or "")
                label = f"Pago Op.: {op_nombre}" + (f" — {concepto}" if concepto else "")
                tipo = "pdf" if ext == ".pdf" else "image"
                eid = str(p.get("equipo_id") or "")
                row_data = {
                    "fecha": p.get("fecha", ""),
                    "operador_nombre": op_nombre,
                    "equipo_nombre": equipos_mapa.get(eid, f"Equipo {eid}" if eid else "—"),
                    "concepto": concepto,
                    "metodo_pago": str(p.get("metodo_pago", "") or ""),
                    "monto": p.get("monto", ""),
                    "nota": str(p.get("nota", "") or ""),
                }
                anexos.append({
                    "label": label, "path": local_path, "type": tipo,
                    "row_data": row_data, "_es_pago_op": True,
                })
            except Exception:
                continue

        return anexos

    def _pago_op_to_pdf_page_with_info(self, img_path: str, label: str, row_data: dict = None) -> str | None:
        """
        Convierte un comprobante de pago de operador en página PDF con mini tabla de info arriba.
        """
        if not row_data:
            return self._image_to_pdf_page(img_path, label)
        try:
            import tempfile
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors as rl_colors

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp_path = tmp.name
            tmp.close()

            styles_p = getSampleStyleSheet()
            story_p = []

            def _v(key, alt=""):
                return str(row_data.get(key) or alt or "")

            currency = getattr(self, "currency_symbol", "RD$")
            monto_val = row_data.get("monto", "")
            try:
                monto_str = f"{currency} {float(monto_val):,.2f}" if monto_val not in ("", None) else ""
            except Exception:
                monto_str = str(monto_val or "")

            info_rows = [
                ["Campo", "Valor"],
                ["Tipo", "Pago a Operador"],
                ["Fecha", _v("fecha")],
                ["Operador", _v("operador_nombre")],
                ["Equipo", _v("equipo_nombre")],
                ["Concepto", _v("concepto")],
                ["Método de Pago", _v("metodo_pago")],
                ["Monto", monto_str],
            ]
            if row_data.get("nota"):
                info_rows.append(["Nota", _v("nota")])

            info_tbl = Table(info_rows, colWidths=[110, 340], hAlign="LEFT")
            info_tbl.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#E8EEF9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.HexColor("#1E3A8A")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, rl_colors.HexColor("#1E3A8A")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#F0F4FF")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))

            story_p.append(Paragraph(label, styles_p["Heading3"]))
            story_p.append(Spacer(1, 6))
            story_p.append(info_tbl)
            story_p.append(Spacer(1, 10))

            try:
                img_rl = RLImage(img_path)
                img_rl._restrictSize(480, 480)
                story_p.append(img_rl)
            except Exception as e:
                logger.warning(f"No se pudo insertar imagen pago_op {img_path}: {e}")
                story_p.append(Paragraph(
                    "<i>No se pudo cargar el comprobante</i>", styles_p["Normal"]
                ))

            doc_p = SimpleDocTemplate(
                tmp_path,
                pagesize=LETTER,
                leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
            )
            doc_p.build(story_p)
            return tmp_path
        except Exception as e:
            logger.error(f"Error en _pago_op_to_pdf_page_with_info: {e}", exc_info=True)
            return self._image_to_pdf_page(img_path, label)

    def _gasto_to_pdf_page_with_info(self, img_path: str, label: str, row_data: dict = None) -> str | None:
        """
        Convierte un adjunto de gasto en página PDF con mini tabla de información arriba.
        """
        if not row_data:
            return self._image_to_pdf_page(img_path, label)
        try:
            import tempfile
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors as rl_colors

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp_path = tmp.name
            tmp.close()

            styles_g = getSampleStyleSheet()
            story_g = []

            def _v(key, alt=""):
                return str(row_data.get(key) or alt or "")

            currency = getattr(self, "currency_symbol", "RD$")
            monto_val = row_data.get("monto", "")
            try:
                monto_str = f"{currency} {float(monto_val):,.2f}" if monto_val not in ("", None) else ""
            except Exception:
                monto_str = str(monto_val or "")

            info_rows = [
                ["Campo", "Valor"],
                ["Tipo", "Gasto"],
                ["Fecha", _v("fecha")],
                ["Equipo", _v("equipo_nombre")],
                ["Descripción", _v("descripcion")],
                ["Monto", monto_str],
            ]

            info_tbl = Table(info_rows, colWidths=[100, 350], hAlign="LEFT")
            info_tbl.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#FEE2E2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.HexColor("#7F1D1D")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, rl_colors.HexColor("#7F1D1D")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#FEF2F2")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))

            story_g.append(Paragraph(label, styles_g["Heading3"]))
            story_g.append(Spacer(1, 6))
            story_g.append(info_tbl)
            story_g.append(Spacer(1, 10))

            try:
                img_rl = RLImage(img_path)
                img_rl._restrictSize(480, 480)
                story_g.append(img_rl)
            except Exception as e:
                logger.warning(f"No se pudo insertar imagen gasto {img_path}: {e}")
                story_g.append(Paragraph("<i>No se pudo cargar la imagen del gasto</i>", styles_g["Normal"]))

            doc_g = SimpleDocTemplate(
                tmp_path,
                pagesize=LETTER,
                leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
            )
            doc_g.build(story_g)
            return tmp_path
        except Exception as e:
            logger.error(f"Error en _gasto_to_pdf_page_with_info: {e}", exc_info=True)
            return self._image_to_pdf_page(img_path, label)

    def _image_to_pdf_page(self, img_path: str, label: str) -> str | None:
        """
        Convierte una imagen en una página PDF con un título (label) arriba.
        Devuelve la ruta al PDF temporal creado.
        """
        try:
            import tempfile
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import LETTER
            from reportlab.lib.utils import ImageReader

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp_path = tmp.name
            tmp.close()

            page_w, page_h = LETTER
            margin = 36  # 0.5in
            title_space = 20

            c = canvas.Canvas(tmp_path, pagesize=LETTER)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(margin, page_h - margin, label)

            # Cargar imagen y escalar manteniendo aspecto
            img = ImageReader(img_path)
            iw, ih = img.getSize()
            max_w = page_w - 2 * margin
            max_h = page_h - 2 * margin - title_space
            scale = min(max_w / iw, max_h / ih)
            draw_w = iw * scale
            draw_h = ih * scale
            x = (page_w - draw_w) / 2
            y = margin
            c.drawImage(img, x, y, draw_w, draw_h, preserveAspectRatio=True, anchor='sw')

            c.showPage()
            c.save()
            return tmp_path
        except Exception:
            return None


    def _image_to_pdf_page_with_info(self, img_path: str, label: str, row_data: dict = None) -> str | None:
        """
        Convierte una imagen en una página PDF con mini tabla de información arriba.
        Si row_data es None o vacío, cae back a _image_to_pdf_page.
        """
        if not row_data:
            return self._image_to_pdf_page(img_path, label)
        try:
            import tempfile
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import LETTER
            from reportlab.lib.utils import ImageReader
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors as rl_colors

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp_path = tmp.name
            tmp.close()

            styles = getSampleStyleSheet()
            story = []

            # Mini tabla de información del conduce
            def _v(key, alt=""):
                return str(row_data.get(key) or alt or "")

            currency = getattr(self, "currency_symbol", "RD$")
            monto_val = row_data.get("monto", "")
            try:
                monto_str = f"{currency} {float(monto_val):,.2f}" if monto_val not in ("", None) else ""
            except Exception:
                monto_str = str(monto_val or "")

            horas_val = row_data.get("horas", "")
            try:
                horas_str = f"{float(horas_val):,.2f}" if horas_val not in ("", None) else ""
            except Exception:
                horas_str = str(horas_val or "")

            info_rows = [
                ["Campo", "Valor"],
                ["Conduce No.", _v("conduce")],
                ["Fecha", _v("fecha")],
                ["Cliente", _v("cliente_nombre") or _v("cliente")],
                ["Equipo", _v("equipo_nombre") or _v("equipo")],
                ["Operador", _v("operador_nombre") or _v("operador")],
                ["Horas", horas_str],
                ["Monto", monto_str],
            ]

            info_tbl = Table(info_rows, colWidths=[100, 350], hAlign="LEFT")
            info_tbl.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#E6F4EA")),
                ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.HexColor("#1F7A1F")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, rl_colors.HexColor("#1F7A1F")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#F8F9FA")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))

            story.append(Paragraph(label, styles["Heading3"]))
            story.append(Spacer(1, 6))
            story.append(info_tbl)
            story.append(Spacer(1, 10))

            # Imagen del conduce
            try:
                img_rl = RLImage(img_path)
                img_rl._restrictSize(480, 480)
                story.append(img_rl)
            except Exception as e:
                logger.warning(f"No se pudo insertar imagen {img_path}: {e}")
                story.append(Paragraph(f"<i>No se pudo cargar la imagen del conduce</i>", styles["Normal"]))

            doc = SimpleDocTemplate(
                tmp_path,
                pagesize=LETTER,
                leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
            )
            doc.build(story)
            return tmp_path
        except Exception as e:
            logger.error(f"Error en _image_to_pdf_page_with_info: {e}", exc_info=True)
            return self._image_to_pdf_page(img_path, label)

    def _merge_main_with_annexes(self, main_pdf: str, annex_pdf_paths: list[str], out_path: str) -> tuple[bool, str | None]:
        """
        Fusiona el PDF principal con una lista de PDFs anexos al final.
        """
        try:
            from PyPDF2 import PdfMerger
            merger = PdfMerger()
            merger.append(main_pdf)
            for p in annex_pdf_paths:
                merger.append(p)
            with open(out_path, "wb") as f:
                merger.write(f)
            merger.close()
            return True, None
        except Exception as e:
            return False, str(e)
        
    def _scale_col_widths_to_page(self, col_widths: list, page_width: float, left_margin: float, right_margin: float) -> list:
        """
        Si la suma de colWidths excede el ancho disponible en la página, escala proporcionalmente para que quepan.
        """
        if not col_widths:
            return col_widths
        available = page_width - (left_margin + right_margin)
        total = sum(col_widths)
        if total <= 0 or total <= available:
            return col_widths
        scale = available / total
        return [w * scale for w in col_widths]
    
    def _is_flexible_col(self, key: str) -> bool:
        """
        Columnas que pueden envolver el texto en varias líneas si no caben.
        """
        return key in {"ubicacion", "equipo_nombre", "operador_nombre", "cliente_nombre"}


    def _format_value_for_measure(self, key: str, val) -> str:
        """
        Devuelve el texto final como se mostrará en la celda (para medir y/o renderizar).
        """
        if key == "horas" and val not in ("", None):
            try:
                return f"{float(val):,.2f}"
            except Exception:
                return str(val or "")
        if key == "monto" and val not in ("", None):
            try:
                return f"{self.currency_symbol} {float(val):,.2f}"
            except Exception:
                return str(val or "")
        return str(val or "")


    def _auto_compute_col_widths(self, column_map: dict, data: list, page_w: float, margins=(36, 36),
                                font_name="Helvetica", font_size=9) -> list[float]:
        """
        Calcula anchos por columna según el texto más largo (headers + filas).
        Si excede el ancho disponible, reduce proporcionalmente SOLO columnas flexibles,
        dejando que el texto se envuelva (las filas aumentan de alto).
        """
        from reportlab.pdfbase.pdfmetrics import stringWidth

        left_margin, right_margin = margins
        available = page_w - (left_margin + right_margin)
        keys = list(column_map.keys())

        # Mínimos por columna (nunca bajamos de esto)
        min_widths = {
            "fecha": 60.0,
            "conduce": 55.0,
            "ubicacion": 90.0,
            "equipo_nombre": 90.0,
            "operador_nombre": 110.0,
            "horas": 45.0,
            "monto": 85.0,
            "cliente_nombre": 110.0,
        }
        pad = 10.0  # padding horizontal estimado por celda

        # 1) Deseados por medición (header + filas)
        desired = []
        for k in keys:
            header_text = str(column_map[k])
            max_w = stringWidth(header_text, font_name, font_size)
            for r in data:
                txt = self._format_value_for_measure(k, r.get(k, ""))
                w = stringWidth(txt, font_name, font_size)
                if w > max_w:
                    max_w = w
            desired_w = max_w + pad
            desired.append(desired_w)

        # 2) Aplicar mínimos
        widths = []
        for k, w in zip(keys, desired):
            widths.append(max(w, min_widths.get(k, 70.0)))

        total = sum(widths)
        if total <= available or available <= 0:
            return widths

        # 3) Reducir solo columnas flexibles hasta caber (proporcional a su "exceso" sobre el mínimo)
        for _ in range(3):  # hasta 3 iteraciones por si queda residuo
            total = sum(widths)
            if total <= available:
                break
            over = total - available

            # Espacio reducible en flex (por encima del mínimo)
            flex_excess = 0.0
            for i, k in enumerate(keys):
                if self._is_flexible_col(k):
                    flex_excess += max(0.0, widths[i] - min_widths.get(k, 70.0))

            if flex_excess <= 1e-6:
                # No hay de dónde reducir (ya estamos en mínimos) -> devolvemos widths, el wrapping hará el resto
                return widths

            # Reducir proporcionalmente a su exceso
            new_widths = list(widths)
            for i, k in enumerate(keys):
                if not self._is_flexible_col(k):
                    continue
                exceso_col = max(0.0, widths[i] - min_widths.get(k, 70.0))
                if exceso_col <= 0:
                    continue
                reduce_i = over * (exceso_col / flex_excess)
                new_w = max(min_widths.get(k, 70.0), widths[i] - reduce_i)
                new_widths[i] = new_w
            widths = new_widths

        return widths


    def _make_wrap_paragraph(self, text: str, font_size=9, align=TA_LEFT) -> Paragraph:
        """
        Crea un Paragraph con wrap para celdas de texto.
        """
        from reportlab.lib.styles import ParagraphStyle
        style = ParagraphStyle(
            name="Cell",
            parent=getSampleStyleSheet()["BodyText"],
            fontName="Helvetica",
            fontSize=font_size,
            leading=font_size + 2,
            alignment=align,
        )
        # escape para caracteres especiales HTML
        return Paragraph(escape(text or ""), style)


    def _rows_with_wrapping(self, column_map: dict, data: list, font_size=9) -> list[list]:
        """
        Construye filas: para columnas flexibles usa Paragraph (wrap) y en numéricas aplica formato.
        """
        rows = []
        keys = list(column_map.keys())
        for r in data:
            row_cells = []
            for k in keys:
                txt = self._format_value_for_measure(k, r.get(k, ""))
                if self._is_flexible_col(k):
                    row_cells.append(self._make_wrap_paragraph(txt, font_size=font_size))
                else:
                    row_cells.append(txt)
            rows.append(row_cells)
        return rows
    
    def generar_reporte_rendimientos_bloques(
        self,
        file_path: str,
        formato: str,
        datos_facturacion: list[dict],
        datos_rendimientos: list[dict],
        resumen: dict,
        moneda: str = "RD$",
        titulo: str = "REPORTE DE RENDIMIENTOS",
        rango_fechas:  str = "",
    ) -> tuple[bool, str | None]:
        """
        Genera reporte de rendimientos con estructura de bloques. 
        
        Soporta PDF y Excel con 3 secciones: 
        1. Bloque Facturación
        2. Bloque Rendimientos
        3. Resumen General
        
        Args:
            file_path:  Ruta donde guardar el archivo
            formato:  "pdf" o "excel"
            datos_facturacion: Lista de dicts con datos de facturación
            datos_rendimientos: Lista de dicts con datos de rendimientos
            resumen: Dict con totales generales
            moneda: Símbolo de moneda
            titulo: Título del reporte
            rango_fechas: Rango de fechas (ej: "2025-01-01 a 2025-01-31")
        
        Returns:
            tuple:  (éxito:  bool, error: str | None)
        """
        try: 
            if formato == "pdf":
                return self._generar_pdf_rendimientos_bloques(
                    file_path, datos_facturacion, datos_rendimientos,
                    resumen, moneda, titulo, rango_fechas
                )
            elif formato == "excel":
                return self._generar_excel_rendimientos_bloques(
                    file_path, datos_facturacion, datos_rendimientos,
                    resumen, moneda, titulo, rango_fechas
                )
            else:
                return False, f"Formato no soportado:  {formato}"
        
        except Exception as e:
            logger.error(f"Error generando reporte rendimientos: {e}", exc_info=True)
            return False, str(e)

    def generar_reporte_rendimientos_bloques(
        self,
        file_path: str,
        formato: str,
        datos_facturacion: list[dict],
        datos_rendimientos: list[dict],
        resumen: dict,
        moneda: str = "RD$",
        titulo: str = "REPORTE DE RENDIMIENTOS",
        rango_fechas: str = "",
    ) -> tuple[bool, str | None]:
        """
        Genera reporte de rendimientos con estructura de bloques. 
        
        Soporta PDF y Excel con 3 secciones: 
        1. Bloque Facturación
        2. Bloque Rendimientos
        3. Resumen General
        
        Args:
            file_path:  Ruta donde guardar el archivo
            formato:  "pdf" o "excel"
            datos_facturacion: Lista de dicts con datos de facturación
            datos_rendimientos: Lista de dicts con datos de rendimientos
            resumen: Dict con totales generales
            moneda: Símbolo de moneda
            titulo: Título del reporte
            rango_fechas: Rango de fechas (ej: "2025-01-01 a 2025-01-31")
        
        Returns:
            tuple:  (éxito:  bool, error: str | None)
        """
        try: 
            if formato == "pdf":
                return self._generar_pdf_rendimientos_bloques(
                    file_path, datos_facturacion, datos_rendimientos,
                    resumen, moneda, titulo, rango_fechas
                )
            elif formato == "excel":
                return self._generar_excel_rendimientos_bloques(
                    file_path, datos_facturacion, datos_rendimientos,
                    resumen, moneda, titulo, rango_fechas
                )
            else:
                return False, f"Formato no soportado:  {formato}"
        
        except Exception as e:
            logger.error(f"Error generando reporte rendimientos: {e}", exc_info=True)
            return False, str(e)

    def _generar_pdf_rendimientos_bloques(
        self,
        file_path: str,
        datos_facturacion: list,
        datos_rendimientos: list,
        resumen: dict,
        moneda: str,
        titulo: str,
        rango_fechas: str,
    ) -> tuple[bool, str | None]:
        """Genera PDF con bloques de Facturación + Rendimientos + Resumen."""
        try:
            print("\n=== INICIO _generar_pdf_rendimientos_bloques ===")
            print(f"File path: {file_path}")
            print(f"Moneda: {moneda}")
            print(f"Título: {titulo}")
            print(f"Rango:  {rango_fechas}")
            print(f"Datos facturación: {len(datos_facturacion)}")
            print(f"Datos rendimientos: {len(datos_rendimientos)}")
            print(f"Resumen: {resumen}")
            
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            from reportlab.lib import colors

            # Crear documento
            print("\n1. Creando documento...")
            doc = SimpleDocTemplate(
                file_path,
                pagesize=landscape(letter),
                leftMargin=36,
                rightMargin=36,
                topMargin=50,
                bottomMargin=50,
            )

            story = []
            styles = getSampleStyleSheet()

            # Estilo personalizado
            style_seccion = ParagraphStyle(
                name="Seccion",
                parent=styles["Heading2"],
                fontSize=12,
                textColor=colors.HexColor("#1F7A1F"),
                spaceAfter=8,
                fontName="Helvetica-Bold",
            )

            # --- ENCABEZADO ---
            print("\n2. Agregando encabezado...")
            story.append(Paragraph(f"<b>{titulo}</b>", styles["Title"]))
            if rango_fechas:
                story.append(Paragraph(f"Período: {rango_fechas}", styles["Normal"]))
            story.append(Spacer(1, 15))

            # --- BLOQUE 1: FACTURACIÓN ---
            print("\n3. Procesando BLOQUE FACTURACIÓN...")
            story.append(Paragraph("📊 FACTURACIÓN", style_seccion))
            
            if datos_facturacion:
                headers_fact = [
                    "Equipo", "Horas Fact.", "Volumen Fact.", "Monto Facturado",
                    "Precio/h", "Precio/u", "Modalidad(s)"
                ]
                
                data_fact = [headers_fact]
                
                for i, d in enumerate(datos_facturacion):
                    print(f"\n  Fila {i} facturación:")
                    print(f"    Datos: {d}")
                    
                    try:
                        equipo = str(d.get("equipo", ""))
                        print(f"    Equipo:  {equipo}")
                        
                        horas = float(d.get('horas_facturadas', 0))
                        horas_txt = f"{horas:.2f} h"
                        print(f"    Horas:  {horas} -> {horas_txt}")
                        
                        volumen = float(d.get('volumen_facturado', 0))
                        volumen_txt = f"{volumen:.2f}"
                        print(f"    Volumen: {volumen} -> {volumen_txt}")
                        
                        monto = float(d.get('monto_facturado', 0))
                        monto_txt = f"{moneda} {monto:,.2f}"
                        print(f"    Monto:  {monto} -> {monto_txt}")
                        
                        precio_h = float(d.get('precio_hora_facturado', 0))
                        precio_h_txt = f"{moneda} {precio_h:,.2f}"
                        print(f"    Precio/h: {precio_h} -> {precio_h_txt}")
                        
                        precio_u = float(d.get('precio_unidad_facturado', 0))
                        precio_u_txt = f"{moneda} {precio_u:,.2f}"
                        print(f"    Precio/u:  {precio_u} -> {precio_u_txt}")
                        
                        modalidades = str(d.get("modalidades", "-"))
                        print(f"    Modalidades: {modalidades}")
                        
                        fila = [equipo, horas_txt, volumen_txt, monto_txt, precio_h_txt, precio_u_txt, modalidades]
                        print(f"    Fila completa: {fila}")
                        data_fact.append(fila)
                        
                    except Exception as e: 
                        print(f"    ❌ ERROR en fila {i}: {e}")
                        import traceback
                        traceback.print_exc()
                        raise
                
                print(f"\n  Total filas facturación: {len(data_fact)}")
                print("  Creando tabla facturación...")
                
                tabla_fact = Table(data_fact, hAlign="LEFT")
                tabla_fact.setStyle(TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6F4EA")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F7A1F")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1F7A1F")),
                    ("ALIGN", (1, 1), (5, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
                ]))
                story.append(tabla_fact)
                print("  ✓ Tabla facturación creada")
            else:
                story.append(Paragraph("Sin datos de facturación", styles["Normal"]))
            
            story.append(Spacer(1, 20))

            # --- BLOQUE 2: RENDIMIENTOS ---
            print("\n4. Procesando BLOQUE RENDIMIENTOS...")
            story.append(Paragraph("💰 RENDIMIENTOS", style_seccion))
            
            if datos_rendimientos:
                headers_rend = [
                    "Equipo", "Horas Pag.", "Pagado Op.", "Gastos Equipo",
                    "Rendimiento Neto", "% Margen"
                ]
                
                data_rend = [headers_rend]
                
                for i, d in enumerate(datos_rendimientos):
                    print(f"\n  Fila {i} rendimientos:")
                    print(f"    Datos: {d}")
                    
                    try:
                        equipo = str(d.get("equipo", ""))
                        horas_pag = float(d.get('horas_pagadas', 0))
                        pag_op = float(d.get('monto_pagado_operador', 0))
                        gastos = float(d.get('gastos_equipo', 0))
                        rend_neto = float(d.get('rendimiento_neto', 0))
                        margen = float(d.get('margen_porcentaje', 0))
                        
                        fila = [
                            equipo,
                            f"{horas_pag:.2f} h",
                            f"{moneda} {pag_op:,.2f}",
                            f"{moneda} {gastos:,.2f}",
                            f"{moneda} {rend_neto:,.2f}",
                            f"{margen:.2f}%",
                        ]
                        print(f"    Fila:  {fila}")
                        data_rend.append(fila)
                        
                    except Exception as e:
                        print(f"    ❌ ERROR en fila {i}: {e}")
                        import traceback
                        traceback.print_exc()
                        raise
                
                print("  Creando tabla rendimientos...")
                tabla_rend = Table(data_rend, hAlign="LEFT")
                tabla_rend.setStyle(TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF4E0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#A35D00")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A35D00")),
                    ("ALIGN", (1, 1), (5, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFFAF0")]),
                ]))
                story.append(tabla_rend)
                print("  ✓ Tabla rendimientos creada")
            else:
                story.append(Paragraph("Sin datos de rendimientos", styles["Normal"]))
            
            story.append(Spacer(1, 25))

            # --- RESUMEN GENERAL ---
            print("\n5. Procesando RESUMEN...")
            print(f"  Datos resumen: {resumen}")
            story.append(Paragraph("📈 RESUMEN GENERAL", style_seccion))
            
            try:
                total_horas = float(resumen.get('total_horas_facturadas', 0))
                total_fact = float(resumen.get('total_facturado', 0))
                total_pag = float(resumen.get('total_pagado_operador', 0))
                total_gast = float(resumen.get('total_gastos', 0))
                rend_neto = float(resumen.get('rendimiento_neto', 0))
                margen_prom = float(resumen.get('margen_promedio', 0))
                
                print(f"  Valores extraídos:")
                print(f"    Horas:  {total_horas}")
                print(f"    Facturado: {total_fact}")
                print(f"    Pagado:  {total_pag}")
                print(f"    Gastos: {total_gast}")
                print(f"    Rendimiento: {rend_neto}")
                print(f"    Margen: {margen_prom}")
                
                resumen_data = [
                    ["Total Horas Facturadas:", f"{total_horas:,.2f} h"],
                    ["Total Facturado:", f"{moneda} {total_fact:,.2f}"],
                    ["Total Pagado Operador:", f"{moneda} {total_pag:,.2f}"],
                    ["Total Gastos Equipos:", f"{moneda} {total_gast:,.2f}"],
                    ["", ""],
                    ["Rendimiento Neto:", f"{moneda} {rend_neto:,.2f}"],
                    ["Margen Promedio:", f"{margen_prom:.2f}%"],
                ]
                
                print("  Creando tabla resumen...")
                tabla_resumen = Table(resumen_data, colWidths=[200, 150], hAlign="CENTER")
                tabla_resumen.setStyle(TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("LINEABOVE", (0, 5), (-1, 5), 2, colors.HexColor("#2E7D32")),
                    ("BACKGROUND", (0, 5), (-1, 6), colors.HexColor("#E8F5E9")),
                    ("TEXTCOLOR", (0, 5), (-1, 6), colors.HexColor("#2E7D32")),
                    ("FONTNAME", (0, 5), (-1, 6), "Helvetica-Bold"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(tabla_resumen)
                print("  ✓ Tabla resumen creada")
                
            except Exception as e:
                print(f"  ❌ ERROR creando resumen: {e}")
                import traceback
                traceback.print_exc()
                raise

            # Construir PDF
            print("\n6. Construyendo PDF...")
            doc.build(story)
            print("  ✓ PDF construido exitosamente")
            
            print("=== FIN _generar_pdf_rendimientos_bloques ===\n")
            return True, None

        except Exception as e: 
            print(f"\n❌ ERROR GENERAL en _generar_pdf_rendimientos_bloques: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Error generando PDF rendimientos: {e}", exc_info=True)
            return False, str(e)        

    def _generar_excel_rendimientos_bloques(
        self,
        file_path: str,
        datos_facturacion: list,
        datos_rendimientos: list,
        resumen: dict,
        moneda: str,
        titulo: str,
        rango_fechas: str,
    ) -> tuple[bool, str | None]:
        """
        Genera Excel con 3 hojas: 
        - Hoja 1: Facturación
        - Hoja 2: Rendimientos
        - Hoja 3: Resumen
        """
        try:
            import pandas as pd
            from openpyxl import load_workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

            # Crear DataFrames
            df_fact = pd.DataFrame(datos_facturacion) if datos_facturacion else pd.DataFrame()
            df_rend = pd.DataFrame(datos_rendimientos) if datos_rendimientos else pd.DataFrame()

            # Formatear columnas de facturación
            if not df_fact.empty:
                df_fact = df_fact.rename(columns={
                    "equipo": "Equipo",
                    "horas_facturadas": "Horas Fact.",
                    "volumen_facturado": "Volumen Fact.",
                    "monto_facturado": "Monto Facturado",
                    "precio_hora_facturado": "Precio/h",
                    "precio_unidad_facturado":  "Precio/u",
                    "modalidades": "Modalidad(s)",
                })

            # Formatear columnas de rendimientos
            if not df_rend.empty:
                df_rend = df_rend.rename(columns={
                    "equipo": "Equipo",
                    "horas_pagadas": "Horas Pag.",
                    "monto_pagado_operador": "Pagado Op.",
                    "gastos_equipo": "Gastos Equipo",
                    "rendimiento_neto": "Rendimiento Neto",
                    "margen_porcentaje": "% Margen",
                })

            # Escribir a Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Hoja 1: Facturación
                if not df_fact.empty:
                    df_fact.to_excel(writer, sheet_name='Facturación', index=False)
                
                # Hoja 2: Rendimientos
                if not df_rend.empty:
                    df_rend.to_excel(writer, sheet_name='Rendimientos', index=False)
                
                # Hoja 3: Resumen
                resumen_data = {
                    "Concepto": [
                        "Total Horas Facturadas",
                        "Total Facturado",
                        "Total Pagado Operador",
                        "Total Gastos Equipos",
                        "",
                        "Rendimiento Neto",
                        "Margen Promedio",
                    ],
                    "Valor": [
                        f"{resumen.get('total_horas_facturadas', 0):,.2f} h",
                        f"{moneda} {resumen.get('total_facturado', 0):,.2f}",
                        f"{moneda} {resumen.get('total_pagado_operador', 0):,.2f}",
                        f"{moneda} {resumen.get('total_gastos', 0):,.2f}",
                        "",
                        f"{moneda} {resumen.get('rendimiento_neto', 0):,.2f}",
                        f"{resumen.get('margen_promedio', 0):,.2f}%",
                    ],
                }
                df_resumen = pd.DataFrame(resumen_data)
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)

            # Aplicar estilos con openpyxl
            wb = load_workbook(file_path)

            # Estilos comunes
            header_fill = PatternFill(start_color="E6F4EA", end_color="E6F4EA", fill_type="solid")
            header_font = Font(bold=True, color="1F7A1F")
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            # Formatear hoja Facturación
            if 'Facturación' in wb.sheetnames:
                ws = wb['Facturación']
                for cell in ws[1]:  # Header
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.border = border
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Ajustar anchos
                ws.column_dimensions['A'].width = 25  # Equipo
                ws.column_dimensions['B'].width = 12  # Horas
                ws.column_dimensions['C'].width = 12  # Volumen
                ws.column_dimensions['D'].width = 15  # Monto
                ws.column_dimensions['E'].width = 12  # Precio/h
                ws.column_dimensions['F'].width = 12  # Precio/u
                ws.column_dimensions['G'].width = 15  # Modalidad

            # Formatear hoja Rendimientos
            if 'Rendimientos' in wb.sheetnames:
                ws = wb['Rendimientos']
                for cell in ws[1]: 
                    cell.fill = PatternFill(start_color="FFF4E0", end_color="FFF4E0", fill_type="solid")
                    cell.font = Font(bold=True, color="A35D00")
                    cell.border = border
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                
                ws.column_dimensions['A'].width = 25
                ws.column_dimensions['B'].width = 12
                ws.column_dimensions['C'].width = 15
                ws.column_dimensions['D'].width = 15
                ws.column_dimensions['E'].width = 18
                ws.column_dimensions['F'].width = 12

            # Formatear hoja Resumen
            if 'Resumen' in wb.sheetnames:
                ws = wb['Resumen']
                
                # Header
                for cell in ws[1]:
                    cell.fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
                    cell.font = Font(bold=True, color="2E7D32")
                    cell.border = border
                
                # Destacar Rendimiento Neto y Margen
                for row_idx in [7, 8]:  # Filas de rendimiento y margen
                    for cell in ws[row_idx]:
                        cell.fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
                        cell.font = Font(bold=True, color="2E7D32")
                
                ws.column_dimensions['A'].width = 30
                ws.column_dimensions['B'].width = 20

            # Guardar cambios
            wb.save(file_path)
            
            return True, None

        except Exception as e:
            logger.error(f"Error generando Excel rendimientos: {e}", exc_info=True)
            return False, str(e)