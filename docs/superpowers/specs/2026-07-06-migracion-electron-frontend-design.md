# Diseño — Migración del front-end a Electron (LogiIA)

- **Fecha:** 2026-07-06
- **Proyecto:** LogiIA — Sistema de gestión logística aduanera (Venezuela)
- **Alcance:** Reemplazar SOLO el front-end (hoy PySide6/Qt) por una app **Electron**. El **backend Python y la base de datos SQLite quedan intactos**.
- **Requisito transversal:** Todo el código nuevo va **comentado línea por línea en español** explicando qué hace cada cosa.

---

## 1. Objetivo

Migrar la interfaz de la app de escritorio de PySide6 a Electron para lograr un dashboard mucho más moderno, con la **estética del dashboard de las fotos de referencia** (domótica) aplicada al contenido logístico, e incorporar **motion graphics** (movimiento continuo, no popups ni zoom in/out).

El backend actual (`src/`), la base de datos (`data/logistica.db`), el histórico (`data/historico_envios.csv`) y el índice legal (`data/indice_legal.pkl`) **no se modifican**. La app Qt (`app.py`) se conserva como respaldo funcional.

---

## 2. Decisiones aprobadas

1. **Mapeo del diseño:** pantalla de **Inicio idéntica al layout de la foto** (hero + lista lateral derecha + 3 tarjetas inferiores) como resumen/overview, **más** los 4 módulos completos accesibles y rediseñados con el mismo estilo.
2. **Motion graphics elegidos:** (a) ambiente vivo de fondo, (b) datos que se animan, (c) micro-interacciones. Las transiciones entre vistas se mantienen **sutiles** (fade 200 ms). Sin popups ni zoom in/out. Se respeta `prefers-reduced-motion`.
3. **Paleta:** cálida y pastel ("puerto al atardecer") sobre lienzo oscuro cálido (ver §5).
4. **Arquitectura del puente:** **sidecar FastAPI** (`api_server.py`) que importa las funciones actuales sin tocarlas; Electron lo arranca como proceso hijo y el front lo consume por `fetch`.
5. **Front:** **HTML + CSS + JavaScript puro** (sin build/React), para que el código sea transparente y 100% comentable.

---

## 3. Arquitectura

### 3.1 Ciclo de vida (un solo doble-clic)

```
Electron abre
  └─ main.js lanza:  python api_server.py   (sidecar FastAPI, puerto 127.0.0.1:8000)
       └─ api_server importa las funciones de src/ (sin tocarlas)
            └─ entrena el modelo ETA UNA vez al arrancar y lo deja caliente en memoria
  └─ main.js hace polling a GET /health hasta 200 OK (splash "Iniciando motor logístico…", timeout ~20 s)
  └─ abre la ventana → el renderer (HTML/CSS/JS) llama por fetch a 127.0.0.1:8000
Al cerrar la app → main.js mata el proceso Python hijo (no queda nada colgado)
```

- El sidecar escucha **solo en `127.0.0.1`** (nunca expuesto a la red).
- Puerto por defecto `8000`; configurable por variable de entorno.

### 3.2 Estructura de archivos

```
Logistica aduanera/
├─ src/ ...............  BACKEND INTACTO (auth, predict_eta, vuce_ai, landed_cost, database, vuce_pdf, ...)
├─ data/ ..............  INTACTO (logistica.db, historico_envios.csv, indice_legal.pkl)
├─ app.py .............  se conserva (app Qt de respaldo)
├─ requirements.txt ...  se le AÑADEN: fastapi, uvicorn (sin quitar nada)
├─ api_server.py ......  NUEVO: capa fina FastAPI que expone src/ como JSON
└─ frontend/ ..........  NUEVO: la app Electron
   ├─ package.json ....  dependencias (electron) + scripts (start)
   ├─ main.js .........  proceso principal: crea ventana + lanza/vigila/mata el sidecar
   ├─ preload.js ......  contextBridge seguro (diálogo nativo "guardar PDF", info de arranque)
   └─ renderer/
      ├─ index.html ...  esqueleto único (una ventana; las vistas se conmutan por JS)
      ├─ styles.css ...  tokens de color, tema, tarjetas glass, motion (CSS)
      ├─ assets/ ......  fuente Manrope (woff2) empaquetada local + íconos SVG
      └─ js/
         ├─ api.js ....  TODAS las llamadas fetch al sidecar en un solo lugar
         ├─ router.js .  cambia entre vistas con fade sutil
         ├─ motion.js .  fondo vivo (canvas), count-up, gauges, dibujo de líneas
         ├─ estado.js .  sesión del usuario en memoria (usuario, rol)
         └─ vistas/ ...  inicio.js · eta.js · vuce.js · landed.js · sesion.js
```

### 3.3 Endpoints del sidecar (`api_server.py`)

Cada endpoint **solo llama a la función existente** y serializa el resultado a JSON. No hay lógica de negocio nueva en el server.

