/**
 * markmap 渲染与导出的公共逻辑（与 Vue 无关，便于无头浏览器验证）。
 * 预览与导出共用同一套 toPure / 选项，保证字号、字重、断行一致。
 */
import { Markmap } from 'markmap-view'
import type { INode, IPureNode } from 'markmap-common'
import type { MapNode } from '@/api/knowledge'
import { KNOWLEDGE_MAP_THEME, branchColor, escapeHtml, fontFor, wrapLines, wrapWidthFor } from './mapTheme'
import { svgToPureSvg, type PureSvg } from './exportMap'

export type BranchIndex = Map<string, number>

export function buildBranchIndex(root: MapNode): BranchIndex {
  const idx: BranchIndex = new Map()
  ;(root.children || []).forEach((c, i) => {
    const mark = (n: MapNode) => {
      idx.set(n.path, i)
      for (const ch of n.children || []) mark(ch)
    }
    mark(c)
  })
  return idx
}

/** 节点 HTML：按深度设置字号/字重/行高，按字号预断行。 */
export function nodeHtml(title: string, depth: number): string {
  const f = fontFor(depth)
  const lines = wrapLines(title, wrapWidthFor(depth)).map(escapeHtml)
  return (
    `<span class="kmap-t" style="font-size:${f.size}px;font-weight:${f.weight};` +
    `line-height:${f.lineHeight}px;color:${KNOWLEDGE_MAP_THEME.textColor};white-space:nowrap">` +
    `${lines.join('<br>')}</span>`
  )
}

export function toPure(n: MapNode): IPureNode {
  return {
    content: nodeHtml(n.title, n.depth),
    children: (n.children || []).map(toPure),
    payload: { line: n.line, path: n.path, id: n.id, depth: n.depth },
  }
}

export function markmapOptions(branches: BranchIndex, extra: Record<string, unknown> = {}) {
  const colorOf = (node: INode): string => {
    const p = node.payload as { depth?: number; path?: string } | undefined
    const depth = p?.depth ?? -1
    return branchColor(depth, branches.get(p?.path || '') ?? 0)
  }
  return {
    autoFit: true,
    duration: 0,
    initialExpandLevel: -1,
    zoom: false,
    pan: false,
    maxWidth: KNOWLEDGE_MAP_THEME.maxWidth,
    paddingX: KNOWLEDGE_MAP_THEME.paddingX,
    spacingHorizontal: KNOWLEDGE_MAP_THEME.spacingHorizontal,
    spacingVertical: KNOWLEDGE_MAP_THEME.spacingVertical,
    color: colorOf,
    lineWidth: (node: INode) => KNOWLEDGE_MAP_THEME.lineWidth(node.state?.depth ?? 0),
    ...extra,
  }
}

/** 在屏幕外容器渲染整棵（子）树并转为纯 SVG；branches 用于保持分片与全图配色一致。 */
export async function renderTreeToPureSvg(
  tree: MapNode,
  opts: { expandLevel?: number; branches?: BranchIndex } = {},
): Promise<PureSvg> {
  const host = document.createElement('div')
  host.style.cssText =
    'position:fixed;left:-100000px;top:0;width:1600px;height:1200px;pointer-events:none;' +
    `font-family:${KNOWLEDGE_MAP_THEME.fontFamily}`
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  svg.setAttribute('width', '1600')
  svg.setAttribute('height', '1200')
  svg.style.fontFamily = KNOWLEDGE_MAP_THEME.fontFamily
  host.appendChild(svg)
  document.body.appendChild(host)
  const branches = opts.branches || buildBranchIndex(tree)
  const mm = Markmap.create(svg, markmapOptions(branches, { initialExpandLevel: opts.expandLevel ?? -1 }))
  try {
    await mm.setData(toPure(tree))
    await mm.fit()
    await new Promise((r) => requestAnimationFrame(() => r(undefined)))
    return svgToPureSvg(svg)
  } finally {
    mm.destroy()
    host.remove()
  }
}
