export interface ApiRes<T> {
  code: number
  data: T
  message: string
}

export interface PageResult<T> {
  total: number
  items: T[]
  pending_total?: number
}

export interface AdminToken {
  access_token: string
  token_type: string
  username: string
  role: string
  permissions: string[]
}

export interface AdminUser {
  id: number
  username: string
  nickname: string
  role_code: string
  is_active: boolean
  created_at: string
  permissions?: string[]
}

export interface Category {
  id: string
  name: string
  parentId?: string | null
  sortOrder?: number
  children?: Category[]
}

export interface Article {
  id: string
  title: string
  source: string
  publishDate: string
  summary: string
  content: string
  tags: string[]
  sections?: unknown[]
  readCount?: number
  categoryId?: string | null
  categoryName?: string | null
  categoryPath?: string[]
  importance?: number
  importanceLabel?: string
  status?: string
  allowQuiz?: boolean
  isFeatured?: boolean
  isDaily?: boolean
}

export interface Question {
  id: string
  articleId: string
  type: string
  stem: string
  options?: string[]
  correctAnswer: string | string[]
  analysis: string
  sourceSentence: string
  status?: string
  origin?: string
  isActive?: boolean
}

export interface AppUser {
  id: string
  nickname: string
  avatar: string
  points: number
  is_member: boolean
  is_active: boolean
  created_at: string
}


export const ARTICLE_STATUSES = [
  { value: 'draft', label: '草稿' },
  { value: 'pending', label: '待审核' },
  { value: 'published', label: '已发布' },
  { value: 'rejected', label: '已驳回' },
]

export const IMPORTANCE_OPTIONS = [
  { value: 1, label: '了解' },
  { value: 2, label: '熟悉' },
  { value: 3, label: '掌握' },
  { value: 4, label: '重点' },
  { value: 5, label: '必考' },
]

export const QUESTION_STATUSES = [
  { value: 'pending', label: '待审核' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已驳回' },
]

export const QUESTION_TYPES = [
  { value: 'single', label: '单选' },
  { value: 'multiple', label: '多选' },
  { value: 'judge', label: '判断' },
]

// ===== 知识框架 =====

export interface KnowledgeNode {
  id: string
  treeKey: string
  parentId: string | null
  title: string
  content: string
  myNote: string
  isStarred: boolean
  depth: number
  sortOrder: number
  path: string
  sourceFile: string
  children?: KnowledgeNode[] | null
}

export interface KnowledgeTree {
  treeKey: string
  title: string
  nodes: KnowledgeNode[]
}

export interface KnowledgeStatus {
  kb_dir: string
  kb_exists: boolean
  local_kb_dir: string
  tree_counts: Record<string, number>
  tree_titles: Record<string, string>
}
