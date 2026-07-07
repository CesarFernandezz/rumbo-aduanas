// sesion.js — Modulo Cuenta/Sesion: login y registro contra el backend (bcrypt + SQLite).

import { api } from '../api.js'                                   // llamadas al sidecar
import { estado } from '../estado.js'                             // estado de sesion en memoria
import { mostrarToast } from '../motion.js'                       // notificaciones
import { iconos } from '../icons.js'                              // icono SVG de usuario

export function renderSesion(contenedor) {
  // Texto de estado segun haya o no sesion iniciada (el icono va aparte, no como emoji).
  const estadoTxt = estado.sesion.usuario                        // ¿hay usuario?
    ? `Conectado como: ${estado.sesion.usuario} [${estado.sesion.rol}]` // conectado
    : 'Modo Invitado (acceso público limitado)'                  // invitado

  // 1) Maquetacion: dos tarjetas (login y registro).
  contenedor.innerHTML = `
    <div class="modulo">
      <h1 class="titulo con-icono"><span class="ico">${iconos.cuenta}</span><span id="sesion-txt">${estadoTxt}</span></h1>
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
        document.getElementById('sesion-txt').textContent =       // actualiza el texto (el icono se conserva)
          `Conectado como: ${user} [${r.rol}]`
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
