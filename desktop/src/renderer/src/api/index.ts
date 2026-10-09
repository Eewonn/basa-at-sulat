import { createHttpApi } from './httpApi'
import type { Api } from './types'

// Every screen shows engine data only. Without an engine port the app shows "engine not running" (App.tsx)
// and never calls this client.
export const enginePort = window.basa?.enginePort ?? null
export const api: Api = createHttpApi(enginePort ?? 0)
