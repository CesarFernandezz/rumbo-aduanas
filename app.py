import sys
import os
import pandas as pd
from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout, QHBoxLayout, QFileDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# COMPONENTES MODERNOS FLUENT (Opción A)
from qfluentwidgets import (FluentWindow, CardWidget, ComboBox, SpinBox, 
                            DoubleSpinBox, PrimaryPushButton, PushButton, 
                            TitleLabel, SubtitleLabel, BodyLabel, TextBrowser, 
                            TextEdit, LineEdit, MessageBox, DatePicker)
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import setTheme, Theme

# IMPORTACIONES DE TU BACKEND ROBUSTO
from src.database import inicializar_tablas, guardar_en_historial
from src.predict_eta import entrenar_modelo_eta
from src.vuce_ai import consultar_asesor_vuce
from src.vuce_pdf import generar_pdf_dictamen
from src.auth import verificar_usuario, registrar_usuario

DISTANCIAS_LOGISTICAS = {
    'Shanghái': {
        'Puerto Cabello': {'Marítimo': 15100, 'La Guaira': 15150, 'Maiquetía': 15150},
        'La Guaira': {'Marítimo': 15150, 'Puerto Cabello': 15100, 'Maiquetía': 15150},
        'Maiquetía': {'Marítimo': 15150, 'Puerto Cabello': 15100, 'La Guaira': 15150}
    },
    'Miami': {
        'Puerto Cabello': {'Marítimo': 1980, 'La Guaira': 2050, 'Maiquetía': 2050},
        'La Guaira': {'Marítimo': 2050, 'Puerto Cabello': 1980, 'Maiquetía': 2050},
        'Maiquetía': {'Marítimo': 2050, 'Puerto Cabello': 1980, 'La Guaira': 2050}
    },
    'Róterdam': {
        'Puerto Cabello': {'Marítimo': 7400, 'La Guaira': 7350, 'Maiquetía': 7350},
        'La Guaira': {'Marítimo': 7350, 'Puerto Cabello': 7400, 'Maiquetía': 7350},
        'Maiquetía': {'Marítimo': 7350, 'Puerto Cabello': 7400, 'La Guaira': 7350}
    }
}

