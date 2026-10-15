import { renderMiniLatex } from '@/utils/latexMini'
import type { RenderedFormula } from './formulaRenderer'
export function renderFormula(source: string, display: boolean, color: string): RenderedFormula {
  return { html: '', nodes: renderMiniLatex(source, display, color) }
}
