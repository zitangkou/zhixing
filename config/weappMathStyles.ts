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
  fs.writeFileSync(path.join(dir, 'katex-mini.wxss'), css)
  // rich-text 内部 class 需要处于承载它的 Taro 自定义组件样式作用域。
  fs.appendFileSync(path.join(dir, 'comp.wxss'), '@import "./katex-mini.wxss";\n')
}
