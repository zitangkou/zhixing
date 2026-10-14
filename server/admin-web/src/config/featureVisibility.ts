/** 管理端侧栏露出。路由仍注册，直链可进。与学员端 featureVisibility 对齐。 */

const VISIBLE_PATHS = new Set([
  '/today',
  '/articles',
  '/theory-briefs',
  '/categories',
  '/wechat-replies',
  '/rmrb/articles',
  '/rmrb-archive/quotes',
  '/rmrb/term-categories',
  '/rmrb/skeletons',
  '/rmrb/argument-methods',
  '/rmrb/sentence-types',
  '/users',
  '/feedbacks',
  '/xingce',
  '/tool-config/copy',
  '/tool-config/images',
  '/tool-config/models',
  '/tool-config/image-generation-jobs',
  '/knowledge',
  '/knowledge-library',
  '/settings',
  '/roles',
  '/project-manual',
  '/english/overview',
  '/english/courses',
  '/english/records',
  '/photography/courses',
  '/photography/map',
  '/photography/cases',
])

export function isAdminNavVisible(path: string): boolean {
  return VISIBLE_PATHS.has(path)
}
