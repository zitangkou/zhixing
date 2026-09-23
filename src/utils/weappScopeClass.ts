import { TaroElement } from '@tarojs/runtime'

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

  proto.setAttribute = function (this: ScopeHost, name: string, value: unknown) {
    if (SCOPE_ATTR.test(name)) {
      const ids = this[SCOPE_IDS] || (this[SCOPE_IDS] = [])
      if (!ids.includes(name)) ids.push(name)
      origSet.call(this, name, value)
      origSet.call(this, 'class', withScope(this, this.getAttribute('class')))
      return
    }
    if (name === 'class') {
      origSet.call(this, name, withScope(this, value))
      return
    }
    origSet.call(this, name, value)
  }

  proto.removeAttribute = function (this: ScopeHost, name: string) {
    if (SCOPE_ATTR.test(name)) {
      const ids = this[SCOPE_IDS]
      if (ids) {
        const index = ids.indexOf(name)
        if (index >= 0) ids.splice(index, 1)
      }
      origRemove.call(this, name)
      const next = withScope(this, this.getAttribute('class'))
      if (next) origSet.call(this, 'class', next)
      else origRemove.call(this, 'class')
      return
    }
    if (name === 'class') {
      const next = withScope(this, '')
      if (next) origSet.call(this, 'class', next)
      else origRemove.call(this, 'class')
      return
    }
    origRemove.call(this, name)
  }
}

installWeappScopeClass()
