// motion.js — Motor de "motion graphics" de LogiIA.
// Reglas: movimiento continuo (fondo vivo, count-up, gauges, barras). Nada de aparicion por zoom/popup.
// Todo respeta prefers-reduced-motion mediante movimientoReducido().

// Devuelve true si el usuario pidio reducir el movimiento (accesibilidad del sistema operativo).
export function movimientoReducido() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches // consulta la preferencia del SO
}

// Interpolacion suave (easeOutCubic): arranca rapido y desacelera al final. Da sensacion premium.
function suavizar(t) {                              // t va de 0 a 1
  return 1 - Math.pow(1 - t, 3)                     // curva de desaceleracion
}

// Fondo vivo: rutas maritimas que fluyen lentamente sobre un degradado calido. Usa requestAnimationFrame.
export function iniciarFondoVivo(canvas) {
  const ctx = canvas.getContext('2d')              // contexto de dibujo 2D
  let ancho = 0, alto = 0                           // dimensiones actuales del lienzo
  function redimensionar() {                        // ajusta el canvas al tamaño de la ventana
    ancho = canvas.width = window.innerWidth        // ancho en pixeles reales
    alto = canvas.height = window.innerHeight       // alto en pixeles reales
  }
  redimensionar()                                   // dimension inicial
  window.addEventListener('resize', redimensionar)  // reajustar al cambiar el tamaño de la ventana

  // Genera un conjunto de "particulas" que representan barcos/paquetes desplazandose por rutas.
  const N = 34                                      // cantidad de particulas (bajo para no distraer)
  const particulas = Array.from({ length: N }, (_, i) => ({ // crea N particulas
    x: Math.random() * (ancho || 1200),             // posicion horizontal inicial aleatoria
    y: Math.random() * (alto || 800),               // posicion vertical inicial aleatoria
    v: 0.15 + Math.random() * 0.35,                 // velocidad lenta (movimiento sutil)
    r: 1 + Math.random() * 2,                       // radio del punto
    c: i % 3 === 0 ? '#84D2C5' : '#F4C77B',         // alterna color frio/calido
  }))

  function pintar() {                               // dibuja un fotograma
    ctx.clearRect(0, 0, ancho, alto)                // limpia el lienzo

    const g = ctx.createLinearGradient(0, 0, ancho, alto) // degradado calido de fondo
    g.addColorStop(0, '#1b1512')                    // esquina superior izquierda
    g.addColorStop(1, '#120f0d')                    // esquina inferior derecha
    ctx.fillStyle = g                               // usa el degradado
    ctx.fillRect(0, 0, ancho, alto)                 // pinta el fondo completo

    for (const p of particulas) {                   // recorre cada particula
      p.x += p.v                                     // avanza lentamente hacia la derecha
      if (p.x > ancho + 10) { p.x = -10; p.y = Math.random() * alto } // reaparece por la izquierda
      ctx.beginPath()                               // inicia el trazo de la estela
      ctx.moveTo(p.x, p.y)                          // punto actual
      ctx.lineTo(p.x - 28, p.y)                     // estela hacia atras (linea de ruta)
      ctx.strokeStyle = p.c + '22'                  // color con baja opacidad (22 en hex ~ 13%)
      ctx.lineWidth = p.r                           // grosor segun tamaño
      ctx.stroke()                                  // dibuja la estela
      ctx.beginPath()                               // dibuja el punto (barco/paquete)
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)        // circulo
      ctx.fillStyle = p.c + '66'                    // relleno semitransparente
      ctx.fill()                                    // pinta el punto
    }
    requestAnimationFrame(pintar)                   // programa el siguiente fotograma (bucle continuo)
  }
  if (movimientoReducido()) {                       // si el usuario pidio menos movimiento
    ctx.fillStyle = '#161311'; ctx.fillRect(0, 0, ancho, alto) // pinta un fondo estatico y no anima
    return                                          // no arranca el bucle
  }
  pintar()                                          // arranca el bucle de animacion
}

