import fs from 'fs'
import path from 'path'
import type { Plugin } from 'vite'

/**
 * Taro 4.0.9 的 vite 小程序分包把 Vue 打进 taro.js，却把 @babel/runtime
 * 打进 vendors.js。NutUI 等 vendors 在模块初始化时调用 taro.defineComponent，
 * 而 taro.js 又在导出 defineComponent 之前 require(vendors.js)，循环依赖下
 * defineComponent 仍是空值，微信开发者工具报 `e.defineComponent is not a function`。
 *
 * 与上游 https://github.com/NervJS/taro/pull/17541 相同：把 @babel 拆到独立的
 * babelHelpers chunk，让 taro chunk 不再依赖 vendors。
 *
 * 额外：KaTeX 仅资料（ziliao）公式页使用。默认会进主包 vendors（JS + 三套字体
 * base64 约 1.4MB）。这里把 katex / latex 工具 / LatexBlock 打进
 * pages/ziliao/katex，并在 CSS 里只保留 woff2，避免主包/分包超限。
 */
const BABEL_DEP = /node_modules[\\/]@babel[\\/]/
const KATEX_DEP = /node_modules[\\/]katex[\\/]/
const LATEX_UTIL = /[\\/]utils[\\/]latex\.ts$/
const LATEX_BLOCK = /[\\/]components[\\/]LatexBlock\.vue$/

/** 去掉同包的 woff/ttf（含 Vite 已 base64 内联的 data: URL），只留 woff2。 */
export function stripKatexExtraFonts(css: string): string {
  if (!css.includes('KaTeX_') && !/katex/i.test(css)) return css
  let next = css
  // 构建前：url(fonts/xxx.woff) format("woff")
  next = next.replace(/,?\s*url\(([^)]+\.woff)\)\s*format\("woff"\)/g, '')
  next = next.replace(/,?\s*url\(([^)]+\.ttf)\)\s*format\("truetype"\)/g, '')
  // 构建后：url(data:font/woff;base64,...) format("woff")
  next = next.replace(
    /,?\s*url\(data:font\/woff;base64,[A-Za-z0-9+/=]+\)\s*format\("woff"\)/g,
    '',
  )
  next = next.replace(
    /,?\s*url\(data:font\/(?:ttf|truetype);base64,[A-Za-z0-9+/=]+\)\s*format\("truetype"\)/g,
    '',
  )
  next = next.replace(/src:\s*,/g, 'src:')
  next = next.replace(/format\("woff2"\)\s*,(?=\s*[;}])/g, 'format("woff2")')
  return next
}

function isKatexRelatedModule(id: string): boolean {
  const bare = id.split('?')[0] || id
  return KATEX_DEP.test(bare) || LATEX_UTIL.test(bare) || LATEX_BLOCK.test(bare)
}

function walkStripWxss(dir: string) {
  if (!fs.existsSync(dir)) return
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      walkStripWxss(full)
      continue
    }
    if (!entry.name.endsWith('.wxss')) continue
    const css = fs.readFileSync(full, 'utf8')
    if (!css.includes('KaTeX_') && !css.includes('font/woff')) continue
    const next = stripKatexExtraFonts(css)
    if (next !== css) fs.writeFileSync(full, next)
  }
}

export function weappBreakVueChunkCycle(): Plugin {
  return {
    name: 'weapp-break-vue-chunk-cycle',
    apply: 'build',
    enforce: 'post',
    config(viteConfig) {
      if (process.env.TARO_ENV !== 'weapp') return
      const output = viteConfig.build?.rollupOptions?.output
      if (!output || Array.isArray(output) || typeof output.manualChunks !== 'function') return
      const original = output.manualChunks
      output.manualChunks = (id, meta) => {
        if (BABEL_DEP.test(id)) return 'babelHelpers'
        // chunkFileNames 为 [name].js → 落在分包目录，不进主包 vendors
        if (isKatexRelatedModule(id)) return 'pages/ziliao/katex'
        return original(id, meta)
      }
    },
    transform(code, id) {
      if (process.env.TARO_ENV !== 'weapp') return null
      const bare = id.split('?')[0] || id
      if (!KATEX_DEP.test(bare) || !/\.css$/i.test(bare)) return null
      const next = stripKatexExtraFonts(code)
      if (next === code) return null
      return { code: next, map: null }
    },
    writeBundle(options) {
      if (process.env.TARO_ENV !== 'weapp') return
      const dir = options.dir || path.resolve('dist')
      walkStripWxss(dir)
    },
  }
}
