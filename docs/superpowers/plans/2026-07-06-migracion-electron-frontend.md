# Migración del front-end a Electron (LogiIA) — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el front-end PySide6 por una app Electron con estética de dashboard moderno y motion graphics, consumiendo el backend Python actual (intacto) a través de un sidecar FastAPI.

**Architecture:** Un sidecar FastAPI (`api_server.py`) importa las funciones de `src/` sin modificarlas y las expone como JSON en `127.0.0.1:8000`. Electron arranca ese proceso Python al abrir, muestra un splash mientras el modelo ETA entrena, y el renderer (HTML/CSS/JS puro) consume los endpoints por `fetch`. Al cerrar, Electron mata el proceso hijo.

**Tech Stack:** Python 3.13 + FastAPI + Uvicorn (sidecar); Electron 31+ (Node 22, npm 11); HTML/CSS/JS puro (sin build); Canvas 2D + CSS animations para motion; pytest + FastAPI TestClient para el sidecar.

## Global Constraints

- **NO modificar** `src/` ni `data/`. El backend y la base de datos quedan intactos. `app.py` (Qt) se conserva.
- **Comentar cada línea** del código nuevo, en español, explicando qué hace (requisito del usuario).
- **Motion:** movimiento continuo (fondo vivo, count-up, gauges, micro-interacciones). PROHIBIDO: animaciones de aparición tipo popup o zoom in/out. Transición entre vistas = fade sutil ≤ 200 ms.
- **Accesibilidad:** todo el motion se reduce/desactiva bajo `@media (prefers-reduced-motion: reduce)`.
- **Seguridad Electron:** `contextIsolation: true`, `nodeIntegration: false`, sidecar escuchando SOLO en `127.0.0.1`.
- **Paleta (tokens CSS, valores exactos):** `--bg-0:#161311` · `--bg-1:#1E1A17` · `--bg-2:#26211D` · `--sidebar:#100E0C` · `--ambar:#F4C77B` · `--durazno:#F3A87C` · `--terracota:#E68A6C` · `--teal:#84D2C5` · `--petroleo:#5FB3AE` · `--salvia:#AEC99C` · `--tinta:#F5EEE4` · `--tinta-suave:#B9AC9B` · `--linea:#3A332D`. Radios: `--r-card:22px` · `--r-pill:999px`.
- **Puerto del sidecar:** `8000` (fijo en este plan).
- **Plataforma:** Windows 11. Al cerrar la app, matar el árbol de procesos con `taskkill /f /t`.
- **Columnas del CSV** (`data/historico_envios.csv`): `origen, aduana_destino, via, operador, tipo_carga, mes, distancia_km, dias_transito_int, dias_fondeo, dias_nacionalizacion, dias_reales`.
- **Dependencias faltantes confirmadas:** `fastapi`, `uvicorn`, `bcrypt` deben instalarse. `sentence-transformers`+`faiss-cpu` (que usa `vuce_ai.py`) son pesadas → el sidecar las importa de forma **perezosa** para arrancar aunque no estén; el Asesor VUCE avisa si faltan.

---

## Estructura de archivos (mapa de responsabilidades)

```
Logistica aduanera/
├─ api_server.py ............ NUEVO. Sidecar FastAPI. Solo enruta a src/. (Fase 1)
├─ requirements.txt ......... MODIFICAR: +fastapi +uvicorn[standard] +bcrypt (+opcionales VUCE)
├─ tests/
│  └─ test_api_server.py .... NUEVO. Tests pytest del sidecar. (Fase 1)
├─ .gitignore .............. NUEVO. Ignora node_modules, __pycache__, etc.
└─ frontend/ ............... NUEVO. App Electron.
   ├─ package.json ......... deps (electron) + script "start"
   ├─ main.js ............. proceso principal: lanza/mata sidecar, crea ventana, IPC guardar-PDF
   ├─ preload.js .......... contextBridge: expone elegirRutaPdf()
   └─ renderer/
      ├─ index.html ....... esqueleto: canvas de fondo, splash, sidebar, contenedor de vistas, toasts
      ├─ styles.css ....... tokens de color, layout, tarjetas glass, controles, motion (keyframes)
      ├─ assets/
      │  └─ Manrope.woff2 .. fuente empaquetada local
      └─ js/
         ├─ api.js ........ todas las llamadas fetch al sidecar
         ├─ estado.js ..... sesión en memoria (usuario, rol)
         ├─ router.js ..... registra y conmuta vistas con fade
         ├─ motion.js ..... fondo vivo (canvas), animarNumero, animarGauge, dibujarLinea, mostrarToast
         ├─ app.js ........ arranque: fondo vivo + polling /health (splash) + sidebar + router
         └─ vistas/
            ├─ inicio.js .. dashboard estilo foto (hero + rutas + 3 tarjetas)
            ├─ eta.js ..... módulo Predictor ETA
            ├─ landed.js .. módulo Landed Cost
            ├─ vuce.js .... módulo Asesor VUCE + descarga PDF
            └─ sesion.js .. login / registro
```

---

## FASE 0 — Preparación

### Task 1: Inicializar toolchain, git y dependencias

**Files:**
- Create: `.gitignore`
- Modify: `requirements.txt`
- Create: `frontend/package.json`
- Create: carpetas `tests/`, `frontend/renderer/js/vistas/`, `frontend/renderer/assets/`

- [ ] **Step 1: Inicializar git** (el directorio aún no es repo)

Run desde la raíz del proyecto (`Logistica aduanera/`):
```bash
git init
git config core.autocrlf true
```
Expected: `Initialized empty Git repository`.

- [ ] **Step 2: Crear `.gitignore`**

```gitignore
# Dependencias de Node (Electron) — nunca se versionan
node_modules/
# Cachés de Python
__pycache__/
*.pyc
# Entornos virtuales
.venv/
venv/
# Artefactos varios
*.log
```

- [ ] **Step 3: Añadir dependencias del sidecar a `requirements.txt`** (agregar al final, sin quitar nada)

```txt
# --- Nuevas dependencias del sidecar Electron (front nuevo) ---
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
bcrypt>=4.0.0
# Opcionales: solo necesarias para el Asesor VUCE (RAG legal). El sidecar arranca sin ellas.
sentence-transformers>=2.2.0
faiss-cpu>=1.7.4
```

- [ ] **Step 4: Instalar dependencias Python obligatorias**

Run:
```bash
python -m pip install "fastapi>=0.110.0" "uvicorn[standard]>=0.29.0" "bcrypt>=4.0.0" pytest httpx
python -m pip install -r requirements.txt
```
Expected: instala sin error `fastapi`, `uvicorn`, `bcrypt`, `pytest`, `httpx`. (Si `sentence-transformers`/`faiss-cpu` fallan o tardan, no bloquea: son opcionales.)

- [ ] **Step 5: Crear carpetas del proyecto**

```bash
mkdir -p tests frontend/renderer/js/vistas frontend/renderer/assets
```

- [ ] **Step 6: Crear `frontend/package.json`**

```json
{
  "name": "logiia-frontend",
  "version": "1.0.0",
  "description": "Front-end Electron de LogiIA (dashboard logistico aduanero)",
  "main": "main.js",
  "scripts": {
    "start": "electron ."
  },
  "devDependencies": {
    "electron": "^31.0.0"
  }
}
```

- [ ] **Step 7: Instalar Electron**

Run desde `frontend/`:
```bash
npm install
```
Expected: crea `frontend/node_modules/` con Electron 31.

- [ ] **Step 8: Descargar la fuente Manrope**

Descargar `Manrope-Variable.woff2` (SIL Open Font License) y guardarla como `frontend/renderer/assets/Manrope.woff2`. Si no hay acceso a internet, usar como respaldo el stack del sistema (el CSS ya lo contempla con `font-family` de reserva). No bloquea el resto del plan.

- [ ] **Step 9: Commit**

```bash
git add .gitignore requirements.txt frontend/package.json frontend/package-lock.json
git commit -m "chore: inicializa toolchain, git y dependencias del sidecar/Electron"
```

---

## FASE 1 — Sidecar FastAPI (TDD)

> Todos los tests se corren desde la **raíz del proyecto** para que `import api_server` y `from src...` resuelvan. El `TestClient` a nivel de módulo no dispara el evento `startup`, así que los tests NO entrenan el modelo real (rápido).

### Task 2: Esqueleto del sidecar + `/health`

**Files:**
- Create: `api_server.py`
- Create: `tests/test_api_server.py`

**Interfaces:**
- Produces: `app` (instancia FastAPI); estado global `MOTOR = {"estado": str, "modelos": dict|None, "encoders": dict|None}`; endpoint `GET /health -> {"estado": "entrenando"|"listo"|"error"}`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_api_server.py
import os                                             # para setear variables de entorno antes de importar
os.environ["LOGIIA_SKIP_TRAIN"] = "1"                 # evita que el startup entrene el modelo real en tests
from fastapi.testclient import TestClient             # cliente de pruebas de FastAPI
import api_server                                     # importa el modulo del sidecar (raiz del proyecto)
from api_server import app                            # la instancia FastAPI a probar

client = TestClient(app)                              # cliente HTTP simulado sobre la app

def test_health_devuelve_estado():                    # verifica que /health responde con un estado
    r = client.get("/health")                         # llamada GET a /health
    assert r.status_code == 200                       # debe responder 200 OK
    assert "estado" in r.json()                       # el JSON debe incluir la clave 'estado'
```

- [ ] **Step 2: Correr el test (debe fallar)**

Run: `python -m pytest tests/test_api_server.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api_server'`.

- [ ] **Step 3: Crear `api_server.py` (esqueleto + /health)**

```python
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
```

- [ ] **Step 4: Correr el test (debe pasar)**

Run: `python -m pytest tests/test_api_server.py -v`
Expected: PASS `test_health_devuelve_estado`.

- [ ] **Step 5: Commit**

```bash
git add api_server.py tests/test_api_server.py
git commit -m "feat(sidecar): esqueleto FastAPI + endpoint /health"
```

---

### Task 3: `/landed-cost`

**Files:**
- Modify: `api_server.py`
- Modify: `tests/test_api_server.py`

**Interfaces:**
- Produces: `POST /landed-cost` con cuerpo `{fob, flete, seguro, arancel, tasa, iva, gastos}` → dict de `calcular_landed_cost` (`cif, arancel, tasa_aduana, iva, total_impuestos, landed_cost, factor, incremento_pct`).

- [ ] **Step 1: Escribir el test que falla** (añadir al final de `tests/test_api_server.py`)

```python
def test_landed_cost_calcula_cif_y_total():           # valida la matematica del landed cost real del backend
    r = client.post("/landed-cost", json={            # envia los parametros financieros
        "fob": 10000, "flete": 1500, "seguro": 300,   # base FOB + flete + seguro
        "arancel": 12, "tasa": 1, "iva": 16, "gastos": 0,  # porcentajes de impuestos y gastos locales
    })
    d = r.json()                                       # respuesta con el desglose
    assert round(d["cif"], 2) == 11800.0               # CIF = 10000 + 1500 + 300
    assert d["landed_cost"] > d["cif"]                 # el total debe superar al CIF (por impuestos)
```

- [ ] **Step 2: Correr (debe fallar)**

Run: `python -m pytest tests/test_api_server.py::test_landed_cost_calcula_cif_y_total -v`
Expected: FAIL — 404 Not Found (endpoint inexistente).

- [ ] **Step 3: Implementar el endpoint** (añadir a `api_server.py`)

```python
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
```

- [ ] **Step 4: Correr (debe pasar)**

Run: `python -m pytest tests/test_api_server.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add api_server.py tests/test_api_server.py
git commit -m "feat(sidecar): endpoint /landed-cost"
```

---

### Task 4: `/login` y `/register`

**Files:**
- Modify: `api_server.py`
- Modify: `tests/test_api_server.py`

**Interfaces:**
- Produces: `POST /login {username,password}` → `{ok, id, rol}`; `POST /register {username,password,empresa?}` → `{ok, msg}`.

- [ ] **Step 1: Test que falla** (añadir a `tests/test_api_server.py`)

```python
def test_login_credenciales_malas_devuelve_ok_false():  # login con credenciales inexistentes
    r = client.post("/login", json={"username": "nadie_zzz", "password": "malaclave"})  # usuario que no existe
    assert r.json()["ok"] is False                       # debe rechazar el acceso
```

- [ ] **Step 2: Correr (debe fallar)**

Run: `python -m pytest tests/test_api_server.py::test_login_credenciales_malas_devuelve_ok_false -v`
Expected: FAIL — 404.

- [ ] **Step 3: Implementar** (añadir a `api_server.py`)

```python
class LoginIn(BaseModel):                             # cuerpo JSON de /login
    username: str                                     # nombre de usuario
    password: str                                     # contraseña en texto plano (se verifica con bcrypt)

class RegisterIn(BaseModel):                          # cuerpo JSON de /register
    username: str                                     # nombre de usuario deseado
    password: str                                     # contraseña deseada
    empresa: str | None = None                        # empresa/organizacion (opcional)

@app.post("/login")                                   # endpoint de autenticacion
def login(datos: LoginIn):                            # recibe usuario y clave
    from src.auth import verificar_usuario            # import perezoso (usa bcrypt)
    ok, id_u, rol = verificar_usuario(datos.username, datos.password)  # verifica contra la DB
    return {"ok": ok, "id": id_u, "rol": rol}         # devuelve resultado y datos de sesion

@app.post("/register")                                # endpoint de registro de nuevos operadores
def register(datos: RegisterIn):                      # recibe usuario, clave y empresa
    from src.auth import registrar_usuario            # import perezoso
    from src.database import conectar_db              # para actualizar la empresa tras crear el usuario
    ok, msg = registrar_usuario(datos.username, datos.password, rol="User")  # crea el usuario (clave hasheada)
    if ok and datos.empresa:                          # si se creo y hay empresa, la guardamos
        conn = conectar_db()                          # abre conexion a SQLite
        conn.execute(                                 # actualiza el campo empresa del usuario recien creado
            "UPDATE usuarios SET empresa = ? WHERE username = ?",
            (datos.empresa, datos.username.strip().lower()),  # auth guarda el username en minusculas
        )
        conn.commit()                                 # confirma el cambio
        conn.close()                                  # cierra la conexion
    return {"ok": ok, "msg": msg}                     # devuelve exito y mensaje
```

- [ ] **Step 4: Correr (debe pasar)**

