# api_server.py
# Sidecar FastAPI: expone el backend Python existente (carpeta src/) como una API JSON local.
# Electron arranca este proceso; el front lo consume por HTTP en 127.0.0.1:8000.
# Regla: aqui NO hay logica de negocio nueva; cada endpoint solo llama a una funcion de src/.

import os                                             # variables de entorno y rutas
import threading                                      # para entrenar el modelo ETA sin bloquear el arranque
import pandas as pd                                   # lectura del CSV historico para KPIs y grafico

from fastapi import FastAPI, HTTPException            # framework web y utilidad para errores HTTP
from fastapi.middleware.cors import CORSMiddleware    # permitir que el renderer (origin file://) llame al API
from pydantic import BaseModel                        # validacion/tipado de los cuerpos JSON de entrada

# Ruta absoluta al CSV historico (mismo archivo que usa el backend). __file__ esta en la raiz del proyecto.
RUTA_CSV = os.path.join(os.path.dirname(__file__), "data", "historico_envios.csv")

app = FastAPI(title="Rumbo Sidecar")                  # instancia principal de la API

# CORS abierto en localhost: el renderer de Electron carga como file:// y necesita permiso para llamar.
app.add_middleware(
    CORSMiddleware,                                   # middleware de control de origen cruzado
    allow_origins=["*"],                             # permitir cualquier origen (solo escuchamos en 127.0.0.1)
    allow_methods=["*"],                             # permitir todos los metodos HTTP
    allow_headers=["*"],                             # permitir todas las cabeceras
)

# Estado global del "motor" de Machine Learning. Empieza 'entrenando' y pasa a 'listo' cuando el modelo termina.
MOTOR = {"estado": "entrenando", "modelos": None, "encoders": None}

def _entrenar_en_segundo_plano():                     # entrena el modelo ETA una sola vez y guarda el resultado
    from src.predict_eta import entrenar_modelo_eta   # import perezoso: carga sklearn solo cuando se entrena
    try:                                              # protege el arranque ante cualquier error de entrenamiento
        modelos, encoders = entrenar_modelo_eta()     # entrena los 4 sub-modelos y devuelve los encoders
        MOTOR["modelos"] = modelos                    # guarda los modelos entrenados en memoria
        MOTOR["encoders"] = encoders                  # guarda los codificadores de categorias
        MOTOR["estado"] = "listo"                     # marca el motor como listo para predecir
    except Exception as e:                            # si algo falla durante el entrenamiento
        MOTOR["estado"] = "error"                     # marca estado de error
        MOTOR["error"] = str(e)                       # guarda el mensaje para diagnostico

@app.on_event("startup")                              # se ejecuta una vez cuando arranca el servidor real
def _startup():                                       # inicializa DB y dispara el entrenamiento en segundo plano
    from src.database import inicializar_tablas       # import perezoso del backend de base de datos
    try:                                              # la creacion de tablas es idempotente pero la protegemos
        inicializar_tablas()                          # asegura que existan las tablas y datos semilla
    except Exception:                                 # si falla (ej. permisos), no impedir el arranque
        pass                                          # continuamos: el resto de endpoints puede seguir
    if os.getenv("LOGIIA_SKIP_TRAIN") != "1":         # en tests seteamos LOGIIA_SKIP_TRAIN=1 para no entrenar
        threading.Thread(target=_entrenar_en_segundo_plano, daemon=True).start()  # entrena en hilo aparte

class LoginIn(BaseModel):                             # cuerpo JSON de /login
    username: str                                     # nombre de usuario
    password: str                                     # contraseña en texto plano (se verifica con bcrypt)

class RegisterIn(BaseModel):                          # cuerpo JSON de /register
    username: str                                     # nombre de usuario deseado
    password: str                                     # contraseña deseada
    empresa: str | None = None                        # empresa/organizacion (opcional)

class LandedIn(BaseModel):                            # esquema del cuerpo JSON para /landed-cost
    fob: float                                        # valor FOB de la mercancia
    flete: float = 0                                  # flete internacional
    seguro: float = 0                                 # seguro internacional
    arancel: float = 0                                # alicuota de arancel (%)
    tasa: float = 0                                   # tasa aduanera de servicio (%)
    iva: float = 16                                   # IVA de importacion (%)
    gastos: float = 0                                 # gastos locales/portuarios
    usuario: str | None = None                        # usuario activo (opcional) para guardar en historial