| Método | Ruta | Llama a | Entrada | Salida |
|---|---|---|---|---|
| GET | `/health` | — | — | `{estado: "listo"\|"entrenando"}` |
| POST | `/login` | `auth.verificar_usuario` | `{username, password}` | `{ok, id, rol}` |
| POST | `/register` | `auth.registrar_usuario` (+ update empresa) | `{username, password, empresa}` | `{ok, msg}` |
| POST | `/predict-eta` | modelos ETA `total/transito/fondeo/aduana` + encoders | `{origen, via, aduana, operador, carga, mes}` | `{dias_total, dias_transito, dias_fondeo, dias_aduana, distancia_km}` |
| GET | `/eta-historico` | pandas sobre `historico_envios.csv` | `?origen=` | `[{operador, dias_promedio}, ...]` |
| POST | `/vuce` | `vuce_ai.consultar_asesor_vuce` | `{regimen, consulta}` | `{html}` |
| POST | `/vuce-pdf` | `vuce_pdf.generar_pdf_dictamen` | `{regimen, consulta, html, ruta}` | `{ok, ruta}` |
| POST | `/landed-cost` | `landed_cost.calcular_landed_cost` | `{fob, flete, seguro, arancel, tasa, iva, gastos}` | desglose completo (CIF, arancel, tasa, IVA, total, factor, incremento_pct) |
| GET | `/dashboard-summary` | agregados de `historico_envios.csv` + `logistica.db` | — | KPIs de Inicio (en tránsito, en aduana, entregados, ETA promedio, por aduana) |

**Mejoras incluidas (sin tocar el back):** el front usa las funciones **completas** que `app.py` no aprovechaba: los 4 sub-modelos de ETA (desglose tránsito/fondeo/aduana además del total) y `landed_cost.calcular_landed_cost` (que hoy `app.py` recalcula a mano de forma simplificada).

### 3.4 Guardado del PDF

El diálogo "guardar como" se resuelve con el **diálogo nativo de Electron** (`dialog.showSaveDialog` en el proceso principal, expuesto vía `preload.js`). El renderer obtiene la ruta elegida y la envía a `POST /vuce-pdf`, que ejecuta `generar_pdf_dictamen(..., ruta)`.

---

## 4. Pantalla de Inicio (mapeo foto → logística)

```
┌────┬─────────────────────────────────┬──────────────────┐
│    │  HERO (mapa de ruta marítima)   │  RUTAS / ADUANAS │
│ N  │  ● Live   [En tránsito: 12]     │  · Puerto Cabello│
│ A  │           [En aduana: 4]        │  · La Guaira   ▸ │
│ V  │           [ETA prom: 18.3 d]    │  · Maiquetía     │
│    │           [Entregados: 340]     │  + NUEVA CONSULTA│
│    ├───────────────┬─────────────────┼──────────────────┤
│    │ PREDICTOR ETA │  LANDED COST    │  ASESOR VUCE     │
│ ⚙  │ ruta + gauge  │  slider dimmer  │  gauge circular  │
│    │ km·días·conf. │  total en vivo  │  viabilidad ▸    │
└────┴───────────────┴─────────────────┴──────────────────┘
```

| En la foto (domótica) | En el dashboard logístico |
|---|---|
| Barra lateral negra con íconos | **Inicio · Predictor ETA · Asesor VUCE · Landed Cost** + abajo **Cuenta/Sesión** |
| Hero (sala + pills 24°C/50%/…) | **Mapa de ruta** con envío que avanza + pills de **KPIs reales** (en tránsito, en aduana, ETA prom, entregados) desde `/dashboard-summary` + badge `● Live` |
| Lista "Rooms" (Bedroom, Kitchen…) | **Rutas / Aduanas** (Puerto Cabello, La Guaira, Maiquetía) con "N envíos", una resaltada, y **+ NUEVA CONSULTA** (equivalente a +ADD ROOM) |
| Tarjeta "Robot vacuum" + 3 stats | **Predictor ETA**: último cálculo + 3 stat-pills (**km · días tránsito · confianza**) + gauge; enlaza al módulo |
| Tarjeta "Smart Lamp" + slider | **Landed Cost**: slider tipo *dimmer* que mueve un parámetro (FOB o % arancel) y recalcula el **total en vivo**; enlaza al módulo |
| Tarjeta "Speakers" + disco girando | **Asesor VUCE**: gauge circular de **viabilidad/riesgo** + controles (nuevo dictamen · PDF); enlaza al módulo |

Si `logistica.db` (tabla `embarques`) está vacía, los KPIs se derivan del `historico_envios.csv` (que sí tiene datos) para que el Inicio nunca se vea vacío.

---

## 5. Sistema visual

### 5.1 Paleta ("puerto al atardecer")

**Lienzo (oscuro cálido):**
| Token | Hex | Uso |
|---|---|---|
| `--bg-0` | `#161311` | fondo más profundo |
| `--bg-1` | `#1E1A17` | base de paneles |
| `--bg-2` | `#26211D` | tarjetas (glass con blur) |
| `--sidebar` | `#100E0C` | barra lateral negra |

