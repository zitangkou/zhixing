import type { Component } from 'vue'
import {
  Calendar,
  Collection,
  DataAnalysis,
  Document,
  Folder,
  Notebook,
  Reading,
  Setting,
  Tickets,
  TrendCharts,
  Promotion,
  User,
} from '@element-plus/icons-vue'
import { isAdminNavVisible } from '@/config/featureVisibility'

export interface NavItem {
  path: string
  title: string
  icon: Component
  /** 任一权限即可显示；空数组表示登录即可 */
  permissions: string[]
}

export interface NavGroup {
  key: string
  title: string
  icon: Component
  children: NavItem[]
}

/** 侧栏菜单：按业务域分组的两级结构 */
export const NAV_GROUPS: NavGroup[] = [
  {
    key: 'content',
    title: '时政考点',
    icon: Document,
    children: [
      { path: '/articles', title: '文章管理', icon: Document, permissions: ['article:read'] },
      { path: '/categories', title: '分类管理', icon: Folder, permissions: ['article:read', 'article:write'] },
    ],
  },
  {
    key: 'rmrb',
    title: '时评精拆',
    icon: Notebook,
    children: [
      { path: '/rmrb/articles', title: '时评文章', icon: Document, permissions: ['rmrb:read'] },
      { path: '/rmrb/term-categories', title: '规范词分类', icon: Collection, permissions: ['rmrb:read'] },
      { path: '/rmrb/skeletons', title: '骨架模版', icon: Notebook, permissions: ['rmrb:read'] },
      { path: '/rmrb/argument-methods', title: '论证方法', icon: Reading, permissions: ['rmrb:read'] },
      { path: '/rmrb/sentence-types', title: '句式类型', icon: Tickets, permissions: ['rmrb:read'] },
    ],
  },
  {
    key: 'teaching',
    title: '备考教学',
    icon: Reading,
    children: [
      { path: '/knowledge', title: '知识框架', icon: Collection, permissions: ['knowledge:read'] },
      { path: '/plan', title: '学习计划', icon: Calendar, permissions: ['plan:read'] },
      { path: '/exam', title: '试卷题库', icon: Tickets, permissions: ['exam:read'] },
      { path: '/question-bank/questions', title: '题目资产', icon: Collection, permissions: ['exam:read'] },
      { path: '/question-bank/papers', title: '真题试卷', icon: Tickets, permissions: ['exam:read'] },
      { path: '/generation', title: '生成工作台', icon: Collection, permissions: ['exam:read'] },
      { path: '/generation/review', title: '教研审核', icon: Promotion, permissions: ['exam:read'] },
      { path: '/ziliao', title: '资料分析', icon: Tickets, permissions: ['ziliao:read'] },
      { path: '/practice/proto', title: '练习闭环原型', icon: Reading, permissions: ['exam:read'] },
    ],
  },
  {
    key: 'analytics',
    title: '学习反馈',
    icon: DataAnalysis,
    children: [
      { path: '/analytics/dashboard', title: '反馈看板', icon: TrendCharts, permissions: ['exam:read'] },
      { path: '/analytics/error-paths', title: '错因归集', icon: DataAnalysis, permissions: ['exam:read'] },
    ],
  },
  {
    key: 'material',
    title: '素材积累',
    icon: Notebook,
    children: [
      { path: '/corpus', title: '语料本', icon: Collection, permissions: ['corpus:read'] },
      { path: '/events', title: '时事事件', icon: TrendCharts, permissions: ['events:read'] },
    ],
  },
  {
    key: 'system',
    title: '系统',
    icon: Setting,
    children: [
      { path: '/users', title: '用户管理', icon: User, permissions: ['user:read'] },
      { path: '/settings', title: '系统设置', icon: Setting, permissions: ['setting:read', 'admin:read'] },
    ],
  },
]

/** 拍平后的全部叶子菜单（路由守卫回退、首页跳转用） */
export const FLAT_NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.children)

/** @deprecated 兼容旧引用，等价于 FLAT_NAV_ITEMS */
export const NAV_ITEMS: NavItem[] = FLAT_NAV_ITEMS

export const ROUTE_TITLES: Record<string, string> = {
  '/articles': '文章管理',
  '/articles/new': '新建文章',
  '/content-ops': '账号运营',
  '/theory-learning': '时政学习入口',
  '/categories': '分类管理',
  '/users': '用户管理',
  '/knowledge': '知识框架',
  '/plan': '学习计划',
  '/exam': '试卷题库',
  '/question-bank/questions': '题目资产',
  '/question-bank/papers': '真题试卷',
  '/generation': '生成工作台',
  '/generation/review': '教研审核',
  '/ziliao': '资料分析',
  '/practice/proto': '练习闭环原型',
  '/analytics/dashboard': '学习反馈看板',
  '/analytics/error-paths': '错因归集',
  '/rmrb/articles': '时评文章',
  '/rmrb/import': '三刀导入',
  '/rmrb/term-categories': '规范词分类',
  '/rmrb/skeletons': '骨架模版',
  '/rmrb/argument-methods': '论证方法',
  '/rmrb/sentence-types': '句式类型',
  '/corpus': '语料本',
  '/events': '时事事件',
  '/settings': '系统设置',
}

export function canAccess(userPerms: string[], required: string[]): boolean {
  if (!required.length) return true
  if (userPerms.includes('*')) return true
  return required.some((p) => userPerms.includes(p))
}

export function visibleNavGroups(): NavGroup[] {
  return NAV_GROUPS.map((group) => ({
    ...group,
    children: group.children.filter((item) => isAdminNavVisible(item.path)),
  })).filter((group) => group.children.length > 0)
}

export function visibleNavItems(): NavItem[] {
  return visibleNavGroups().flatMap((g) => g.children)
}
