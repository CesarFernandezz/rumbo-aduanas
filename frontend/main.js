// main.js — Proceso principal de Electron.
// Responsabilidades: lanzar el sidecar Python, crear la ventana, exponer el dialogo de guardado, y
// matar el proceso hijo al cerrar para no dejar servidores colgados.

const { app, BrowserWindow, ipcMain, dialog } = require('electron') // APIs de Electron
const { spawn } = require('child_process')                          // para lanzar/matar el proceso Python
const path = require('path')                                        // manejo de rutas de archivos

let ventana = null            // referencia a la ventana principal (para el dialogo y evitar recoleccion)
let procesoPython = null      // referencia al proceso hijo del sidecar

const PUERTO = 8000           // puerto donde escucha el sidecar (debe coincidir con api.js)
const RAIZ_PROYECTO = path.join(__dirname, '..')  // frontend/ esta dentro del proyecto; '..' = raiz con api_server.py

function lanzarSidecar() {                          // arranca uvicorn sirviendo api_server:app
  // 'python -m uvicorn ...' con cwd en la raiz para que 'from src...' e 'import api_server' resuelvan.
  procesoPython = spawn(
    'python',                                       // interprete de Python del sistema
    ['-m', 'uvicorn', 'api_server:app', '--host', '127.0.0.1', '--port', String(PUERTO)], // argumentos
    { cwd: RAIZ_PROYECTO, env: { ...process.env } } // directorio de trabajo = raiz del proyecto
  )
  procesoPython.stdout.on('data', d => console.log('[sidecar]', d.toString()))  // log de salida estandar
  procesoPython.stderr.on('data', d => console.log('[sidecar]', d.toString()))  // log de errores
  procesoPython.on('exit', code => console.log('[sidecar] termino con codigo', code)) // aviso al terminar
  procesoPython.on('error', (e) => console.error('[sidecar] no se pudo iniciar Python:', e.message)) // evita que un 'error' sin manejar tumbe el proceso principal
}

function crearVentana() {                           // crea la ventana principal del dashboard
  ventana = new BrowserWindow({                     // configura la ventana de Chromium
    width: 1280, height: 820,                       // tamaño inicial parecido a las fotos
    minWidth: 1024, minHeight: 680,                 // tamaño minimo utilizable
    backgroundColor: '#161311',                     // color de fondo mientras carga (evita flash blanco)
    autoHideMenuBar: true,                          // ocultar la barra de menu nativa
    webPreferences: {                               // opciones de seguridad del renderer
      preload: path.join(__dirname, 'preload.js'),  // script puente seguro
      contextIsolation: true,                       // aisla el contexto del renderer (seguridad)
      nodeIntegration: false,                       // el renderer NO accede a Node directamente
    },
  })
  ventana.loadFile(path.join(__dirname, 'renderer', 'index.html')) // carga la interfaz
}

app.whenReady().then(() => {                        // cuando Electron esta listo
  lanzarSidecar()                                   // 1) arranca el backend Python
  crearVentana()                                    // 2) abre la ventana (el renderer hara el polling /health)
})

// IPC: el renderer pide abrir el dialogo nativo "guardar como" para el PDF y recibe la ruta elegida.
ipcMain.handle('elegir-ruta-pdf', async () => {     // maneja la invocacion desde preload
  const r = await dialog.showSaveDialog(ventana, {  // muestra el dialogo del sistema operativo
    title: 'Guardar Dictamen',                      // titulo de la ventana
    defaultPath: 'Dictamen_VUCE.pdf',               // nombre sugerido
    filters: [{ name: 'PDF', extensions: ['pdf'] }],// solo archivos .pdf
  })
  return r.canceled ? null : r.filePath             // devuelve la ruta o null si el usuario cancelo
})

function matarSidecar() {                           // detiene el proceso Python hijo
  if (!procesoPython) return                        // si no hay proceso, nada que hacer
  if (process.platform === 'win32') {               // en Windows hay que matar el arbol de procesos
    const tk = spawn('taskkill', ['/pid', String(procesoPython.pid), '/f', '/t']) // /f forzar, /t incluir hijos
    tk.on('error', () => {})                        // ignorar si taskkill no esta disponible
  } else {                                          // en otros sistemas
    procesoPython.kill()                            // envia SIGTERM
  }
  procesoPython = null                              // limpia la referencia
}

app.on('window-all-closed', () => {                 // cuando se cierran todas las ventanas
  matarSidecar()                                    // detener el sidecar
  app.quit()                                        // salir de la app (tambien en macOS, por simplicidad)
})
app.on('before-quit', matarSidecar)                 // red de seguridad: matar el sidecar antes de salir