**Acentos pastel cálidos:**
| Token | Hex | Uso |
|---|---|---|
| `--ambar` | `#F4C77B` | primario (aduana/valor/botones clave) |
| `--durazno` | `#F3A87C` | secundario / resaltes |
| `--terracota` | `#E68A6C` | alertas / demorado |

**Frío marítimo (datos):**
| Token | Hex | Uso |
|---|---|---|
| `--teal` | `#84D2C5` | tránsito / cifras / líneas |
| `--petroleo` | `#5FB3AE` | gráficos secundarios |
| `--salvia` | `#AEC99C` | éxito / entregado |

**Texto y líneas:** `--tinta #F5EEE4`, `--tinta-suave #B9AC9B`, `--linea #3A332D`.

**Estados de envío:** En Tránsito → teal · En Aduana → ámbar · Entregado → salvia · Demorado → terracota.

### 5.2 Tipografía y forma

- **Manrope** (geométrica, cálida) empaquetada local (`assets/`), para titulares, cifras KPI y cuerpo.
- Esquinas muy redondeadas (`--r-card: 22px`, `--r-pill: 999px`).
- Tarjetas *glass*: `backdrop-filter: blur(20px)` + fondo semitransparente + borde 1px claro sutil + sombra suave + glow que respira.

---

## 6. Los 4 módulos

- **Predictor ETA** — formulario (origen, vía, aduana, operador, tipo de carga, fecha) en tarjeta glass; resultado con **desglose animado** (total + tránsito + fondeo + aduana) y **gráfico histórico por operador** dibujado en Canvas (reemplaza matplotlib; datos vía `/eta-historico`).
- **Asesor VUCE** — régimen + consulta → dictamen HTML renderizado; botón **Descargar PDF** (diálogo nativo → `generar_pdf_dictamen`). Guarda en historial si hay sesión.
- **Landed Cost** — inputs FOB/flete/seguro/arancel/tasa/IVA/gastos → **desglose completo** (CIF, arancel, tasa, IVA, factor, % incremento) con barras que se llenan. Guarda en historial si hay sesión.
- **Cuenta / Sesión** — login y registro (bcrypt) en dos tarjetas; el estado de sesión se guarda en `estado.js` y habilita el registro de operaciones en el historial.

---

## 7. Motion graphics

- **Ambiente vivo de fondo:** `<canvas>` a pantalla completa con `requestAnimationFrame` → líneas suaves tipo rutas marítimas que fluyen lento + gradiente cálido que se desplaza. Glow que **respira** en los bordes de tarjetas (keyframes de opacidad, muy lento).
- **Datos que se animan:** función `animarNumero()` (count-up con easing); barras/gauges que se llenan (transición de `width`/`transform` o `stroke-dashoffset`); líneas de gráfico que se dibujan (`stroke-dashoffset`); gauge circular que gira al cargar.
- **Micro-interacciones:** tarjetas se elevan + glow al hover; botones con subrayado que crece (`::after` con `scaleX`); sliders y toggles que se deslizan con `cubic-bezier`.
- **Transición de vista:** fade 200 ms. Sin scale/zoom de aparición ni popups.
- **Accesibilidad:** todo el motion se reduce/desactiva con `@media (prefers-reduced-motion: reduce)`.

---

## 8. Manejo de errores y estados

- **Arranque:** splash con animación mientras el sidecar entrena; timeout ~20 s → si no responde, aviso con botón "Reintentar".
- **Llamadas fetch:** cada una con try/catch; error → *toast* discreto que se desliza (sin popup/zoom). Estados de carga con *shimmer*/skeleton.
- **Validaciones en JS** antes de llamar (campos vacíos, usuario/clave ≥ 4 caracteres, números válidos).
- **Cierre:** al cerrar la ventana o la app, el proceso Python hijo se mata (evitar procesos huérfanos en Windows).
- **Backend Python:** ya trae try/except; el server traduce fallos a `{ok:false, error}` con código HTTP apropiado.

---

## 9. Pruebas

- **Humo del sidecar:** script que arranca `api_server.py`, espera `/health` y hace una llamada de ejemplo a `/landed-cost` y `/predict-eta` verificando el JSON.
- **Recorrido manual guiado** por cada módulo (checklist en el plan de implementación).
- **Verificación E2E final:** arrancar la app Electron real y recorrer Inicio + los 4 módulos, confirmando datos reales del backend y el motion.

---

## 10. Fuera de alcance (YAGNI por ahora)

- Empaquetado/instalador (electron-builder + PyInstaller del sidecar) — se documenta como fase futura; el objetivo de esta migración es correr en desarrollo (`npm start` lanza Electron, que lanza el sidecar).
- Cambios en el esquema de la base de datos o en la lógica del backend.
- Variante de tema claro (se puede añadir después; se implementa primero el oscuro cálido).

---

## 11. Notas de entorno

- El directorio **no es un repositorio git** todavía. El commit del documento de diseño queda pendiente hasta hacer `git init` (opcional; se ofrece al usuario).
- Plataforma: Windows 11. El manejo del proceso hijo (matar el sidecar al cerrar) debe contemplar el árbol de procesos de Windows.
