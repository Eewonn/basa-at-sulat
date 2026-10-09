// Text size for older or small laptops: zooms the whole UI so every px-based size scales together.
export type TextSize = 'normal' | 'large'

const ZOOM: Record<TextSize, string> = { normal: '1', large: '1.15' }

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // Setting just won't persist across restarts.
  }
}

export function getTextSize(): TextSize {
  return read('textSize') === 'large' ? 'large' : 'normal'
}

export function applyTextSize(size: TextSize): void {
  write('textSize', size)
  if (!isPresentation()) document.documentElement.style.zoom = ZOOM[size]
}

// Presentation mode for demos (Ctrl+Shift+P): large text and no "sample data" badges.
export function isPresentation(): boolean {
  return read('presentation') === '1'
}

export function applyPresentation(on: boolean): void {
  write('presentation', on ? '1' : '0')
  document.documentElement.toggleAttribute('data-presentation', on)
  document.documentElement.style.zoom = on ? ZOOM.large : ZOOM[getTextSize()]
}

export function isSetupDone(): boolean {
  return read('setupDone') === '1'
}

export function markSetupDone(): void {
  write('setupDone', '1')
}
