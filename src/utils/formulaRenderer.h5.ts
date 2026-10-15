import { renderLatex } from '@/utils/latex'
import type { RenderedFormula } from './formulaRenderer'
export function renderFormula(source: string, display: boolean, _color: string): RenderedFormula {
  return { html: renderLatex(source, { displayMode: display }), nodes: [] }
}
