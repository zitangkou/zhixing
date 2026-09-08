/** 游客可浏览；其余页面先登录。 */

export const LOGIN_REDIRECT_KEY = 'zhixing_login_redirect'

const GUEST_PREFIXES = [
  '/pages/article/',
  '/pages/auth/',
  '/pages/rmrb/article-list',
  '/pages/rmrb/article-detail',
]

const GUEST_EXACT = new Set([
  '/pages/today/index',
  '/pages/index/index',
  '/pages/question/index',
  '/pages/question/theory-packs',
  '/pages/question/article-pick',
  '/pages/user/index',
  '/pages/rmrb/index',
  '/pages/rmrb/article-list',
  '/pages/rmrb/article-detail',
])

export function normalizePagePath(url: string): string {
  const path = (url || '').split('?')[0]
  return path.startsWith('/') ? path : `/${path}`
}

/** 当前路径是否允许未登录访问 */
export function isGuestAllowedPath(url: string): boolean {
  const path = normalizePagePath(url)
  if (GUEST_EXACT.has(path)) return true
  return GUEST_PREFIXES.some((p) => path === p || path.startsWith(p))
}
