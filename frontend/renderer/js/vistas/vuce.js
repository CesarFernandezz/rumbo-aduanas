// vuce.js — Modulo Asesor VUCE: consulta -> dictamen HTML del backend -> opcion de exportar a PDF.

import { api } from '../api.js'                                   // llamadas al sidecar
import { mostrarToast } from '../motion.js'                       // notificaciones
import { estado } from '../estado.js'                             // sesion

export function renderVuce(contenedor) {
  // 1) Maquetacion: tarjeta de consulta arriba, visor del dictamen abajo, boton de PDF.
  contenedor.innerHTML = `
    <div class="modulo">
      <h1 class="titulo">Asesor de Comercio Exterior (VUCE)</h1>
      <p class="subtitulo">Guía de procedimiento aduanero generada por IA.</p>
      <div class="tarjeta">
        <div class="campo"><label>Régimen Aduanero</label>
          <select id="vuce-regimen"><option>IMPORTACIÓN</option><option>EXPORTACIÓN</option></select></div>
        <div class="campo"><label>Describa la mercancía o partida arancelaria</label>
          <textarea id="vuce-consulta" rows="3" placeholder="Ej: café en grano verde para siembra"></textarea></div>
        <button class="boton boton-primario" id="vuce-btn">Generar Dictamen con IA</button>
      </div>
      <div class="tarjeta" id="vuce-visor" style="margin-top:14px;min-height:120px">
        <span class="kpi-lbl">El dictamen aparecerá aquí…</span>       <!-- placeholder inicial -->
      </div>
      <button class="boton" id="vuce-pdf" style="margin-top:12px" disabled>Descargar Reporte en PDF</button>
    </div>
  `

  let ultimoHtml = ''                                             // guarda el ultimo dictamen para el PDF
  const visor = document.getElementById('vuce-visor')            // contenedor del dictamen
  const btnPdf = document.getElementById('vuce-pdf')            // boton de exportacion

  // 2) Generar dictamen: llama al sidecar y renderiza el HTML devuelto.
  document.getElementById('vuce-btn').onclick = async () => {
    const consulta = document.getElementById('vuce-consulta').value.trim() // texto de la consulta
    if (!consulta) { mostrarToast('Escribe una consulta primero.', 'error'); return } // validacion
    const regimen = document.getElementById('vuce-regimen').value // regimen elegido
    visor.innerHTML = '<span class="kpi-lbl">Generando dictamen…</span>' // estado de carga
    try {
      const r = await api.vuce(regimen, consulta)                 // pide el dictamen
      ultimoHtml = r.html                                         // guarda el HTML para el PDF
      visor.innerHTML = r.html                                    // muestra el dictamen (HTML del backend)
      btnPdf.disabled = false                                     // habilita la descarga
      if (estado.sesion.usuario) mostrarToast('Consulta registrada en tu historial.') // aviso si hay sesion
    } catch (e) {
      visor.innerHTML = '<span class="kpi-lbl">No se pudo generar el dictamen.</span>' // estado de error
      mostrarToast(e.message, 'error')                            // detalle del error (ej. deps VUCE faltan)
    }
  }

  // 3) Exportar a PDF: pide la ruta con el dialogo nativo y manda a generar el archivo.
  btnPdf.onclick = async () => {
    if (!ultimoHtml) return                                       // nada que exportar
    const ruta = await window.nativo.elegirRutaPdf()              // dialogo nativo "guardar como"
    if (!ruta) return                                             // usuario cancelo
    try {
      await api.vucePdf({                                         // pide al backend generar el PDF
        regimen: document.getElementById('vuce-regimen').value,   // regimen actual
        consulta: document.getElementById('vuce-consulta').value.trim(), // consulta actual
        html: ultimoHtml,                                         // dictamen
        ruta,                                                     // ruta elegida
      })
      mostrarToast('PDF guardado correctamente.')                 // exito
    } catch (e) {
      mostrarToast(e.message, 'error')                            // error al generar
    }
  }
}
