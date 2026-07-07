// inicio.js — Pantalla principal con el layout de la foto, mapeado a DATOS REALES del historico.
// Estructura: HERO (KPIs reales + mapa) | lista RUTAS/ADUANAS | 3 tarjetas (ETA, Landed, VUCE).

import { api } from '../api.js'                               // datos del sidecar
import { animarNumero, animarGauge, mostrarToast, movimientoReducido } from '../motion.js' // animaciones
import { router } from '../router.js'                         // para enlazar a los modulos
import { iconos } from '../icons.js'                          // iconos SVG (reemplazan emojis)

// Dibuja un grafico de barras REAL: volumen de envios por mes (crecen con animacion suave).
function dibujarBarrasMes(canvas, datos) {
  const ctx = canvas.getContext('2d')                         // contexto 2D del lienzo
  canvas.width = canvas.clientWidth || 700                    // ancho real segun el layout (nitidez 1:1)
  canvas.height = canvas.clientHeight || 230                  // alto real segun el layout (llena el HERO)
  const W = canvas.width, H = canvas.height                   // dimensiones de dibujo
  const meses = ['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'] // iniciales de los meses
  const maxV = Math.max(...datos.map(d => d.envios), 1)       // valor maximo para escalar (evita /0)
  const padL = 6, padR = 6, padT = 12, padB = 24             // margenes internos
  const areaW = W - padL - padR, areaH = H - padT - padB      // area util del grafico
  const paso = areaW / datos.length                          // ancho asignado a cada mes
  const bw = paso * 0.58                                      // ancho visible de cada barra
  const dur = movimientoReducido() ? 0 : 850                 // duracion de la animacion (0 si se reduce el motion)
  const inicio = performance.now()                           // marca de tiempo inicial
  function frame(ahora) {                                     // dibuja un fotograma de la animacion de crecimiento
    const p = dur === 0 ? 1 : Math.min(1, (ahora - inicio) / dur) // progreso 0..1
    const e = 1 - Math.pow(1 - p, 3)                         // easing easeOutCubic (desacelera al final)
    ctx.clearRect(0, 0, W, H)                                // limpia el lienzo
    for (let i = 0; i < datos.length; i++) {                 // recorre cada mes
      const x = padL + i * paso + (paso - bw) / 2            // posicion horizontal de la barra
      const alturaMax = (datos[i].envios / maxV) * areaH     // altura final segun el volumen
      const h = alturaMax * e                                // altura animada en este fotograma
      const y = padT + areaH - h                             // borde superior de la barra
      const grad = ctx.createLinearGradient(0, y, 0, padT + areaH) // degradado calido vertical
      grad.addColorStop(0, '#F4C77B'); grad.addColorStop(1, '#F3A87C')
      ctx.fillStyle = grad                                   // aplica el degradado
      const r = Math.min(4, bw / 2)                          // radio de las esquinas superiores
      ctx.beginPath(); ctx.roundRect(x, y, bw, h, [r, r, 0, 0]); ctx.fill() // barra con esquinas redondeadas
      ctx.fillStyle = '#B9AC9B'; ctx.font = '11px Manrope'; ctx.textAlign = 'center' // estilo de etiqueta
      ctx.fillText(meses[i], x + bw / 2, H - 7)              // etiqueta del mes bajo la barra
    }
    if (p < 1) requestAnimationFrame(frame)                  // continua hasta completar la animacion
  }
  requestAnimationFrame(frame)                               // arranca el dibujo
}

// Guarda el listener de resize activo para poder retirarlo al recargar la vista (evita fugas al navegar).
let _resizeInicio = null

