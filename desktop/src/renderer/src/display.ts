// Text size for older or small laptops: zooms the whole UI so every px-based size scales together.
export type TextSize = 'normal' | 'large'

const ZOOM: Record<TextSize, string> = { normal: '1', large: '1.15' }

export function getTextSize(): TextSize {
  try {
    return localStorage.getItem('textSize') === 'large' ? 'large' : 'normal'
  } catch {
    return 'normal'
  }
}

export function applyTextSize(size: TextSize): void {
  document.documentElement.style.zoom = ZOOM[size]
  try {
    localStorage.setItem('textSize', size)
  } catch {
    // Size just won't persist across restarts.
  }
}