Run: `python -m pytest tests/test_api_server.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add api_server.py tests/test_api_server.py
git commit -m "feat(sidecar): endpoints /login y /register"
```

---

### Task 5: `/predict-eta` y `/eta-historico`

**Files:**
- Modify: `api_server.py`
- Modify: `tests/test_api_server.py`

**Interfaces:**
- Produces: `POST /predict-eta {origen,via,aduana,operador,carga,mes}` → `{dias_total,dias_transito,dias_fondeo,dias_aduana,distancia_km}`; `GET /eta-historico?origen=` → `[{operador,dias_promedio}]`.

- [ ] **Step 1: Test que falla** (añadir a `tests/test_api_server.py`) — usa un modelo/encoder falso para no entrenar

```python
def test_predict_eta_con_modelo_stub():               # prueba la estructura de la prediccion sin entrenar de verdad
    class ModeloFalso:                                # modelo simulado que siempre predice 10 dias
        def predict(self, X):                         # imita la interfaz .predict de sklearn
            return [10.0]                             # devuelve una lista con un valor
    class EncoderFalso:                               # encoder simulado que siempre devuelve 0
        def transform(self, v):                       # imita LabelEncoder.transform
            return [0]                                # codigo ficticio
    api_server.MOTOR["estado"] = "listo"              # marcamos el motor como listo
    api_server.MOTOR["modelos"] = {k: ModeloFalso() for k in ["total", "transito", "fondeo", "aduana"]}  # 4 modelos
    api_server.MOTOR["encoders"] = {k: EncoderFalso() for k in            # 5 encoders esperados
        ["origen", "aduana_destino", "via", "operador", "tipo_carga"]}
    r = client.post("/predict-eta", json={            # peticion de prediccion
        "origen": "Miami", "via": "Maritimo", "aduana": "La Guaira",
        "operador": "Maersk", "carga": "Textil y Calzado", "mes": 6,
    })
    d = r.json()                                       # respuesta con el desglose
    assert d["dias_total"] == 10.0                     # el modelo falso predice 10
    assert {"dias_total", "dias_transito", "dias_fondeo", "dias_aduana", "distancia_km"} <= set(d.keys())  # claves

def test_eta_historico_devuelve_lista():              # el grafico historico debe devolver una lista por operador
    r = client.get("/eta-historico", params={"origen": "Miami"})  # agregado para origen Miami
    assert r.status_code == 200                        # 200 OK
    assert isinstance(r.json(), list)                  # debe ser una lista (posiblemente vacia)
```

- [ ] **Step 2: Correr (debe fallar)**

Run: `python -m pytest tests/test_api_server.py -k "predict_eta_con_modelo_stub or eta_historico" -v`
Expected: FAIL — 404.

- [ ] **Step 3: Implementar** (añadir a `api_server.py`)

```python
# Distancias logisticas (copiadas de app.py para reproducir la misma logica de ETA sin tocar el backend).
DISTANCIAS_LOGISTICAS = {
    "Shanghái": {"Puerto Cabello": {"Marítimo": 15100, "La Guaira": 15150, "Maiquetía": 15150},
                 "La Guaira": {"Marítimo": 15150, "Puerto Cabello": 15100, "Maiquetía": 15150},
                 "Maiquetía": {"Marítimo": 15150, "Puerto Cabello": 15100, "La Guaira": 15150}},
    "Miami": {"Puerto Cabello": {"Marítimo": 1980, "La Guaira": 2050, "Maiquetía": 2050},
              "La Guaira": {"Marítimo": 2050, "Puerto Cabello": 1980, "Maiquetía": 2050},
              "Maiquetía": {"Marítimo": 2050, "Puerto Cabello": 1980, "La Guaira": 2050}},
    "Róterdam": {"Puerto Cabello": {"Marítimo": 7400, "La Guaira": 7350, "Maiquetía": 7350},
                 "La Guaira": {"Marítimo": 7350, "Puerto Cabello": 7400, "Maiquetía": 7350},
                 "Maiquetía": {"Marítimo": 7350, "Puerto Cabello": 7400, "La Guaira": 7350}},
}

class EtaIn(BaseModel):                               # cuerpo JSON de /predict-eta
    origen: str                                       # ciudad de origen internacional
    via: str                                          # via de transporte (Maritimo/Aereo)
    aduana: str                                       # aduana de ingreso en Venezuela
    operador: str                                     # operador logistico / naviera
    carga: str                                        # tipo de mercancia
    mes: int                                          # mes estimado de envio (1-12)

@app.post("/predict-eta")                             # endpoint de prediccion de ETA
def predict_eta(datos: EtaIn):                        # recibe los parametros de la ruta
    if MOTOR["estado"] != "listo":                    # si el modelo aun no termino de entrenar
        raise HTTPException(503, "El modelo ETA aun se esta entrenando. Intenta en unos segundos.")
    modelos = MOTOR["modelos"]                         # modelos entrenados (o falsos en test)
    encoders = MOTOR["encoders"]                       # codificadores de categorias
    # Distancia segun tabla; si la combinacion no existe (ej. Aereo), usa 4000 km por defecto (igual que app.py).
    distancia = DISTANCIAS_LOGISTICAS.get(datos.origen, {}).get(datos.aduana, {}).get(datos.via, 4000)
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
    return {                                          # desglose completo (los 4 sub-modelos que app.py no usaba)
        "dias_total": float(modelos["total"].predict(X)[0]),      # dias totales estimados
        "dias_transito": float(modelos["transito"].predict(X)[0]),# dias de transito maritimo/aereo
        "dias_fondeo": float(modelos["fondeo"].predict(X)[0]),    # dias de espera/fondeo en puerto
        "dias_aduana": float(modelos["aduana"].predict(X)[0]),    # dias de nacionalizacion en aduana
        "distancia_km": distancia,                                # distancia usada en el calculo
    }

@app.get("/eta-historico")                            # datos para el grafico de barras por operador
def eta_historico(origen: str):                       # recibe el origen por query string
    df = pd.read_csv(RUTA_CSV)                         # carga el historico completo
    filtrado = df[df["origen"] == origen]             # filtra por el origen seleccionado
    if filtrado.empty:                                # si no hay filas para ese origen
        return []                                     # devuelve lista vacia
    rep = filtrado.groupby("operador")["dias_reales"].mean().reset_index()  # promedio de dias por operador
    return [{"operador": str(r["operador"]), "dias_promedio": float(r["dias_reales"])}  # serializa cada fila
            for _, r in rep.iterrows()]
```

- [ ] **Step 4: Correr (debe pasar)**

Run: `python -m pytest tests/test_api_server.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add api_server.py tests/test_api_server.py
git commit -m "feat(sidecar): endpoints /predict-eta (desglose completo) y /eta-historico"
```

---

### Task 6: `/vuce` y `/vuce-pdf` (import perezoso, degradacion elegante)

**Files:**
- Modify: `api_server.py`
- Modify: `tests/test_api_server.py`

**Interfaces:**
- Produces: `POST /vuce {regimen,consulta}` → `{html}` (o error 503 si faltan deps); `POST /vuce-pdf {regimen,consulta,html,ruta}` → `{ok,ruta}`.

- [ ] **Step 1: Test que falla** (añadir a `tests/test_api_server.py`) — no depende de las libs pesadas

```python
def test_vuce_pdf_genera_archivo(tmp_path):           # verifica que /vuce-pdf escribe un PDF en la ruta dada
    destino = str(tmp_path / "dictamen_test.pdf")     # ruta temporal de salida
    r = client.post("/vuce-pdf", json={               # peticion con un HTML minimo
        "regimen": "IMPORTACIÓN", "consulta": "cafe en grano",
        "html": "<h3>Guia</h3><ul><li>Paso 1</li></ul>", "ruta": destino,
    })
    assert r.json()["ok"] is True                      # debe reportar exito
    assert os.path.exists(destino)                     # el archivo PDF debe existir en disco
```

- [ ] **Step 2: Correr (debe fallar)**

Run: `python -m pytest tests/test_api_server.py::test_vuce_pdf_genera_archivo -v`
Expected: FAIL — 404.

- [ ] **Step 3: Implementar** (añadir a `api_server.py`)

```python
class VuceIn(BaseModel):                              # cuerpo JSON de /vuce
    regimen: str                                      # IMPORTACIÓN o EXPORTACIÓN
    consulta: str                                     # descripcion de la mercancia/consulta

class VucePdfIn(BaseModel):                           # cuerpo JSON de /vuce-pdf
    regimen: str                                      # regimen aduanero
    consulta: str                                     # consulta original
    html: str                                         # dictamen HTML generado por /vuce
    ruta: str                                         # ruta de guardado (la elige Electron)

@app.post("/vuce")                                    # endpoint del asesor legal VUCE
def vuce(datos: VuceIn):                              # recibe regimen y consulta
    try:                                              # import perezoso: sentence-transformers/faiss pueden faltar
        from src.vuce_ai import consultar_asesor_vuce # cargar el asesor solo al usarlo
    except Exception as e:                            # si las dependencias pesadas no estan instaladas
        raise HTTPException(503, f"Modulo VUCE no disponible: {e}. Instala sentence-transformers y faiss-cpu.")
    html = consultar_asesor_vuce(datos.regimen, datos.consulta)  # genera el dictamen HTML
    return {"html": html}                             # lo devuelve al front para mostrarlo

@app.post("/vuce-pdf")                                # endpoint que exporta el dictamen a PDF
def vuce_pdf(datos: VucePdfIn):                       # recibe el dictamen y la ruta destino
    from src.vuce_pdf import generar_pdf_dictamen     # import perezoso (reportlab)
    generar_pdf_dictamen(datos.regimen, datos.consulta, datos.html, datos.ruta)  # escribe el PDF en disco
    return {"ok": True, "ruta": datos.ruta}           # confirma la ruta guardada
```

- [ ] **Step 4: Correr (debe pasar)**

Run: `python -m pytest tests/test_api_server.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add api_server.py tests/test_api_server.py
git commit -m "feat(sidecar): endpoints /vuce y /vuce-pdf con import perezoso"
```

---

### Task 7: `/dashboard-summary`

**Files:**
- Modify: `api_server.py`
- Modify: `tests/test_api_server.py`

**Interfaces:**
- Produces: `GET /dashboard-summary` → `{registros_historicos, eta_promedio, por_aduana:[{aduana,envios}], operador_mas_rapido, estados:{"En Tránsito","Aduana","Entregado","Demorado"}}`.

- [ ] **Step 1: Test que falla** (añadir a `tests/test_api_server.py`)

```python
def test_dashboard_summary_tiene_kpis():              # el resumen del Inicio debe traer KPIs del historico
    r = client.get("/dashboard-summary")              # peticion del resumen
    d = r.json()                                       # respuesta agregada
    assert d["registros_historicos"] > 0               # el CSV tiene datos historicos
    assert "eta_promedio" in d                          # promedio general de dias reales
    assert isinstance(d["por_aduana"], list)            # distribucion por aduana
    assert "estados" in d                               # conteos por estado de embarque
```

- [ ] **Step 2: Correr (debe fallar)**

Run: `python -m pytest tests/test_api_server.py::test_dashboard_summary_tiene_kpis -v`
Expected: FAIL — 404.

- [ ] **Step 3: Implementar** (añadir a `api_server.py`)

```python
@app.get("/dashboard-summary")                        # KPIs agregados para la pantalla de Inicio
def dashboard_summary():                              # combina el historico CSV con la tabla embarques
    resumen = {}                                      # acumulador de resultados
    df = pd.read_csv(RUTA_CSV)                         # carga el historico (siempre hay datos)
    resumen["registros_historicos"] = int(len(df))    # total de envios historicos registrados
    resumen["eta_promedio"] = round(float(df["dias_reales"].mean()), 1)  # promedio general de dias reales
    conteo_aduana = df["aduana_destino"].value_counts()  # cuantos envios por cada aduana
    resumen["por_aduana"] = [{"aduana": str(k), "envios": int(v)}  # serializa la distribucion por aduana
                             for k, v in conteo_aduana.items()]
    promedio_operador = df.groupby("operador")["dias_reales"].mean().sort_values()  # operadores por rapidez
    resumen["operador_mas_rapido"] = str(promedio_operador.index[0])  # el de menor promedio de dias
    # Conteos "en vivo" desde la tabla embarques (si esta vacia, quedan en 0).
    estados = {"En Tránsito": 0, "Aduana": 0, "Entregado": 0, "Demorado": 0}  # estados posibles
    try:                                              # la tabla podria no existir o estar vacia
        from src.database import conectar_db          # import perezoso de la conexion
        conn = conectar_db()                          # abre SQLite
        cur = conn.cursor()                           # cursor de consulta
        cur.execute("SELECT estado, COUNT(*) FROM embarques GROUP BY estado")  # agrupa por estado
        for est, n in cur.fetchall():                 # recorre los resultados
            if est in estados:                        # solo estados conocidos
                estados[est] = int(n)                 # asigna el conteo
        conn.close()                                  # cierra la conexion
    except Exception:                                 # ante cualquier error de DB
        pass                                          # dejamos los estados en 0 (no rompe el Inicio)
    resumen["estados"] = estados                      # agrega los conteos por estado
    return resumen                                    # devuelve el resumen completo
```

- [ ] **Step 4: Correr toda la suite (debe pasar)**

Run: `python -m pytest tests/test_api_server.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Verificación manual del sidecar real** (arranca y responde de verdad)

Run desde la raíz:
```bash
python -m uvicorn api_server:app --host 127.0.0.1 --port 8000
```
En otra terminal:
```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/landed-cost -H "Content-Type: application/json" -d "{\"fob\":10000,\"flete\":1500,\"seguro\":300,\"arancel\":12,\"tasa\":1,\"iva\":16,\"gastos\":0}"
```
Expected: `/health` da `{"estado":"entrenando"}` y a los segundos `{"estado":"listo"}`; `/landed-cost` devuelve el desglose con `landed_cost`. Detener con Ctrl+C.

- [ ] **Step 6: Commit**

```bash
git add api_server.py tests/test_api_server.py
git commit -m "feat(sidecar): endpoint /dashboard-summary (KPIs de Inicio)"
```

---

## FASE 2 — Cascarón Electron

### Task 8: `main.js` + `preload.js` (arranque, ventana, ciclo de vida, IPC)

**Files:**
- Create: `frontend/main.js`
- Create: `frontend/preload.js`
- Create: `frontend/renderer/index.html` (versión mínima temporal para verificar el arranque)

**Interfaces:**
- Produces: canal IPC `elegir-ruta-pdf` → devuelve `string|null`; `window.nativo.elegirRutaPdf()` en el renderer.

- [ ] **Step 1: Crear `frontend/main.js`**

```javascript
// main.js — Proceso principal de Electron.
// Responsabilidades: lanzar el sidecar Python, crear la ventana, exponer el dialogo de guardado, y
// matar el proceso hijo al cerrar para no dejar servidores colgados.