class VentanaLogisticaModerna(FluentWindow):
    def __init__(self):
        super().__init__()
        
        # Configuración estética global
        setTheme(Theme.DARK)
        self.setWindowTitle("LogiIA - Sistema Inteligente de Gestión Logística [Acceso Público]")
        self.resize(1150, 820)
        
        # Control de Sesión
        self.usuario_actual = None
        self.rol_actual = None
        self.ultimo_html_dictamen = ""

        # Inicializar Modelos Predictivos
        try: self.modelo_eta, self.encoders = entrenar_modelo_eta()
        except Exception: self.modelo_eta, self.encoders = None, None

        self.ruta_csv = os.path.join(os.path.dirname(__file__), 'data', 'historico_envios.csv')
        self.df_historico = pd.read_csv(self.ruta_csv) if os.path.exists(self.ruta_csv) else None

        # Crear contenedores para las interfaces
        self.vista_dashboard = QFrame(self)
        self.vista_vuce = QFrame(self)
        self.vista_landed = QFrame(self)
        self.vista_sesion = QFrame(self)

        #Asignar nombres de objetos
        self.vista_dashboard.setObjectName("vista_dashboard")
        self.vista_vuce.setObjectName("vista_vuce")
        self.vista_landed.setObjectName("vista_landed")
        self.vista_sesion.setObjectName("vista_sesion")

        # Inicializar cada módulo visualmente
        self.inicializar_tab_dashboard()
        self.inicializar_tab_vuce()
        self.inicializar_tab_landed_cost()
        self.inicializar_tab_sesion()

        # Armar el menú lateral dinámico vinculando las vistas
        self.configurar_menu_lateral()
        self.actualizar_grafico()

    def configurar_menu_lateral(self):
        self.navigationInterface.setExpandWidth(200)
        
        # Módulos core con íconos Fluent nativos
        self.addSubInterface(self.vista_dashboard, FIF.APPLICATION, 'Predictor ETA')
        self.addSubInterface(self.vista_vuce, FIF.CHAT, 'Asesor VUCE')
        self.addSubInterface(self.vista_landed, FIF.SETTING, 'Landed Cost')
        
        # Sección de usuario abajo fija
        self.navigationInterface.addSeparator()
        self.addSubInterface(self.vista_sesion, FIF.PEOPLE, 'Cuenta / Acceso')

    # =================================================================
    # 🔮 MÓDULO 1: PREDICTOR ETA
    # =================================================================
    def inicializar_tab_dashboard(self):
        layout = QVBoxLayout(self.vista_dashboard)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        layout.addWidget(TitleLabel("Optimización del Tiempo Estimado de Arribo (ETA)"))
        
        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(20)
        
        # Formulario
        tarjeta_form = CardWidget(self.vista_dashboard)
        lay_f = QVBoxLayout(tarjeta_form)
        
        self.combo_origen = ComboBox()
        self.combo_origen.addItems(['Shanghái', 'Miami', 'Róterdam'])
        self.combo_origen.currentTextChanged.connect(self.actualizar_grafico)
        
        self.combo_via = ComboBox()
        self.combo_via.addItems(['Marítimo', 'Aéreo'])
        
        self.combo_aduana = ComboBox()
        self.combo_aduana.addItems(['Puerto Cabello', 'La Guaira', 'Maiquetía'])
        
        self.combo_naviera = ComboBox()
        self.combo_naviera.addItems(['Maersk', 'MSC', 'CMA CGM'])
        
        self.combo_carga = ComboBox()
        self.combo_carga.addItems(['Tecnología y Electrónica', 'Materia Prima Industrial', 'Textil y Calzado'])
        
        self.date_picker_envio = DatePicker()
        
        lay_f.addWidget(BodyLabel("<b>Origen Internacional:</b>")); lay_f.addWidget(self.combo_origen)
        lay_f.addWidget(BodyLabel("<b>Vía de Transporte:</b>")); lay_f.addWidget(self.combo_via)
        lay_f.addWidget(BodyLabel("<b>Aduana de Ingreso (Venezuela):</b>")); lay_f.addWidget(self.combo_aduana)
        lay_f.addWidget(BodyLabel("<b>Operador Logístico:</b>")); lay_f.addWidget(self.combo_naviera)
        lay_f.addWidget(BodyLabel("<b>Tipo de Mercancía:</b>")); lay_f.addWidget(self.combo_carga)
        lay_f.addWidget(BodyLabel("<b>Fecha Estimada de Envío:</b>")); lay_f.addWidget(self.date_picker_envio)
        
        self.btn_predecir = PrimaryPushButton("Calcular Predicción de ETA")
        self.btn_predecir.clicked.connect(self.ejecutar_prediccion_eta)
        lay_f.addWidget(self.btn_predecir)
        sub_layout.addWidget(tarjeta_form, 4)
        
        # Resultados y Gráfica
        lay_derecha = QVBoxLayout()
        self.tarjeta_resultado = CardWidget(self.vista_dashboard)
        lay_res = QVBoxLayout(self.tarjeta_resultado)
        self.lbl_resultado_eta = SubtitleLabel("Esperando parámetros operacionales...")
        lay_res.addWidget(self.lbl_resultado_eta)
        lay_derecha.addWidget(self.tarjeta_resultado, 3)
        
        tarjeta_g = CardWidget(self.vista_dashboard)
        lay_g = QVBoxLayout(tarjeta_g)
        self.figura = Figure(figsize=(5, 2.2), facecolor='#1e293b')
        self.canvas = FigureCanvas(self.figura); lay_g.addWidget(self.canvas)
        lay_derecha.addWidget(tarjeta_g, 5)
        
        sub_layout.addLayout(lay_derecha, 6)
        layout.addLayout(sub_layout)

    def ejecutar_prediccion_eta(self):
        if not self.modelo_eta: return
        try:
            origen = self.combo_origen.currentText()
            aduana = self.combo_aduana.currentText()
            via = self.combo_via.currentText()
            operador = self.combo_naviera.currentText()
            carga = self.combo_carga.currentText()
            
            # --- NUEVA LÓGICA REQUERIDA PARA EL BACKEND ---
            # Obtenemos el objeto QDate de Qt desde el date picker
            fecha_seleccionada = self.date_picker_envio.date
            
            # Extraemos el número del mes de manera automática (devuelve un int del 1 al 12)
            mes = fecha_seleccionada.month() 
            # -----------------------------------------------
            
            distancia = DISTANCIAS_LOGISTICAS.get(origen, {}).get(aduana, {}).get(via, 4000)
            
            orig_cod = self.encoders['origen'].transform([origen])[0]
            adua_cod = self.encoders['aduana_destino'].transform([aduana])[0]
            via_cod = self.encoders['via'].transform([via])[0]
            oper_cod = self.encoders['operador'].transform([operador])[0]
            carg_cod = self.encoders['tipo_carga'].transform([carga])[0]
            
            columnas = ['origen', 'aduana_destino', 'via', 'operador', 'tipo_carga', 'mes', 'distancia_km']
            datos_entrada = pd.DataFrame([[orig_cod, adua_cod, via_cod, oper_cod, carg_cod, mes, distancia]], columns=columnas)
            dias_totales = self.modelo_eta['total'].predict(datos_entrada)[0]
            
            if self.usuario_actual:
                guardar_en_historial(self.usuario_actual, "PREDICTOR_ETA", f"Ruta: {origen}➔{aduana} | ETA: {dias_totales:.1f} días")

            self.lbl_resultado_eta.setText(f"Predicción Calculada: {max(0.5, dias_totales):.1f} días totales.")
        except Exception as e: print(e)

    def actualizar_grafico(self):
        if self.df_historico is None: return
        try:
            df_filtrado = self.df_historico[(self.df_historico['origen'] == self.combo_origen.currentText())]
            if df_filtrado.empty: return
            reporte = df_filtrado.groupby('operador')['dias_reales'].mean().reset_index()
            self.figura.clear(); ax = self.figura.add_subplot(111); ax.set_facecolor('#1e293b')
            ax.bar(reporte['operador'], reporte['dias_reales'], color='#38bdf8', width=0.4)
            ax.tick_params(colors='#94a3b8', labelsize=8); self.canvas.draw()
        except Exception: pass

    # =================================================================
    # 💼 MÓDULO 2: ASESOR VUCE AI
    # =================================================================
    def inicializar_tab_vuce(self):
        layout = QVBoxLayout(self.vista_vuce)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        layout.addWidget(TitleLabel("Asesor Inteligente de Comercio Exterior (VUCE)"))
        
        tarjeta = CardWidget(self.vista_vuce)
        lay_f = QVBoxLayout(tarjeta)
        self.combo_regimen = ComboBox()
        self.combo_regimen.addItems(["IMPORTACIÓN", "EXPORTACIÓN"])
        self.txt_consulta_vuce = TextEdit()
        self.txt_consulta_vuce.setFixedHeight(60)
        
        lay_f.addWidget(BodyLabel("<b>Régimen Aduanero:</b>")); lay_f.addWidget(self.combo_regimen)
        lay_f.addWidget(BodyLabel("<b>Describa la mercancía o partida arancelaria:</b>")); lay_f.addWidget(self.txt_consulta_vuce)
        
        self.btn_consultar_vuce = PrimaryPushButton("Generar Dictamen Legal con IA")
        self.btn_consultar_vuce.clicked.connect(self.ejecutar_consulta_vuce_ai)
        lay_f.addWidget(self.btn_consultar_vuce)
        layout.addWidget(tarjeta)
        
        self.visor_reporte_vuce = TextBrowser()
        layout.addWidget(self.visor_reporte_vuce)
        
        self.btn_descargar_pdf = PushButton("Descargar Reporte Homologado en PDF")
        self.btn_descargar_pdf.setEnabled(False)
        self.btn_descargar_pdf.clicked.connect(self.ejecutar_descarga_pdf)
        layout.addWidget(self.btn_descargar_pdf)

    def ejecutar_consulta_vuce_ai(self):
        consulta = self.txt_consulta_vuce.toPlainText().strip()
        if not consulta: return
        self.btn_consultar_vuce.setEnabled(False)
        QApplication.processEvents()
        
        self.ultimo_html_dictamen = consultar_asesor_vuce(self.combo_regimen.currentText(), consulta)
        if self.usuario_actual:
            guardar_en_historial(self.usuario_actual, "ASESOR_VUCE", f"Modo: {self.combo_regimen.currentText()} | {consulta[:30]}")
            
        self.visor_reporte_vuce.setHtml(self.ultimo_html_dictamen)
        self.btn_consultar_vuce.setEnabled(True)
        self.btn_descargar_pdf.setEnabled(True)

    def ejecutar_descarga_pdf(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar Dictamen", "Dictamen_VUCE.pdf", "Archivos PDF (*.pdf)")
        if ruta:
            generar_pdf_dictamen(self.combo_regimen.currentText(), self.txt_consulta_vuce.toPlainText().strip(), self.ultimo_html_dictamen, ruta)

    # =================================================================
    # 💰 MÓDULO 3: LANDED COST
    # =================================================================
    def inicializar_tab_landed_cost(self):
        layout = QVBoxLayout(self.vista_landed)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        layout.addWidget(TitleLabel("Calculadora Financiera de Landed Cost"))
        sub_lay = QHBoxLayout()
        
        tarjeta_in = CardWidget(self.vista_landed)
        lay_i = QVBoxLayout(tarjeta_in)
        
        self.input_fob = DoubleSpinBox(); self.input_fob.setRange(0, 999999); self.input_fob.setValue(10000)
        self.input_flete = DoubleSpinBox(); self.input_flete.setRange(0, 99999); self.input_flete.setValue(1500)
        self.input_seguro = DoubleSpinBox(); self.input_seguro.setRange(0, 99999); self.input_seguro.setValue(300)
        self.input_arancel = DoubleSpinBox(); self.input_arancel.setValue(12)
        self.input_iva = DoubleSpinBox(); self.input_iva.setValue(16)
        
        lay_i.addWidget(BodyLabel("<b>Valor FOB Mercancía ($):</b>")); lay_i.addWidget(self.input_fob)
        lay_i.addWidget(BodyLabel("<b>Flete Internacional ($):</b>")); lay_i.addWidget(self.input_flete)
        lay_i.addWidget(BodyLabel("<b>Seguro Internacional ($):</b>")); lay_i.addWidget(self.input_seguro)
        lay_i.addWidget(BodyLabel("<b>Alícuota Arancel (%):</b>")); lay_i.addWidget(self.input_arancel)
        lay_i.addWidget(BodyLabel("<b>IVA Importación (%):</b>")); lay_i.addWidget(self.input_iva)
        
        self.btn_landed = PrimaryPushButton("Calcular Estructura Económica")
        self.btn_landed.clicked.connect(self.ejecutar_calculo_landed)
        lay_i.addWidget(self.btn_landed)
        sub_lay.addWidget(tarjeta_in, 4)
        
        self.visor_landed = TextBrowser()
        sub_lay.addWidget(self.visor_landed, 6)
        layout.addLayout(sub_lay)

    def ejecutar_calculo_landed(self):
        fob = self.input_fob.value()
        cif = fob + self.input_flete.value() + self.input_seguro.value()
        arancel = cif * (self.input_arancel.value() / 100.0)
        iva = (cif + arancel) * (self.input_iva.value() / 100.0)
        total = cif + arancel + iva
        
        if self.usuario_actual:
            guardar_en_historial(self.usuario_actual, "CALCULO_FINANCIERO", f"FOB: ${fob} | Total Landed: ${total:.2f}")
            
        html = f"<h3>Resumen Financiero</h3><b>Base CIF:</b> ${cif:,.2f}<br><b>Derechos Aduanales:</b> ${arancel:,.2f}<br><b>IVA:</b> ${iva:,.2f}<hr><h2>Total Puesto en Almacén: ${total:,.2f}</h2>"
        self.visor_landed.setHtml(html)

    # =================================================================
    # 🔐 MÓDULO 4: GESTIÓN DE SESIÓN (AUTENTICACIÓN / REGISTRO)
    # =================================================================
    def inicializar_tab_sesion(self):
        layout = QVBoxLayout(self.vista_sesion)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        self.lbl_estatus_usuario = TitleLabel("👤 Modo Invitado (Acceso Público Limitado)")
        layout.addWidget(self.lbl_estatus_usuario)
        
        layout_dos_columnas = QHBoxLayout()
        
        # Panel Login
        t_login = CardWidget(self.vista_sesion); lay_l = QVBoxLayout(t_login)
        lay_l.addWidget(SubtitleLabel("Ingresar al Sistema"))
        self.log_user = LineEdit()
        self.log_pass = LineEdit(); self.log_pass.setEchoMode(LineEdit.EchoMode.Password)
        lay_l.addWidget(BodyLabel("Usuario:")); lay_l.addWidget(self.log_user)
        lay_l.addWidget(BodyLabel("Contraseña:")); lay_l.addWidget(self.log_pass)
        self.btn_login = PrimaryPushButton("Iniciar Sesión")
        self.btn_login.clicked.connect(self.procesar_login)
        lay_l.addWidget(self.btn_login)
        layout_dos_columnas.addWidget(t_login)
        
        # Panel Registro
        t_reg = CardWidget(self.vista_sesion); lay_r = QVBoxLayout(t_reg)
        lay_r.addWidget(SubtitleLabel("Registrar Nuevo Operador VUCE"))
        self.reg_user = LineEdit()
        self.reg_pass = LineEdit(); self.reg_pass.setEchoMode(LineEdit.EchoMode.Password)
        self.reg_empresa = LineEdit()
        lay_r.addWidget(BodyLabel("Nombre de Usuario:")); lay_r.addWidget(self.reg_user)
        lay_r.addWidget(BodyLabel("Contraseña:")); lay_r.addWidget(self.reg_pass)
        lay_r.addWidget(BodyLabel("Empresa / Organización (Opcional):")); lay_r.addWidget(self.reg_empresa)
        self.btn_registrar = PushButton("Crear Cuenta")
        self.btn_registrar.clicked.connect(self.procesar_registro)
        lay_r.addWidget(self.btn_registrar)
        layout_dos_columnas.addWidget(t_reg)
        
        layout.addLayout(layout_dos_columnas)

    def procesar_login(self):
        user = self.log_user.text().strip()
        p_hash = self.log_pass.text().strip()
        exito, id_u, rol = verificar_usuario(user, p_hash)
        
        if exito:
            self.usuario_actual = user
            self.rol_actual = rol
            self.lbl_estatus_usuario.setText(f"👤 Conectado como: {self.usuario_actual} [{self.rol_actual}]")
            self.setWindowTitle(f"LogiIA - Operador Activo: [{self.usuario_actual}]")
            MessageBox("Autenticación", f"¡Bienvenido de nuevo, {user}! Actividades enlazadas al historial.", self).exec()
        else:
            MessageBox("Error", "Credenciales incorrectas.", self).exec()

    def procesar_registro(self):
        user = self.reg_user.text().strip()
        p_hash = self.reg_pass.text().strip()
        empresa = self.reg_empresa.text().strip()
        
        if len(user) < 4 or len(p_hash) < 4:
            MessageBox("Validación", "El usuario y clave deben tener más de 4 caracteres.", self).exec()
            return
            
        exito, msg = registrar_usuario(user, p_hash, rol="User")
        if exito:
            import sqlite3
            from src.database import DB_PATH
            conn = sqlite3.connect(DB_PATH)
            conn.execute("UPDATE usuarios SET empresa = ? WHERE username = ?", (empresa if empresa else None, user))
            conn.commit(); conn.close()
            MessageBox("Éxito", f"Operador '{user}' dado de alta exitosamente.", self).exec()
        else:
            MessageBox("Error", msg, self).exec()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try: inicializar_tablas()
    except Exception: pass
    w = VentanaLogisticaModerna()
    w.show()
    sys.exit(app.exec())