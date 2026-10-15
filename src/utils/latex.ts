/** LaTeX → HTML（KaTeX）。失败时返回空串，UI 用 formulaPlain 兜底。 */

import katex from 'katex'
import 'katex/dist/katex.min.css'

export function renderLatex(tex: string, opts?: { displayMode?: boolean }): string {
  const src = (tex || '').trim()
  if (!src) return ''
  try {
    return katex.renderToString(src, {
      throwOnError: true,
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
