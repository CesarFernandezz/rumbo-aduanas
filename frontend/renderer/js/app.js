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
