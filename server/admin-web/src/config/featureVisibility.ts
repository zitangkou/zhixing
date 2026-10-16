/** 管理端侧栏露出。路由仍注册，直链可进。隐藏项见项目功能与操作手册。 */

const VISIBLE_PATHS = new Set([
  '/theory-briefs',
  '/rmrb-archive/quotes',
  '/rmrb-archive/shenlun-materials',
  '/rmrb-archive/vocabulary',
  '/knowledge',
  '/ziliao',
  '/users',
  '/feedbacks',
  '/settings',
  '/tool-config/images',
  '/tool-config/models',
  '/tool-config/image-generation-jobs',
  '/tool-config/llm-usage',
  '/wechat-replies',
  '/roles',
  '/project-manual',
])

export function isAdminNavVisible(path: string): boolean {
  return VISIBLE_PATHS.has(path)
}
