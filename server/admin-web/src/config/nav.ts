import type { Component } from 'vue'
import {
  Calendar,
  Collection,
  Cpu,
  DataAnalysis,
  Document,
  Folder,
  Notebook,
  Reading,
  ChatDotRound,
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
      { path: '/today', title: '今日学员端', icon: Calendar, permissions: ['article:read', 'rmrb:read'] },
      { path: '/articles', title: '文章管理', icon: Document, permissions: ['article:read'] },
      { path: '/categories', title: '分类管理', icon: Folder, permissions: ['article:read', 'article:write'] },
    ],
  },
  {
    key: 'official-account',
    title: '公众号运营',
    icon: ChatDotRound,
    children: [
      { path: '/wechat-replies', title: '消息回复', icon: ChatDotRound, permissions: ['wechat_reply:read'] },
    ],
  },
  {
    key: 'rmrb-archive',
    title: '人民日报',
    icon: Reading,
    children: [
      { path: '/rmrb-archive/articles', title: '全量文章', icon: Document, permissions: ['rmrb:read'] },
      { path: '/rmrb-archive/batches', title: '采集批次', icon: Calendar, permissions: ['rmrb:read'] },
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
      { path: '/knowledge-library', title: '知库文档', icon: Document, permissions: ['knowledge:read'] },
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
    key: 'english',
    title: '英语学习',
    icon: ChatDotRound,
    children: [
      { path: '/english/overview', title: '学习概览', icon: DataAnalysis, permissions: ['english:read'] },
      { path: '/english/courses', title: '场景与课程', icon: Reading, permissions: ['english:read'] },
      { path: '/english/records', title: '学习记录', icon: Tickets, permissions: ['english:read'] },
    ],
  },
  {
    key: 'photography',
    title: '摄影学习',
    icon: Reading,
    children: [
      { path: '/photography/courses', title: '技巧课程', icon: Reading, permissions: ['photography:read'] },
      { path: '/photography/map', title: '知识地图', icon: Collection, permissions: ['photography:read'] },
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
    key: 'tool-config',
    title: '工具配置',
    icon: Folder,
    children: [
      { path: '/tool-config/copy', title: '文案配置', icon: Document, permissions: ['setting:read'] },
      { path: '/tool-config/images', title: '图片配置', icon: Collection, permissions: ['setting:read'] },
      { path: '/tool-config/models', title: '模型配置', icon: Cpu, permissions: ['setting:read'] },
      { path: '/tool-config/image-generation-jobs', title: '图片生成记录', icon: Tickets, permissions: ['setting:read'] },
    ],
  },
  {
    key: 'system',
    title: '系统',
    icon: Setting,
    children: [
      { path: '/users', title: '用户管理', icon: User, permissions: ['user:read'] },
      { path: '/feedbacks', title: '反馈建议', icon: ChatDotRound, permissions: ['feedback:read'] },
      { path: '/xingce', title: '行测管理', icon: Tickets, permissions: ['xingce:read'] },
      { path: '/settings', title: '系统设置', icon: Setting, permissions: ['setting:read'] },
      { path: '/roles', title: '角色与权限', icon: User, permissions: ['admin:read'] },
    ],
  },
]

/** 拍平后的全部叶子菜单（路由守卫回退、首页跳转用） */
export const FLAT_NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.children)

/** @deprecated 兼容旧引用，等价于 FLAT_NAV_ITEMS */
export const NAV_ITEMS: NavItem[] = FLAT_NAV_ITEMS

export const ROUTE_TITLES: Record<string, string> = {
  '/today': '今日学员端',
  '/articles': '文章管理',
  '/articles/new': '新建文章',
  '/content-ops': '账号运营',
  '/wechat-replies': '公众号消息回复',
  '/theory-learning': '时政学习入口',
  '/categories': '分类管理',
  '/users': '用户管理',
  '/feedbacks': '反馈建议',
  '/xingce': '行测管理',
  '/tool-config/copy': '文案配置',
  '/tool-config/images': '图片配置',
  '/tool-config/models': '模型配置',
  '/tool-config/image-generation-jobs': '图片生成记录',
  '/knowledge': '知识框架',
  '/knowledge-library': '知库文档',
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
  '/rmrb-archive/articles': '全量文章',
  '/rmrb-archive/batches': '采集批次',
  '/rmrb/import': '三刀导入',
  '/rmrb/term-categories': '规范词分类',
  '/rmrb/skeletons': '骨架模版',
  '/rmrb/argument-methods': '论证方法',
  '/rmrb/sentence-types': '句式类型',
  '/corpus': '语料本',
  '/events': '时事事件',
  '/english/overview': '英语学习 · 学习概览',
  '/english/courses': '英语学习 · 场景与课程',
  '/english/records': '英语学习 · 学习记录',
  '/photography/courses': '摄影学习 · 技巧课程',
  '/photography/map': '摄影学习 · 知识地图',
  '/settings': '系统设置',
  '/roles': '角色与权限',
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
