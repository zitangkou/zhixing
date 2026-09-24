import { TaroElement, document as taroDocument } from '@tarojs/runtime'

/**
 * 小程序模板渲染不出 Vue 的 data-v 属性。把 scope id 记成 class，
 * 与 config/weappScopedCss.ts 改写后的 `.data-v-hash` 选择器对应。
 *
 * Vue 先 setScopeId，再 patch class，所以写 class 时要把已记录的 scope id 拼回去。
 */
const SCOPE_ATTR = /^data-v-[0-9a-f]+(?:-s)?$/
const SCOPE_IDS = '__zkScopeIds'
const PATCHED = '__zkScopeClassPatched'

type ScopeHost = {
  setAttribute: (name: string, value: unknown) => void
  removeAttribute: (name: string) => void
  getAttribute: (name: string) => string | null
  [SCOPE_IDS]?: string[]
  [PATCHED]?: boolean
}

function tokens(value: unknown): string[] {
  if (value == null || value === false) return []
  return String(value)
    .split(/\s+/)
    .filter(Boolean)
}

function withScope(el: ScopeHost, value: unknown): string {
  const cls = tokens(value).filter((token) => !SCOPE_ATTR.test(token))
  const ids = el[SCOPE_IDS] || []
  for (const id of ids) {
    if (!cls.includes(id)) cls.push(id)
  }
  return cls.join(' ')
}

export function installWeappScopeClass(): void {
  if (process.env.TARO_ENV !== 'weapp') return
  const proto = TaroElement.prototype as unknown as ScopeHost
  if (proto[PATCHED]) return
  proto[PATCHED] = true

  const origSet = proto.setAttribute
  const origRemove = proto.removeAttribute

  proto.setAttribute = function (name: string, value: unknown) {
    const el = this as ScopeHost
    if (SCOPE_ATTR.test(name)) {
      const ids = el[SCOPE_IDS] || (el[SCOPE_IDS] = [])
      if (!ids.includes(name)) ids.push(name)
      origSet.call(el, name, value)
      origSet.call(el, 'class', withScope(el, el.getAttribute('class')))
      return
    }
    if (name === 'class') {
      origSet.call(el, name, withScope(el, value))
      return
    }
    origSet.call(el, name, value)
  }

  proto.removeAttribute = function (name: string) {
    const el = this as ScopeHost
    if (SCOPE_ATTR.test(name)) {
      const ids = el[SCOPE_IDS]
      if (ids) {
        const index = ids.indexOf(name)
        if (index >= 0) ids.splice(index, 1)
      }
      origRemove.call(el, name)
      const next = withScope(el, el.getAttribute('class'))
      if (next) origSet.call(el, 'class', next)
      else origRemove.call(el, 'class')
      return
    }
    if (name === 'class') {
      const next = withScope(el, '')
      if (next) origSet.call(el, 'class', next)
      else origRemove.call(el, 'class')
      return
    }
    origRemove.call(el, name)
  }
}

/**
 * Vue 的 onClick 在小程序里注册成 click，基础库只派发 tap。
 * nut-cell / nut-switch 的根是 view，改成 tap 就能点。
 * nut-button 的根是原生 button，见下面的标签映射：disabled 空绑定会吞掉 tap。
 * 同时写了 @click 和 @tap 的节点会挂上两个 tap；业务回调本身可重复调用。
 */
const CLICK_PATCHED = '__zkClickAlias'

function installWeappClickAlias(): void {
  if (process.env.TARO_ENV !== 'weapp') return
  const proto = TaroElement.prototype as unknown as {
    addEventListener: (type: string, handler: unknown, options?: unknown) => void
    removeEventListener: (type: string, handler: unknown, sideEffect?: unknown) => void
    [CLICK_PATCHED]?: boolean
  }
  if (proto[CLICK_PATCHED]) return
  proto[CLICK_PATCHED] = true
  const origAdd = proto.addEventListener
  const origRemove = proto.removeEventListener
  proto.addEventListener = function (type: string, handler: unknown, options?: unknown) {
    const name = String(type || '').toLowerCase()
    if (name === 'click') return origAdd.call(this, 'tap', handler, options)
    return origAdd.call(this, type, handler, options)
  }
  proto.removeEventListener = function (type: string, handler: unknown, sideEffect?: unknown) {
    const name = String(type || '').toLowerCase()
    if (name === 'click') return origRemove.call(this, 'tap', handler, sideEffect)
    return origRemove.call(this, type, handler, sideEffect)
  }
}

/**
 * NutUI 图标默认标签是 i。base.wxml 没有 tmpl_0_i，
 * 基础库在每次 setData 报 Template not found，图标格子是空的。
 * i 改走 view（:before 图标字体才能画出来）；其它行内标签改走 text，块级标签改走 view。
 *
 * NutUI Button 渲染原生 button。模板里是 disabled="{{i.pN}}"，没有像 loading 那样的 false 兜底。
 * NutUI 不传 disabled 时这个值是 undefined，按钮看起来正常，但基础库不派发 tap，所以没有报错。
 * 页面上的 @click 只是在等子组件 emit，点不到内部 button 就不会进 onLogin。
 * 本应用没有 open-type / form-type=submit，把 button 画成 view 后走和「去注册」一样的 tap。
 */
const AS_TEXT = new Set([
  'em',
  'b',
  'strong',
  'span',
  'small',
  'sub',
  'sup',
  'u',
  's',
  'cite',
  'code',
  'abbr',
  'del',
  'ins',
  'mark',
  'font',
])
const AS_VIEW = new Set([
  'div',
  'p',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'section',
  'article',
  'header',
  'footer',
  'nav',
  'ul',
  'ol',
  'li',
  'br',
  'figure',
  'figcaption',
])

function installWeappHtmlTagMap(): void {
  if (process.env.TARO_ENV !== 'weapp') return
  const proto = Object.getPrototypeOf(taroDocument) as {
    createElement?: (type: string) => unknown
    __zkHtmlTagMap?: boolean
  }
  if (!proto?.createElement || proto.__zkHtmlTagMap) return
  proto.__zkHtmlTagMap = true
  const orig = proto.createElement
  proto.createElement = function (type: string) {
    const name = String(type || '').toLowerCase()
    // button：见上方注释。必须在通用映射之前。
    if (name === 'i' || name === 'button') return orig.call(this, 'view')
    if (AS_TEXT.has(name)) return orig.call(this, 'text')
    if (AS_VIEW.has(name)) return orig.call(this, 'view')
    return orig.call(this, type)
  }
}

installWeappScopeClass()
installWeappHtmlTagMap()
installWeappClickAlias()
