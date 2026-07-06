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

app = FastAPI(title="LogiIA Sidecar")                 # instancia principal de la API

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

@app.get("/health")                                   # endpoint de salud que consulta el splash de Electron
def health():                                         # devuelve el estado actual del motor de ML
    return {"estado": MOTOR["estado"]}                # 'entrenando' | 'listo' | 'error'

class LandedIn(BaseModel):                            # esquema del cuerpo JSON para /landed-cost
    fob: float                                        # valor FOB de la mercancia
    flete: float = 0                                  # flete internacional
    seguro: float = 0                                 # seguro internacional
    arancel: float = 0                                # alicuota de arancel (%)
    tasa: float = 0                                   # tasa aduanera de servicio (%)
    iva: float = 16                                   # IVA de importacion (%)
    gastos: float = 0                                 # gastos locales/portuarios

@app.post("/landed-cost")                             # endpoint de la calculadora financiera
def landed(datos: LandedIn):                          # recibe y valida el cuerpo con Pydantic
    from src.landed_cost import calcular_landed_cost  # import perezoso de la funcion del backend
    return calcular_landed_cost(                      # llama a la funcion existente y devuelve su dict tal cual
        datos.fob, datos.flete, datos.seguro,         # componentes CIF
        datos.arancel, datos.tasa, datos.iva,         # porcentajes de impuestos
        datos.gastos,                                 # gastos locales
    )
