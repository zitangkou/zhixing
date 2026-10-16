import fs from 'fs'
import path from 'path'

/** 构建时内嵌本地字体，避免小程序依赖境外字体 CDN 和额外域名配置。 */
export function writeWeappMathStyles(dir: string): void {
  const source = path.resolve('node_modules/@rojer/katex-mini/dist/index.css')
  let css = fs.readFileSync(source, 'utf8')
  css = css.replace(/@font-face\{[^}]+\}/g, (rule) => {
    const font = rule.match(/\/([^/()]+\.woff2)/)?.[1]
    if (!font) throw new Error('KaTeX font rule has no woff2 source')
    const bytes = fs.readFileSync(path.resolve('node_modules/katex/dist/fonts', font))
    return rule.replace(
      /src:[^;]+;/,
      `src:url(data:font/woff2;base64,${bytes.toString('base64')}) format("woff2");`,
    )
  })
  // 公式只在知识框架和资料分析分包页面使用。避免把约 360 KB 的字体
  // 样式加入主包 comp.wxss，导致微信代码质量检查主包超过 1.5 MB。
  const formulaPages = [
    'pages/knowledge/index.wxss',
    'pages/ziliao/quick-calc.wxss',
    'pages/ziliao/formulas.wxss',
    'pages/ziliao/formula-detail.wxss',
  ]
  for (const page of formulaPages) {
    const subpackageDir = path.dirname(path.join(dir, page))
    fs.mkdirSync(subpackageDir, { recursive: true })
    fs.writeFileSync(path.join(subpackageDir, 'katex-mini.wxss'), css)
    const pageStyles = path.join(dir, page)
    if (!fs.existsSync(pageStyles)) throw new Error(`缺少公式页面样式：${page}`)
    const current = fs.readFileSync(pageStyles, 'utf8')
    if (!current.includes('katex-mini.wxss')) {
      fs.appendFileSync(pageStyles, '\n@import "./katex-mini.wxss";\n')
    }
  }
}
