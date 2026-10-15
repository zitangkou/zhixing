import parse from '@rojer/katex-mini'

export interface FormulaNode {
  type?: string
  name?: string
  text?: string
  attrs?: Record<string, string>
  children?: FormulaNode[]
}

/** SVG 根号、伸展符号被转成图片，必须显式写入主题色才能适配深色。 */
function colorSvg(nodes: FormulaNode[], color: string): FormulaNode[] {
  for (const node of nodes) {
    const src = node.attrs?.src
    if (src?.startsWith('data:image/svg+xml,')) {
      const svg = decodeURIComponent(src.slice(src.indexOf(',') + 1)).replace(
        /<svg\b([^>]*)>/,
        (_match, attributes: string) =>
          /\bfill=/.test(attributes)
            ? `<svg${attributes}>`
            : `<svg fill="${color}" color="${color}"${attributes}>`,
      )
      node.attrs!.src = 'data:image/svg+xml,' + encodeURIComponent(svg)
    }
    if (node.children) colorSvg(node.children, color)
  }
  return nodes
}

export function renderMiniLatex(latex: string, displayMode: boolean, color: string): FormulaNode[] {
  return colorSvg(
    parse(latex, {
      displayMode,
      throwError: true,
      throwOnError: true,
      strict: 'ignore',
      trust: false,
      maxExpand: 500,
      maxSize: 20,
    }) as FormulaNode[],
    color,
  )
}