@app.get("/health")                                   # endpoint de salud que consulta el splash de Electron
def health():                                         # devuelve el estado actual del motor de ML
    return {"estado": MOTOR["estado"]}                # 'entrenando' | 'listo' | 'error'

@app.post("/login")                                   # endpoint de autenticacion
def login(datos: LoginIn):                            # recibe usuario y clave
    from src.auth import verificar_usuario            # import perezoso (usa bcrypt)
    try:                                              # protege contra hashes mal formados (ej. semilla en texto plano)
        ok, id_u, rol = verificar_usuario(datos.username, datos.password)  # verifica contra la DB
    except Exception:                                 # bcrypt lanza si el hash almacenado no es valido
        ok, id_u, rol = False, None, None             # se trata como credencial invalida, NO como error 500
    return {"ok": ok, "id": id_u, "rol": rol}         # devuelve resultado y datos de sesion

@app.post("/register")                                # endpoint de registro de nuevos operadores
def register(datos: RegisterIn):                      # recibe usuario, clave y empresa
    from src.auth import registrar_usuario            # import perezoso
    from src.database import conectar_db              # para actualizar la empresa tras crear el usuario
    ok, msg = registrar_usuario(datos.username, datos.password, rol="User")  # crea el usuario (clave hasheada)
    if ok and datos.empresa:                          # si se creo y hay empresa, la guardamos
        try:                                          # si falla el guardado de empresa, el usuario ya fue creado; no romper el registro
            conn = conectar_db()                      # abre conexion a SQLite
            conn.execute(                             # actualiza el campo empresa del usuario recien creado
                "UPDATE usuarios SET empresa = ? WHERE username = ?",
                (datos.empresa, datos.username.strip().lower()),  # auth guarda el username en minusculas
            )
            conn.commit()                             # confirma el cambio
            conn.close()                              # cierra la conexion
        except Exception:                             # error transitorio de DB: no debe tumbar el registro exitoso
            pass
    return {"ok": ok, "msg": msg}                     # devuelve exito y mensaje

@app.post("/landed-cost")                             # endpoint de la calculadora financiera
def landed(datos: LandedIn):                          # recibe y valida el cuerpo con Pydantic
    from src.landed_cost import calcular_landed_cost  # import perezoso de la funcion del backend
    r = calcular_landed_cost(                         # llama a la funcion existente
        datos.fob, datos.flete, datos.seguro,         # componentes CIF
        datos.arancel, datos.tasa, datos.iva,         # porcentajes de impuestos
        datos.gastos,                                 # gastos locales
    )
    if datos.usuario:                                 # si hay sesion, guarda la operacion en el historial real
        try:
            from src.database import guardar_en_historial
            guardar_en_historial(datos.usuario, "CALCULO_FINANCIERO",
                                 f"FOB: ${datos.fob:,.0f} | Total: ${r['landed_cost']:,.2f}")
        except Exception:                             # historial best-effort; no romper el calculo
            pass
    return r                                           # devuelve el desglose completo

# Distancias (km) por VIA y ORIGEN, EXACTAMENTE como en el entrenamiento (src/generar_data_logistica.py).
# Antes la tabla solo tenia rutas maritimas de 3 origenes, por lo que toda prediccion "Aerea" (y los origenes
# Veracruz/Panama) caian a un valor fijo de 4000 km -> prediccion silenciosamente erronea. Ahora coincide con el modelo.
DISTANCIAS_LOGISTICAS = {
    "Marítimo": {"Shanghái": 15100, "Miami": 1980, "Róterdam": 7400, "Veracruz": 2600, "Panamá": 1050},
    "Aéreo":    {"Shanghái": 15900, "Miami": 2100, "Róterdam": 8050, "Veracruz": 3150, "Panamá": 1280},
}

class EtaIn(BaseModel):                               # cuerpo JSON de /predict-eta
    origen: str                                       # ciudad de origen internacional
    via: str                                          # via de transporte (Marítimo/Aéreo)
    aduana: str                                       # aduana de ingreso en Venezuela
    operador: str                                     # operador logistico / naviera / aerolinea
    carga: str                                        # tipo de mercancia
    mes: int                                          # mes estimado de envio (1-12)
    usuario: str | None = None                        # usuario activo (opcional) para guardar en historial

class VuceIn(BaseModel):                              # cuerpo JSON de /vuce
    regimen: str                                      # IMPORTACIÓN o EXPORTACIÓN
    consulta: str                                     # descripcion de la mercancia/consulta
    usuario: str | None = None                        # usuario activo (opcional) para guardar en historial

