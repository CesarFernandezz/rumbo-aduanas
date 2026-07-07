// icons.js — Conjunto de iconos SVG de linea (estilo Lucide) y la marca "Rumbo".
// Reemplazan a los emojis: usan stroke="currentColor" para heredar el color del contenedor,
// escalan sin pixelarse y se animan con el tema (hover, activo).

// Envuelve una serie de trazos en un <svg> 24x24 con los atributos de linea estandar.
function svg(trazos) {
  // fill:none + stroke:currentColor = icono de linea que toma el color del texto del padre.
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${trazos}</svg>`
}

// Diccionario de iconos por nombre (cada valor es el markup <svg> listo para inyectar en el DOM).
export const iconos = {
  // Casa: pantalla de Inicio / resumen.
  inicio: svg('<path d="M3 9.5 12 3l9 6.5"/><path d="M5 9v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9"/><path d="M9 21v-6h6v6"/>'),
  // Reloj: Predictor ETA (tiempo estimado de arribo).
  eta: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>'),
  // Documento con check: Asesor VUCE (dictamen legal aduanero).
  vuce: svg('<path d="M14 3v4a1 1 0 0 0 1 1h4"/><path d="M15 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="m9 15 2 2 4-4"/>'),
  // Dolar en circulo: Landed Cost (calculadora financiera).
  landed: svg('<circle cx="12" cy="12" r="9"/><path d="M14.8 9A2 2 0 0 0 13 8h-2a2 2 0 0 0 0 4h2a2 2 0 0 1 0 4h-2a2 2 0 0 1-1.8-1"/><path d="M12 6v2m0 8v2"/>'),
  // Usuario: Cuenta / Sesion.
  cuenta: svg('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'),
  // Signo mas: accion de "nueva consulta".
  mas: svg('<path d="M12 5v14M5 12h14"/>'),
  // Flecha derecha: indicador de "entrar/abrir" en listas.
  chevron: svg('<path d="m9 6 6 6-6 6"/>'),
  // Descargar: exportar el dictamen a PDF.
  descarga: svg('<path d="M12 3v12"/><path d="m7 11 5 5 5-5"/><path d="M5 21h14"/>'),
  // Contenedor de carga: isotipo de la marca "Rumbo" (aduana / comercio).
  contenedor: svg('<rect x="3" y="8" width="18" height="9" rx="1"/><path d="M8 8v9"/><path d="M12 8v9"/><path d="M16 8v9"/>'),
}
