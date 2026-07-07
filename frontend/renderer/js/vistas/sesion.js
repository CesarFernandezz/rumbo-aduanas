// sesion.js — Cuenta / Sesion: pantalla de autenticacion rediseñada (panel de marca + formulario con pestañas).
// Un solo formulario que alterna entre "Iniciar sesion" y "Crear cuenta". Backend intacto (bcrypt + SQLite).

import { api } from '../api.js'                                   // llamadas al sidecar
import { estado } from '../estado.js'                             // estado de sesion en memoria
import { mostrarToast } from '../motion.js'                       // notificaciones
import { iconos } from '../icons.js'                              // iconos SVG

// Construye un campo con icono a la izquierda (y opcionalmente un boton "ojo" para ver la contraseña).
function campo(id, etiqueta, tipo, icono, conOjo = false) {
  return `
    <div class="campo">
      <label>${etiqueta}</label>
      <div class="campo-icono">
        ${icono}                                                 <!-- icono decorativo del campo -->
        <input id="${id}" type="${tipo}" autocomplete="off" />   <!-- control de entrada -->
        ${conOjo ? `<button type="button" class="ojo" data-target="${id}" title="Mostrar u ocultar">${iconos.eye}</button>` : ''}
      </div>
    </div>`
}

export function renderSesion(contenedor) {
  // 1) Maquetacion: tarjeta partida (marca a la izquierda, formulario a la derecha).
  contenedor.innerHTML = `
    <div class="auth-wrap">                                       <!-- centra la tarjeta en la pantalla -->
      <div class="tarjeta auth-card">
        <aside class="auth-brand">                                <!-- panel de marca -->
          <span class="auth-badge">${iconos.contenedor}</span>    <!-- isotipo Rumbo -->
          <div>
            <div class="auth-marca">Rumbo</div>                   <!-- nombre -->
            <div class="kpi-lbl">Gestión aduanera inteligente</div> <!-- lema -->
          </div>
          <ul class="auth-features">                              <!-- que ofrece la app -->
            <li>${iconos.eta}<span>Predicción de ETA con IA</span></li>
            <li>${iconos.vuce}<span>Dictámenes VUCE al instante</span></li>
            <li>${iconos.landed}<span>Cálculo de landed cost</span></li>
          </ul>
          <div class="kpi-lbl auth-estado" id="auth-estado"></div> <!-- estado de sesion actual -->
        </aside>

        <section class="auth-form">                               <!-- panel del formulario -->
          <h2 class="titulo" id="auth-titulo">Bienvenido de nuevo</h2>
          <p class="subtitulo" id="auth-sub">Ingresa para enlazar tu actividad al historial.</p>
          <div class="seg">                                       <!-- pestañas iniciar sesion / crear cuenta -->
            <button id="seg-login" class="activo">Iniciar sesión</button>
            <button id="seg-reg">Crear cuenta</button>
          </div>
          <div id="auth-campos"></div>                            <!-- aqui se pintan los campos segun el modo -->
          <button class="boton boton-primario" id="auth-submit" style="width:100%;margin-top:6px">Iniciar sesión</button>
        </section>
      </div>
    </div>
  `

  let modo = 'login'                                              // modo actual: 'login' o 'reg'

  // 2) Pinta los campos segun el modo y conecta los botones de "ojo".
  function pintarCampos(m) {
    const cont = document.getElementById('auth-campos')           // contenedor de campos
    if (m === 'login') {                                          // modo iniciar sesion
      cont.innerHTML = campo('log-user', 'Usuario', 'text', iconos.cuenta)
                     + campo('log-pass', 'Contraseña', 'password', iconos.lock, true)
    } else {                                                      // modo crear cuenta
      cont.innerHTML = campo('reg-user', 'Nombre de usuario', 'text', iconos.cuenta)
                     + campo('reg-pass', 'Contraseña', 'password', iconos.lock, true)
                     + campo('reg-empresa', 'Empresa (opcional)', 'text', iconos.empresa)
    }
    cont.classList.remove('vista-entrando'); void cont.offsetWidth; cont.classList.add('vista-entrando') // fade sutil
    cont.querySelectorAll('.ojo').forEach(b => b.onclick = () => { // alterna ver/ocultar contraseña
      const inp = document.getElementById(b.dataset.target)       // input asociado
      const ver = inp.type === 'password'                         // ¿esta oculta?
      inp.type = ver ? 'text' : 'password'                        // alterna el tipo
      b.innerHTML = ver ? iconos.eyeOff : iconos.eye              // alterna el icono del ojo
    })
  }

  // 3) Cambia de modo (actualiza pestañas, textos y campos).
  function setModo(m) {
    modo = m                                                      // guarda el modo
    document.getElementById('seg-login').classList.toggle('activo', m === 'login') // resalta pestaña
    document.getElementById('seg-reg').classList.toggle('activo', m === 'reg')
    document.getElementById('auth-titulo').textContent = m === 'login' ? 'Bienvenido de nuevo' : 'Crea tu cuenta'
    document.getElementById('auth-sub').textContent = m === 'login'
      ? 'Ingresa para enlazar tu actividad al historial.'
      : 'Regístrate como operador para guardar tu historial.'
    document.getElementById('auth-submit').textContent = m === 'login' ? 'Iniciar sesión' : 'Crear cuenta'
    pintarCampos(m)                                               // repinta los campos del nuevo modo
  }

  // 4) Muestra el estado de sesion actual (y permite cerrar sesion).
  function pintarEstado() {
    const el = document.getElementById('auth-estado')             // etiqueta de estado
    if (estado.sesion.usuario) {                                  // hay sesion iniciada
      el.innerHTML = `Conectado como <b>${estado.sesion.usuario}</b> [${estado.sesion.rol}] · <a href="#" id="logout">Cerrar sesión</a>`
      document.getElementById('logout').onclick = (e) => {        // accion de cerrar sesion
        e.preventDefault(); estado.salir(); pintarEstado(); mostrarToast('Sesión cerrada.')
      }
    } else {                                                      // modo invitado
      el.textContent = 'Actualmente en modo invitado (acceso público limitado).'
    }
  }

  // 5) Conecta las pestañas y el boton de enviar.
  document.getElementById('seg-login').onclick = () => setModo('login') // pestaña iniciar sesion
  document.getElementById('seg-reg').onclick = () => setModo('reg')     // pestaña crear cuenta

  document.getElementById('auth-submit').onclick = async () => {  // enviar segun el modo
    if (modo === 'login') {                                       // ---- INICIAR SESION ----
      const user = document.getElementById('log-user').value.trim() // usuario
      const pass = document.getElementById('log-pass').value.trim() // clave
      if (!user || !pass) { mostrarToast('Completa usuario y contraseña.', 'error'); return } // validacion
      try {
        const r = await api.login(user, pass)                     // verifica credenciales
        if (r.ok) { estado.entrar(user, r.rol); pintarEstado(); mostrarToast(`¡Bienvenido, ${user}!`) } // exito
        else mostrarToast('Credenciales incorrectas.', 'error')   // credenciales invalidas
      } catch (e) { mostrarToast(e.message, 'error') }            // error de red/servidor
    } else {                                                      // ---- CREAR CUENTA ----
      const user = document.getElementById('reg-user').value.trim()       // usuario deseado
      const pass = document.getElementById('reg-pass').value.trim()       // clave deseada
      const empresa = document.getElementById('reg-empresa').value.trim() // empresa opcional
      if (user.length < 4 || pass.length < 4) {                   // regla del backend original
        mostrarToast('Usuario y clave deben tener al menos 4 caracteres.', 'error'); return
      }
      try {
        const r = await api.register(user, pass, empresa)         // crea el usuario
        if (r.ok) { mostrarToast(`Operador '${user}' creado con éxito. Ya puedes iniciar sesión.`); setModo('login') } // exito -> pasa a login
        else mostrarToast(r.msg, 'error')                         // error (ej. usuario ya existe)
      } catch (e) { mostrarToast(e.message, 'error') }            // error de red/servidor
    }
  }

  // 6) Estado inicial: modo login + estado de sesion.
  setModo('login')                                                // arranca en iniciar sesion
  pintarEstado()                                                  // muestra el estado actual
}
