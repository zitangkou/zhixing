import type { MapNode } from '@/api/knowledge'
import { KNOWLEDGE_MAP_THEME } from './mapTheme'

export const MAX_EDGE = 4096
export const PREFERRED_SCALE = 2
export const MIN_SCALE = 1.5
const THUMB_MAX_W = 750
const THUMB_MAX_H = 1024
const SVG_NS = 'http://www.w3.org/2000/svg'

export interface PureSvg {
  svg: string
  /** SVG 用户单位尺寸（= 1x 像素） */
  width: number
  height: number
}

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

function num(v: string | null | undefined, d = 0): number {
  const n = parseFloat(v || '')
  return Number.isFinite(n) ? n : d
}

function copyPaint(src: Element, dst: Element, props: string[]) {
  const cs = getComputedStyle(src)
  for (const p of props) {
    const v = cs.getPropertyValue(p).trim()
    if (v && v !== 'auto') dst.setAttribute(p, v.replace(/^(-?[\d.]+)px$/, '$1'))
  }
}

/**
 * 把已在 DOM 中渲染完成的 markmap SVG 转为「纯 SVG」：
 * - 不含 foreignObject / <style> / class 依赖，所有绘制属性显式写入（连线 fill=none）
 * - 文字按源 DOM 中每一行的实际位置（getClientRects + CTM 反变换）生成 <text>，左对齐，
 *   字号/字重/颜色取自源节点的计算样式，保证与预览一致
 * - 去掉顶层 <g> 的 fit 变换，viewBox 按内容包围盒 + 边距计算，图铺满画布
 */
export function svgToPureSvg(source: SVGSVGElement, opts?: { bg?: string; pad?: number }): PureSvg {
  const bg = opts?.bg ?? KNOWLEDGE_MAP_THEME.background
  const pad = opts?.pad ?? 24
  const srcTop = source.querySelector(':scope > g') as SVGGElement | null
  if (!srcTop) throw new Error('markmap 未渲染')
  const toLocal = srcTop.getScreenCTM()?.inverse()
  if (!toLocal) throw new Error('无法计算坐标变换')

  const out = document.createElementNS(SVG_NS, 'svg')
  const top = srcTop.cloneNode(true) as SVGGElement
  top.removeAttribute('transform')

  // 1) 连线 / 圆点 / 下划线：显式绘制属性
  const srcPaths = Array.from(srcTop.querySelectorAll('path'))
  const dstPaths = Array.from(top.querySelectorAll('path'))
  srcPaths.forEach((s, i) => {
    const d = dstPaths[i]
    if (!d) return
    copyPaint(s, d, ['stroke', 'stroke-width', 'stroke-opacity', 'opacity'])
    d.setAttribute('fill', 'none')
  })
  const srcCircles = Array.from(srcTop.querySelectorAll('circle'))
  const dstCircles = Array.from(top.querySelectorAll('circle'))
  srcCircles.forEach((s, i) => {
    const d = dstCircles[i]
    if (d) copyPaint(s, d, ['fill', 'stroke', 'stroke-width', 'opacity'])
  })
  const srcLines = Array.from(srcTop.querySelectorAll('line'))
  const dstLines = Array.from(top.querySelectorAll('line'))
  srcLines.forEach((s, i) => {
    const d = dstLines[i]
    if (d) copyPaint(s, d, ['stroke', 'stroke-width', 'opacity'])
  })

  // 2) foreignObject → text（按源 DOM 行框定位）
  const srcFos = Array.from(srcTop.querySelectorAll('foreignObject'))
  const dstFos = Array.from(top.querySelectorAll('foreignObject'))
  const toLocalPt = (x: number, y: number) => new DOMPoint(x, y).matrixTransform(toLocal)
  // 文字所在节点 <g> 的局部坐标 = 顶层局部坐标 - 节点平移；这里统一放到顶层坐标系
  const textLayer = document.createElementNS(SVG_NS, 'g')
  srcFos.forEach((fo, i) => {
    const holder = (fo.querySelector('.kmap-t') as HTMLElement | null) || (fo.querySelector('div') as HTMLElement | null)
    dstFos[i]?.remove()
    if (!holder) return
    const cs = getComputedStyle(holder)
    const text = document.createElementNS(SVG_NS, 'text')
    text.setAttribute('font-family', KNOWLEDGE_MAP_THEME.fontFamily)
    text.setAttribute('font-size', String(num(cs.fontSize, 14)))
    text.setAttribute('font-weight', cs.fontWeight || '400')
    text.setAttribute('fill', cs.color || KNOWLEDGE_MAP_THEME.textColor)
    text.setAttribute('dominant-baseline', 'central')
    text.setAttribute('text-anchor', 'start')
    // 逐行：遍历文本节点，用 Range 取行框
    const walker = document.createTreeWalker(holder, NodeFilter.SHOW_TEXT)
    let node: Node | null
    while ((node = walker.nextNode())) {
      const content = node.textContent || ''
      if (!content.trim()) continue
      const range = document.createRange()
      range.selectNodeContents(node)
      const rects = Array.from(range.getClientRects()).filter((r) => r.width > 0 && r.height > 0)
      if (!rects.length) continue
      const r = rects[0]
      const p1 = toLocalPt(r.left, r.top)
      const p2 = toLocalPt(r.right, r.bottom)
      const tspan = document.createElementNS(SVG_NS, 'tspan')
      tspan.setAttribute('x', p1.x.toFixed(2))
      tspan.setAttribute('y', ((p1.y + p2.y) / 2).toFixed(2))
      tspan.textContent = content
      text.appendChild(tspan)
    }
    if (text.childNodes.length) textLayer.appendChild(text)
  })

  // 3) 清理：class/data-* 等与绘制无关的属性
  for (const el of [top, ...Array.from(top.querySelectorAll('*'))]) {
    for (const a of Array.from(el.attributes)) {
      if (a.name === 'class' || a.name === 'style' || a.name.startsWith('data-')) el.removeAttribute(a.name)
    }
  }
  top.appendChild(textLayer)

  // 4) 包围盒：源顶层 g 的局部 bbox（不含其自身 transform）
  const b = srcTop.getBBox()
  const vbX = Math.floor(b.x - pad)
  const vbY = Math.floor(b.y - pad)
  const vbW = Math.ceil(b.width + pad * 2)
  const vbH = Math.ceil(b.height + pad * 2)

  out.setAttribute('xmlns', SVG_NS)
  out.setAttribute('viewBox', `${vbX} ${vbY} ${vbW} ${vbH}`)
  out.setAttribute('width', String(vbW))
  out.setAttribute('height', String(vbH))
  const rect = document.createElementNS(SVG_NS, 'rect')
  rect.setAttribute('x', String(vbX))
  rect.setAttribute('y', String(vbY))
  rect.setAttribute('width', String(vbW))
  rect.setAttribute('height', String(vbH))
  rect.setAttribute('fill', bg)
  out.appendChild(rect)
  out.appendChild(top)
  return { svg: new XMLSerializer().serializeToString(out), width: vbW, height: vbH }
}