export async function renderInicio(contenedor) {
  if (_resizeInicio) { window.removeEventListener('resize', _resizeInicio); _resizeInicio = null } // limpia el de una carga previa
  // 1) Estructura HTML del dashboard. Las cifras arrancan en 0 y se animan con datos reales al cargar.
  contenedor.innerHTML = `
    <div class="inicio-grid">                                <!-- rejilla principal -->
      <section class="tarjeta hero">                          <!-- panel HERO grande -->
        <div class="kpis">                                    <!-- fila de KPIs (datos reales del CSV) -->
          <div><div class="kpi-num" id="kpi-hist">0</div><div class="kpi-lbl">Envíos analizados</div></div>
          <div><div class="kpi-num" id="kpi-eta">0</div><div class="kpi-lbl">ETA prom (días)</div></div>
          <div><div class="kpi-num" id="kpi-transito">0</div><div class="kpi-lbl">Tránsito prom (días)</div></div>
          <div><div class="kpi-num" id="kpi-aduana">0</div><div class="kpi-lbl">Aduana prom (días)</div></div>
        </div>
        <div class="hero-chart">                              <!-- grafico REAL de volumen mensual -->
          <div class="kpi-lbl">Volumen de envíos por mes</div>
          <canvas id="hero-canvas"></canvas>                  <!-- barras dibujadas con datos reales -->
        </div>
      </section>

      <aside class="tarjeta rutas">                           <!-- lista lateral derecha (como "Rooms") -->
        <h3 class="titulo" style="font-size:18px">Rutas / Aduanas</h3>
        <div id="lista-aduanas"></div>                        <!-- se llena con las aduanas (datos reales) -->
        <button class="boton boton-primario" id="btn-nueva" style="width:100%;margin-top:12px">${iconos.mas} Nueva consulta</button>
      </aside>

      <div class="cards">                                     <!-- fila inferior: contiene las 3 tarjetas -->
        <button class="tarjeta mini" id="card-eta">           <!-- tarjeta inferior izquierda: ETA -->
          <div class="mini-top"><span>Predictor ETA</span></div>
          <div class="mini-cifra"><span class="kpi-num" id="mini-eta">0</span><span class="kpi-lbl"> días prom.</span></div>
          <div class="mini-pills">
            <span class="pill">Op. más rápido: <b id="op-rapido">—</b></span>
          </div>
        </button>

        <div class="tarjeta mini" role="button" tabindex="0" id="card-landed"> <!-- div (no button): contiene un input, invalido anidar interactivos en un button -->
          <div class="mini-top"><span>Landed Cost</span></div>
          <div class="mini-cifra"><span class="kpi-lbl">Simulación (arancel 12% · IVA 16%)</span></div>
          <input type="range" min="1000" max="50000" value="10000" class="slider" id="mini-slider" />
          <div class="mini-cifra"><span class="kpi-num" id="mini-total">0</span><span class="kpi-lbl"> total puesto en almacén</span></div>
        </div>

        <button class="tarjeta mini" id="card-vuce">          <!-- tarjeta inferior derecha: VUCE (gauge) -->
          <div class="mini-top"><span>Puntualidad histórica</span></div>
          <svg viewBox="0 0 120 120" class="gauge" width="110" height="110"> <!-- gauge circular -->
            <circle class="gauge-track" cx="60" cy="60" r="50"></circle>     <!-- aro de fondo -->
            <circle class="gauge-fill" cx="60" cy="60" r="50" id="gauge-vuce"
                    transform="rotate(-90 60 60)"></circle>                  <!-- arco que se llena -->
          </svg>
          <div class="kpi-lbl" style="text-align:center">Envíos dentro del ETA promedio</div>
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
  document.getElementById('btn-nueva').onclick = () => router.ir('vuce')     // "Nueva consulta" -> VUCE

  // 3) Slider tipo "dimmer": calcula el landed cost con el BACKEND REAL (no una formula falsa del cliente).
  const slider = document.getElementById('mini-slider')                      // control deslizante
  const elTotal = document.getElementById('mini-total')                      // cifra del total
  let temporizador = null                                                    // para "debounce" del slider
  async function recalcularMini() {
    const fob = Number(slider.value)                                         // valor FOB elegido
    try {
      // Flete/seguro tipicos (10% y 1% del FOB) enviados a la funcion real calcular_landed_cost del backend.
      const r = await api.landedCost({ fob, flete: fob * 0.10, seguro: fob * 0.01, arancel: 12, tasa: 1, iva: 16, gastos: 0 })
      elTotal.textContent = '$' + Math.round(r.landed_cost).toLocaleString('es-VE') // muestra el total real
    } catch (e) { /* si el sidecar falla, no rompemos el Inicio */ }
  }
  slider.oninput = () => { clearTimeout(temporizador); temporizador = setTimeout(recalcularMini, 180) } // debounce
  recalcularMini()                                                           // calculo inicial

  // 4) Traer los KPIs REALES del sidecar y animarlos (count-up) + llenar la lista de aduanas + gauge real.
  try {
    const d = await api.dashboardSummary()                                   // pide el resumen (agregados del CSV)
    animarNumero(document.getElementById('kpi-hist'), 0, d.registros_historicos)               // total analizados
    animarNumero(document.getElementById('kpi-eta'), 0, d.eta_promedio, { decimales: 1 })       // ETA promedio
    animarNumero(document.getElementById('kpi-transito'), 0, d.dias_transito_promedio, { decimales: 1 }) // transito
    animarNumero(document.getElementById('kpi-aduana'), 0, d.dias_aduana_promedio, { decimales: 1 })     // aduana
    animarNumero(document.getElementById('mini-eta'), 0, d.eta_promedio, { decimales: 1 })      // ETA en tarjeta
    document.getElementById('op-rapido').textContent = d.operador_mas_rapido                     // operador real

    // Lista de aduanas (como la lista "Rooms"): nombre + N envios reales, con chevron, la primera resaltada.
    const cont = document.getElementById('lista-aduanas')                    // contenedor de la lista
    d.por_aduana.forEach((a, i) => {                                         // recorre cada aduana (dato real)
      const fila = document.createElement('div')                            // fila de la lista
      fila.className = 'aduana-fila' + (i === 0 ? ' activa' : '')            // resalta la primera
      fila.innerHTML = `<span>${a.aduana}</span><span class="kpi-lbl" style="display:inline-flex;align-items:center;gap:4px">${a.envios} envíos ${iconos.chevron}</span>`
      cont.appendChild(fila)                                                 // agrega a la lista
    })

    // Gauge de puntualidad REAL: % de envios cuyo tiempo real quedo dentro del ETA promedio.
    animarGauge(document.getElementById('gauge-vuce'), 50, d.pct_a_tiempo)   // llena el aro con el % real

    // Grafico del HERO: barras reales de volumen de envios por mes.
    const canvasHero = document.getElementById('hero-canvas')               // lienzo del grafico
    dibujarBarrasMes(canvasHero, d.por_mes)                                 // dibuja las 12 barras animadas
    // Redibuja el grafico (con "debounce") cuando cambia el tamaño de la ventana, para que no se vea borroso.
    let tRedibujo = null
    _resizeInicio = () => { clearTimeout(tRedibujo); tRedibujo = setTimeout(() => dibujarBarrasMes(canvasHero, d.por_mes), 150) }
    window.addEventListener('resize', _resizeInicio)                         // escucha el redimensionado
  } catch (e) {                                                              // si el sidecar fallo
    mostrarToast('No se pudieron cargar los indicadores.', 'error')          // avisa sin romper la vista
  }
}
