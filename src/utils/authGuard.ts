import Taro from '@tarojs/taro'
import { isGuestAllowedPath, normalizePagePath } from '@/constants/guestAccess'
import { isAuthPageRoute, isLoggedIn, requireLogin } from '@/utils/auth'

function queryFromParams(params?: Record<string, string>): string {
  if (!params) return ''
  const qs = Object.entries(params)
    .filter(([, v]) => v != null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&')
  return qs ? `?${qs}` : ''
}

/** 深链/刷新进入绑定页时补登录，不踢回首页。 */
export function guardGuestRoute(): void {
  if (isLoggedIn()) return
  try {
    const inst = Taro.getCurrentInstance()
    const route = inst.router?.path || ''
    if (!route) return
    const path = normalizePagePath(route)
    if (isAuthPageRoute(path) || isGuestAllowedPath(path)) return
    const qs = queryFromParams(inst.router?.params as Record<string, string> | undefined)
    requireLogin(`${path}${qs}`)
  } catch {
    /* ignore */
  }
}

function allowNav(url: string): boolean {
  return isLoggedIn() || isGuestAllowedPath(url)
}

/** 拦截直调 Taro.navigateTo，避免绕过游客白名单。 */
export function installNavGuards(): void {
  const nav = Taro.navigateTo.bind(Taro)
  const red = Taro.redirectTo.bind(Taro)
  const rel = Taro.reLaunch.bind(Taro)

  Taro.navigateTo = ((opts: Taro.navigateTo.Option) => {
    const url = opts.url || ''
    if (!allowNav(url)) {
      requireLogin(url)
      return Promise.resolve({ errMsg: 'navigateTo:ok' })
    }
    return nav(opts)
  }) as typeof Taro.navigateTo

  Taro.redirectTo = ((opts: Taro.redirectTo.Option) => {
    const url = opts.url || ''
    if (!allowNav(url)) {
      requireLogin(url)
      return Promise.resolve({ errMsg: 'redirectTo:ok' })
    }
    return red(opts)
  }) as typeof Taro.redirectTo

  Taro.reLaunch = ((opts: Taro.reLaunch.Option) => {
    const url = opts.url || ''
    if (!allowNav(url)) {
      requireLogin(url)
      return Promise.resolve({ errMsg: 'reLaunch:ok' })
    }
    return rel(opts)
  }) as typeof Taro.reLaunch
}
