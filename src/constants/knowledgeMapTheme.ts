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
  lineWidth: (depth: number) => Math.max(1, 3 - depth * 0.5),
  spacingHorizontal: 64,
  spacingVertical: 8,
  paddingX: 8,
  wrapCjkWidth: 18,
  maxWidth: 280,
} as const

export function wrapTitle(title: string, maxCjk = KNOWLEDGE_MAP_THEME.wrapCjkWidth): string {
  const chars = Array.from(title || '')
  if (!chars.length) return ''
  const lines: string[] = []
  let cur = ''
  let width = 0
  for (const ch of chars) {
    const w = /[\u4e00-\u9fff]/.test(ch) ? 1 : 0.5
    if (width + w > maxCjk && cur) {
      lines.push(cur)
      cur = ch
      width = w
    } else {
      cur += ch
      width += w
    }
  }
  if (cur) lines.push(cur)
  return lines.join('<br>')
}

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function branchColor(depth: number, branchIndex: number): string {
  if (depth <= 0) return KNOWLEDGE_MAP_THEME.rootColor
  const colors = KNOWLEDGE_MAP_THEME.branchColors
  return colors[Math.abs(branchIndex) % colors.length]
}
