/**
 * 小程序端的 latex 工具（Taro 多端文件：weapp 构建时替代 latex.ts）。
 *
 * 小程序里 v-html 会把 KaTeX 的 HTML 转成 view/text，KaTeX 的 class 样式与根号等
 * SVG 都无法还原，公式会错乱（如 \dfrac{1}{7} 显示成「71」）。因此小程序不打包
 * KaTeX，renderLatex 恒返回空串，LatexBlock 改显示纯文本。H5 仍走 latex.ts。
 */

export function renderLatex(_tex: string, _opts?: { displayMode?: boolean }): string {
  return ''
}

export async function preloadKatex(): Promise<void> {
  /* 小程序不加载 KaTeX */
}