const { app, BrowserWindow, ipcMain, dialog } = require('electron') // APIs de Electron
const { spawn } = require('child_process')                          // para lanzar/matar el proceso Python
const path = require('path')                                        // manejo de rutas de archivos

let ventana = null            // referencia a la ventana principal (para el dialogo y evitar recoleccion)
let procesoPython = null      // referencia al proceso hijo del sidecar

const PUERTO = 8000           // puerto donde escucha el sidecar (debe coincidir con api.js)
const RAIZ_PROYECTO = path.join(__dirname, '..')  // frontend/ esta dentro del proyecto; '..' = raiz con api_server.py

function lanzarSidecar() {                          // arranca uvicorn sirviendo api_server:app
  // 'python -m uvicorn ...' con cwd en la raiz para que 'from src...' e 'import api_server' resuelvan.
  procesoPython = spawn(
    'python',                                       // interprete de Python del sistema
    ['-m', 'uvicorn', 'api_server:app', '--host', '127.0.0.1', '--port', String(PUERTO)], // argumentos
    { cwd: RAIZ_PROYECTO, env: { ...process.env } } // directorio de trabajo = raiz del proyecto
  )
  procesoPython.stdout.on('data', d => console.log('[sidecar]', d.toString()))  // log de salida estandar
  procesoPython.stderr.on('data', d => console.log('[sidecar]', d.toString()))  // log de errores
  procesoPython.on('exit', code => console.log('[sidecar] termino con codigo', code)) // aviso al terminar
}

function crearVentana() {                           // crea la ventana principal del dashboard
  ventana = new BrowserWindow({                     // configura la ventana de Chromium
    width: 1280, height: 820,                       // tamaño inicial parecido a las fotos
    minWidth: 1024, minHeight: 680,                 // tamaño minimo utilizable
    backgroundColor: '#161311',                     // color de fondo mientras carga (evita flash blanco)
    autoHideMenuBar: true,                          // ocultar la barra de menu nativa
    webPreferences: {                               // opciones de seguridad del renderer
      preload: path.join(__dirname, 'preload.js'),  // script puente seguro
      contextIsolation: true,                       // aisla el contexto del renderer (seguridad)
      nodeIntegration: false,                       // el renderer NO accede a Node directamente
    },
  })
  ventana.loadFile(path.join(__dirname, 'renderer', 'index.html')) // carga la interfaz
}

app.whenReady().then(() => {                        // cuando Electron esta listo
  lanzarSidecar()                                   // 1) arranca el backend Python
  crearVentana()                                    // 2) abre la ventana (el renderer hara el polling /health)
})

// IPC: el renderer pide abrir el dialogo nativo "guardar como" para el PDF y recibe la ruta elegida.
ipcMain.handle('elegir-ruta-pdf', async () => {     // maneja la invocacion desde preload
  const r = await dialog.showSaveDialog(ventana, {  // muestra el dialogo del sistema operativo
    title: 'Guardar Dictamen',                      // titulo de la ventana
    defaultPath: 'Dictamen_VUCE.pdf',               // nombre sugerido
    filters: [{ name: 'PDF', extensions: ['pdf'] }],// solo archivos .pdf
  })
  return r.canceled ? null : r.filePath             // devuelve la ruta o null si el usuario cancelo
})

function matarSidecar() {                           // detiene el proceso Python hijo
  if (!procesoPython) return                        // si no hay proceso, nada que hacer
  if (process.platform === 'win32') {               // en Windows hay que matar el arbol de procesos
    spawn('taskkill', ['/pid', String(procesoPython.pid), '/f', '/t']) // /f forzar, /t incluir hijos
  } else {                                          // en otros sistemas
    procesoPython.kill()                            // envia SIGTERM
  }
  procesoPython = null                              // limpia la referencia
}

app.on('window-all-closed', () => {                 // cuando se cierran todas las ventanas
  matarSidecar()                                    // detener el sidecar
  app.quit()                                        // salir de la app (tambien en macOS, por simplicidad)
})
app.on('before-quit', matarSidecar)                 // red de seguridad: matar el sidecar antes de salir
```

- [ ] **Step 2: Crear `frontend/preload.js`**

```javascript
// preload.js — Puente seguro entre el renderer (sin acceso a Node) y el proceso principal.
// Solo expone lo minimo necesario a traves de contextBridge.

const { contextBridge, ipcRenderer } = require('electron') // APIs permitidas en el preload

contextBridge.exposeInMainWorld('nativo', {          // crea window.nativo en el renderer
  // Abre el dialogo nativo de guardado y devuelve la ruta elegida (o null si se cancela).
  elegirRutaPdf: () => ipcRenderer.invoke('elegir-ruta-pdf'), // reenvia al canal IPC del main
})
```

- [ ] **Step 3: Crear `frontend/renderer/index.html` mínimo (temporal, solo para verificar arranque)**

```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>LogiIA</title>
</head>
<body style="background:#161311;color:#F5EEE4;font-family:sans-serif;padding:40px">
  <!-- Contenido temporal: se reemplaza por completo en la Fase 3 -->
  <h1>LogiIA — cascaron Electron OK</h1>
  <p id="salud">Consultando sidecar…</p>
  <script>
    // Prueba minima: consulta /health y muestra el estado, para confirmar que el puente funciona.
    async function probar() {                                  // funcion asincrona de prueba
      try {                                                    // intenta llamar al sidecar
        const r = await fetch('http://127.0.0.1:8000/health')  // peticion a /health
        const j = await r.json()                               // parsea el JSON
        document.getElementById('salud').textContent = 'Sidecar: ' + j.estado // muestra el estado
      } catch (e) {                                            // si el sidecar aun no responde
        document.getElementById('salud').textContent = 'Sidecar no responde aun, reintentando…' // aviso
        setTimeout(probar, 800)                                // reintenta en 800 ms
      }
    }
    probar()                                                   // inicia la prueba
  </script>
</body>
</html>
```

- [ ] **Step 4: Verificar el arranque de punta a punta**

Run desde `frontend/`:
```bash
npm start
```
Expected: se abre una ventana negra con "LogiIA — cascaron Electron OK" y, tras unos segundos, `Sidecar: listo`. En la consola aparecen logs `[sidecar]`. Cerrar la ventana y confirmar en el Administrador de tareas que **no** queda ningún `python.exe`/`uvicorn` colgado.

- [ ] **Step 5: Commit**

```bash
git add frontend/main.js frontend/preload.js frontend/renderer/index.html
git commit -m "feat(electron): cascaron principal, ciclo de vida del sidecar e IPC de guardado"
```

---

## FASE 3 — Sistema visual base

### Task 9: `index.html` completo + `styles.css` (tokens, layout, tarjetas glass, controles)

**Files:**
- Modify: `frontend/renderer/index.html` (reemplazo completo)
- Create: `frontend/renderer/styles.css`

**Interfaces:**
- Produces: estructura DOM con ids fijos que consumen los JS: `#fondo` (canvas), `#splash`, `#app`, `#sidebar-nav`, `#vista` (contenedor de vistas), `#toasts`; clases reutilizables `.tarjeta`, `.pill`, `.boton`, `.boton-primario`, `.campo`, `.gauge`.

- [ ] **Step 1: Reemplazar `frontend/renderer/index.html` por la estructura definitiva**

```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />                                    <!-- codificacion -->
  <meta name="viewport" content="width=device-width, initial-scale=1" /> <!-- escala -->
  <title>LogiIA — Dashboard Logístico</title>                <!-- titulo de la ventana -->
  <link rel="stylesheet" href="styles.css" />                <!-- hoja de estilos principal -->
</head>
<body>
  <canvas id="fondo"></canvas>                               <!-- lienzo del ambiente vivo (motion de fondo) -->

  <!-- Splash: se muestra mientras el sidecar entrena el modelo; motion.js lo anima; app.js lo oculta -->
  <div id="splash">
    <div class="splash-glow"></div>                          <!-- halo que respira detras del logo -->
    <div class="splash-logo">LogiIA</div>                    <!-- marca -->
    <div class="splash-msg" id="splash-msg">Iniciando motor logístico…</div> <!-- mensaje de estado -->
    <div class="splash-barra"><span></span></div>            <!-- barra indeterminada animada -->
  </div>

  <!-- App principal: oculta hasta que el sidecar esta 'listo' -->
  <div id="app" class="oculto">
    <aside id="sidebar">                                     <!-- barra lateral negra con iconos (como la foto) -->
      <div class="sidebar-marca">LI</div>                    <!-- logo compacto arriba -->
      <nav id="sidebar-nav"></nav>                           <!-- botones de navegacion (los inyecta app.js) -->
      <div class="sidebar-pie" id="sidebar-pie"></div>       <!-- seccion inferior: Cuenta/Sesion -->
    </aside>
    <main id="vista"></main>                                 <!-- aqui el router monta cada vista -->
  </div>

  <div id="toasts"></div>                                    <!-- contenedor de notificaciones deslizantes -->

  <!-- El punto de entrada es app.js (modulo ES); el resto se importa desde ahi -->
  <script type="module" src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Crear `frontend/renderer/styles.css`**

```css
/* styles.css — Tema, layout y motion de LogiIA. Paleta "puerto al atardecer". */

/* Fuente Manrope empaquetada local (con respaldo del sistema si no se descargo el woff2). */
@font-face {
  font-family: 'Manrope';                         /* nombre logico de la fuente */
  src: url('assets/Manrope.woff2') format('woff2');/* archivo local */
  font-weight: 200 800;                            /* rango variable de grosores */
  font-display: swap;                              /* muestra texto de inmediato con la de respaldo */
}

/* Tokens de color y forma (constantes reutilizables en toda la app). */
:root {
  --bg-0:#161311; --bg-1:#1E1A17; --bg-2:#26211D; --sidebar:#100E0C;  /* lienzo oscuro calido */
  --ambar:#F4C77B; --durazno:#F3A87C; --terracota:#E68A6C;            /* acentos calidos */
  --teal:#84D2C5; --petroleo:#5FB3AE; --salvia:#AEC99C;               /* frio maritimo / exito */
  --tinta:#F5EEE4; --tinta-suave:#B9AC9B; --linea:#3A332D;            /* texto y bordes */
  --r-card:22px; --r-pill:999px;                                      /* radios */
  --glass: rgba(38,33,29,0.55);                                       /* fondo semitransparente de tarjetas */
}

/* Reset basico y tipografia global. */
* { box-sizing:border-box; margin:0; padding:0; }  /* modelo de caja uniforme */
html, body { height:100%; }                        /* ocupar toda la ventana */
body {
  font-family:'Manrope', system-ui, 'Segoe UI', sans-serif; /* fuente principal + respaldos */
  color:var(--tinta);                              /* color de texto por defecto */
  background:var(--bg-0);                          /* fondo base */
  overflow:hidden;                                 /* la app maneja su propio scroll interno */
}

/* Canvas de fondo: cubre toda la ventana, detras de todo. */
#fondo { position:fixed; inset:0; z-index:0; }     /* fijo, ocupando todo, en la capa mas baja */

/* Utilidad para ocultar elementos sin quitarlos del DOM. */
.oculto { display:none !important; }               /* se usa para el splash y la app */

/* ---------- SPLASH ---------- */
#splash {
  position:fixed; inset:0; z-index:10;             /* sobre todo lo demas */
  display:flex; flex-direction:column;             /* columna centrada */
  align-items:center; justify-content:center; gap:18px; /* centrado con separacion */
}
.splash-logo { font-size:44px; font-weight:800; letter-spacing:2px; color:var(--ambar); } /* marca */
.splash-msg { color:var(--tinta-suave); }          /* mensaje de estado */
.splash-glow {                                     /* halo calido que respira detras del logo */
  position:absolute; width:340px; height:340px; border-radius:50%;
  background:radial-gradient(circle, rgba(244,199,123,0.25), transparent 70%);
  animation:respirar 3.2s ease-in-out infinite;    /* motion continuo, no popup */
}
.splash-barra { width:220px; height:4px; border-radius:var(--r-pill); background:var(--linea); overflow:hidden; }
.splash-barra span {                               /* barra indeterminada que recorre de lado a lado */
  display:block; width:40%; height:100%; border-radius:var(--r-pill);
  background:linear-gradient(90deg, var(--ambar), var(--teal));
  animation:recorrer 1.4s ease-in-out infinite;    /* movimiento continuo */
}

/* ---------- LAYOUT PRINCIPAL ---------- */
#app { position:relative; z-index:1; display:flex; height:100vh; padding:14px; gap:14px; } /* sidebar + vista */

/* Barra lateral negra con iconos (como en la foto). */
#sidebar {
  width:74px; background:var(--sidebar); border-radius:var(--r-card);
  display:flex; flex-direction:column; align-items:center; padding:16px 0; gap:8px;
}
.sidebar-marca {
  width:40px; height:40px; border-radius:12px; margin-bottom:12px;
  display:grid; place-items:center; font-weight:800; color:var(--bg-0);
  background:linear-gradient(135deg, var(--ambar), var(--durazno)); /* logo con degradado calido */
}
#sidebar-nav, .sidebar-pie { display:flex; flex-direction:column; gap:8px; align-items:center; }
.sidebar-pie { margin-top:auto; }                  /* empuja la seccion de cuenta hacia abajo */

/* Boton de navegacion de la barra lateral. */
.nav-btn {
  width:46px; height:46px; border:none; border-radius:14px; cursor:pointer;
  background:transparent; color:var(--tinta-suave); font-size:18px;
  display:grid; place-items:center;
  transition:background .25s ease, color .25s ease, transform .25s ease; /* micro-interaccion suave */
}
.nav-btn:hover { color:var(--tinta); transform:translateY(-2px); }       /* elevacion al pasar el cursor */
.nav-btn.activo { background:var(--bg-2); color:var(--ambar); }          /* item seleccionado */

