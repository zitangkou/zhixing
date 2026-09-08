export type ProductTabKey = 'home' | 'user' | 'today' | 'quiz'

export interface ProductNavigationTab {
  key: ProductTabKey
  path: string
  text: string
  icon: 'home' | 'user'
}

export const CURRENT_PRODUCT_TABS: ProductNavigationTab[] = [
  { key: 'home', path: '/pages/index/index', text: '学习', icon: 'home' },
  { key: 'user', path: '/pages/user/index', text: '我的', icon: 'user' },
]

export const PRODUCT_HOME_ROUTE = CURRENT_PRODUCT_TABS[0].path
