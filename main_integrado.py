# main_integrado.py

"""
Aplicación Principal Integrada - ZOEC EQUIPOS
Incluye todos los módulos: Dashboard, Combustible, Cuentas por Cobrar, WhatsApp
"""

# ========== IMPORTS CORREGIDOS ==========

import sys
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMessageBox
from PyQt6.QtGui import QAction

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zoec_equipos.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Importar módulos principales
from firebase_manager import FirebaseManager
from dashboard_ejecutivo import DashboardEjecutivo
from gestor_combustible import GestorCombustible
from cuentas_por_cobrar import CuentasPorCobrar
from whatsapp_integration import WhatsAppIntegration

# Importar módulos existentes del proyecto
# (Ajusta estos según lo que tengas implementado)
try:
    from dashboard_tab import DashboardTab
except ImportError:
    DashboardTab = None
    logger.warning("dashboard_tab no encontrado")

try:
    from registro_alquileres_tab_modern import RegistroAlquileresTabModern
except ImportError:
    RegistroAlquileresTabModern = None
    logger.warning("registro_alquileres_tab_modern no encontrado")

try:
    from gastos_tab_modern import GastosTabModern
except ImportError:
    GastosTabModern = None
    logger.warning("gastos_tab_modern no encontrado")

try:
    from tab_pagos_operadores_modern import TabPagosOperadoresModern
except ImportError:
    TabPagosOperadoresModern = None
    logger.warning("tab_pagos_operadores_modern no encontrado")

# Estilos globales
MAIN_STYLE = """
QMainWindow {
    background-color: #F3F4F6;
}
QTabWidget::pane {
    border: none;
    background-color: #F3F4F6;
}
QTabBar::tab {
    background-color: #E5E7EB;
    color: #374151;
    padding: 12px 24px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
    font-size: 11pt;
}
QTabBar::tab:selected {
    background-color: #F59E0B;
    color: white;
}
QTabBar::tab:hover {
    background-color: #D1D5DB;
}
QMenuBar {
    background-color: #1F2937;
    color: white;
    padding: 5px;
}
QMenuBar::item {
    background-color: transparent;
    color: white;
    padding: 8px 15px;
}
QMenuBar::item:selected {
    background-color: #374151;
}
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
}
QMenu::item {
    padding: 8px 30px;
    color: #1F2937;
}
QMenu::item:selected {
    background-color: #FEF3C7;
}
"""