/* Contenedor donde el router monta cada vista. Scroll interno propio. */
#vista { flex:1; overflow:auto; border-radius:var(--r-card); }

/* Transicion de vista: fade sutil (sin zoom ni popup). app.js/router.js alternan la clase. */
.vista-entrando { animation:aparecer-suave .2s ease both; }
@keyframes aparecer-suave { from { opacity:0; } to { opacity:1; } } /* solo opacidad, nada de escala */

/* ---------- TARJETAS GLASS ---------- */
.tarjeta {
  background:var(--glass); border:1px solid rgba(245,238,228,0.08); /* fondo translucido + borde claro */
  border-radius:var(--r-card); padding:20px;
  backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px);   /* efecto vidrio */
  box-shadow:0 10px 30px rgba(0,0,0,0.35);                          /* sombra suave */
  transition:transform .28s ease, box-shadow .28s ease;            /* micro-interaccion */
}
.tarjeta:hover { transform:translateY(-3px); box-shadow:0 16px 40px rgba(0,0,0,0.45); } /* elevacion */
.tarjeta.brilla { animation:glow-borde 4s ease-in-out infinite; }  /* glow que respira (opcional por tarjeta) */

.titulo { font-size:22px; font-weight:800; margin-bottom:4px; }    /* titulo de seccion */
.subtitulo { color:var(--tinta-suave); margin-bottom:16px; }       /* subtitulo/descripcion */

/* ---------- PILLS / KPIs ---------- */
.pill {
  display:inline-flex; align-items:center; gap:8px;
  padding:8px 14px; border-radius:var(--r-pill);
  background:rgba(245,238,228,0.06); color:var(--tinta); font-size:13px;
}
.kpi-num { font-size:28px; font-weight:800; }                      /* cifra grande de KPI (animada) */
.kpi-lbl { color:var(--tinta-suave); font-size:12px; }             /* etiqueta del KPI */

/* ---------- BOTONES ---------- */
.boton {
  border:1px solid var(--linea); background:transparent; color:var(--tinta);
  padding:12px 18px; border-radius:14px; cursor:pointer; font-family:inherit; font-size:14px;
  transition:background .2s ease, border-color .2s ease, transform .12s ease; /* micro-interaccion */
}
.boton:hover { border-color:var(--ambar); transform:translateY(-1px); }       /* realce al pasar cursor */
.boton:active { transform:translateY(0); }                                     /* feedback al presionar */
.boton-primario {
  border:none; color:var(--bg-0); font-weight:700;
  background:linear-gradient(135deg, var(--ambar), var(--durazno)); /* boton clave calido */
}
.boton-primario:disabled { opacity:.5; cursor:default; transform:none; }       /* estado deshabilitado */

/* ---------- CAMPOS DE FORMULARIO ---------- */
.campo { display:flex; flex-direction:column; gap:6px; margin-bottom:12px; }   /* etiqueta + control */
.campo > label { font-size:13px; color:var(--tinta-suave); }                   /* etiqueta del campo */
.campo select, .campo input, .campo textarea {
  background:var(--bg-1); border:1px solid var(--linea); color:var(--tinta);
  padding:11px 12px; border-radius:12px; font-family:inherit; font-size:14px;
  transition:border-color .2s ease, box-shadow .2s ease;                       /* foco animado */
}
.campo select:focus, .campo input:focus, .campo textarea:focus {
  outline:none; border-color:var(--ambar);
  box-shadow:0 0 0 3px rgba(244,199,123,0.15);                                 /* halo de foco */
}

/* ---------- SLIDER (estilo dimmer de la foto) ---------- */
.slider { -webkit-appearance:none; width:100%; height:8px; border-radius:var(--r-pill);
  background:linear-gradient(90deg, var(--ambar), var(--bg-1)); outline:none; }
.slider::-webkit-slider-thumb {
  -webkit-appearance:none; width:22px; height:22px; border-radius:50%;
  background:var(--tinta); cursor:pointer; border:3px solid var(--ambar);
  transition:transform .15s ease;                                              /* resorte suave */
}
.slider::-webkit-slider-thumb:hover { transform:scale(1.15); }                  /* realce del pulgar */

/* ---------- TOGGLE ---------- */
.toggle { width:46px; height:26px; border-radius:var(--r-pill); background:var(--linea);
  position:relative; cursor:pointer; transition:background .25s ease; }
.toggle.on { background:var(--teal); }                                          /* encendido */
.toggle::after { content:''; position:absolute; top:3px; left:3px; width:20px; height:20px;
  border-radius:50%; background:var(--tinta); transition:transform .25s ease; } /* perilla deslizante */
.toggle.on::after { transform:translateX(20px); }                              /* se desliza al encender */

/* ---------- GAUGE CIRCULAR (SVG) ---------- */
.gauge-track { fill:none; stroke:var(--linea); stroke-width:10; }              /* aro de fondo */
.gauge-fill { fill:none; stroke:var(--ambar); stroke-width:10; stroke-linecap:round;
  transition:stroke-dashoffset 1s ease; }                                      /* el arco se llena animado */

/* ---------- BARRAS DE DESGLOSE ---------- */
.barra { height:12px; border-radius:var(--r-pill); background:var(--linea); overflow:hidden; }
.barra > span { display:block; height:100%; width:0;                            /* arranca en 0 y se llena */
  background:linear-gradient(90deg, var(--teal), var(--petroleo)); transition:width 1s ease; }

/* ---------- TOASTS ---------- */
#toasts { position:fixed; right:20px; bottom:20px; z-index:20; display:flex; flex-direction:column; gap:10px; }
.toast { padding:12px 16px; border-radius:14px; background:var(--bg-2); color:var(--tinta);
  border-left:4px solid var(--teal); box-shadow:0 10px 30px rgba(0,0,0,.4);
  animation:toast-in .25s ease both; }                                          /* entra deslizando, no zoom */
.toast.error { border-left-color:var(--terracota); }                            /* variante de error */
@keyframes toast-in { from { opacity:0; transform:translateX(20px); } to { opacity:1; transform:none; } }

/* ---------- KEYFRAMES DE MOTION ---------- */
@keyframes respirar { 0%,100% { transform:scale(1); opacity:.7; } 50% { transform:scale(1.08); opacity:1; } }
@keyframes recorrer { 0% { transform:translateX(-120%);} 100% { transform:translateX(360%);} }
@keyframes glow-borde { 0%,100% { box-shadow:0 10px 30px rgba(0,0,0,.35);} 50% { box-shadow:0 10px 40px rgba(244,199,123,.18);} }
@keyframes girar { to { transform:rotate(360deg); } }                           /* para el disco/gauge del Inicio */

/* ---------- ACCESIBILIDAD: reducir movimiento ---------- */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation:none !important; transition:none !important; } /* desactiva todo el motion */
}
```

- [ ] **Step 3: Verificación visual rápida**

Run `npm start` desde `frontend/`. Como `app.js` aún no existe, la consola de Electron mostrará un error de módulo — es esperado. Verificar que `styles.css` no tiene errores de sintaxis abriendo `index.html` directamente en un navegador (el splash debe verse con el glow y la barra animándose). Continuar.

- [ ] **Step 4: Commit**

```bash
git add frontend/renderer/index.html frontend/renderer/styles.css
git commit -m "feat(ui): estructura HTML definitiva y sistema visual (tokens, glass, controles, motion)"
```

---

## FASE 4 — Motor de motion

### Task 10: `motion.js` (fondo vivo, count-up, gauge, barra, línea de gráfico, toast)

**Files:**
- Create: `frontend/renderer/js/motion.js`

**Interfaces:**
- Produces (exports): `iniciarFondoVivo(canvas)`, `animarNumero(el, desde, hasta, {duracion, decimales, sufijo})`, `animarGauge(elFill, radio, porcentaje)`, `animarBarra(elSpan, porcentaje)`, `dibujarLineaCanvas(ctx, puntos, color)`, `mostrarToast(texto, tipo)`, `movimientoReducido()`.

- [ ] **Step 1: Crear `frontend/renderer/js/motion.js`**

```javascript
// motion.js — Motor de "motion graphics" de LogiIA.
// Reglas: movimiento continuo (fondo vivo, count-up, gauges, barras). Nada de aparicion por zoom/popup.
// Todo respeta prefers-reduced-motion mediante movimientoReducido().

// Devuelve true si el usuario pidio reducir el movimiento (accesibilidad del sistema operativo).
export function movimientoReducido() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches // consulta la preferencia del SO
}

// Interpolacion suave (easeOutCubic): arranca rapido y desacelera al final. Da sensacion premium.
function suavizar(t) {                              // t va de 0 a 1
  return 1 - Math.pow(1 - t, 3)                     // curva de desaceleracion
}

// Fondo vivo: rutas maritimas que fluyen lentamente sobre un degradado calido. Usa requestAnimationFrame.
export function iniciarFondoVivo(canvas) {
  const ctx = canvas.getContext('2d')              // contexto de dibujo 2D
  let ancho = 0, alto = 0                           // dimensiones actuales del lienzo
  function redimensionar() {                        // ajusta el canvas al tamaño de la ventana
    ancho = canvas.width = window.innerWidth        // ancho en pixeles reales
    alto = canvas.height = window.innerHeight       // alto en pixeles reales
  }
  redimensionar()                                   // dimension inicial
  window.addEventListener('resize', redimensionar)  // reajustar al cambiar el tamaño de la ventana

  // Genera un conjunto de "particulas" que representan barcos/paquetes desplazandose por rutas.
  const N = 34                                      // cantidad de particulas (bajo para no distraer)
  const particulas = Array.from({ length: N }, (_, i) => ({ // crea N particulas
    x: Math.random() * (ancho || 1200),             // posicion horizontal inicial aleatoria
    y: Math.random() * (alto || 800),               // posicion vertical inicial aleatoria
    v: 0.15 + Math.random() * 0.35,                 // velocidad lenta (movimiento sutil)
    r: 1 + Math.random() * 2,                       // radio del punto
    c: i % 3 === 0 ? '#84D2C5' : '#F4C77B',         // alterna color frio/calido
  }))

  function pintar() {                               // dibuja un fotograma
    ctx.clearRect(0, 0, ancho, alto)                // limpia el lienzo

    const g = ctx.createLinearGradient(0, 0, ancho, alto) // degradado calido de fondo
    g.addColorStop(0, '#1b1512')                    // esquina superior izquierda
    g.addColorStop(1, '#120f0d')                    // esquina inferior derecha
    ctx.fillStyle = g                               // usa el degradado
    ctx.fillRect(0, 0, ancho, alto)                 // pinta el fondo completo

    for (const p of particulas) {                   // recorre cada particula
      p.x += p.v                                     // avanza lentamente hacia la derecha
      if (p.x > ancho + 10) { p.x = -10; p.y = Math.random() * alto } // reaparece por la izquierda
      ctx.beginPath()                               // inicia el trazo de la estela
      ctx.moveTo(p.x, p.y)                          // punto actual
      ctx.lineTo(p.x - 28, p.y)                     // estela hacia atras (linea de ruta)
      ctx.strokeStyle = p.c + '22'                  // color con baja opacidad (22 en hex ~ 13%)
      ctx.lineWidth = p.r                           // grosor segun tamaño
      ctx.stroke()                                  // dibuja la estela
      ctx.beginPath()                               // dibuja el punto (barco/paquete)
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)        // circulo
      ctx.fillStyle = p.c + '66'                    // relleno semitransparente
      ctx.fill()                                    // pinta el punto
    }
    requestAnimationFrame(pintar)                   // programa el siguiente fotograma (bucle continuo)
  }
  if (movimientoReducido()) {                       // si el usuario pidio menos movimiento
    ctx.fillStyle = '#161311'; ctx.fillRect(0, 0, ancho, alto) // pinta un fondo estatico y no anima
    return                                          // no arranca el bucle
  }
  pintar()                                          // arranca el bucle de animacion
}

// Count-up: anima el texto de un elemento desde un numero a otro con easing.
export function animarNumero(el, desde, hasta, opciones = {}) {
  const duracion = opciones.duracion ?? 900         // duracion en ms
  const decimales = opciones.decimales ?? 0         // cantidad de decimales a mostrar
  const sufijo = opciones.sufijo ?? ''              // texto que se agrega al final (ej. ' d', '%')
  if (movimientoReducido()) {                       // si se reduce el movimiento
    el.textContent = hasta.toFixed(decimales) + sufijo // muestra el valor final sin animar
    return                                          // termina
  }
  const inicio = performance.now()                  // marca de tiempo inicial
  function paso(ahora) {                             // funcion de cada fotograma
    const t = Math.min(1, (ahora - inicio) / duracion) // progreso 0..1
    const valor = desde + (hasta - desde) * suavizar(t) // valor interpolado con easing
    el.textContent = valor.toFixed(decimales) + sufijo  // actualiza el texto
    if (t < 1) requestAnimationFrame(paso)          // continua hasta llegar a 1
  }
  requestAnimationFrame(paso)                        // inicia la animacion
}

// Gauge circular (SVG): llena el arco segun un porcentaje usando stroke-dashoffset.
export function animarGauge(elFill, radio, porcentaje) {
  const circunferencia = 2 * Math.PI * radio         // longitud total del circulo
  elFill.style.strokeDasharray = String(circunferencia) // el trazo completo ocupa toda la circunferencia
  const objetivo = circunferencia * (1 - Math.min(1, Math.max(0, porcentaje / 100))) // offset segun %
  elFill.style.strokeDashoffset = String(circunferencia) // arranca vacio (offset = circunferencia)
  requestAnimationFrame(() => {                      // en el siguiente fotograma dispara la transicion CSS
    elFill.style.strokeDashoffset = movimientoReducido() ? String(objetivo) : String(objetivo) // llena
  })
}

// Barra de desglose: lleva el ancho de 0% al porcentaje indicado (la transicion CSS hace el resto).
export function animarBarra(elSpan, porcentaje) {
  const pct = Math.min(100, Math.max(0, porcentaje)) // acota el valor a 0..100
  requestAnimationFrame(() => { elSpan.style.width = pct + '%' }) // aplica el ancho (transicion definida en CSS)
}

