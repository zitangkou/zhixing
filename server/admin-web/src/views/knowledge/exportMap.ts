import type { MapNode } from '@/api/knowledge'
import { KNOWLEDGE_MAP_THEME } from './mapTheme'

const MAX_EDGE = 4096
const MIN_SCALE = 1.5
const THUMB_WIDTH = 750

export interface RasterResult {
  blob: Blob
  width: number
  height: number
  scale: number
  sha256: string
  filename: string
}

export async function sha256Hex(buf: ArrayBuffer): Promise<string> {
  const hash = await crypto.subtle.digest('SHA-256', buf)
  return [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

/** 把含 foreignObject 的 markmap SVG 转成纯 SVG（text/tspan），避免 canvas 污染。 */
export function svgToPureSvg(source: SVGSVGElement, opts?: { bg?: string }): string {
  const clone = source.cloneNode(true) as SVGSVGElement
  const bg = opts?.bg ?? KNOWLEDGE_MAP_THEME.background
  const fontFamily = KNOWLEDGE_MAP_THEME.fontFamily

  // 去掉 HTML 依赖的 style
  clone.querySelectorAll('style').forEach((el) => el.remove())

  const fos = Array.from(clone.querySelectorAll('foreignObject'))
  for (const fo of fos) {
    const html = fo.querySelector('div,span,p')?.textContent || fo.textContent || ''
    const lines = html.split(/\n/).flatMap((l) => l.split(/\u200b/)).map((s) => s.trim()).filter(Boolean)
    // markmap 预览用 <br>，foreignObject 里可能是多行
    const brLines = (fo.innerHTML.match(/>([^<]*)</g) || [])
      .map((m) => m.slice(1, -1).replace(/&nbsp;/g, ' ').trim())
      .filter(Boolean)
    const useLines = brLines.length > 1 ? brLines : lines.length ? lines : [html.trim() || ' ']

    const x = parseFloat(fo.getAttribute('x') || '0')
    const y = parseFloat(fo.getAttribute('y') || '0')
    const w = parseFloat(fo.getAttribute('width') || '0')
    const fontSize = 14
    const lineH = fontSize * 1.35

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    text.setAttribute('x', String(x + w / 2))
    text.setAttribute('y', String(y + fontSize))
    text.setAttribute('text-anchor', 'middle')
    text.setAttribute('fill', KNOWLEDGE_MAP_THEME.textColor)
    text.setAttribute('font-family', fontFamily)
    text.setAttribute('font-size', String(fontSize))
    text.setAttribute('font-weight', '400')

    useLines.forEach((line, i) => {
      const tspan = document.createElementNS('http://www.w3.org/2000/svg', 'tspan')
      tspan.setAttribute('x', String(x + w / 2))
      if (i === 0) tspan.setAttribute('dy', '0')
      else tspan.setAttribute('dy', String(lineH))
      tspan.textContent = line.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/&quot;/g, '"')
      text.appendChild(tspan)
    })
    fo.replaceWith(text)
  }

  // 包围盒
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  const walk = (el: Element) => {
    if (el instanceof SVGGraphicsElement) {
      try {
        const b = el.getBBox()
        if (b.width || b.height) {
          minX = Math.min(minX, b.x)
          minY = Math.min(minY, b.y)
          maxX = Math.max(maxX, b.x + b.width)
          maxY = Math.max(maxY, b.y + b.height)
        }
      } catch {
        /* detached */
      }
    }
    for (const c of Array.from(el.children)) walk(c)
  }
  // 用源 SVG 的 state rect 更稳：从 clone 的 transform group 估算
  const g = clone.querySelector('g')
  if (g) {
    try {
      // clone 不在 DOM，getBBox 可能失败；用源 SVG
      const srcG = source.querySelector('g')
      if (srcG) {
        const b = (srcG as SVGGraphicsElement).getBBox()
        minX = b.x
        minY = b.y
        maxX = b.x + b.width
        maxY = b.y + b.height
      }
    } catch {
      walk(clone)
    }
  }
  if (!Number.isFinite(minX)) {
    minX = 0
    minY = 0
    maxX = 800
    maxY = 600
  }
  const pad = 24
  const vbX = minX - pad
  const vbY = minY - pad
  const vbW = Math.max(1, maxX - minX + pad * 2)
  const vbH = Math.max(1, maxY - minY + pad * 2)

  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clone.setAttribute('viewBox', `${vbX} ${vbY} ${vbW} ${vbH}`)
  clone.setAttribute('width', String(Math.ceil(vbW)))
  clone.setAttribute('height', String(Math.ceil(vbH)))

  const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
  rect.setAttribute('x', String(vbX))
  rect.setAttribute('y', String(vbY))
  rect.setAttribute('width', String(vbW))
  rect.setAttribute('height', String(vbH))
  rect.setAttribute('fill', bg)
  clone.insertBefore(rect, clone.firstChild)

  return new XMLSerializer().serializeToString(clone)
}

export async function rasterizeSvg(
  svgMarkup: string,
  filename: string,
  preferredScale = 2,
): Promise<RasterResult> {
  const img = new Image()
  const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgMarkup)}`
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve()
    img.onerror = () => reject(new Error('SVG 加载失败'))
    img.src = url
  })
  const w = img.naturalWidth || 800
  const h = img.naturalHeight || 600
  let scale = preferredScale
  const edge = Math.max(w, h)
  if (edge * scale > MAX_EDGE) {
    scale = MAX_EDGE / edge
  }
  if (scale < MIN_SCALE && edge * MIN_SCALE <= MAX_EDGE) {
    scale = MIN_SCALE
  }
  const cw = Math.max(1, Math.round(w * scale))
  const ch = Math.max(1, Math.round(h * scale))
  const canvas = document.createElement('canvas')
  canvas.width = cw
  canvas.height = ch
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('canvas 不可用')
  ctx.fillStyle = KNOWLEDGE_MAP_THEME.background
  ctx.fillRect(0, 0, cw, ch)
  ctx.drawImage(img, 0, 0, cw, ch)
  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('toBlob 失败'))), 'image/png')
  })
  const sha256 = await sha256Hex(await blob.arrayBuffer())
  return { blob, width: cw, height: ch, scale, sha256, filename }
}

export async function makeThumb(png: Blob, filename: string): Promise<RasterResult> {
  const img = new Image()
  const obj = URL.createObjectURL(png)
  try {
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve()
      img.onerror = () => reject(new Error('缩略图源加载失败'))
      img.src = obj
    })
    const ratio = THUMB_WIDTH / img.naturalWidth
    const tw = THUMB_WIDTH
    const th = Math.max(1, Math.round(img.naturalHeight * ratio))
    const canvas = document.createElement('canvas')
    canvas.width = tw
    canvas.height = th
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('canvas 不可用')
    ctx.fillStyle = KNOWLEDGE_MAP_THEME.background
    ctx.fillRect(0, 0, tw, th)
    ctx.drawImage(img, 0, 0, tw, th)
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('thumb toBlob 失败'))), 'image/png')
    })
    const sha256 = await sha256Hex(await blob.arrayBuffer())
    return { blob, width: tw, height: th, scale: ratio, sha256, filename }
  } finally {
    URL.revokeObjectURL(obj)
  }
}

/** 从 MapNode 按 path 取子树，根标题可改写。 */
export function sliceTree(root: MapNode, rootPath: string, rootTitle?: string): MapNode | null {
  if (!rootPath || root.path === rootPath) {
    return { ...root, title: rootTitle || root.title, children: root.children ? [...root.children] : [] }
  }
  const walk = (n: MapNode): MapNode | null => {
    if (n.path === rootPath) {
      return {
        ...n,
        title: rootTitle || n.title,
        children: n.children ? [...n.children] : [],
      }
    }
    for (const c of n.children || []) {
      const hit = walk(c)
      if (hit) return hit
    }
    return null
  }
  return walk(root)
}

/** 概览：只保留 depth≤1 的子节点（相对切片根）。 */
export function overviewTree(root: MapNode): MapNode {
  const clip = (n: MapNode, d: number): MapNode => ({
    ...n,
    children: d >= 1 ? [] : (n.children || []).map((c) => clip(c, d + 1)),
  })
  return clip(root, 0)
}
