export const IMPORTANCE_LABELS: Record<number, string> = {
  1: '了解',
  2: '熟悉',
  3: '掌握',
  4: '重点',
  5: '必考',
}

export const IMPORTANCE_TAG_TYPE: Record<number, 'default' | 'primary' | 'warning' | 'danger'> = {
  1: 'default',
  2: 'default',
  3: 'primary',
  4: 'warning',
  5: 'danger',
}

export const QUIZ_MODES = [
  { mode: 'random' as const, title: '随机刷题', desc: '全库随机抽题', icon: 'Refresh' },
  { mode: 'article' as const, title: '按文章练', desc: '选一篇文章出题', icon: 'Category' },
]
