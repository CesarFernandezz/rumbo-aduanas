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
