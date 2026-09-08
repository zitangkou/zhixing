/** 主题色：深蓝 */
export const PRIMARY_COLOR = '#1E3A5F'
export const BG_COLOR = '#FFFFFF'
export const PAGE_BG = '#F5F5F5'

/** 艾宾浩斯复习间隔（天） */
export const REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30] as const

/** 积分规则 */
export const POINTS_RULES = {
  SIGN_BASE: 5,
  SIGN_STREAK_BONUS: 10,
  READ_ARTICLE: 3,
  CORRECT_ANSWER: 2,
  WRONG_REVIEW: 5,
  FEEDBACK_ADOPTED: 10,
} as const

/** 政治术语关键词（用于出题挖空） */
export const POLITICAL_KEYWORDS = [
  '两个确立',
  '两个维护',
  '新质生产力',
  '中国式现代化',
  '根本保证',
  '核心',
  '本质',
  '根本立场',
  '最大优势',
  '必由之路',
  '根本方向',
  '根本任务',
  '鲜明特色',
  '本质要求',
  '战略支撑',
  '根本遵循',
]

export type RankType = 'daily' | 'weekly' | 'monthly' | 'total'

export const RANK_TYPE_LABELS: Record<RankType, string> = {
  daily: '日榜',
  weekly: '周榜',
  monthly: '月榜',
  total: '总榜',
}
