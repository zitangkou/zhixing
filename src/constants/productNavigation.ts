import { CURRENT_PRODUCT_KEY } from './product'

export type ProductTabKey = 'today' | 'home' | 'quiz' | 'user'

export interface ProductNavigationTab {
  key: ProductTabKey
  path: string
  text: string
  icon: 'clock' | 'home' | 'edit' | 'user'
}

const PRODUCT_NAVIGATION: Record<string, ProductNavigationTab[]> = {
  general: [
    { key: 'today', path: '/pages/today/index', text: '今日', icon: 'clock' },
    { key: 'home', path: '/pages/index/index', text: '学习', icon: 'home' },
    { key: 'quiz', path: '/pages/question/index', text: '练习', icon: 'edit' },
    { key: 'user', path: '/pages/user/index', text: '我的', icon: 'user' },
  ],
  shenlun: [
    { key: 'today', path: '/pages/rmrb/index', text: '今日', icon: 'clock' },
    { key: 'home', path: '/pages/rmrb/article-list', text: '精读', icon: 'home' },
    { key: 'quiz', path: '/pages/rmrb/drill', text: '训练', icon: 'edit' },
    { key: 'user', path: '/pages/user/index', text: '我的', icon: 'user' },
  ],
  theory: [
    { key: 'today', path: '/pages/theory/index', text: '今日', icon: 'clock' },
    { key: 'home', path: '/pages/index/index', text: '专题', icon: 'home' },
    { key: 'quiz', path: '/pages/question/index', text: '刷题', icon: 'edit' },
    { key: 'user', path: '/pages/user/index', text: '我的', icon: 'user' },
  ],
}

export const CURRENT_PRODUCT_TABS = PRODUCT_NAVIGATION[CURRENT_PRODUCT_KEY]
export const PRODUCT_HOME_ROUTE = CURRENT_PRODUCT_TABS[0].path