// Count-up: anima el texto de un elemento desde un numero a otro con easing.
export function animarNumero(el, desde, hasta, opciones = {}) {
  const duracion = opciones.duracion ?? 900         // duracion en ms
  const decimales = opciones.decimales ?? 0         // cantidad de decimales a mostrar
  const sufijo = opciones.sufijo ?? ''              // texto que se agrega al final (ej. ' d', '%')
  if (movimientoReducido()) {                       // si se reduce el movimiento
    el.textContent = hasta.toFixed(decimales) + sufijo // muestra el valor final sin animar
    return                                          // termina
  }
  const inicio = performance.now()                  // marca de tiempo inicial
  function paso(ahora) {                             // funcion de cada fotograma
    const t = Math.min(1, (ahora - inicio) / duracion) // progreso 0..1
    const valor = desde + (hasta - desde) * suavizar(t) // valor interpolado con easing
    el.textContent = valor.toFixed(decimales) + sufijo  // actualiza el texto
    if (t < 1) requestAnimationFrame(paso)          // continua hasta llegar a 1
  }
  requestAnimationFrame(paso)                        // inicia la animacion
}

// Gauge circular (SVG): llena el arco segun un porcentaje usando stroke-dashoffset.
export function animarGauge(elFill, radio, porcentaje) {
  const circunferencia = 2 * Math.PI * radio         // longitud total del circulo
  elFill.style.strokeDasharray = String(circunferencia) // el trazo completo ocupa toda la circunferencia
  const objetivo = circunferencia * (1 - Math.min(1, Math.max(0, porcentaje / 100))) // offset segun %
  elFill.style.strokeDashoffset = String(circunferencia) // arranca vacio (offset = circunferencia)
  requestAnimationFrame(() => {                      // en el siguiente fotograma dispara la transicion CSS
    elFill.style.strokeDashoffset = movimientoReducido() ? String(objetivo) : String(objetivo) // llena
  })
}

// Barra de desglose: lleva el ancho de 0% al porcentaje indicado (la transicion CSS hace el resto).
export function animarBarra(elSpan, porcentaje) {
  const pct = Math.min(100, Math.max(0, porcentaje)) // acota el valor a 0..100
  requestAnimationFrame(() => { elSpan.style.width = pct + '%' }) // aplica el ancho (transicion definida en CSS)
}

// Dibuja una polilinea "dibujandose" sobre un canvas 2D (para el grafico historico del modulo ETA).
export function dibujarLineaCanvas(ctx, puntos, color) {
  if (!puntos.length) return                         // si no hay puntos, nada que dibujar
  let progreso = 0                                   // cuantos segmentos se han dibujado (0..1)
  function paso() {                                  // fotograma de la animacion de dibujo
    progreso = Math.min(1, progreso + 0.03)          // avanza el trazo
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height) // limpia para redibujar
    ctx.beginPath()                                  // inicia la linea
    const total = puntos.length - 1                  // segmentos totales
    const hasta = Math.floor(total * progreso)       // hasta que punto dibujar en este fotograma
    ctx.moveTo(puntos[0].x, puntos[0].y)             // primer punto
    for (let i = 1; i <= hasta; i++) ctx.lineTo(puntos[i].x, puntos[i].y) // une los puntos alcanzados
    ctx.strokeStyle = color                          // color de la linea
    ctx.lineWidth = 3                                // grosor
    ctx.stroke()                                     // traza
    if (progreso < 1 && !movimientoReducido()) requestAnimationFrame(paso) // continua si falta y hay motion
  }
  paso()                                             // arranca el dibujo
}

// Toast: notificacion que entra deslizando desde la derecha y desaparece sola (sin popup/zoom).
export function mostrarToast(texto, tipo = 'ok') {
  const cont = document.getElementById('toasts')     // contenedor de toasts
  const el = document.createElement('div')           // crea el elemento
  el.className = 'toast' + (tipo === 'error' ? ' error' : '') // clase base + variante de error
  el.textContent = texto                             // mensaje
  cont.appendChild(el)                               // lo agrega a la pantalla
  setTimeout(() => {                                 // tras unos segundos
    el.style.transition = 'opacity .3s ease'         // prepara el desvanecido
    el.style.opacity = '0'                           // desvanece
    setTimeout(() => el.remove(), 320)               // lo quita del DOM al terminar
  }, 3200)                                            // visible ~3.2 s
}