class VucePdfIn(BaseModel):                           # cuerpo JSON de /vuce-pdf
    regimen: str                                      # regimen aduanero
    consulta: str                                     # consulta original
    html: str                                         # dictamen HTML generado por /vuce
    ruta: str                                         # ruta de guardado (la elige Electron)

@app.post("/predict-eta")                             # endpoint de prediccion de ETA
def predict_eta(datos: EtaIn):                        # recibe los parametros de la ruta
    if MOTOR["estado"] != "listo":                    # si el modelo aun no termino de entrenar
        raise HTTPException(503, "El modelo ETA aun se esta entrenando. Intenta en unos segundos.")
    modelos = MOTOR["modelos"]                         # modelos entrenados (o falsos en test)
    encoders = MOTOR["encoders"]                       # codificadores de categorias
    # Distancia real segun via + origen (coincide con el entrenamiento); 4000 solo si llega algo inesperado.
    distancia = DISTANCIAS_LOGISTICAS.get(datos.via, {}).get(datos.origen, 4000)
    try:                                              # codificar las categorias con los encoders del modelo
        oc = encoders["origen"].transform([datos.origen])[0]            # codigo del origen
        ac = encoders["aduana_destino"].transform([datos.aduana])[0]    # codigo de la aduana
        vc = encoders["via"].transform([datos.via])[0]                  # codigo de la via
        pc = encoders["operador"].transform([datos.operador])[0]        # codigo del operador
        cc = encoders["tipo_carga"].transform([datos.carga])[0]         # codigo del tipo de carga
    except Exception:                                 # si alguna categoria no fue vista durante el entrenamiento
        raise HTTPException(400, "Alguna opcion seleccionada no existe en los datos historicos del modelo.")
    cols = ["origen", "aduana_destino", "via", "operador", "tipo_carga", "mes", "distancia_km"]  # orden esperado
    X = pd.DataFrame([[oc, ac, vc, pc, cc, datos.mes, distancia]], columns=cols)  # fila de entrada para el modelo
    resultado = {                                     # desglose completo (los 4 sub-modelos que app.py no usaba)
        "dias_total": float(modelos["total"].predict(X)[0]),      # dias totales estimados
        "dias_transito": float(modelos["transito"].predict(X)[0]),# dias de transito maritimo/aereo
        "dias_fondeo": float(modelos["fondeo"].predict(X)[0]),    # dias de espera/fondeo en puerto
        "dias_aduana": float(modelos["aduana"].predict(X)[0]),    # dias de nacionalizacion en aduana
        "distancia_km": distancia,                                # distancia usada en el calculo
    }
    if datos.usuario:                                 # si hay sesion iniciada, guarda la operacion en el historial real
        try:
            from src.database import guardar_en_historial   # import perezoso del backend
            guardar_en_historial(datos.usuario, "PREDICTOR_ETA",
                                 f"Ruta: {datos.origen} -> {datos.aduana} | ETA: {resultado['dias_total']:.1f} dias")
        except Exception:                             # el historial es best-effort; nunca romper la prediccion
            pass
    return resultado                                  # devuelve el desglose

@app.get("/eta-historico")                            # datos para el grafico de barras por operador
def eta_historico(origen: str):                       # recibe el origen por query string
    df = pd.read_csv(RUTA_CSV)                         # carga el historico completo
    filtrado = df[df["origen"] == origen]             # filtra por el origen seleccionado
    if filtrado.empty:                                # si no hay filas para ese origen
        return []                                     # devuelve lista vacia
    rep = filtrado.groupby("operador")["dias_reales"].mean().reset_index()  # promedio de dias por operador
    return [{"operador": str(r["operador"]), "dias_promedio": float(r["dias_reales"])}  # serializa cada fila
            for _, r in rep.iterrows()]

