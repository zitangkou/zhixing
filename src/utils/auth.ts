import Taro from '@tarojs/taro'
import { LOGIN_REDIRECT_KEY, normalizePagePath } from '@/constants/guestAccess'
import { PRODUCT_HOME_ROUTE } from '@/constants/productNavigation'

const TAB_PATHS = new Set([
  '/pages/index/index',
  '/pages/user/index',
])

const TOKEN_KEY = 'zhixing_token'

export function getToken(): string {
  return Taro.getStorageSync(TOKEN_KEY) || ''
}

export function setToken(token: string): void {
  Taro.setStorageSync(TOKEN_KEY, token)
}

export function clearToken(): void {
  Taro.removeStorageSync(TOKEN_KEY)
}

export function isLoggedIn(): boolean {
  return !!getToken()
}

export function isAuthPageRoute(route?: string): boolean {
  return !!route?.includes('pages/auth/')
}

export function rememberLoginRedirect(url?: string): void {
  if (url) Taro.setStorageSync(LOGIN_REDIRECT_KEY, url)
}

export function consumeLoginRedirect(): string {
  const url = Taro.getStorageSync(LOGIN_REDIRECT_KEY) || ''
  if (url) Taro.removeStorageSync(LOGIN_REDIRECT_KEY)
  return url
}

/** 未登录则去登录页，登录后尽量回到当前功能。已登录返回 true。 */
export function requireLogin(redirectUrl?: string): boolean {
  if (isLoggedIn()) return true
  const pages = Taro.getCurrentPages()
  const current = pages[pages.length - 1]
  const fallback = current?.route ? `/${current.route}` : PRODUCT_HOME_ROUTE
  rememberLoginRedirect(redirectUrl || fallback)
  if (isAuthPageRoute(current?.route)) return false
  Taro.navigateTo({ url: '/pages/auth/login' })
  return false
}

/** 登录成功后回到原功能（含查询串），否则进首页 */
export function enterAfterAuth(): void {
  const redirect = consumeLoginRedirect()
  const path = normalizePagePath(redirect)
  if (TAB_PATHS.has(path)) {
    Taro.switchTab({ url: path })
    return
  }
  if (path && !path.includes('/pages/auth/')) {
    const url = redirect.startsWith('/') ? redirect : `/${redirect}`
    Taro.redirectTo({ url })
    return
  }
  Taro.switchTab({ url: PRODUCT_HOME_ROUTE })
}

export function skipAuth(): void {
  Taro.switchTab({ url: PRODUCT_HOME_ROUTE })
}
