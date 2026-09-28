export const KNOWLEDGE_MAP_THEME = {
  background: '#FFFFFF',
  rootColor: '#D0021B',
  branchColors: ['#1E3A5F', '#0F7D4F', '#5B3A8E', '#A26500', '#2F6FED', '#0F9D6C', '#C47D00', '#8B0000'],
  colorFreezeLevel: 2,
  textColor: '#1F2329',
  mutedTextColor: '#5C6370',
  fontFamily:
    "-apple-system, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif",
  fontSize: { root: 20, depth1: 16, depth2: 15, default: 14 },
  fontWeight: { root: 700, depth1: 600, default: 400 },
  lineHeight: 1.35,
  lineWidth: (depth: number) => Math.max(1, 3 - depth * 0.5),
  spacingHorizontal: 64,
  spacingVertical: 8,
  paddingX: 8,
  /** 文本区最大宽度（px）；预断行按字号计算每行字数，避免 markmap 再自动折出孤字 */
  textWidth: 264,
  maxWidth: 300,
} as const

export type KnowledgeMapTheme = typeof KNOWLEDGE_MAP_THEME

/** 节点 depth：-1 = 科目根，0 = 题型（一级分支），1 = 二级 … */
export function fontFor(depth: number): { size: number; weight: number; lineHeight: number } {
  const t = KNOWLEDGE_MAP_THEME
  let size: number = t.fontSize.default
  let weight: number = t.fontWeight.default
  if (depth < 0) {
    size = t.fontSize.root
    weight = t.fontWeight.root
  } else if (depth === 0) {
    size = t.fontSize.depth1
    weight = t.fontWeight.depth1
  } else if (depth === 1) {
    size = t.fontSize.depth2
  }
  return { size, weight, lineHeight: Math.round(size * t.lineHeight) }
}

/** 每行可容纳的 CJK 字数（CJK 计 1，ASCII 计 0.5）。 */
export function wrapWidthFor(depth: number): number {
  return Math.max(6, Math.floor(KNOWLEDGE_MAP_THEME.textWidth / fontFor(depth).size))
}

const charWidth = (ch: string) => (/[\u2e80-\u9fff\uff00-\uffef\u3000-\u303f]/.test(ch) ? 1 : 0.5)

// 行首禁则：这些标点不放在行首（并入上一行，允许略超 limit；textWidth 与 maxWidth 之间留有余量）
const NO_LINE_START = /[、，。；：？！）》」』”’,.;:?!)\]}%]/

/** 按字宽预断行，返回行数组；多行时均分行宽，避免末行只剩一两个字；遵守行首禁则。 */
export function wrapLines(title: string, maxCjk: number): string[] {
  const chars = Array.from(title || '')
  if (!chars.length) return ['']
  const total = chars.reduce((s, ch) => s + charWidth(ch), 0)
  if (total <= maxCjk) return [chars.join('')]
  const n = Math.ceil(total / maxCjk)
  const limit = Math.min(maxCjk, Math.ceil(total / n))
  const lines: string[] = []
  let cur = ''
  let width = 0
  for (const ch of chars) {
    const w = charWidth(ch)
    if (width + w > limit && cur && !NO_LINE_START.test(ch)) {
      lines.push(cur)
      cur = ch
      width = w
    } else {
      cur += ch
      width += w
    }
  }
  if (cur) lines.push(cur)
  return lines
}

/** 兼容旧调用：用 <br> 连接。 */
export function wrapTitle(title: string, maxCjk = wrapWidthFor(1)): string {
  return wrapLines(title, maxCjk).join('<br>')
}

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function branchColor(depth: number, branchIndex: number): string {
  if (depth < 0) return KNOWLEDGE_MAP_THEME.rootColor
  const colors = KNOWLEDGE_MAP_THEME.branchColors
  return colors[Math.abs(branchIndex) % colors.length]
}
