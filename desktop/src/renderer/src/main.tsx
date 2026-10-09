import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import { applyPresentation, applyTextSize, getTextSize, isPresentation } from './display'
import './styles/app.css'

applyTextSize(getTextSize())
applyPresentation(isPresentation())

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
