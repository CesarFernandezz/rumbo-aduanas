# Rumbo — Gestión Aduanera Inteligente

Aplicación de escritorio (**Electron**) para logística y comercio exterior en Venezuela. El front‑end moderno consume un **backend en Python** (intacto) a través de un pequeño servidor local (*sidecar*) **FastAPI**.

## ¿Qué hace?

- **Predictor ETA** — estima el tiempo de arribo de un embarque con un modelo de *Machine Learning* (Gradient Boosting), con desglose de tránsito, fondeo y nacionalización, y gráfico histórico por operador.
- **Asesor VUCE** — genera una guía/dictamen de procedimiento aduanero con IA y permite exportarlo a **PDF**.
- **Landed Cost** — calculadora financiera del costo puesto en almacén (CIF, arancel, tasa, IVA, factor de importación).
- **Cuenta / Sesión** — registro e inicio de sesión de operadores (contraseñas con `bcrypt`, base de datos SQLite).
- **Inicio** — panel con indicadores **reales** del histórico (5.000+ envíos): volumen mensual, ETA promedio, distribución por aduana, puntualidad, etc.

## Arquitectura

```
Electron (frontend/)  ──lanza──►  api_server.py  (sidecar FastAPI, 127.0.0.1:8000)
   HTML/CSS/JS puro                    └─ importa y expone las funciones de src/ como JSON
   (renderer)          ◄──fetch───           (backend Python + SQLite, sin modificar)
```

El proceso principal de Electron arranca el sidecar automáticamente al abrir la app y lo detiene al cerrarla.

## Requisitos

| Herramienta | Versión recomendada |
|---|---|
| **Python** | 3.11 o superior (probado en 3.13) |
| **Node.js** | 18 o superior (probado en 22) |
| **npm** | 9 o superior |
| Sistema | Windows 10/11 (también funciona en macOS/Linux) |

## Instalación

Clona el repositorio y, desde la carpeta raíz del proyecto:

### 1) Dependencias de Python (backend + sidecar)

```bash
python -m pip install -r requirements.txt
```

> **Opcional (Asesor VUCE con RAG legal):** el módulo VUCE puede usar embeddings para buscar en gacetas. Son dependencias pesadas (traen PyTorch) y la app **arranca y funciona sin ellas** (el Asesor devuelve una guía estructurada; avisa si faltan). Para habilitarlo:
> ```bash
> python -m pip install -r requirements-vuce-rag.txt
> ```
>
> **Legado:** para correr la app de escritorio original en PySide6/Qt (`app.py`), instala además `requirements-legacy-qt.txt`. La app Electron no lo necesita.

### 2) Dependencias del front‑end (Electron)

```bash
cd frontend
npm install
```

### 3) Configuración (opcional)

> **Nota:** en su estado actual el Asesor VUCE genera una guía estructurada localmente (no llama a un LLM externo), así que **no necesitas ninguna clave para usar la app**. El archivo `.env` / `GEMINI_API_KEY` solo hace falta si más adelante conectas un modelo de IA generativa.

Si conectas un proveedor de IA, crea un archivo `.env` en la raíz con tu propia clave:

```env
GEMINI_API_KEY=tu_clave_aqui
```

> ⚠️ **No subas tu `.env` al repositorio** (ya está en `.gitignore`). Usa tu propia clave.

## Ejecutar la app

Desde la carpeta `frontend/`:

```bash
npm start
```

Esto abre la ventana de **Rumbo**. Verás un *splash* mientras el modelo de ML se entrena por primera vez (unos segundos); luego aparece el dashboard.

> La app lanza el sidecar de Python por ti; no necesitas iniciarlo aparte.

## Pruebas

Desde la **raíz del proyecto**:

```bash
# Pruebas unitarias/integración del sidecar (rápidas, no entrenan el modelo real)
python -m pytest tests/test_api_server.py -v

# Prueba de humo (levanta el sidecar real, entrena el modelo y verifica endpoints)
python tests/humo_sidecar.py
```

## Estructura del proyecto

```
.
├─ api_server.py            # Sidecar FastAPI: expone src/ como API JSON (no tiene lógica nueva)
├─ app.py                   # App original en PySide6/Qt (se conserva como respaldo)
├─ src/                     # Backend Python (ML, IA, PDF, auth, base de datos) — intacto
├─ data/                    # SQLite, histórico CSV, índice legal
├─ tests/                   # pytest del sidecar + prueba de humo
└─ frontend/                # App Electron
   ├─ main.js               #   proceso principal (lanza/mata el sidecar, ventana, icono)
   ├─ preload.js            #   puente seguro (diálogo nativo para guardar PDF)
   └─ renderer/             #   interfaz (HTML/CSS/JS)
      ├─ index.html
      ├─ styles.css
      ├─ assets/            #     fuente e icono de la app
      └─ js/                #     api.js, router.js, motion.js, icons.js, vistas/…
```

## Notas

- **La app Qt original sigue disponible**: `python app.py` (requiere PySide6). La versión Electron es el nuevo front‑end.
- El sidecar escucha **solo en `127.0.0.1`** (no se expone a la red).
- En Windows, al cerrar la app se termina el árbol de procesos del sidecar automáticamente.

---

Hecho migrando el front a Electron con motion graphics, sobre el backend Python existente.