@app.post("/vuce")                                    # endpoint del asesor legal VUCE
def vuce(datos: VuceIn):                              # recibe regimen y consulta
    try:                                              # import perezoso: sentence-transformers/faiss pueden faltar
        from src.vuce_ai import consultar_asesor_vuce # cargar el asesor solo al usarlo
    except Exception as e:                            # si las dependencias pesadas no estan instaladas
        raise HTTPException(503, f"Modulo VUCE no disponible: {e}. Instala sentence-transformers y faiss-cpu.")  # error 503
    html = consultar_asesor_vuce(datos.regimen, datos.consulta)  # genera el dictamen HTML
    if datos.usuario:                                 # si hay sesion, guarda la consulta en el historial real
        try:
            from src.database import guardar_en_historial
            guardar_en_historial(datos.usuario, "ASESOR_VUCE", f"{datos.regimen} | {datos.consulta[:40]}")
        except Exception:                             # historial best-effort; no romper la consulta
            pass
    return {"html": html}                             # lo devuelve al front para mostrarlo

@app.post("/vuce-pdf")                                # endpoint que exporta el dictamen a PDF
def vuce_pdf(datos: VucePdfIn):                       # recibe el dictamen y la ruta destino
    # La ruta la elige el usuario en el dialogo nativo (proceso confiable). Aun asi, validamos que sea un .pdf
    # como defensa en profundidad (evita usar el endpoint para escribir archivos con otra extension).
    if not datos.ruta.lower().endswith(".pdf"):       # solo permitimos escribir archivos PDF
        raise HTTPException(400, "La ruta de guardado debe terminar en .pdf")
    from src.vuce_pdf import generar_pdf_dictamen     # import perezoso (reportlab)
    generar_pdf_dictamen(datos.regimen, datos.consulta, datos.html, datos.ruta)  # escribe el PDF en disco
    return {"ok": True, "ruta": datos.ruta}           # confirma la ruta guardada

@app.get("/dashboard-summary")                        # KPIs agregados REALES para la pantalla de Inicio
def dashboard_summary():                              # todos los indicadores salen del historico real (CSV)
    resumen = {}                                      # acumulador de resultados
    try:                                              # el CSV podria faltar o venir vacio
        df = pd.read_csv(RUTA_CSV)                     # carga el historico completo (miles de envios reales)
    except Exception:                                 # archivo ausente o ilegible
        df = None
    if df is None or df.empty:                        # sin datos: devolvemos un resumen en cero (no un 500)
        return {"registros_historicos": 0, "eta_promedio": 0, "dias_transito_promedio": 0,
                "dias_aduana_promedio": 0, "pct_a_tiempo": 0, "por_aduana": [], "por_via": [],
                "operador_mas_rapido": "—", "top_carga": "—",
                "por_mes": [{"mes": m, "envios": 0} for m in range(1, 13)]}
    resumen["registros_historicos"] = int(len(df))    # total de envios historicos analizados
    prom = float(df["dias_reales"].mean())            # promedio general de dias reales de trayecto
    resumen["eta_promedio"] = round(prom, 1)          # ETA promedio (dias)
    resumen["dias_transito_promedio"] = round(float(df["dias_transito_int"].mean()), 1)      # transito promedio
    resumen["dias_aduana_promedio"] = round(float(df["dias_nacionalizacion"].mean()), 1)     # aduana promedio
    # Puntualidad real: % de envios cuyo tiempo real quedo dentro (<=) del ETA promedio.
    resumen["pct_a_tiempo"] = round(float((df["dias_reales"] <= prom).mean() * 100), 1)
    conteo_aduana = df["aduana_destino"].value_counts()  # cuantos envios por cada aduana (real)
    resumen["por_aduana"] = [{"aduana": str(k), "envios": int(v)}  # serializa la distribucion por aduana
                             for k, v in conteo_aduana.items()]
    conteo_via = df["via"].value_counts()             # cuantos envios por cada via de transporte (real)
    resumen["por_via"] = [{"via": str(k), "envios": int(v)}  # serializa la distribucion por via
                          for k, v in conteo_via.items()]
    promedio_operador = df.groupby("operador")["dias_reales"].mean().sort_values()  # operadores por rapidez
    resumen["operador_mas_rapido"] = str(promedio_operador.index[0])  # el de menor promedio de dias (real)
    resumen["top_carga"] = str(df["tipo_carga"].value_counts().index[0])  # tipo de carga mas frecuente (real)
    # Volumen de envios por mes (1-12), rellenando con 0 los meses sin registros. Alimenta el grafico del HERO.
    conteo_mes = df["mes"].value_counts()             # cuantos envios por numero de mes
    resumen["por_mes"] = [{"mes": m, "envios": int(conteo_mes.get(m, 0))}  # lista ordenada de enero (1) a diciembre (12)
                          for m in range(1, 13)]
    return resumen                                    # devuelve el resumen completo con datos reales
