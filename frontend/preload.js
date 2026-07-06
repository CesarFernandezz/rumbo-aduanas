// preload.js — Puente seguro entre el renderer (sin acceso a Node) y el proceso principal.
// Solo expone lo minimo necesario a traves de contextBridge.

const { contextBridge, ipcRenderer } = require('electron') // APIs permitidas en el preload

contextBridge.exposeInMainWorld('nativo', {          // crea window.nativo en el renderer
  // Abre el dialogo nativo de guardado y devuelve la ruta elegida (o null si se cancela).
  elegirRutaPdf: () => ipcRenderer.invoke('elegir-ruta-pdf'), // reenvia al canal IPC del main
})