// Dibuja una polilinea "dibujandose" sobre un canvas 2D (para el grafico historico del modulo ETA).
export function dibujarLineaCanvas(ctx, puntos, color) {
  if (!puntos.length) return                         // si no hay puntos, nada que dibujar
  let progreso = 0                                   // cuantos segmentos se han dibujado (0..1)
  function paso() {                                  // fotograma de la animacion de dibujo
    progreso = Math.min(1, progreso + 0.03)          // avanza el trazo
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height) // limpia para redibujar
    ctx.beginPath()                                  // inicia la linea
    const total = puntos.length - 1                  // segmentos totales
    const hasta = Math.floor(total * progreso)       // hasta que punto dibujar en este fotograma
    ctx.moveTo(puntos[0].x, puntos[0].y)             // primer punto
    for (let i = 1; i <= hasta; i++) ctx.lineTo(puntos[i].x, puntos[i].y) // une los puntos alcanzados
    ctx.strokeStyle = color                          // color de la linea
    ctx.lineWidth = 3                                // grosor
    ctx.stroke()                                     // traza
    if (progreso < 1 && !movimientoReducido()) requestAnimationFrame(paso) // continua si falta y hay motion
  }
  paso()                                             // arranca el dibujo
}

// Toast: notificacion que entra deslizando desde la derecha y desaparece sola (sin popup/zoom).
export function mostrarToast(texto, tipo = 'ok') {
  const cont = document.getElementById('toasts')     // contenedor de toasts
  const el = document.createElement('div')           // crea el elemento
  el.className = 'toast' + (tipo === 'error' ? ' error' : '') // clase base + variante de error
  el.textContent = texto                             // mensaje
  cont.appendChild(el)                               // lo agrega a la pantalla
  setTimeout(() => {                                 // tras unos segundos
    el.style.transition = 'opacity .3s ease'         // prepara el desvanecido
    el.style.opacity = '0'                           // desvanece
    setTimeout(() => el.remove(), 320)               // lo quita del DOM al terminar
  }, 3200)                                            // visible ~3.2 s
}
```

- [ ] **Step 2: Verificación**

No hay UI aún que dispare estas funciones; se validan en las siguientes tareas al integrarlas. Confirmar que el archivo no tiene errores de sintaxis: `node --check frontend/renderer/js/motion.js`.
Expected: sin salida (sintaxis válida).

- [ ] **Step 3: Commit**

```bash
git add frontend/renderer/js/motion.js
git commit -m "feat(motion): motor de animaciones (fondo vivo, count-up, gauge, barra, linea, toast)"
```

---

## FASE 5 — Núcleo del front (API, estado, router, arranque, Inicio)

### Task 11: `api.js` (todas las llamadas al sidecar)

**Files:**
- Create: `frontend/renderer/js/api.js`

**Interfaces:**
- Produces (export `api`): `health()`, `login(u,p)`, `register(u,p,empresa)`, `predictEta(datos)`, `etaHistorico(origen)`, `vuce(regimen,consulta)`, `vucePdf(datos)`, `landedCost(datos)`, `dashboardSummary()`. Cada uno devuelve una promesa con el JSON; lanza `Error` en fallo.

- [ ] **Step 1: Crear `frontend/renderer/js/api.js`**

```javascript
// api.js — Unico lugar donde el front habla con el sidecar Python. Centraliza fetch, JSON y errores.

const BASE = 'http://127.0.0.1:8000'                 // el sidecar escucha aqui (mismo puerto que main.js)

// Helper interno: hace una peticion, valida el codigo HTTP y devuelve el JSON.
async function pedir(ruta, opciones = {}) {
  const r = await fetch(BASE + ruta, {               // realiza la peticion
    headers: { 'Content-Type': 'application/json' }, // enviamos/recibimos JSON
    ...opciones,                                     // metodo y cuerpo si aplican
  })
  if (!r.ok) {                                        // si el servidor respondio con error (4xx/5xx)
    let detalle = r.status                            // por defecto, el codigo
    try { detalle = (await r.json()).detail || detalle } catch (e) {} // intenta leer el mensaje del backend
    throw new Error('Error del servidor: ' + detalle) // lanza para que la vista muestre un toast
  }
  return r.json()                                     // devuelve el cuerpo ya parseado
}

// Helper para POST con cuerpo JSON.
function postJson(ruta, cuerpo) {
  return pedir(ruta, { method: 'POST', body: JSON.stringify(cuerpo) }) // serializa el objeto a JSON
}

// API publica que consumen las vistas.
export const api = {
  health: () => pedir('/health'),                    // estado del motor (para el splash)
  login: (username, password) => postJson('/login', { username, password }), // autenticacion
  register: (username, password, empresa) => postJson('/register', { username, password, empresa }), // registro
  predictEta: (datos) => postJson('/predict-eta', datos), // prediccion de ETA (datos = {origen,via,...})
  etaHistorico: (origen) => pedir('/eta-historico?origen=' + encodeURIComponent(origen)), // grafico historico
  vuce: (regimen, consulta) => postJson('/vuce', { regimen, consulta }), // dictamen legal
  vucePdf: (datos) => postJson('/vuce-pdf', datos), // exportar dictamen a PDF (datos={regimen,consulta,html,ruta})
  landedCost: (datos) => postJson('/landed-cost', datos), // calculadora financiera
  dashboardSummary: () => pedir('/dashboard-summary'), // KPIs de la pantalla de Inicio
}
```

- [ ] **Step 2: Verificación**

Run: `node --check frontend/renderer/js/api.js`
Expected: sin salida (sintaxis válida).

- [ ] **Step 3: Commit**

```bash
git add frontend/renderer/js/api.js
git commit -m "feat(front): capa api.js (llamadas centralizadas al sidecar)"
```

---

### Task 12: `estado.js` + `router.js`

**Files:**
- Create: `frontend/renderer/js/estado.js`
- Create: `frontend/renderer/js/router.js`

**Interfaces:**
- Produces: `estado.sesion = {usuario:null, rol:null}`, `estado.entrar(usuario,rol)`, `estado.salir()`; `router.registrar(nombre, fnRender)`, `router.ir(nombre)`, `router.actual()`.

- [ ] **Step 1: Crear `frontend/renderer/js/estado.js`**

```javascript
// estado.js — Estado de sesion en memoria, compartido por todas las vistas.

export const estado = {                              // objeto unico de estado global
  sesion: { usuario: null, rol: null },              // usuario autenticado (null = invitado)
  entrar(usuario, rol) {                             // registra una sesion iniciada
    this.sesion.usuario = usuario                     // guarda el nombre de usuario
    this.sesion.rol = rol                             // guarda el rol (User/Admin)
  },
  salir() {                                           // cierra la sesion
    this.sesion.usuario = null                        // limpia el usuario
    this.sesion.rol = null                            // limpia el rol
  },
}
```

- [ ] **Step 2: Crear `frontend/renderer/js/router.js`**

```javascript
// router.js — Conmuta entre vistas montandolas en #vista con un fade sutil (sin zoom/popup).

const vistas = {}          // registro nombre -> funcion de render
let vistaActual = null     // nombre de la vista mostrada

// Registra una vista: 'nombre' identifica y 'fnRender(contenedor)' construye su DOM.
export const router = {
  registrar(nombre, fnRender) {
    vistas[nombre] = fnRender                          // guarda la funcion de render
  },
  actual() { return vistaActual },                    // devuelve el nombre de la vista activa
  ir(nombre) {                                        // navega a una vista
    const contenedor = document.getElementById('vista') // contenedor principal
    const fn = vistas[nombre]                          // busca el render de la vista
    if (!fn) return                                    // si no existe, no hace nada
    vistaActual = nombre                               // actualiza la vista activa
    contenedor.innerHTML = ''                          // limpia el contenido anterior
    contenedor.classList.remove('vista-entrando')      // reinicia la animacion de entrada
    void contenedor.offsetWidth                        // fuerza reflow para reejecutar el keyframe
    contenedor.classList.add('vista-entrando')         // aplica el fade de entrada
    fn(contenedor)                                     // construye la nueva vista
    // Marca el boton de navegacion activo (si existe) segun el nombre de la vista.
    document.querySelectorAll('.nav-btn').forEach(b => // recorre los botones del sidebar
      b.classList.toggle('activo', b.dataset.vista === nombre)) // resalta el que corresponde
  },
}
```

- [ ] **Step 3: Verificación**

Run: `node --check frontend/renderer/js/estado.js && node --check frontend/renderer/js/router.js`
Expected: sin salida.

- [ ] **Step 4: Commit**

```bash
git add frontend/renderer/js/estado.js frontend/renderer/js/router.js
git commit -m "feat(front): estado de sesion y router de vistas con fade"
```

---

### Task 13: `app.js` (arranque, splash con polling, sidebar, registro de vistas)

**Files:**
- Create: `frontend/renderer/js/app.js`

**Interfaces:**
- Consumes: `iniciarFondoVivo` (motion), `api.health` (api), `router` (router), y los `render` de cada vista.
- Produces: arranque completo de la app; función `construirSidebar()`.

> NOTA: este archivo importa las 5 vistas. Se crea AHORA con imports a archivos que se completan en las Tasks 14-18. Para que `npm start` funcione tras esta tarea, las vistas se crean como stubs mínimos en el Step 2 y se completan luego. (Alternativa: ejecutar Tasks 14-18 antes de probar `app.js`.)

- [ ] **Step 1: Crear `frontend/renderer/js/app.js`**

```javascript
// app.js — Punto de entrada del renderer. Arranca el fondo vivo, espera al sidecar (splash) y monta la app.

import { iniciarFondoVivo, mostrarToast } from './motion.js' // motor de motion
import { api } from './api.js'                               // llamadas al sidecar
import { router } from './router.js'                         // navegacion entre vistas
import { estado } from './estado.js'                         // estado de sesion
import { renderInicio } from './vistas/inicio.js'            // vista Inicio
import { renderEta } from './vistas/eta.js'                  // vista Predictor ETA
import { renderVuce } from './vistas/vuce.js'                // vista Asesor VUCE
import { renderLanded } from './vistas/landed.js'            // vista Landed Cost
import { renderSesion } from './vistas/sesion.js'            // vista Cuenta/Sesion

// 1) Arranca el ambiente vivo de fondo cuanto antes.
iniciarFondoVivo(document.getElementById('fondo'))           // pinta el canvas de fondo

// 2) Registra todas las vistas en el router.
router.registrar('inicio', renderInicio)                     // pantalla principal estilo foto
router.registrar('eta', renderEta)                           // modulo ETA
router.registrar('vuce', renderVuce)                         // modulo VUCE
router.registrar('landed', renderLanded)                     // modulo Landed Cost
router.registrar('sesion', renderSesion)                     // modulo de cuenta

// 3) Construye la barra lateral (iconos de navegacion + seccion de cuenta).
function construirSidebar() {
  const nav = document.getElementById('sidebar-nav')         // contenedor de navegacion superior
  const pie = document.getElementById('sidebar-pie')         // contenedor inferior (cuenta)
  // Definicion de los botones: [nombre de vista, emoji-icono, titulo accesible].
  const items = [                                            // items superiores
    ['inicio', '▦', 'Inicio'],                               // dashboard
    ['eta', '⏱', 'Predictor ETA'],                           // prediccion
    ['vuce', '⚖', 'Asesor VUCE'],                            // asesor legal
    ['landed', '$', 'Landed Cost'],                          // finanzas
  ]
  nav.innerHTML = ''                                          // limpia por si se reconstruye
  for (const [vista, icono, titulo] of items) {              // crea cada boton
    const b = document.createElement('button')               // elemento boton
    b.className = 'nav-btn'                                   // estilo de navegacion
    b.dataset.vista = vista                                   // asocia el nombre de vista (para resaltar)
    b.title = titulo                                          // tooltip accesible
    b.textContent = icono                                    // icono visible
    b.onclick = () => router.ir(vista)                        // al hacer clic, navega
    nav.appendChild(b)                                        // agrega al sidebar
  }
  // Boton de cuenta/sesion, fijo abajo.
  const bc = document.createElement('button')                // boton de cuenta
  bc.className = 'nav-btn'                                    // mismo estilo
  bc.dataset.vista = 'sesion'                                 // vista de sesion
  bc.title = 'Cuenta / Acceso'                                // tooltip
  bc.textContent = '👤'                                       // icono de usuario
  bc.onclick = () => router.ir('sesion')                      // navega a sesion
  pie.innerHTML = ''                                          // limpia
  pie.appendChild(bc)                                         // agrega abajo
}

// 4) Espera a que el sidecar este 'listo' (polling a /health) mostrando el splash, luego revela la app.
async function esperarSidecar() {
  const msg = document.getElementById('splash-msg')          // texto del splash
  for (let intento = 0; intento < 60; intento++) {           // hasta ~60 intentos (unos 30 s)
    try {                                                    // intenta consultar la salud
      const j = await api.health()                            // { estado: ... }
      if (j.estado === 'listo') return true                   // motor entrenado: salir del bucle
      if (j.estado === 'error') { msg.textContent = 'Error al iniciar el motor.'; return false } // fallo
      msg.textContent = 'Entrenando modelo predictivo…'       // mensaje mientras entrena
    } catch (e) {                                             // el sidecar aun no responde
      msg.textContent = 'Conectando con el motor logístico…'  // mensaje de conexion
    }
    await new Promise(r => setTimeout(r, 500))                // espera 500 ms antes de reintentar
  }
  return false                                                // se agoto el tiempo
}

// 5) Orquesta el arranque: espera al sidecar, oculta el splash y muestra el dashboard.
async function arrancar() {
  construirSidebar()                                          // arma la navegacion
  const listo = await esperarSidecar()                        // espera al backend
  if (!listo) {                                               // si no arranco a tiempo
    mostrarToast('No se pudo iniciar el motor. Reinicia la app.', 'error') // avisa
    return                                                    // no continua
  }
  document.getElementById('splash').classList.add('oculto')   // oculta el splash
  document.getElementById('app').classList.remove('oculto')   // muestra la app
  router.ir('inicio')                                         // abre la pantalla de Inicio
}

