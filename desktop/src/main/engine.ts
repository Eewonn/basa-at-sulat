import { spawn, spawnSync, type ChildProcess } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { connect, createServer } from 'node:net'
import { join, resolve } from 'node:path'
import { app } from 'electron'

// Starts Ollama (for group plans) and the engine (engine/, FastAPI) when the app opens, the same way
// scripts/launch.py does, and stops them when the app quits. Settings, all optional: BASA_PYTHON,
// BASA_ENGINE_DIR, BASA_DATA_DIR, OLLAMA_URL.
let engine: ChildProcess | null = null
let ollama: ChildProcess | null = null // only set when we started it; an Ollama that was already running isn't ours to stop

function isListening(host: string, port: number): Promise<boolean> {
  return new Promise((done) => {
    const socket = connect({ host, port, timeout: 1000 })
    socket.once('connect', () => (socket.destroy(), done(true)))
    socket.once('error', () => done(false))
    socket.once('timeout', () => (socket.destroy(), done(false)))
  })
}

// Without Ollama, plans still come back as the activity template, just without an example sentence.
async function startOllama(): Promise<void> {
  const url = new URL(process.env['OLLAMA_URL'] ?? 'http://127.0.0.1:11434')
  const host = url.hostname
  const port = Number(url.port || 11434)
  if (await isListening(host, port)) return
  const proc = spawn('ollama', ['serve'], { stdio: 'ignore', env: { ...process.env, OLLAMA_HOST: `${host}:${port}` } })
  proc.once('error', () => console.error('[ollama] not installed: group plans will use templates'))
  proc.once('spawn', () => (ollama = proc))
  proc.once('exit', () => (ollama = null))
}

const engineDir = (): string => resolve(process.env['BASA_ENGINE_DIR'] ?? join(app.getAppPath(), '..', 'engine'))

function findPython(dir: string): string {
  if (process.env['BASA_PYTHON']) return process.env['BASA_PYTHON']
  for (const venv of [join(dir, '.venv', 'bin', 'python'), join(dir, '.venv', 'Scripts', 'python.exe')]) {
    if (existsSync(venv)) return venv
  }
  return process.platform === 'win32' ? 'python' : 'python3'
}

function freePort(): Promise<number> {
  return new Promise((done, fail) => {
    const server = createServer()
    server.once('error', fail)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      server.close(() => (typeof address === 'object' && address ? done(address.port) : fail(new Error('no port'))))
    })
  })
}

// A fresh laptop gets a new, seeded database. An existing one is never touched.
function prepareDatabase(python: string, dir: string, dataDir: string): boolean {
  const db = join(dataDir, 'basa.db')
  if (existsSync(db)) return true
  mkdirSync(dataDir, { recursive: true })
  for (const module of ['app.init_db', 'app.seed']) {
    const result = spawnSync(python, ['-m', module, '--path', db], { cwd: dir, encoding: 'utf8' })
    if (result.status !== 0) {
      console.error(`[engine] could not create the database (${module}):`, result.error?.message ?? result.stderr)
      return false
    }
  }
  return true
}

/** Start the engine and return its port, or null if it can't be started. The engine answers /health once it's ready. */
export async function startEngine(): Promise<number | null> {
  const dir = engineDir()
  if (!existsSync(join(dir, 'app'))) {
    console.error(`[engine] no engine at ${dir}; set BASA_ENGINE_DIR`)
    return null
  }
  void startOllama()
  const python = findPython(dir)
  const dataDir = resolve(process.env['BASA_DATA_DIR'] ?? join(dir, 'storage'))
  if (!prepareDatabase(python, dir, dataDir)) return null

  const port = await freePort()
  engine = spawn(python, ['-m', 'app', '--port', String(port), '--data-dir', dataDir], {
    cwd: dir,
    // Load the aligner at startup so the first reading check isn't 10 s slower.
    env: { ...process.env, BASA_WARM_UP: process.env['BASA_WARM_UP'] ?? '1' },
    stdio: 'inherit'
  })
  engine.once('error', (err) => console.error('[engine] could not start:', err.message))
  engine.once('exit', (code) => {
    if (code) console.error(`[engine] stopped with code ${code}`)
    engine = null
  })
  return port
}

export function stopEngine(): void {
  engine?.kill()
  engine = null
  ollama?.kill()
  ollama = null
}
