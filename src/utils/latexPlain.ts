/**
 * LaTeX → 可读纯文本（不依赖 KaTeX）。
 *
 * 小程序端不打包 KaTeX（v-html / rich-text 还原不了它的样式和 SVG），公式优先显示
 * 数据里的 formula_plain；缺失时用这里把常见 LaTeX 粗略转成文本，如
 * `\dfrac{A_{1}}{1+r}` → `A₁/(1+r)`，`10\sqrt{3}` → `10√3`。
 */

const SUB_MAP: Record<string, string> = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
  '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
  a: 'ₐ', e: 'ₑ', h: 'ₕ', i: 'ᵢ', j: 'ⱼ', k: 'ₖ', l: 'ₗ', m: 'ₘ', n: 'ₙ', o: 'ₒ', p: 'ₚ', r: 'ᵣ',
  s: 'ₛ', t: 'ₜ', u: 'ᵤ', v: 'ᵥ', x: 'ₓ',
}

const SUP_MAP: Record<string, string> = {
  '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
  '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾', n: 'ⁿ', i: 'ⁱ',
}

const SYMBOLS: Array<[RegExp, string]> = [
  [/\s*\\times\s*/g, '×'],
  [/\s*\\div\s*/g, '÷'],
  [/\s*\\cdot\s*/g, '·'],
  [/\\pm\s*/g, '±'],
  [/\s*\\approx\s*/g, '≈'],
  [/\s*\\neq\s*/g, '≠'],
  [/\s*\\leq?(?![a-z])\s*/g, '≤'],
  [/\s*\\geq?(?![a-z])\s*/g, '≥'],
  [/\\Delta\s*/g, 'Δ'],
  [/\\pi(?![a-z])\s*/g, 'π'],
  [/\\%/g, '%'],
  [/\\(?:quad|qquad|[,;: !])/g, ' '],
]

function mapScript(raw: string, table: Record<string, string>, marker: string): string {
  const body = raw.trim()
  const chars = [...body]
  if (chars.length && chars.every((ch) => table[ch])) return chars.map((ch) => table[ch]).join('')
  return chars.length > 1 ? `${marker}(${body})` : `${marker}${body}`
}

/** 分子/分母含运算符时加括号，避免 a+b/c 这类歧义。 */
function wrap(part: string): string {
  const s = part.trim()
  return /[+\-−×÷·/\s]/.test(s) && s.length > 1 ? `(${s})` : s
}

export function latexToPlain(tex: string): string {
  let s = (tex || '').trim()
  if (!s) return ''
  s = s.replace(/^\$+|\$+$/g, '').replace(/^\\\(|\\\)$/g, '').replace(/^\\\[|\\\]$/g, '')
  s = s.replace(/\\(?:left|right)\s*/g, '')
  s = s.replace(/\\(?:text|mathrm|textrm|mathbf|operatorname)\s*\{([^{}]*)\}/g, '$1')

  let prev = ''
  while (prev !== s) {
    prev = s
    s = s.replace(/_\{([^{}]*)\}/g, (_m, b: string) => mapScript(b, SUB_MAP, '_'))
    s = s.replace(/\^\{([^{}]*)\}/g, (_m, b: string) => mapScript(b, SUP_MAP, '^'))
    s = s.replace(/\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, (_m, a: string, b: string) => `${wrap(a)}/${wrap(b)}`)
    s = s.replace(/\\sqrt\s*\{([^{}]*)\}/g, (_m, a: string) => `√${wrap(a)}`)
    s = s.replace(/\\(?:bar|overline)\s*\{([^{}]*)\}/g, (_m, a: string) => `${a.trim()}\u0304`)
  }
  s = s.replace(/_([A-Za-z0-9])/g, (_m, b: string) => mapScript(b, SUB_MAP, '_'))
  s = s.replace(/\^([A-Za-z0-9])/g, (_m, b: string) => mapScript(b, SUP_MAP, '^'))
  for (const [re, rep] of SYMBOLS) s = s.replace(re, rep)
  s = s.replace(/\\([A-Za-z]+)/g, '$1').replace(/[{}]/g, '')
  return s.replace(/\s+/g, ' ').replace(/\(\s+/g, '(').replace(/\s+\)/g, ')').trim()
}