arrancar()                                                    // inicia todo
```

- [ ] **Step 2: Crear stubs mínimos de las 5 vistas** (para que los imports resuelvan; se completan en Tasks 14-18)

```javascript
// frontend/renderer/js/vistas/inicio.js  (STUB temporal)
export function renderInicio(c){ c.innerHTML = '<div class="tarjeta" style="margin:14px"><h1 class="titulo">Inicio</h1></div>' }
```
```javascript
// frontend/renderer/js/vistas/eta.js  (STUB temporal)
export function renderEta(c){ c.innerHTML = '<div class="tarjeta" style="margin:14px"><h1 class="titulo">ETA</h1></div>' }
```
```javascript
// frontend/renderer/js/vistas/vuce.js  (STUB temporal)
export function renderVuce(c){ c.innerHTML = '<div class="tarjeta" style="margin:14px"><h1 class="titulo">VUCE</h1></div>' }
```
```javascript
// frontend/renderer/js/vistas/landed.js  (STUB temporal)
export function renderLanded(c){ c.innerHTML = '<div class="tarjeta" style="margin:14px"><h1 class="titulo">Landed</h1></div>' }
```
```javascript
// frontend/renderer/js/vistas/sesion.js  (STUB temporal)
export function renderSesion(c){ c.innerHTML = '<div class="tarjeta" style="margin:14px"><h1 class="titulo">Sesión</h1></div>' }
```

- [ ] **Step 3: Verificación E2E del cascarón completo**

Run `npm start` desde `frontend/`. Expected: aparece el splash con glow/barra; tras el entrenamiento (segundos) se revela el dashboard con la barra lateral (5 iconos) y la vista "Inicio" (stub). Al hacer clic en cada icono, cambia la vista con fade y se resalta el icono activo. El fondo muestra las partículas fluyendo.

- [ ] **Step 4: Commit**

```bash
git add frontend/renderer/js/app.js frontend/renderer/js/vistas/
git commit -m "feat(front): arranque, splash con polling, sidebar y registro de vistas (vistas stub)"
```

---

### Task 14: `vistas/inicio.js` (dashboard estilo foto)

**Files:**
- Modify: `frontend/renderer/js/vistas/inicio.js` (reemplaza el stub)

**Interfaces:**
- Consumes: `api.dashboardSummary()`, `animarNumero`, `animarGauge`, `router.ir`.
- Produces: `renderInicio(contenedor)`.

- [ ] **Step 1: Reemplazar `frontend/renderer/js/vistas/inicio.js`**

```javascript
// inicio.js — Pantalla principal con el layout de la foto, mapeado a datos logisticos.
// Estructura: HERO (KPIs + mapa) | lista RUTAS/ADUANAS | 3 tarjetas (ETA, Landed, VUCE).

import { api } from '../api.js'                               // datos del sidecar
import { animarNumero, animarGauge, mostrarToast } from '../motion.js' // animaciones
import { router } from '../router.js'                         // para enlazar a los modulos

export async function renderInicio(contenedor) {
  // 1) Estructura HTML del dashboard (grid parecido a la foto). Las cifras arrancan en 0 y se animan luego.
  contenedor.innerHTML = `
    <div class="inicio-grid">                                <!-- rejilla principal -->
      <section class="tarjeta hero">                          <!-- panel HERO grande -->
        <div class="hero-top">                                <!-- fila superior de pills/KPIs -->
          <span class="pill">● Live</span>                    <!-- indicador en vivo -->
          <div class="kpis">                                  <!-- grupo de KPIs -->
            <div><div class="kpi-num" id="kpi-transito">0</div><div class="kpi-lbl">En tránsito</div></div>
            <div><div class="kpi-num" id="kpi-aduana">0</div><div class="kpi-lbl">En aduana</div></div>
            <div><div class="kpi-num" id="kpi-eta">0</div><div class="kpi-lbl">ETA prom (días)</div></div>
            <div><div class="kpi-num" id="kpi-hist">0</div><div class="kpi-lbl">Históricos</div></div>
          </div>
        </div>
        <div class="hero-mapa" id="hero-mapa"></div>          <!-- zona de "mapa de ruta" (decorativa animada) -->
      </section>

      <aside class="tarjeta rutas">                           <!-- lista lateral derecha (como "Rooms") -->
        <h3 class="titulo" style="font-size:18px">Rutas / Aduanas</h3>
        <div id="lista-aduanas"></div>                        <!-- se llena con las aduanas -->
        <button class="boton boton-primario" id="btn-nueva" style="width:100%;margin-top:12px">+ NUEVA CONSULTA</button>
      </aside>

      <div class="cards">                                     <!-- fila inferior: contiene las 3 tarjetas -->
        <button class="tarjeta mini" id="card-eta">           <!-- tarjeta inferior izquierda: ETA -->
          <div class="mini-top"><span>Predictor ETA</span></div>
          <div class="mini-cifra"><span class="kpi-num" id="mini-eta">0</span><span class="kpi-lbl"> días prom.</span></div>
          <div class="mini-pills">
            <span class="pill">Op. más rápido: <b id="op-rapido">—</b></span>
          </div>
        </button>

        <button class="tarjeta mini" id="card-landed">        <!-- tarjeta inferior central: Landed Cost -->
          <div class="mini-top"><span>Landed Cost</span></div>
          <div class="mini-cifra"><span class="kpi-lbl">Simulación rápida FOB</span></div>
          <input type="range" min="1000" max="50000" value="10000" class="slider" id="mini-slider" />
          <div class="mini-cifra"><span class="kpi-num" id="mini-total">0</span><span class="kpi-lbl"> total est.</span></div>
        </button>

        <button class="tarjeta mini" id="card-vuce">          <!-- tarjeta inferior derecha: VUCE (gauge) -->
          <div class="mini-top"><span>Asesor VUCE</span></div>
          <svg viewBox="0 0 120 120" class="gauge" width="110" height="110"> <!-- gauge circular -->
            <circle class="gauge-track" cx="60" cy="60" r="50"></circle>     <!-- aro de fondo -->
            <circle class="gauge-fill" cx="60" cy="60" r="50" id="gauge-vuce"
                    transform="rotate(-90 60 60)"></circle>                  <!-- arco que se llena -->
          </svg>
          <div class="kpi-lbl" style="text-align:center">Viabilidad estimada</div>
        </button>
      </div>
    </div>
  `

  // 2) Enlaces de navegacion: cada tarjeta lleva a su modulo.
  document.getElementById('card-eta').onclick = () => router.ir('eta')       // abre ETA
  document.getElementById('card-vuce').onclick = () => router.ir('vuce')     // abre VUCE
  document.getElementById('card-landed').onclick = (e) => {                  // abre Landed salvo al mover el slider
    if (e.target.id !== 'mini-slider') router.ir('landed')                   // evita navegar al arrastrar
  }
  document.getElementById('btn-nueva').onclick = () => router.ir('vuce')     // "+ NUEVA CONSULTA" -> VUCE

  // 3) Slider tipo "dimmer": recalcula un total estimado en vivo (arancel fijo 12% + IVA 16%, demo).
  const slider = document.getElementById('mini-slider')                      // control deslizante
  const elTotal = document.getElementById('mini-total')                      // cifra del total
  function recalcularMini() {
    const fob = Number(slider.value)                                         // valor FOB elegido
    const cif = fob * 1.18                                                   // + flete/seguro aprox (18%)
    const total = cif * 1.12 * 1.16                                          // + arancel 12% + IVA 16%
    elTotal.textContent = '$' + Math.round(total).toLocaleString('es-VE')    // muestra el total formateado
  }
  slider.oninput = recalcularMini                                            // recalcula al mover
  recalcularMini()                                                           // valor inicial

  // 4) Traer los KPIs reales del sidecar y animarlos (count-up) + llenar la lista de aduanas + gauge.
  try {
    const d = await api.dashboardSummary()                                   // pide el resumen
    animarNumero(document.getElementById('kpi-transito'), 0, d.estados['En Tránsito']) // KPI en transito
    animarNumero(document.getElementById('kpi-aduana'), 0, d.estados['Aduana'])        // KPI en aduana
    animarNumero(document.getElementById('kpi-eta'), 0, d.eta_promedio, { decimales: 1 }) // ETA promedio
    animarNumero(document.getElementById('kpi-hist'), 0, d.registros_historicos)        // historicos
    animarNumero(document.getElementById('mini-eta'), 0, d.eta_promedio, { decimales: 1 }) // ETA en tarjeta
    document.getElementById('op-rapido').textContent = d.operador_mas_rapido            // operador mas rapido

    // Lista de aduanas (como la lista "Rooms" de la foto): nombre + N envios, una resaltada.
    const cont = document.getElementById('lista-aduanas')                    // contenedor de la lista
    d.por_aduana.forEach((a, i) => {                                         // recorre cada aduana
      const fila = document.createElement('div')                            // fila de la lista
      fila.className = 'aduana-fila' + (i === 0 ? ' activa' : '')            // resalta la primera
      fila.innerHTML = `<span>${a.aduana}</span><span class="kpi-lbl">${a.envios} envíos ›</span>` // contenido
      cont.appendChild(fila)                                                 // agrega a la lista
    })

    // Gauge de "viabilidad" (demo): un valor alto para reflejar operacion viable.
    animarGauge(document.getElementById('gauge-vuce'), 50, 78)               // llena el 78% del aro
  } catch (e) {                                                              // si el sidecar fallo
    mostrarToast('No se pudieron cargar los indicadores.', 'error')          // avisa sin romper la vista
  }
}
```

- [ ] **Step 2: Añadir los estilos específicos del Inicio al final de `styles.css`**

```css
/* ---------- PANTALLA DE INICIO (layout de la foto) ---------- */
.inicio-grid {                                     /* rejilla: 2 columnas arriba, 3 tarjetas abajo */
  display:grid; gap:14px; padding:14px; height:100%;
  grid-template-columns:2fr 1fr;                   /* HERO ancho + lista lateral */
  grid-template-rows:1.4fr 1fr;                    /* fila superior alta + fila de tarjetas */
  grid-template-areas:"hero rutas" "cards cards";  /* zonas nombradas */
}
.hero { grid-area:hero; display:flex; flex-direction:column; gap:16px; }     /* panel principal */
.rutas { grid-area:rutas; display:flex; flex-direction:column; }             /* lista lateral */
.hero-top { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; flex-wrap:wrap; }
.kpis { display:flex; gap:22px; flex-wrap:wrap; }                            /* fila de KPIs */
.hero-mapa {                                        /* "mapa" decorativo con degradado y ruta punteada animada */
  flex:1; border-radius:16px; position:relative; overflow:hidden;
  background:radial-gradient(120% 120% at 20% 20%, rgba(132,210,197,.12), transparent 60%), var(--bg-1);
}
.hero-mapa::after {                                 /* linea de ruta que fluye (dash animado) */
  content:''; position:absolute; left:8%; right:8%; top:55%; height:2px;
  background:repeating-linear-gradient(90deg, var(--ambar) 0 10px, transparent 10px 20px);
  animation:recorrer-ruta 6s linear infinite;       /* movimiento continuo */
}
@keyframes recorrer-ruta { from { background-position:0 0; } to { background-position:120px 0; } }
.aduana-fila {                                      /* fila de la lista de aduanas */
  display:flex; justify-content:space-between; align-items:center;
  padding:12px 14px; border-radius:14px; margin-bottom:8px; background:rgba(245,238,228,.04);
  transition:background .2s ease, transform .2s ease; cursor:pointer;
}
.aduana-fila:hover { transform:translateX(3px); }   /* micro-interaccion */
.aduana-fila.activa { background:var(--bg-2); border:1px solid rgba(244,199,123,.25); } /* resaltada */
.cards { grid-area:cards; display:grid; grid-template-columns:repeat(3,1fr); gap:14px; } /* 3 tarjetas */
.mini { grid-column:span 1; display:flex; flex-direction:column; gap:10px; text-align:left;
  cursor:pointer; border:none; font-family:inherit; color:var(--tinta); }    /* tarjetas-boton inferiores */
.mini-top { display:flex; justify-content:space-between; font-weight:700; }   /* titulo de la mini tarjeta */
.mini-cifra { display:flex; align-items:baseline; gap:6px; }                  /* cifra + etiqueta */
.mini-pills { display:flex; gap:8px; flex-wrap:wrap; margin-top:auto; }       /* pills al pie */
.gauge { display:block; margin:0 auto; }                                      /* centra el gauge */
```
> NOTA: el `.cards` ocupa toda la fila inferior; las 3 `.mini` se reparten en 3 columnas. La rejilla superior usa `hero` (2fr) y `rutas` (1fr).

- [ ] **Step 3: Verificación visual**

Run `npm start`. Expected: la pantalla de Inicio reproduce el layout de la foto — HERO con 4 KPIs que hacen count-up desde 0, "mapa" con línea de ruta fluyendo, lista de aduanas a la derecha (primera resaltada), y 3 tarjetas abajo (ETA con días, Landed con slider que recalcula el total en vivo, VUCE con gauge que se llena al 78%). Clic en cada tarjeta/icono navega al módulo (aún stub para ETA/VUCE/Landed/Sesión).

- [ ] **Step 4: Commit**

```bash
git add frontend/renderer/js/vistas/inicio.js frontend/renderer/styles.css
git commit -m "feat(inicio): dashboard estilo foto mapeado a KPIs logisticos con motion"
```

---

## FASE 6 — Módulos completos

### Task 15: `vistas/eta.js` (Predictor ETA + gráfico Canvas)

**Files:**
- Modify: `frontend/renderer/js/vistas/eta.js` (reemplaza el stub)

**Interfaces:**
- Consumes: `api.predictEta`, `api.etaHistorico`, `animarNumero`, `animarBarra`, `dibujarLineaCanvas`, `mostrarToast`, `estado.sesion`.
- Produces: `renderEta(contenedor)`.

- [ ] **Step 1: Reemplazar `frontend/renderer/js/vistas/eta.js`**

```javascript
// eta.js — Modulo Predictor ETA: formulario + desglose animado (4 sub-modelos) + grafico historico en Canvas.

import { api } from '../api.js'                                   // llamadas al sidecar
import { animarNumero, animarBarra, dibujarLineaCanvas, mostrarToast } from '../motion.js' // animaciones
import { estado } from '../estado.js'                             // sesion (para saber si guardar historial)

// Opciones de los desplegables (mismas que la app Qt original).
const ORIGENES = ['Shanghái', 'Miami', 'Róterdam']               // origenes internacionales
const VIAS = ['Marítimo', 'Aéreo']                               // vias de transporte
const ADUANAS = ['Puerto Cabello', 'La Guaira', 'Maiquetía']     // aduanas de ingreso
const OPERADORES = ['Maersk', 'MSC', 'CMA CGM']                  // operadores logisticos
const CARGAS = ['Tecnología y Electrónica', 'Materia Prima Industrial', 'Textil y Calzado'] // tipos de carga

