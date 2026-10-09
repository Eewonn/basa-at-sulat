import { contextBridge } from 'electron'

const portArg = process.argv.find((a) => a.startsWith('--basa-engine-port='))
const port = Number(portArg?.split('=')[1])

contextBridge.exposeInMainWorld('basa', {
  platform: process.platform,
  enginePort: Number.isInteger(port) && port > 0 ? port : null
})
