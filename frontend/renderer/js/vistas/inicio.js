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