// Helper: construye un <select> con opciones a partir de un arreglo.
function selectDe(id, opciones) {
  return `<select id="${id}">${opciones.map(o => `<option>${o}</option>`).join('')}</select>` // options
}

export function renderEta(contenedor) {
  // 1) Maquetacion: formulario a la izquierda, resultado + grafico a la derecha.
  contenedor.innerHTML = `
    <div class="modulo">                                          <!-- envoltura con padding -->
      <h1 class="titulo">Predictor de Tiempo de Arribo (ETA)</h1>
      <p class="subtitulo">Estimación inteligente del tránsito hacia aduanas venezolanas.</p>
      <div class="dos-columnas">                                  <!-- rejilla 2 columnas -->
        <div class="tarjeta">                                     <!-- formulario -->
          <div class="campo"><label>Origen Internacional</label>${selectDe('eta-origen', ORIGENES)}</div>
          <div class="campo"><label>Vía de Transporte</label>${selectDe('eta-via', VIAS)}</div>
          <div class="campo"><label>Aduana de Ingreso</label>${selectDe('eta-aduana', ADUANAS)}</div>
          <div class="campo"><label>Operador Logístico</label>${selectDe('eta-operador', OPERADORES)}</div>
          <div class="campo"><label>Tipo de Mercancía</label>${selectDe('eta-carga', CARGAS)}</div>
          <div class="campo"><label>Fecha Estimada de Envío</label><input type="date" id="eta-fecha" /></div>
          <button class="boton boton-primario" id="eta-btn" style="width:100%">Calcular Predicción</button>
        </div>
        <div style="display:flex;flex-direction:column;gap:14px">  <!-- columna derecha -->
          <div class="tarjeta brilla">                            <!-- resultado con glow que respira -->
            <div class="kpi-lbl">ETA total estimado</div>
            <div><span class="kpi-num" id="eta-total" style="font-size:44px">0</span>
                 <span class="kpi-lbl"> días</span></div>
            <div id="eta-desglose" style="margin-top:16px;display:flex;flex-direction:column;gap:12px"></div>
          </div>
          <div class="tarjeta">                                   <!-- grafico historico -->
            <div class="kpi-lbl">Promedio histórico por operador (según origen)</div>
            <canvas id="eta-canvas" width="460" height="180" style="width:100%;margin-top:10px"></canvas>
          </div>
        </div>
      </div>
    </div>
  `

  // 2) Referencias a los controles.
  const btn = document.getElementById('eta-btn')                  // boton calcular
  const canvas = document.getElementById('eta-canvas')            // lienzo del grafico
  const ctx = canvas.getContext('2d')                             // contexto 2D

  // 3) Dibuja el grafico historico para el origen seleccionado.
  async function actualizarGrafico() {
    const origen = document.getElementById('eta-origen').value    // origen elegido
    try {
      const datos = await api.etaHistorico(origen)                // [{operador, dias_promedio}]
      ctx.clearRect(0, 0, canvas.width, canvas.height)            // limpia el lienzo
      if (!datos.length) return                                   // sin datos, no dibuja
      const maxY = Math.max(...datos.map(d => d.dias_promedio))    // valor maximo para escalar
      // Convierte cada operador en un punto (x uniforme, y proporcional al promedio).
      const puntos = datos.map((d, i) => ({
        x: 40 + i * ((canvas.width - 80) / Math.max(1, datos.length - 1)), // x distribuida
        y: canvas.height - 30 - (d.dias_promedio / maxY) * (canvas.height - 60), // y invertida (0 abajo)
      }))
      dibujarLineaCanvas(ctx, puntos, '#84D2C5')                  // dibuja la linea "dibujandose"
      // Etiquetas de operador bajo cada punto.
      ctx.fillStyle = '#B9AC9B'; ctx.font = '11px Manrope'         // estilo de texto
      datos.forEach((d, i) => ctx.fillText(d.operador, puntos[i].x - 18, canvas.height - 10)) // nombres
    } catch (e) {
      mostrarToast('No se pudo cargar el histórico.', 'error')     // aviso de error
    }
  }
  document.getElementById('eta-origen').onchange = actualizarGrafico // redibuja al cambiar origen
  actualizarGrafico()                                             // dibujo inicial

  // 4) Ejecuta la prediccion al pulsar el boton.
  btn.onclick = async () => {
    btn.disabled = true                                           // evita doble clic
    try {
      const fechaStr = document.getElementById('eta-fecha').value  // 'YYYY-MM-DD' o ''
      const mes = fechaStr ? Number(fechaStr.split('-')[1]) : 6     // mes del envio (por defecto junio)
      const datos = {                                              // arma el cuerpo para el sidecar
        origen: document.getElementById('eta-origen').value,
        via: document.getElementById('eta-via').value,
        aduana: document.getElementById('eta-aduana').value,
        operador: document.getElementById('eta-operador').value,
        carga: document.getElementById('eta-carga').value,
        mes,
      }
      const r = await api.predictEta(datos)                        // pide la prediccion
      animarNumero(document.getElementById('eta-total'), 0, Math.max(0.5, r.dias_total), { decimales: 1 }) // total

      // Desglose: transito, fondeo y aduana como barras que se llenan proporcionalmente al total.
      const total = Math.max(r.dias_total, 0.1)                    // evita division por cero
      const partes = [                                             // definicion de las 3 barras
        ['Tránsito', r.dias_transito],
        ['Fondeo en puerto', r.dias_fondeo],
        ['Nacionalización', r.dias_aduana],
      ]
      const cont = document.getElementById('eta-desglose')         // contenedor del desglose
      cont.innerHTML = partes.map(([nom]) => `                     <!-- una fila por parte -->
        <div>
          <div style="display:flex;justify-content:space-between">
            <span class="kpi-lbl">${nom}</span><span class="kpi-lbl bar-val">—</span>
          </div>
          <div class="barra"><span></span></div>
        </div>`).join('')
      // Anima cada barra y su valor numerico.
      cont.querySelectorAll('.barra > span').forEach((sp, i) => {   // recorre las barras
        animarBarra(sp, (partes[i][1] / total) * 100)              // ancho proporcional al total
      })
      cont.querySelectorAll('.bar-val').forEach((v, i) => {         // recorre los valores
        animarNumero(v, 0, partes[i][1], { decimales: 1, sufijo: ' d' }) // count-up con sufijo dias
      })

      if (estado.sesion.usuario) {                                  // si hay sesion iniciada
        mostrarToast('Predicción registrada en tu historial.')      // (el backend guarda via su logica)
      }
    } catch (e) {
      mostrarToast(e.message, 'error')                              // muestra el error del sidecar
    } finally {
      btn.disabled = false                                          // rehabilita el boton
    }
  }
}
```

- [ ] **Step 2: Añadir estilos compartidos de módulos a `styles.css`** (una sola vez; los reutilizan ETA/VUCE/Landed/Sesión)

```css
/* ---------- LAYOUT COMUN DE MODULOS ---------- */
.modulo { padding:22px; }                                       /* margen interno de cada modulo */
.dos-columnas { display:grid; grid-template-columns:4fr 6fr; gap:16px; align-items:start; } /* form + resultado */
@media (max-width:980px){ .dos-columnas { grid-template-columns:1fr; } } /* apila en ventanas angostas */
.bar-val { min-width:48px; text-align:right; }                  /* alinea los valores del desglose */
```

- [ ] **Step 3: Verificación**

Run `npm start` → Inicio → clic en "Predictor ETA". Expected: formulario glass + al calcular, el número grande hace count-up, aparecen 3 barras que se llenan (tránsito/fondeo/aduana) con sus días, y el gráfico histórico se dibuja como línea. Cambiar el origen redibuja el gráfico.

- [ ] **Step 4: Commit**

```bash
git add frontend/renderer/js/vistas/eta.js frontend/renderer/styles.css
git commit -m "feat(eta): modulo Predictor ETA con desglose animado y grafico Canvas"
```

---

### Task 16: `vistas/landed.js` (Landed Cost)

**Files:**
- Modify: `frontend/renderer/js/vistas/landed.js` (reemplaza el stub)

**Interfaces:**
- Consumes: `api.landedCost`, `animarNumero`, `animarBarra`, `mostrarToast`.
- Produces: `renderLanded(contenedor)`.

- [ ] **Step 1: Reemplazar `frontend/renderer/js/vistas/landed.js`**

```javascript
// landed.js — Modulo Landed Cost: inputs financieros -> desglose completo (CIF, arancel, tasa, IVA, total).

import { api } from '../api.js'                                   // llamadas al sidecar
import { animarNumero, animarBarra, mostrarToast } from '../motion.js' // animaciones

// Definicion de los campos numericos: [id, etiqueta, valor por defecto].
const CAMPOS = [
  ['fob', 'Valor FOB Mercancía ($)', 10000],                     // valor de la mercancia
  ['flete', 'Flete Internacional ($)', 1500],                    // flete
  ['seguro', 'Seguro Internacional ($)', 300],                   // seguro
  ['arancel', 'Alícuota Arancel (%)', 12],                       // arancel %
  ['tasa', 'Tasa de Servicio Aduanero (%)', 1],                  // tasa %
  ['iva', 'IVA Importación (%)', 16],                            // IVA %
  ['gastos', 'Gastos Locales/Portuarios ($)', 0],               // gastos locales
]

// Formatea un numero como moneda en formato venezolano.
function money(n) { return '$' + Number(n).toLocaleString('es-VE', { maximumFractionDigits: 2 }) }

export function renderLanded(contenedor) {
  // 1) Maquetacion: inputs a la izquierda, resultado a la derecha.
  contenedor.innerHTML = `
    <div class="modulo">
      <h1 class="titulo">Calculadora de Landed Cost</h1>
      <p class="subtitulo">Costo total puesto en almacén, con desglose impositivo.</p>
      <div class="dos-columnas">
        <div class="tarjeta">                                     <!-- formulario de inputs -->
          ${CAMPOS.map(([id, lbl, val]) => `
            <div class="campo"><label>${lbl}</label>
              <input type="number" id="lc-${id}" value="${val}" min="0" step="any" /></div>`).join('')}
          <button class="boton boton-primario" id="lc-btn" style="width:100%">Calcular Estructura</button>
        </div>
        <div class="tarjeta brilla">                              <!-- resultado con glow -->
          <div class="kpi-lbl">Total puesto en almacén</div>
          <div><span class="kpi-num" id="lc-total" style="font-size:44px">0</span></div>
          <div id="lc-desglose" style="margin-top:18px;display:flex;flex-direction:column;gap:14px"></div>
          <div id="lc-factor" class="pill" style="margin-top:16px">Factor de importación: —</div>
        </div>
      </div>
    </div>
  `

  // 2) Al pulsar Calcular: enviar los valores y animar el desglose.
  document.getElementById('lc-btn').onclick = async () => {
    // Lee cada input y lo convierte a numero (0 si esta vacio).
    const datos = {}                                              // objeto de parametros
    for (const [id] of CAMPOS) datos[id] = Number(document.getElementById('lc-' + id).value) || 0 // lee valores
    try {
      const r = await api.landedCost(datos)                       // pide el calculo al backend
      animarNumero(document.getElementById('lc-total'), 0, r.landed_cost, { decimales: 2 }) // total con count-up

      // Desglose: CIF, arancel, tasa, IVA. Cada barra se llena proporcional al total.
      const filas = [                                             // definicion de las filas del desglose
        ['Base CIF', r.cif, '#84D2C5'],
        ['Arancel', r.arancel, '#F4C77B'],
        ['Tasa aduanera', r.tasa_aduana, '#F3A87C'],
        ['IVA', r.iva, '#E68A6C'],
      ]
      const cont = document.getElementById('lc-desglose')         // contenedor del desglose
      cont.innerHTML = filas.map(([nom]) => `                     <!-- una fila por concepto -->
        <div>
          <div style="display:flex;justify-content:space-between">
            <span class="kpi-lbl">${nom}</span><span class="kpi-lbl lc-val">—</span>
          </div>
          <div class="barra"><span></span></div>
        </div>`).join('')
      cont.querySelectorAll('.barra > span').forEach((sp, i) => {   // anima anchos
        sp.style.background = filas[i][2]                          // color especifico por concepto
        animarBarra(sp, (filas[i][1] / r.landed_cost) * 100)       // proporcion respecto al total
      })
      cont.querySelectorAll('.lc-val').forEach((v, i) => {         // anima los montos
        const el = v                                              // referencia
        const inicio = performance.now()                          // (usamos animarNumero con formato moneda)
        animarNumero(el, 0, filas[i][1], { decimales: 2 })        // count-up numerico
        setTimeout(() => { el.textContent = money(filas[i][1]) }, 950) // al terminar, formatea como moneda
      })
      // Factor de importacion e incremento porcentual.
      document.getElementById('lc-factor').textContent =
        `Factor de importación: ${r.factor.toFixed(2)}×  ·  +${r.incremento_pct.toFixed(1)}%` // indicadores
    } catch (e) {
      mostrarToast(e.message, 'error')                             // muestra error del sidecar
    }
  }
}
```

- [ ] **Step 2: Verificación**

Run `npm start` → "Landed Cost" → Calcular. Expected: el total hace count-up; aparecen 4 barras de colores (CIF/arancel/tasa/IVA) que se llenan; el factor de importación y el % de incremento se muestran. Cambiar valores y recalcular actualiza todo.

- [ ] **Step 3: Commit**

```bash
git add frontend/renderer/js/vistas/landed.js
git commit -m "feat(landed): modulo Landed Cost con desglose animado usando calcular_landed_cost real"
```

---

### Task 17: `vistas/vuce.js` (Asesor VUCE + PDF)

**Files:**
- Modify: `frontend/renderer/js/vistas/vuce.js` (reemplaza el stub)

**Interfaces:**
- Consumes: `api.vuce`, `api.vucePdf`, `window.nativo.elegirRutaPdf`, `mostrarToast`, `estado.sesion`.
- Produces: `renderVuce(contenedor)`.

- [ ] **Step 1: Reemplazar `frontend/renderer/js/vistas/vuce.js`**

```javascript
// vuce.js — Modulo Asesor VUCE: consulta -> dictamen HTML del backend -> opcion de exportar a PDF.

import { api } from '../api.js'                                   // llamadas al sidecar
import { mostrarToast } from '../motion.js'                       // notificaciones
import { estado } from '../estado.js'                             // sesion

