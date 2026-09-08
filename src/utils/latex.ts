/** LaTeX → HTML（KaTeX）。失败时返回空串，UI 用 formulaPlain 兜底。 */

import katex from 'katex'
import 'katex/dist/katex.min.css'

export function renderLatex(tex: string, opts?: { displayMode?: boolean }): string {
  const src = (tex || '').trim()
  if (!src) return ''
  // 旧数据：中文可读式写在 latex 字段，无 TeX 命令
  if (!src.includes('\\') && !/[$_^]/.test(src)) return ''
  try {
    return katex.renderToString(src, {
      throwOnError: false,
      strict: 'ignore',
      displayMode: opts?.displayMode !== false,
      output: 'html',
    })
  } catch {
    return ''
  }
}

export async function preloadKatex(): Promise<void> {
  /* sync import 已完成 */
}
