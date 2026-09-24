import { normalizePagePath } from '@/constants/guestAccess'
import { CURRENT_PRODUCT_TABS, PRODUCT_HOME_ROUTE } from '@/constants/productNavigation'

export interface PostAuthTarget {
  method: 'switchTab' | 'redirectTo'
  url: string
}

/** 与 app.config.ts tabBar、H5 AppTabBar 同一份列表。非 tab 页不能 switchTab。 */
const TAB_PATHS = new Set(CURRENT_PRODUCT_TABS.map((tab) => tab.path))

function withQuery(raw: string, path: string): string {
  const index = raw.indexOf('?')
  if (index < 0) return path
  const query = raw.slice(index)
  return query.length > 1 ? `${path}${query}` : path
}

/**
 * 登录/注册成功后的去向。
 * 空跳转经 normalize 会变成 "/"，微信 redirectTo 报 page "" is not found。
 * tabBar 只能 switchTab；普通页保留查询串走 redirectTo。
 */
export function resolveAfterAuthTarget(redirect: string): PostAuthTarget {
  const raw = (redirect || '').trim()
  const path = normalizePagePath(raw)
  if (!path.startsWith('/pages/') || path.includes('/pages/auth/')) {
    return { method: 'switchTab', url: PRODUCT_HOME_ROUTE }
  }
  if (TAB_PATHS.has(path)) {
    return { method: 'switchTab', url: path }
  }
  return { method: 'redirectTo', url: withQuery(raw, path) }
}