export function renderVuce(contenedor) {
  // 1) Maquetacion: tarjeta de consulta arriba, visor del dictamen abajo, boton de PDF.
  contenedor.innerHTML = `
    <div class="modulo">
      <h1 class="titulo">Asesor de Comercio Exterior (VUCE)</h1>
      <p class="subtitulo">Guía de procedimiento aduanero generada por IA.</p>
      <div class="tarjeta">
        <div class="campo"><label>Régimen Aduanero</label>
          <select id="vuce-regimen"><option>IMPORTACIÓN</option><option>EXPORTACIÓN</option></select></div>
        <div class="campo"><label>Describa la mercancía o partida arancelaria</label>
          <textarea id="vuce-consulta" rows="3" placeholder="Ej: café en grano verde para siembra"></textarea></div>
        <button class="boton boton-primario" id="vuce-btn">Generar Dictamen con IA</button>
      </div>
      <div class="tarjeta" id="vuce-visor" style="margin-top:14px;min-height:120px">
        <span class="kpi-lbl">El dictamen aparecerá aquí…</span>       <!-- placeholder inicial -->
      </div>
      <button class="boton" id="vuce-pdf" style="margin-top:12px" disabled>Descargar Reporte en PDF</button>
    </div>
  `

  let ultimoHtml = ''                                             // guarda el ultimo dictamen para el PDF
  const visor = document.getElementById('vuce-visor')            // contenedor del dictamen
  const btnPdf = document.getElementById('vuce-pdf')            // boton de exportacion

  // 2) Generar dictamen: llama al sidecar y renderiza el HTML devuelto.
  document.getElementById('vuce-btn').onclick = async () => {
    const consulta = document.getElementById('vuce-consulta').value.trim() // texto de la consulta
    if (!consulta) { mostrarToast('Escribe una consulta primero.', 'error'); return } // validacion
    const regimen = document.getElementById('vuce-regimen').value // regimen elegido
    visor.innerHTML = '<span class="kpi-lbl">Generando dictamen…</span>' // estado de carga
    try {
      const r = await api.vuce(regimen, consulta)                 // pide el dictamen
      ultimoHtml = r.html                                         // guarda el HTML para el PDF
      visor.innerHTML = r.html                                    // muestra el dictamen (HTML del backend)
      btnPdf.disabled = false                                     // habilita la descarga
      if (estado.sesion.usuario) mostrarToast('Consulta registrada en tu historial.') // aviso si hay sesion
    } catch (e) {
      visor.innerHTML = '<span class="kpi-lbl">No se pudo generar el dictamen.</span>' // estado de error
      mostrarToast(e.message, 'error')                            // detalle del error (ej. deps VUCE faltan)
    }
  }

  // 3) Exportar a PDF: pide la ruta con el dialogo nativo y manda a generar el archivo.
  btnPdf.onclick = async () => {
    if (!ultimoHtml) return                                       // nada que exportar
    const ruta = await window.nativo.elegirRutaPdf()              // dialogo nativo "guardar como"
    if (!ruta) return                                             // usuario cancelo
    try {
      await api.vucePdf({                                         // pide al backend generar el PDF
        regimen: document.getElementById('vuce-regimen').value,   // regimen actual
        consulta: document.getElementById('vuce-consulta').value.trim(), // consulta actual
        html: ultimoHtml,                                         // dictamen
        ruta,                                                     // ruta elegida
      })
      mostrarToast('PDF guardado correctamente.')                 // exito
    } catch (e) {
      mostrarToast(e.message, 'error')                            // error al generar
    }
  }
}
```

- [ ] **Step 2: Verificación**

Run `npm start` → "Asesor VUCE" → escribir una consulta → Generar. Expected: se muestra el dictamen HTML (con sus títulos en ámbar/teal). El botón PDF se habilita; al pulsarlo abre el diálogo nativo de Windows y guarda el archivo. Nota: si `sentence-transformers`/`faiss-cpu` no están instaladas, el toast mostrará el aviso 503 (comportamiento esperado de degradación).

- [ ] **Step 3: Commit**

```bash
git add frontend/renderer/js/vistas/vuce.js
git commit -m "feat(vuce): modulo Asesor VUCE con render de dictamen y exportacion PDF nativa"
```

---

### Task 18: `vistas/sesion.js` (login / registro)

**Files:**
- Modify: `frontend/renderer/js/vistas/sesion.js` (reemplaza el stub)

**Interfaces:**
- Consumes: `api.login`, `api.register`, `estado.entrar/salir`, `mostrarToast`.
- Produces: `renderSesion(contenedor)`.

- [ ] **Step 1: Reemplazar `frontend/renderer/js/vistas/sesion.js`**

```javascript
// sesion.js — Modulo Cuenta/Sesion: login y registro contra el backend (bcrypt + SQLite).

import { api } from '../api.js'                                   // llamadas al sidecar
import { estado } from '../estado.js'                             // estado de sesion en memoria
import { mostrarToast } from '../motion.js'                       // notificaciones

export function renderSesion(contenedor) {
  // Texto de estado segun haya o no sesion iniciada.
  const estadoTxt = estado.sesion.usuario                        // ¿hay usuario?
    ? `👤 Conectado como: ${estado.sesion.usuario} [${estado.sesion.rol}]` // conectado
    : '👤 Modo Invitado (acceso público limitado)'               // invitado

  // 1) Maquetacion: dos tarjetas (login y registro).
  contenedor.innerHTML = `
    <div class="modulo">
      <h1 class="titulo" id="sesion-estado">${estadoTxt}</h1>
      <div class="dos-columnas">
        <div class="tarjeta">                                     <!-- login -->
          <h3 class="titulo" style="font-size:18px">Ingresar al Sistema</h3>
          <div class="campo"><label>Usuario</label><input id="log-user" /></div>
          <div class="campo"><label>Contraseña</label><input id="log-pass" type="password" /></div>
          <button class="boton boton-primario" id="btn-login" style="width:100%">Iniciar Sesión</button>
        </div>
        <div class="tarjeta">                                     <!-- registro -->
          <h3 class="titulo" style="font-size:18px">Registrar Nuevo Operador</h3>
          <div class="campo"><label>Nombre de Usuario</label><input id="reg-user" /></div>
          <div class="campo"><label>Contraseña</label><input id="reg-pass" type="password" /></div>
          <div class="campo"><label>Empresa (opcional)</label><input id="reg-empresa" /></div>
          <button class="boton" id="btn-reg" style="width:100%">Crear Cuenta</button>
        </div>
      </div>
    </div>
  `

  // 2) Login: valida y llama al backend.
  document.getElementById('btn-login').onclick = async () => {
    const user = document.getElementById('log-user').value.trim() // usuario
    const pass = document.getElementById('log-pass').value.trim() // clave
    if (!user || !pass) { mostrarToast('Completa usuario y contraseña.', 'error'); return } // validacion
    try {
      const r = await api.login(user, pass)                       // verifica credenciales
      if (r.ok) {                                                 // acceso concedido
        estado.entrar(user, r.rol)                               // guarda la sesion
        document.getElementById('sesion-estado').textContent =    // actualiza el encabezado
          `👤 Conectado como: ${user} [${r.rol}]`
        mostrarToast(`¡Bienvenido, ${user}!`)                     // saludo
      } else {                                                   // credenciales invalidas
        mostrarToast('Credenciales incorrectas.', 'error')        // aviso
      }
    } catch (e) { mostrarToast(e.message, 'error') }             // error de red/servidor
  }

  // 3) Registro: valida longitud minima y llama al backend.
  document.getElementById('btn-reg').onclick = async () => {
    const user = document.getElementById('reg-user').value.trim() // usuario deseado
    const pass = document.getElementById('reg-pass').value.trim() // clave deseada
    const empresa = document.getElementById('reg-empresa').value.trim() // empresa opcional
    if (user.length < 4 || pass.length < 4) {                    // regla del backend original
      mostrarToast('Usuario y clave deben tener al menos 4 caracteres.', 'error'); return
    }
    try {
      const r = await api.register(user, pass, empresa)           // crea el usuario
      if (r.ok) mostrarToast(`Operador '${user}' creado con éxito.`) // exito
      else mostrarToast(r.msg, 'error')                          // error (ej. usuario ya existe)
    } catch (e) { mostrarToast(e.message, 'error') }             // error de red/servidor
  }
}
```

- [ ] **Step 2: Verificación**

Run `npm start` → "Cuenta / Acceso". Expected: dos tarjetas. Login con `admin` / `admin123` (usuario semilla) muestra "Conectado como: admin [Admin]". Registrar con usuario nuevo (≥4 chars) muestra éxito; repetir el mismo usuario muestra el error de duplicado. Tras iniciar sesión, en ETA/VUCE/Landed aparece el toast "registrado en tu historial".

- [ ] **Step 3: Commit**

```bash
git add frontend/renderer/js/vistas/sesion.js
git commit -m "feat(sesion): modulo de login y registro contra el backend"
```

---

## FASE 7 — Verificación integral

### Task 19: Recorrido E2E + script de humo del sidecar

**Files:**
- Create: `tests/humo_sidecar.py`

- [ ] **Step 1: Crear `tests/humo_sidecar.py`** (arranca el server real y golpea endpoints clave)

```python
# tests/humo_sidecar.py
# Prueba de humo: levanta el sidecar en un subproceso, espera a que este 'listo' y verifica endpoints reales.
import subprocess                                     # para lanzar uvicorn
import sys                                            # ejecutable de python actual
import time                                           # esperas
import os                                             # rutas
import urllib.request                                 # cliente HTTP simple
import urllib.error                                   # errores HTTP
import json                                           # parseo de respuestas

RAIZ = os.path.dirname(os.path.dirname(__file__))     # raiz del proyecto (carpeta de api_server.py)

def get(ruta):                                        # helper GET que devuelve dict
    with urllib.request.urlopen("http://127.0.0.1:8000" + ruta, timeout=5) as r:  # abre la URL
        return json.loads(r.read().decode())          # parsea el JSON

def post(ruta, cuerpo):                               # helper POST con JSON
    datos = json.dumps(cuerpo).encode()               # serializa el cuerpo
    req = urllib.request.Request("http://127.0.0.1:8000" + ruta, data=datos,       # arma la peticion
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:# ejecuta
        return json.loads(r.read().decode())          # devuelve el JSON

def main():                                           # rutina principal de humo
    proc = subprocess.Popen(                          # lanza el sidecar
        [sys.executable, "-m", "uvicorn", "api_server:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=RAIZ)                                      # cwd = raiz para que resuelvan los imports
    try:
        # Espera a que el motor este 'listo' (entrena el modelo real).
        for _ in range(60):                           # hasta ~60 s
            try:
                if get("/health").get("estado") == "listo":  # consulta salud
                    break                             # listo: continua
            except Exception:                         # aun no responde
                pass
            time.sleep(1)                             # espera 1 s
        else:
            raise SystemExit("El sidecar no llego a 'listo' a tiempo")  # timeout

        # Verifica landed-cost (math conocida).
        lc = post("/landed-cost", {"fob": 10000, "flete": 1500, "seguro": 300,
                                   "arancel": 12, "tasa": 1, "iva": 16, "gastos": 0})
        assert round(lc["cif"], 2) == 11800.0, "CIF incorrecto"        # valida CIF
        # Verifica predict-eta (con el modelo real ya entrenado).
        eta = post("/predict-eta", {"origen": "Miami", "via": "Marítimo", "aduana": "La Guaira",
                                    "operador": "Maersk", "carga": "Textil y Calzado", "mes": 6})
        assert "dias_total" in eta, "Falta dias_total"                 # valida estructura
        # Verifica dashboard-summary.
        ds = get("/dashboard-summary")                # KPIs
        assert ds["registros_historicos"] > 0, "Sin registros historicos"  # valida datos
        print("HUMO OK:", {"cif": lc["cif"], "eta_total": round(eta["dias_total"], 1),
                           "historicos": ds["registros_historicos"]})  # resumen
    finally:
        proc.terminate()                              # detiene el sidecar
        try: proc.wait(timeout=5)                     # espera cierre limpio
        except Exception: proc.kill()                 # fuerza si no cierra

if __name__ == "__main__":                            # ejecucion directa
    main()                                            # corre la prueba
```

- [ ] **Step 2: Correr el humo**

Run desde la raíz: `python tests/humo_sidecar.py`
Expected: imprime `HUMO OK: {...}` con CIF 11800.0, un ETA total y >0 históricos, y termina sin dejar procesos.

- [ ] **Step 3: Recorrido E2E manual (checklist)**

Run `npm start` desde `frontend/` y verificar:
- [ ] Splash con glow/barra → se revela el dashboard cuando el modelo está listo.
- [ ] Fondo vivo: partículas/estelas fluyen continuamente (sin parpadeos).
- [ ] Inicio: 4 KPIs hacen count-up; lista de aduanas cargada; gauge VUCE se llena; slider de Landed recalcula total en vivo.
- [ ] Navegación: los 5 iconos cambian de vista con fade y el icono activo se resalta.
- [ ] ETA: calcular anima el total + 3 barras de desglose; el gráfico se dibuja; cambiar origen lo redibuja.
- [ ] Landed: calcular anima total + 4 barras + factor/incremento.
- [ ] VUCE: genera dictamen; PDF abre diálogo nativo y guarda (o toast 503 si faltan deps VUCE).
- [ ] Sesión: login `admin`/`admin123` conecta; registro nuevo funciona; duplicado da error.
- [ ] Cerrar la app NO deja `python.exe`/uvicorn colgado (Administrador de tareas).
- [ ] Activar "reducir movimiento" en Windows → al reabrir, el motion se desactiva y todo sigue usable.

- [ ] **Step 4: Commit**

```bash
git add tests/humo_sidecar.py
git commit -m "test: prueba de humo del sidecar y checklist E2E"
```

---

## Notas finales

- **Ejecutar la app:** desde `frontend/`, `npm start` (arranca Electron, que lanza el sidecar). El backend Qt original sigue disponible con `python app.py`.
- **Dependencias VUCE:** si se quiere el Asesor VUCE plenamente funcional, instalar `sentence-transformers` y `faiss-cpu` (pesadas por torch). Sin ellas, el resto de la app funciona y VUCE avisa con un toast.
- **Fase futura (fuera de alcance):** empaquetado con electron-builder + PyInstaller para distribuir un instalador único.
