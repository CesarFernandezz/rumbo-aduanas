// router.js — Conmuta entre vistas montandolas en #vista con un fade sutil (sin zoom/popup).

const vistas = {}          // registro nombre -> funcion de render
let vistaActual = null     // nombre de la vista mostrada

// Registra una vista: 'nombre' identifica y 'fnRender(contenedor)' construye su DOM.
export const router = {
  registrar(nombre, fnRender) {
    vistas[nombre] = fnRender                          // guarda la funcion de render
  },
  actual() { return vistaActual },                    // devuelve el nombre de la vista activa
  ir(nombre) {                                        // navega a una vista
    const contenedor = document.getElementById('vista') // contenedor principal
    const fn = vistas[nombre]                          // busca el render de la vista
    if (!fn) return                                    // si no existe, no hace nada
    vistaActual = nombre                               // actualiza la vista activa
    contenedor.innerHTML = ''                          // limpia el contenido anterior
    contenedor.classList.remove('vista-entrando')      // reinicia la animacion de entrada
    void contenedor.offsetWidth                        // fuerza reflow para reejecutar el keyframe
    contenedor.classList.add('vista-entrando')         // aplica el fade de entrada
    fn(contenedor)                                     // construye la nueva vista
    // Marca el boton de navegacion activo (si existe) segun el nombre de la vista.
    document.querySelectorAll('.nav-btn').forEach(b => // recorre los botones del sidebar
      b.classList.toggle('activo', b.dataset.vista === nombre)) // resalta el que corresponde
  },
}
