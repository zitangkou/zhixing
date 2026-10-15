/** 保留正文，仅把显式分隔符及 latex 围栏转为公式；未闭合内容按原文展示。 */
export interface MathSegment {
  type: 'text' | 'formula'
  text: string
  display: boolean
}

export function normalizeLatex(source: string): string {
  const text = source.trim()
  const wrappers = [
    ['$$', '$$'],
    ['\\[', '\\]'],
    ['\\(', '\\)'],
    ['$', '$'],
  ]
  for (const [left, right] of wrappers) {
    if (text.startsWith(left) && text.endsWith(right) && text.length > left.length + right.length)
      return text.slice(left.length, -right.length).trim()
  }
  return text.replace(/^```(?:latex|math|tex)\s*\n([\s\S]*?)\n```$/i, '$1').trim()
}

export function splitMathText(source: string): MathSegment[] {
  const result: MathSegment[] = []
  const pattern =
    /```(?:latex|math|tex)\s*\n([\s\S]*?)\n```|\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([^\n]+?)\\\)|\$(?!\$)([^$\n]+?)\$(?!\$)/g
  let cursor = 0
  let match: RegExpExecArray | null
  while ((match = pattern.exec(source)) !== null) {
    const index = match.index
    let escapes = 0
    for (let i = index - 1; i >= 0 && source[i] === '\\'; i--) escapes++
    if (escapes % 2 || (match[5] && source[index - 1] === '$')) continue
    if (index > cursor)
      result.push({ type: 'text', text: source.slice(cursor, index), display: false })
    const tex = match[1] ?? match[2] ?? match[3] ?? match[4] ?? match[5]
    result.push({
      type: 'formula',
      text: tex.trim(),
      display: !!(match[1] || match[2] || match[3]),
    })
    cursor = index + match[0].length
  }
  if (cursor < source.length)
    result.push({ type: 'text', text: source.slice(cursor), display: false })
  return result
}