/** 给定 1x 尺寸，计算导出倍率：优先 2x，长边不超过 MAX_EDGE。 */
export function exportScale(width: number, height: number): number {
  const edge = Math.max(width, height, 1)
  return Math.min(PREFERRED_SCALE, MAX_EDGE / edge)
}

export async function rasterizeSvg(pure: PureSvg, filename: string, scale = exportScale(pure.width, pure.height)): Promise<RasterResult> {
  const img = new Image()
  const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(pure.svg)}`
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve()
    img.onerror = () => reject(new Error('SVG 加载失败'))
    img.src = url
  })
  const cw = Math.max(1, Math.min(MAX_EDGE, Math.round(pure.width * scale)))
  const ch = Math.max(1, Math.min(MAX_EDGE, Math.round(pure.height * scale)))
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

/** 缩略图：等比缩放到 750×1024 框内（不放大）。 */
export async function makeThumb(png: Blob, filename: string): Promise<RasterResult> {
  const img = new Image()
  const obj = URL.createObjectURL(png)
  try {
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve()
      img.onerror = () => reject(new Error('缩略图源加载失败'))
      img.src = obj
    })
    const ratio = Math.min(1, THUMB_MAX_W / img.naturalWidth, THUMB_MAX_H / img.naturalHeight)
    const tw = Math.max(1, Math.round(img.naturalWidth * ratio))
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
      return { ...n, title: rootTitle || n.title, children: n.children ? [...n.children] : [] }
    }
    for (const c of n.children || []) {
      const hit = walk(c)
      if (hit) return hit
    }
    return null
  }
  return walk(root)
}

/** 概览：只保留科目根 + 一级分支 + 二级分支。 */
export function overviewTree(root: MapNode): MapNode {
  const clip = (n: MapNode, d: number): MapNode => ({
    ...n,
    children: d >= 2 ? [] : (n.children || []).map((c) => clip(c, d + 1)),
  })
  return clip(root, 0)
}

export function countNodes(n: MapNode): number {
  return 1 + (n.children || []).reduce((s, c) => s + countNodes(c), 0)
}

export interface SegmentJob {
  /** ASCII key：s01、s01-02、s01-02-p1 … */
  key: string
  title: string
  rootPath: string
  nodeCount: number
  pure: PureSvg
  scale: number
}

/**
 * 按实际渲染尺寸递归拆分：倍率 < MIN_SCALE（即 2x 放不进 4096）时，
 * 按子分支拆；只有一个子分支则下钻；子节点全是叶子则按数量二分（-p1/-p2）。
 */
export async function planSegment(
  node: MapNode,
  key: string,
  breadcrumb: string[],
  render: (t: MapNode) => Promise<PureSvg>,
  depth = 0,
): Promise<SegmentJob[]> {
  const title = [...breadcrumb, node.title].join(' › ')
  const view: MapNode = { ...node, title }
  const pure = await render(view)
  const scale = exportScale(pure.width, pure.height)
  const kids = node.children || []
  if (scale >= MIN_SCALE || kids.length === 0 || depth >= 6) {
    return [{ key, title, rootPath: node.path, nodeCount: countNodes(node), pure, scale }]
  }
  if (kids.length === 1) {
    return planSegment(kids[0], key, [...breadcrumb, node.title], render, depth + 1)
  }
  const hasGrandKids = kids.some((k) => (k.children || []).length > 0)
  if (!hasGrandKids) {
    const mid = Math.ceil(kids.length / 2)
    const parts = [kids.slice(0, mid), kids.slice(mid)]
    const out: SegmentJob[] = []
    for (let i = 0; i < parts.length; i++) {
      const part: MapNode = { ...node, title: `${node.title}（${i + 1}/2）`, children: parts[i] }
      out.push(...(await planSegment(part, `${key}-p${i + 1}`, breadcrumb, render, depth + 1)))
    }
    return out
  }
  const out: SegmentJob[] = []
  for (let i = 0; i < kids.length; i++) {
    const k = String(i + 1).padStart(2, '0')
    out.push(...(await planSegment(kids[i], `${key}-${k}`, [...breadcrumb, node.title], render, depth + 1)))
  }
  return out
}
