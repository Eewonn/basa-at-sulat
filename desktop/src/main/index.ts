import { join } from 'node:path'
import { app, BrowserWindow, session, shell } from 'electron'

const DEV_URL = process.env['ELECTRON_RENDERER_URL']

// Only our own page (dev server or bundled file) may use the microphone or navigate.
function isAppUrl(url: string): boolean {
  return DEV_URL ? url.startsWith(DEV_URL) : url.startsWith('file://')
}

function createWindow(): void {
  // The engine port comes from the launcher (P0-FE-4). Until the engine exists,
  // no port means the renderer runs on mock data.
  const enginePort = process.env['BASA_ENGINE_PORT'] ?? ''

  const win = new BrowserWindow({
    width: 1366,
    height: 800,
    minWidth: 1280,
    minHeight: 720,
    show: false,
    title: 'Basa at Sulat',
    backgroundColor: '#FAF6EE',
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      additionalArguments: [`--basa-engine-port=${enginePort}`]
    }
  })

  win.once('ready-to-show', () => win.show())

  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  win.webContents.on('will-navigate', (event, url) => {
    if (!isAppUrl(url)) event.preventDefault()
  })

  if (DEV_URL) win.loadURL(DEV_URL)
  else win.loadFile(join(__dirname, '../renderer/index.html'))
}

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((_wc, permission, callback, details) => {
    callback(permission === 'media' && isAppUrl(details.requestingUrl))
  })
  session.defaultSession.setPermissionCheckHandler((_wc, permission, requestingOrigin) => {
    return permission === 'media' && isAppUrl(requestingOrigin)
  })

  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// External links (e.g. license pages in Settings) open in the system browser, never in-app.
app.on('web-contents-created', (_e, contents) => {
  contents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) shell.openExternal(url)
    return { action: 'deny' }
  })
})
