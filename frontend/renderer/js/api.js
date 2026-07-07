// api.js — Unico lugar donde el front habla con el sidecar Python. Centraliza fetch, JSON y errores.

const BASE = 'http://127.0.0.1:8000'                 // el sidecar escucha aqui (mismo puerto que main.js)

// Token de autenticacion (lo entrega el proceso principal via preload). Se pide una sola vez y se cachea.
let _token = null
async function obtenerToken() {
  if (_token) return _token                          // ya lo tenemos en cache
  try { _token = await window.nativo.obtenerToken() } // lo pedimos al proceso principal
  catch (e) { _token = null }                        // fuera de Electron (dev/test) no hay token; el sidecar tampoco lo exige
  return _token
}

// Helper interno: hace una peticion, valida el codigo HTTP y devuelve el JSON.
async function pedir(ruta, opciones = {}) {
  const token = await obtenerToken()                 // obtiene el token (o null)
  const r = await fetch(BASE + ruta, {               // realiza la peticion
    ...opciones,                                     // metodo y cuerpo si aplican
    headers: {                                       // cabeceras: JSON + token de autenticacion
      'Content-Type': 'application/json',
      ...(token ? { 'X-Rumbo-Token': token } : {}),  // solo se envia si existe
      ...(opciones.headers || {}),                   // permite sobreescribir si hiciera falta
    },
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
  vuce: (regimen, consulta, usuario) => postJson('/vuce', { regimen, consulta, usuario }), // dictamen legal (+usuario para historial)
  vucePdf: (datos) => postJson('/vuce-pdf', datos), // exportar dictamen a PDF (datos={regimen,consulta,html,ruta})
  landedCost: (datos) => postJson('/landed-cost', datos), // calculadora financiera
  dashboardSummary: () => pedir('/dashboard-summary'), // KPIs de la pantalla de Inicio
  historial: (usuario, opts = {}) => pedir('/historial?usuario=' + encodeURIComponent(usuario)  // operaciones reales del usuario
    + (opts.limite ? '&limite=' + opts.limite : '')
    + (opts.modulo ? '&modulo=' + encodeURIComponent(opts.modulo) : '')),
}
