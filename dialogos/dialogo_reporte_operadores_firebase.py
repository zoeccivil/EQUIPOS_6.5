from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit, QPushButton,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont
from firebase_manager import FirebaseManager
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class DialogoReporteOperadoresFirebase(QDialog):
    """
    Diálogo de filtros para Reporte de Operadores (versión Firebase).

    Filtros:
      - Operador (Todos / uno)
      - Equipo (Todos / uno)
      - Rango de fechas (desde primera transacción global u operador hasta hoy)
    """

    def __init__(
        self,
        fm: FirebaseManager,
        operadores_mapa: dict,
        equipos_mapa: dict,
        clientes_mapa: dict = None,
        proyecto_id=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Reporte de Operadores - Filtros")
        self.fm = fm
        self.proyecto_id = proyecto_id
        self.formato = None

        self.operadores_mapa = operadores_mapa or {}
        self.equipos_mapa = equipos_mapa or {}
        self.clientes_mapa = clientes_mapa or {}

        # Aplicar tema consistente
        self.setStyleSheet("""
            QDialog {
                background-color: #F3F4F6;
                font-family: 'Segoe UI';
            }
            QLabel {
                color: #374151;
                font-size: 11pt;
                font-weight: 500;
            }
            QComboBox {
                background-color: #FFFFFF;
                border: 2px solid #E5E7EB;
                border-radius: 6px;
                padding: 8px 12px;
                color: #1F2937;
                font-size: 10pt;
                min-height: 25px;
            }
            QComboBox:hover {
                border: 2px solid #F59E0B;
            }
            QComboBox:focus {
                border: 2px solid #F59E0B;
            }
            QDateEdit {
                background-color: #FFFFFF;
                border: 2px solid #E5E7EB;
                border-radius: 6px;
                padding: 8px 12px;
                color: #1F2937;
                font-size: 10pt;
                min-height: 25px;
            }
            QDateEdit:hover {
                border: 2px solid #F59E0B;
            }
            QDateEdit:focus {
                border: 2px solid #F59E0B;
            }
            QPushButton {
                background-color: #F59E0B;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 10pt;
                font-weight: 600;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #D97706;
            }
            QPushButton:pressed {
                background-color: #B45309;
            }
            QPushButton#btn_cancel {
                background-color: #E5E7EB;
                color: #374151;
            }
            QPushButton#btn_cancel:hover {
                background-color: #D1D5DB;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Título
        titulo = QLabel("Filtros de Reporte")
        titulo.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1F2937; margin-bottom: 10px;")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)

        # Operador
        hlayout_op = QHBoxLayout()
        hlayout_op.setSpacing(10)
        lbl_op = QLabel("Operador:")
        lbl_op.setFixedWidth(80)
        hlayout_op.addWidget(lbl_op)
        self.combo_operador = QComboBox()
        self.combo_operador.addItem("Todos", None)
        for oid, nom in sorted(self.operadores_mapa.items(), key=lambda x: x[1]):
            self.combo_operador.addItem(nom, str(oid))
        hlayout_op.addWidget(self.combo_operador)
        layout.addLayout(hlayout_op)

        # Equipo
        hlayout_eq = QHBoxLayout()
        hlayout_eq.setSpacing(10)
        lbl_eq = QLabel("Equipo:")
        lbl_eq.setFixedWidth(80)
        hlayout_eq.addWidget(lbl_eq)
        self.combo_equipo = QComboBox()
        self.combo_equipo.addItem("Todos", None)
        for eid, nom in sorted(self.equipos_mapa.items(), key=lambda x: x[1]):
            self.combo_equipo.addItem(nom, str(eid))
        hlayout_eq.addWidget(self.combo_equipo)
        layout.addLayout(hlayout_eq)

        # Fechas
        hlayout_fechas = QHBoxLayout()
        hlayout_fechas.setSpacing(10)
        
        lbl_desde = QLabel("Desde:")
        lbl_desde.setFixedWidth(80)
        hlayout_fechas.addWidget(lbl_desde)
        
        self.fecha_inicio = QDateEdit(calendarPopup=True)
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        self.fecha_inicio.setCalendarPopup(True)
        hlayout_fechas.addWidget(self.fecha_inicio)

        hlayout_fechas.addSpacing(15)

        lbl_hasta = QLabel("Hasta:")
        lbl_hasta.setFixedWidth(60)
        hlayout_fechas.addWidget(lbl_hasta)
        
        self.fecha_fin = QDateEdit(calendarPopup=True)
        self.fecha_fin.setDisplayFormat("yyyy-MM-dd")
        self.fecha_fin.setCalendarPopup(True)
        hlayout_fechas.addWidget(self.fecha_fin)
        
        layout.addLayout(hlayout_fechas)

        layout.addSpacing(10)

        # Botones
        btns = QHBoxLayout()
        btns.setSpacing(10)
        
        self.btn_pdf = QPushButton("📄 Exportar PDF")
        self.btn_pdf.clicked.connect(self.exportar_pdf)
        btns.addWidget(self.btn_pdf)

        self.btn_excel = QPushButton("📊 Exportar Excel")
        self.btn_excel.clicked.connect(self.exportar_excel)
        btns.addWidget(self.btn_excel)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)

        layout.addLayout(btns)

        # Enlaces
        self.combo_operador.currentIndexChanged.connect(self.actualizar_rango_fechas)

        # Inicializar fechas
        self.actualizar_rango_fechas()
        
        # Tamaño mínimo
        self.setMinimumWidth(550)

    def get_filtros(self) -> dict:
        """Devuelve los filtros seleccionados"""
        operador_id = self.combo_operador.currentData()
        equipo_id = self.combo_equipo.currentData()

        return {
            "operador_id": str(operador_id) if operador_id else None,
            "operador_nombre": self.combo_operador.currentText(),
            "equipo_id": str(equipo_id) if equipo_id else None,
            "equipo_nombre": self.combo_equipo.currentText(),
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
        }

    def exportar_pdf(self):
        """Genera el PDF del reporte de operadores"""
        try:
            # Obtener filtros
            filtros = self.get_filtros()
            operador_nombre = filtros["operador_nombre"]
            operador_id = filtros["operador_id"]
            equipo_id = filtros["equipo_id"]
            fecha_inicio = filtros["fecha_inicio"]
            fecha_fin = filtros["fecha_fin"]

            # Diálogo para guardar
            nombre_sugerido = f"Reporte_Operadores_{operador_nombre.replace(' ', '_')}_{fecha_inicio}_a_{fecha_fin}.pdf"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte de Operadores",
                nombre_sugerido,
                "PDF (*.pdf)"
            )

            if not file_path:
                return  # Usuario canceló

            # Obtener datos de alquileres (facturas) con filtros
            filtros_alq = {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
            }
            if operador_id:
                filtros_alq["operador_id"] = operador_id
            if equipo_id:
                filtros_alq["equipo_id"] = equipo_id

            alquileres = self.fm.obtener_alquileres(filtros_alq) or []

            # Enriquecer con nombres
            for alq in alquileres:
                oid = str(alq.get("operador_id", "") or "")
                eid = str(alq.get("equipo_id", "") or "")
                cid = str(alq.get("cliente_id", "") or "")
                
                alq["operador_nombre"] = self.operadores_mapa.get(oid, f"ID:{oid}")
                alq["equipo_nombre"] = self.equipos_mapa.get(eid, f"ID:{eid}")
                alq["cliente_nombre"] = self.clientes_mapa.get(cid, f"ID:{cid}")

            # Obtener pagos a operadores
            try:
                pagos = self.fm.obtener_pagos_operadores(
                    operador_id=operador_id,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                ) or []
            except Exception as e:
                logger.warning(f"No se pudieron obtener pagos: {e}")
                pagos = []

            # Calcular totales
            total_horas = sum(float(a.get("horas", 0) or 0) for a in alquileres)
            total_facturado = sum(float(a.get("monto", 0) or 0) for a in alquileres)
            total_pagado = sum(float(p.get("monto", 0) or 0) for p in pagos)

            # Preparar datos para PDF
            from report_generator import ReportGenerator

            titulo = f"REPORTE DE OPERADORES - {operador_nombre.upper()}"
            date_range = f"{fecha_inicio} a {fecha_fin}"

            column_map = {
                "fecha": "Fecha",
                "equipo_nombre": "Equipo",
                "cliente_nombre": "Cliente",
                "horas": "Horas",
                "monto": "Monto",
            }

            # Obtener storage_manager
            storage_manager = None
            if hasattr(self.fm, 'storage_manager'):
                storage_manager = self.fm.storage_manager
            elif self.parent() and hasattr(self.parent(), 'sm'):
                storage_manager = self.parent().sm

            rg = ReportGenerator(
                data=alquileres,
                title=titulo,
                cliente=operador_nombre,
                date_range=date_range,
                currency_symbol="RD$",
                storage_manager=storage_manager,
                column_map=column_map
            )

            # Agregar resumen de operadores al final
            rg.total_facturado = total_facturado
            rg.total_abonado = total_pagado
            rg.saldo = total_facturado - total_pagado

            # Agregar datos custom para operadores
            rg.total_horas = total_horas
            rg.pagos_operador = pagos

            # Generar PDF
            exito, error = rg.to_pdf_operadores(file_path)

            if exito:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Reporte generado exitosamente:\n{file_path}"
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo generar el reporte:\n{error}"
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error generando PDF operadores: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error generando el reporte:\n{e}"
            )

    def exportar_excel(self):
        """Genera el Excel del reporte de operadores"""
        try:
            import pandas as pd
            
            filtros = self.get_filtros()
            operador_nombre = filtros["operador_nombre"]
            operador_id = filtros["operador_id"]
            equipo_id = filtros["equipo_id"]
            fecha_inicio = filtros["fecha_inicio"]
            fecha_fin = filtros["fecha_fin"]

            nombre_sugerido = f"Reporte_Operadores_{operador_nombre.replace(' ', '_')}_{fecha_inicio}_a_{fecha_fin}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Reporte de Operadores",
                nombre_sugerido,
                "Excel (*.xlsx)"
            )

            if not file_path:
                return

            # Obtener datos
            filtros_alq = {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
            }
            if operador_id:
                filtros_alq["operador_id"] = operador_id
            if equipo_id:
                filtros_alq["equipo_id"] = equipo_id

            alquileres = self.fm.obtener_alquileres(filtros_alq) or []

            # Enriquecer
            for alq in alquileres:
                oid = str(alq.get("operador_id", "") or "")
                eid = str(alq.get("equipo_id", "") or "")
                cid = str(alq.get("cliente_id", "") or "")
                alq["operador_nombre"] = self.operadores_mapa.get(oid, f"ID:{oid}")
                alq["equipo_nombre"] = self.equipos_mapa.get(eid, f"ID:{eid}")
                alq["cliente_nombre"] = self.clientes_mapa.get(cid, f"ID:{cid}")

            # Crear DataFrame
            df = pd.DataFrame(alquileres)
            
            if not df.empty:
                columnas_mostrar = ["fecha", "equipo_nombre", "operador_nombre", "cliente_nombre", "horas", "monto"]
                columnas_existentes = [c for c in columnas_mostrar if c in df.columns]
                df = df[columnas_existentes]
                
                df = df.rename(columns={
                    "fecha": "Fecha",
                    "equipo_nombre": "Equipo",
                    "operador_nombre": "Operador",
                    "cliente_nombre": "Cliente",
                    "horas": "Horas",
                    "monto": "Monto"
                })

            # Guardar
            df.to_excel(file_path, index=False, sheet_name="Operadores")

            QMessageBox.information(
                self,
                "Éxito",
                f"Reporte generado exitosamente:\n{file_path}"
            )
            self.accept()

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error generando Excel operadores: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error generando el reporte:\n{e}"
            )

    def actualizar_rango_fechas(self):
        """Actualiza el rango de fechas según operador seleccionado"""
        operador_id = self.combo_operador.currentData()
        try:
            if operador_id:
                fecha_inicio_str = self.fm.obtener_fecha_primera_transaccion_operador(str(operador_id))
            else:
                fecha_inicio_str = self.fm.obtener_fecha_primera_transaccion()
        except Exception:
            fecha_inicio_str = None

        if fecha_inicio_str:
            qd = QDate.fromString(fecha_inicio_str, "yyyy-MM-dd")
            if qd.isValid():
                self.fecha_inicio.setDate(qd)
            else:
                self.fecha_inicio.setDate(QDate.currentDate())
        else:
            self.fecha_inicio.setDate(QDate.currentDate())

        self.fecha_fin.setDate(QDate.currentDate())