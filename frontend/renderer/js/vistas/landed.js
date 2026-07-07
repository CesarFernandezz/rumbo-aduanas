// landed.js — Modulo Landed Cost: inputs financieros -> desglose completo (CIF, arancel, tasa, IVA, total).

import { api } from '../api.js'                                   // llamadas al sidecar
import { animarNumero, animarBarra, mostrarToast } from '../motion.js' // animaciones
import { estado } from '../estado.js'                             // sesion (para guardar en historial)

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
            <div class="campo"><label for="lc-${id}">${lbl}</label>
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
    datos.usuario = estado.sesion.usuario                         // usuario activo (o null): el backend lo guarda en historial
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
        animarBarra(sp, r.landed_cost > 0 ? (filas[i][1] / r.landed_cost) * 100 : 0) // guarda division por cero
      })
      cont.querySelectorAll('.lc-val').forEach((v, i) => {         // anima los montos
        const el = v                                              // referencia
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
