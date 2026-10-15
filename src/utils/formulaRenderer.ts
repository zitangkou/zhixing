import type { FormulaNode } from '@/utils/latexMini'
export interface RenderedFormula {
  html: string
  nodes: FormulaNode[]
}
/** Taro 按端解析 .h5.ts / .weapp.ts，其他平台保留可读式。 */
export function renderFormula(_source: string, _display: boolean, _color: string): RenderedFormula {
  return { html: '', nodes: [] }
}
