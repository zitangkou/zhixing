import { normalizePagePath } from '@/constants/guestAccess'
import { CURRENT_PRODUCT_TABS, PRODUCT_HOME_ROUTE } from '@/constants/productNavigation'

export interface PostAuthTarget {
  method: 'switchTab' | 'reLaunch' | 'redirectTo'
  url: string
}

/** 与 H5 AppTabBar、微信单页 Tab 容器共用同一份主 Tab 列表。 */
const TAB_PATHS = new Set(CURRENT_PRODUCT_TABS.map((tab) => tab.path))

function homeTarget(): PostAuthTarget {
  return process.env.TARO_ENV === 'weapp'
    ? { method: 'reLaunch', url: PRODUCT_HOME_ROUTE }
    : { method: 'switchTab', url: PRODUCT_HOME_ROUTE }
}

function withQuery(raw: string, path: string): string {
  const index = raw.indexOf('?')
  if (index < 0) return path
  const query = raw.slice(index)
  return query.length > 1 ? `${path}${query}` : path
}

/**
 * 登录/注册成功后的去向。
 * 空跳转经 normalize 会变成 "/"，微信 redirectTo 报 page "" is not found。
 * 微信主 Tab 由单页容器承载；普通页保留查询串走 redirectTo。
 */
export function resolveAfterAuthTarget(redirect: string): PostAuthTarget {
  const raw = (redirect || '').trim()
  const path = normalizePagePath(raw)
  if (!path.startsWith('/pages/') || path.includes('/pages/auth/')) {
    return homeTarget()
  }
  if (TAB_PATHS.has(path)) {
    if (process.env.TARO_ENV === 'weapp') {
      return {
        method: 'reLaunch',
        url: path.endsWith('/user/index') ? `${PRODUCT_HOME_ROUTE}?tab=user` : PRODUCT_HOME_ROUTE,
      }
    }
    return { method: 'switchTab', url: path }
  }
  return { method: 'redirectTo', url: withQuery(raw, path) }
}