class ZoecEquiposApp(QMainWindow):
    """Aplicación principal de ZOEC EQUIPOS"""
    
    def __init__(self):
        super().__init__()
        
        # Configuración
        self.config = self._cargar_configuracion()
        
        # Firebase Manager
        try:
            self.fm = FirebaseManager(self.config)
            logger.info("Firebase Manager inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando Firebase: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error de Conexión",
                f"No se pudo conectar a Firebase:\n{e}\n\n"
                "Verifique su configuración."
            )
            sys.exit(1)
        
        self.setWindowTitle("ZOEC EQUIPOS - Sistema de Gestión")
        self.setMinimumSize(1400, 800)
        
        self.setStyleSheet(MAIN_STYLE)
        
        self._init_ui()
        self._crear_menu()
        
        # Centrar ventana
        self._centrar_ventana()
    
    def _cargar_configuracion(self):
        """Carga la configuración de la aplicación"""
        # Aquí puedes cargar desde un archivo JSON o usar valores por defecto
        config = {
            'app': {
                'nombre': 'ZOEC EQUIPOS',
                'version': '2.0.0',
                'moneda': 'RD$'
            },
            'firebase': {
                # Tus credenciales de Firebase
                'credentials_path': 'path/to/credentials.json',
                'project_id': 'tu-project-id'
            },
            'whatsapp': {
                'provider': 'twilio',  # o 'whatsapp_business'
                'twilio_account_sid': '',
                'twilio_auth_token': '',
                'twilio_from': '',
                'api_token': '',
                'phone_id': ''
            }
        }
        
        return config
    
    def _init_ui(self):
        """Inicializa la interfaz de usuario"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tabs principales
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # === MÓDULOS NUEVOS ===
        
        # Dashboard Ejecutivo
        try:
            self.tab_dashboard = DashboardEjecutivo(self.fm, self.config)
            self.tabs.addTab(self.tab_dashboard, "📊 Dashboard")
            logger.info("Módulo Dashboard cargado")
        except Exception as e:
            logger.error(f"Error cargando Dashboard: {e}", exc_info=True)
        
        # Control de Combustible
        try:
            self.tab_combustible = GestorCombustible(self.fm, self.config)
            self.tabs.addTab(self.tab_combustible, "⛽ Combustible")
            logger.info("Módulo Combustible cargado")
        except Exception as e:
            logger.error(f"Error cargando Combustible: {e}", exc_info=True)
        
        # Cuentas por Cobrar
        try:
            self.tab_cuentas = CuentasPorCobrar(self.fm, self.config)
            self.tabs.addTab(self.tab_cuentas, "💳 Cuentas x Cobrar")
            logger.info("Módulo Cuentas por Cobrar cargado")
        except Exception as e:
            logger.error(f"Error cargando Cuentas por Cobrar: {e}", exc_info=True)
        
        # WhatsApp Business
        try:
            self.tab_whatsapp = WhatsAppIntegration(self.fm, self.config)
            self.tabs.addTab(self.tab_whatsapp, "📱 WhatsApp")
            logger.info("Módulo WhatsApp cargado")
        except Exception as e:
            logger.error(f"Error cargando WhatsApp: {e}", exc_info=True)
        
        # === MÓDULOS EXISTENTES (descomenta y ajusta según tus archivos) ===
        
        # from gestion_alquileres import GestionAlquileres
        # self.tab_alquileres = GestionAlquileres(self.fm, self.config)
        # self.tabs.addTab(self.tab_alquileres, "🚜 Alquileres")
        
        # from gestion_gastos import GestionGastos
        # self.tab_gastos = GestionGastos(self.fm, self.config)
        # self.tabs.addTab(self.tab_gastos, "💸 Gastos")
        
        # from gestion_equipos_dialog import GestionEquiposDialog
        # (Este lo puedes llamar desde el menú)
        
        layout.addWidget(self.tabs)
    
    def _crear_menu(self):
        """Crea la barra de menú"""
        menubar = self.menuBar()
        
        # Menú Archivo
        menu_archivo = menubar.addMenu("&Archivo")
        
        action_configuracion = QAction("⚙️ Configuración", self)
        action_configuracion.triggered.connect(self._abrir_configuracion)
        menu_archivo.addAction(action_configuracion)
        
        menu_archivo.addSeparator()
        
        action_salir = QAction("❌ Salir", self)
        action_salir.triggered.connect(self.close)
        menu_archivo.addAction(action_salir)
        
        # Menú Gestión
        menu_gestion = menubar.addMenu("&Gestión")
        
        action_equipos = QAction("🚜 Equipos", self)
        action_equipos.triggered.connect(self._abrir_gestion_equipos)
        menu_gestion.addAction(action_equipos)
        
        action_clientes = QAction("👥 Clientes", self)
        action_clientes.triggered.connect(lambda: self._abrir_gestion_entidades("Cliente"))
        menu_gestion.addAction(action_clientes)
        
        action_operadores = QAction("👷 Operadores", self)
        action_operadores.triggered.connect(lambda: self._abrir_gestion_entidades("Operador"))
        menu_gestion.addAction(action_operadores)
        
        # Menú Reportes
        menu_reportes = menubar.addMenu("&Reportes")
        
        action_rendimientos = QAction("📊 Rendimientos", self)
        action_rendimientos.triggered.connect(self._abrir_reporte_rendimientos)
        menu_reportes.addAction(action_rendimientos)
        
        action_prograin = QAction("📄 Exportar PROGRAIN", self)
        action_prograin.triggered.connect(self._abrir_exportador_prograin)
        menu_reportes.addAction(action_prograin)
        
        # Menú Ayuda
        menu_ayuda = menubar.addMenu("&Ayuda")
        
        action_acerca = QAction("ℹ️ Acerca de", self)
        action_acerca.triggered.connect(self._mostrar_acerca_de)
        menu_ayuda.addAction(action_acerca)
    
    def _centrar_ventana(self):
        """Centra la ventana en la pantalla"""
        screen = QApplication.primaryScreen().geometry()
        window = self.frameGeometry()
        center = screen.center()
        window.moveCenter(center)
        self.move(window.topLeft())
    
    def _abrir_configuracion(self):
        """Abre diálogo de configuración general"""
        QMessageBox.information(
            self,
            "Configuración",
            "Configuración general próximamente.\n\n"
            "Por ahora use los botones de configuración en cada módulo."
        )
    
    def _abrir_gestion_equipos(self):
        """Abre diálogo de gestión de equipos"""
        try:
            from dialogos.gestion_equipos_dialog import GestionEquiposDialog
            dialog = GestionEquiposDialog(self.fm, parent=self)
            dialog.exec()
        except ImportError:
            QMessageBox.warning(
                self,
                "Módulo no disponible",
                "El módulo de gestión de equipos no está disponible.\n\n"
                "Asegúrese de que existe:\n"
                "dialogos/gestion_equipos_dialog.py"
            )
        except Exception as e:
            logger.error(f"Error abriendo gestión de equipos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al abrir gestión de equipos:\n{e}")
    
    def _abrir_gestion_entidades(self, tipo):
        """Abre diálogo de gestión de entidades (clientes/operadores)"""
        try:
            from dialogos.gestion_entidad_dialog import GestionEntidadDialog
            dialog = GestionEntidadDialog(self.fm, tipo, parent=self)
            dialog.exec()
        except ImportError:
            QMessageBox.warning(
                self,
                "Módulo no disponible",
                f"El módulo de gestión de {tipo}s no está disponible.\n\n"
                "Asegúrese de que existe:\n"
                "dialogos/gestion_entidad_dialog.py"
            )
        except Exception as e:
            logger.error(f"Error abriendo gestión de {tipo}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al abrir gestión de {tipo}:\n{e}")
        
    def _abrir_reporte_rendimientos(self):
        """Abre diálogo de reporte de rendimientos"""
        try:
            from dialogos.dialogo_reporte_rendimientos_firebase import (
                DialogoReporteRendimientosFirebase,
            )
            equipos = self.fm.obtener_equipos(activo=True)
            equipos_mapa = {str(e['id']): e['nombre'] for e in equipos}
            
            dialog = DialogoReporteRendimientosFirebase(self.fm, equipos_mapa, parent=self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                # Aquí puedes manejar la generación del reporte
                pass
        except ImportError:
            QMessageBox.warning(
                self,
                "Módulo no disponible",
                "El módulo de reportes de rendimientos no está disponible.\n\n"
                "Asegúrese de que existe:\n"
                "dialogos/dialogo_reporte_rendimientos_firebase.py"
            )
        except Exception as e:
            logger.error(f"Error abriendo reporte de rendimientos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al abrir reporte:\n{e}")


    def _abrir_exportador_prograin(self):
        """Abre diálogo de exportador PROGRAIN"""
        try:
            from dialogos.dialogo_exportador_prograin import DialogoExportadorPrograin
            
            # Cargar todos los mapas necesarios
            equipos = self.fm.obtener_equipos()
            clientes = self.fm.obtener_entidades(tipo="Cliente")
            
            mapas = {
                'equipos': {str(e['id']): e['nombre'] for e in equipos},
                'clientes': {str(c['id']): c['nombre'] for c in clientes}
            }
            
            dialog = DialogoExportadorPrograin(self.fm, mapas, self.config, parent=self)
            dialog.exec()
        except ImportError:
            QMessageBox.warning(
                self,
                "Módulo no disponible",
                "El exportador PROGRAIN no está disponible.\n\n"
                "Asegúrese de que existe:\n"
                "dialogos/dialogo_exportador_prograin.py"
            )
        except Exception as e:
            logger.error(f"Error abriendo exportador PROGRAIN: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al abrir exportador:\n{e}")
    
    def _mostrar_acerca_de(self):
        """Muestra información sobre la aplicación"""
        QMessageBox.about(
            self,
            "Acerca de ZOEC EQUIPOS",
            f"<h2>ZOEC EQUIPOS</h2>"
            f"<p><b>Versión:</b> {self.config['app']['version']}</p>"
            f"<p>Sistema Integral de Gestión de Alquiler de Equipos Pesados</p>"
            f"<hr>"
            f"<p><b>Módulos incluidos:</b></p>"
            f"<ul>"
            f"<li>📊 Dashboard Ejecutivo</li>"
            f"<li>🚜 Gestión de Alquileres</li>"
            f"<li>💸 Control de Gastos</li>"
            f"<li>⛽ Control de Combustible</li>"
            f"<li>💳 Cuentas por Cobrar</li>"
            f"<li>📱 WhatsApp Business</li>"
            f"<li>📊 Reportes y Análisis</li>"
            f"</ul>"
            f"<hr>"
            f"<p>© 2024 ZOEC CIVIL - Todos los derechos reservados</p>"
        )


def main():
    """Función principal"""
    app = QApplication(sys.argv)
    
    # Configurar aplicación
    app.setApplicationName("ZOEC EQUIPOS")
    app.setOrganizationName("ZOEC CIVIL")
    app.setApplicationVersion("2.0.0")
    
    # Crear y mostrar ventana principal
    ventana = ZoecEquiposApp()
    ventana.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()