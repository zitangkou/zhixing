import fs from 'fs'
import path from 'path'
import type { Plugin } from 'vite'

/**
 * Vue scoped 编译成 `[data-v-hash]` 属性选择器。Taro 的 base.wxml 只绑定
 * class / style / 已知属性，data-v 不会出现在节点上，于是小程序里整页规则都不命中。
 * H5 的 DOM 会写入该属性，所以 H5 正常。
 *
 * 这里把属性选择器改成同类名。运行时见 src/utils/weappScopeClass.ts：
 * setAttribute('data-v-*') 时把同名 class 写进节点。
 *
 * `:root` / `page[data-v]` 改成 class 后仍匹配不到页面根，默认 CSS 变量要落在 `page` 上才能继承。
 */
const SCOPE_ATTR = /\[(data-v-[0-9a-f]+(?:-s)?)\]/g
const SCOPED_ROOT_PAIR = /\[(data-v-[0-9a-f]+(?:-s)?)\]:root\s*,\s*page\[\1\]/g

export function rewriteWeappScopedCss(css: string): string {
  if (!css.includes('[data-v-')) return css
  const withPageTokens = css.replace(SCOPED_ROOT_PAIR, 'page')
  return withPageTokens.replace(SCOPE_ATTR, '.$1')
}

function rewriteWxssFile(file: string) {
  const css = fs.readFileSync(file, 'utf8')
  const next = rewriteWeappScopedCss(css)
  if (next !== css) fs.writeFileSync(file, next)
}

const PAGE_META =
  '<page-meta page-style="{{zkTheme.pageStyle}}" background-color="{{zkTheme.backgroundColor}}" background-color-top="{{zkTheme.backgroundColorTop}}" background-color-bottom="{{zkTheme.backgroundColorBottom}}" root-background-color="{{zkTheme.rootBackgroundColor}}" background-text-style="{{zkTheme.backgroundTextStyle}}" />'

function patchPageWxml(file: string) {
  const rel = file.split(path.sep).join('/')
  if (!rel.includes('/pages/')) return
  let xml = fs.readFileSync(file, 'utf8')
  if (xml.includes('<page-meta')) return
  if (xml.includes('<import')) xml = xml.replace(/(<import[^>]*\/>)/, `$1\n${PAGE_META}`)
  else xml = `${PAGE_META}\n${xml}`
  fs.writeFileSync(file, xml)
}

function patchPageJson(file: string) {
  const rel = file.split(path.sep).join('/')
  if (!rel.includes('/pages/') || !file.endsWith('.json')) return
  const json = JSON.parse(fs.readFileSync(file, 'utf8')) as Record<string, unknown>
  if (json.enablePageMeta === true) return
  json.enablePageMeta = true
  fs.writeFileSync(file, JSON.stringify(json, null, 2) + '\n')
}

function patchCompJson(file: string) {
  if (path.basename(file) !== 'comp.json') return
  const json = JSON.parse(fs.readFileSync(file, 'utf8')) as Record<string, unknown>
  if (json.addGlobalClass === true) return
  json.addGlobalClass = true
  fs.writeFileSync(file, JSON.stringify(json, null, 2) + '\n')
}

/** 页面 wxss 引入 app-origin，apply-shared 才能把 .theme-dark .nut-* 打进自定义组件。 */
function importAppOrigin(file: string) {
  const rel = file.split(path.sep).join('/')
  if (!rel.includes('/pages/') || !file.endsWith('.wxss')) return
  let css = fs.readFileSync(file, 'utf8')
  if (css.includes('app-origin.wxss')) return
  const stmt = '@import "../../app-origin.wxss";'
  css = css.startsWith('@charset') ? css.replace(/^(@charset[^;]+;)/, `$1${stmt}`) : `${stmt}${css}`
  fs.writeFileSync(file, css)
}

function walkDist(dir: string) {
  if (!fs.existsSync(dir)) return
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) walkDist(full)
    else if (entry.name.endsWith('.wxss')) {
      rewriteWxssFile(full)
      importAppOrigin(full)
    } else if (entry.name.endsWith('.wxml')) patchPageWxml(full)
    else if (entry.name.endsWith('.json')) {
      patchPageJson(full)
      patchCompJson(full)
    }
  }
}

export function weappScopedCss(): Plugin {
  return {
    name: 'weapp-scoped-css',
    apply: 'build',
    enforce: 'post',
    transform(code, id) {
      if (process.env.TARO_ENV !== 'weapp') return null
      if (!id.includes('type=style') && !/[?&]lang\.(css|scss)/.test(id)) return null
      const next = rewriteWeappScopedCss(code)
      if (next === code) return null
      return { code: next, map: null }
    },
    writeBundle(options) {
      if (process.env.TARO_ENV !== 'weapp') return
      const dir = options.dir || path.resolve('dist')
      walkDist(dir)
    },
  }
}
