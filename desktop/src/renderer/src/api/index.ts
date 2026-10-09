import { createHttpApi } from './httpApi'
import { mockApi } from './mockApi'
import type { Api } from './types'

// Engine port from the Electron launcher means real data; no port means sample data.
const port = window.basa?.enginePort
export const api: Api = port ? createHttpApi(port) : mockApi
