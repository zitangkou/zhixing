/** 管理端侧栏露出。路由仍注册，直链可进。与学员端 featureVisibility 对齐。 */

const VISIBLE_PATHS = new Set([
  '/today',
  '/articles',
  '/categories',
  '/rmrb/articles',
  '/rmrb/term-categories',
  '/rmrb/skeletons',
  '/rmrb/argument-methods',
  '/rmrb/sentence-types',
  '/users',
  '/settings',
])

export function isAdminNavVisible(path: string): boolean {
  return VISIBLE_PATHS.has(path)
}
