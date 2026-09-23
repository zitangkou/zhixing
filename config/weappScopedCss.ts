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

function walkWxss(dir: string) {
  if (!fs.existsSync(dir)) return
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) walkWxss(full)
    else if (entry.name.endsWith('.wxss')) rewriteWxssFile(full)
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
      walkWxss(dir)
    },
  }
}
