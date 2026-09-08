import Taro from '@tarojs/taro'
import { getToken } from '@/utils/auth'
import type {
  CorpusItem,
  CorpusStats,
  KnowledgeTree,
  ShenlunArgumentSkeleton,
  ShenlunMeta,
  ShenlunMineLog,
  ShenlunMineTermItem,
  ShenlunNormTerm,
  ShenlunQuoteItem,
  ShenlunDrillLog,
  ShenlunSkeletonStructure,
  ShenlunSkeletonTemplate,
  ShenlunTemplateItem,
  ShenlunTermCategory,
  ShenlunVerbItem,
} from '@/types'

export interface ApiResponse<T> {
  code: number
  data: T | null
  message: string
}

export type DailyTaskState = 'not_started' | 'in_progress' | 'submitted' | 'reviewed' | 'completed'
export type DailyTaskEvent = 'start' | 'save' | 'submit' | 'review' | 'complete'

export interface DailyTaskProgress {
  state: DailyTaskState
  currentStep: number
  totalSteps: number
  draft: Record<string, unknown>
  updatedAt?: string
}

export interface DailyLearningTask {
  id: string
  productKey: 'shenlun'
  taskDate: string
  taskType: string
  title: string
  description: string
  contentType: string
  contentId: string
  estimatedMinutes: number
  totalSteps: number
  sortOrder: number
  metadata: Record<string, unknown>
  progress: DailyTaskProgress
}

export interface DailyTaskList {
  date: string
  productKey: 'shenlun'
  completion: number
  completedCount: number
  totalCount: number
  estimatedMinutes: number
  tasks: DailyLearningTask[]
}

export interface ShenlunStats {
  weekMineDays: number
  weekMineTarget: number
  termCount: number
  learningTermCount: number
  todayMined: boolean
  weekDrillCount: number
}

export interface RmrbArticle {
  id: string
  title: string
  source: string
  sourceUrl: string
  publishDate: string
  summary: string
  content: string
  tags: string[]
  isPublished: boolean
  sortOrder: number
  readCount: number
}

export interface ShenlunLearningArticle {
  id: string
  title: string
  source: string
  sourceUrl: string
  publishDate: string
  summary: string
  content: string
  tags: string[]
  teachingVersion: string
}

export interface ShenlunTeachingPractice {
  prompt: string
  minLength: number
  maxLength: number
  checks: string[]
  referenceAnswer: string
}

export interface ShenlunTeachingExample {
  id: string
  version: string
  sourceExcerpt: string
  argument: ShenlunArgumentSkeleton
  terms: ShenlunMineTermItem[]
  quotes: ShenlunQuoteItem[]
  verbs: ShenlunVerbItem[]
  templates: ShenlunTemplateItem[]
  practice: ShenlunTeachingPractice
}

export interface ShenlunLearningBundle {
  article: Omit<ShenlunLearningArticle, 'teachingVersion'>
  example: ShenlunTeachingExample
  revision: string
}

export interface GuestLearningRecord {
  recordType: 'shenlun_short_practice'
  contentId: string
  revision: string
  payload: Record<string, unknown>
  updatedAt: string
}

export interface GuestLearningMergeResult {
  accepted: number
  unchanged: number
  records: GuestLearningRecord[]
}

export interface UserMe {
  id: string
  username?: string
  nickname: string
  avatar: string
  email: string
  phone: string
  isMember: boolean
  points: number
  hasSignedToday: boolean
  signDates: string[]
}

export interface ShenlunMine {
  id: string
  mineDate: string
  articleId: string
  articleTitle: string
  sourceExcerpt: string
  argumentChain: string
  templateSentence: string
  terms: Array<{ term: string; category: string; plainWord?: string }>
}

export interface ShenlunDrill {
  id: string
  drillType: 'sentence' | 'imitate' | 'oral'
  content: string
  prompt: string
  refMineId?: string | null
  refTermIds: string[]
  createdAt: string
}

interface AuthResult { access_token: string; token_type: string; user: UserMe }

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: unknown
  auth?: boolean
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
  const token = options.auth === false ? '' : getToken()
  try {
    const response = await Taro.request<ApiResponse<T>>({
      url: `${API_BASE_URL}${path}`,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Content-Type': 'application/json',
        'X-Product-Key': PRODUCT_KEY,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
    if (response.statusCode === 401 || response.statusCode === 403) {
      return { code: response.statusCode, data: null, message: '登录后同步你的今日任务' }
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      const detail = (response.data as unknown as { detail?: string })?.detail
      return {
        code: response.statusCode,
        data: null,
        message: detail || `服务暂不可用（${response.statusCode}）`,
      }
    }
    return response.data
  } catch {
    return { code: -1, data: null, message: '暂时无法连接学习服务' }
  }
}

export const api = {
  mergeGuestRecords(deviceId: string, records: GuestLearningRecord[]) {
    return request<GuestLearningMergeResult>('/api/learning/guest-records/merge', {
      method: 'POST', data: { deviceId, records },
    })
  },
  login(username: string, password: string) {
    return request<AuthResult>('/api/auth/login', {
      method: 'POST', data: { username, password }, auth: false,
    })
  },
  register(username: string, password: string, passwordConfirm: string) {
    return request<AuthResult>('/api/auth/register', {
      method: 'POST', data: { username, password, passwordConfirm }, auth: false,
    })
  },
  getMe() { return request<UserMe>('/api/user/me') },
  submitFeedback(content: string) {
    return request<{ id: string; status: string; adopted: boolean }>('/api/feedback', { method: 'POST', data: { content } })
  },
  getDailyTasks(date?: string) {
    const query = date ? `?date=${encodeURIComponent(date)}` : ''
    return request<DailyTaskList>(`/api/product/daily-tasks${query}`)
  },
  updateDailyTask(
    taskId: string,
    payload: { event: DailyTaskEvent; currentStep?: number; draft?: Record<string, unknown> },
  ) {
    return request<DailyLearningTask>(`/api/product/daily-tasks/${taskId}/progress`, {
      method: 'POST',
      data: payload,
    })
  },
  getStats() {
    return request<ShenlunStats>('/api/rmrb/stats')
  },
  getRmrbStats() {
    return request<ShenlunStats>('/api/rmrb/stats')
  },
  getRmrbMeta() { return request<ShenlunMeta>('/api/rmrb/meta') },
  createRmrbSkeletonTemplate(data: {
    name: string
    description?: string
    mode?: string
    structure?: ShenlunSkeletonStructure
    sortOrder?: number
    isEnabled?: boolean
  }) {
    return request<ShenlunSkeletonTemplate>('/api/rmrb/skeleton-templates', { method: 'POST', data })
  },
  createRmrbTermCategory(data: {
    name: string
    kind?: 'term' | 'verb' | string
    sortOrder?: number
    isEnabled?: boolean
  }) {
    return request<ShenlunTermCategory>('/api/rmrb/term-categories', { method: 'POST', data })
  },
  getRmrbMine(id: string) { return request<ShenlunMineLog>(`/api/rmrb/mines/${id}`) },
  getRmrbMineByDate(date: string) {
    return request<ShenlunMineLog>(`/api/rmrb/mines/by-date/${encodeURIComponent(date)}`)
  },
  upsertRmrbMine(data: {
    mineDate?: string
    articleId?: string | null
    articleTitle?: string
    sourceExcerpt?: string
    argumentChain?: string
    templateSentence?: string
    terms?: Array<ShenlunMineTermItem | string>
    quotes?: ShenlunQuoteItem[]
    verbs?: ShenlunVerbItem[]
    argument?: ShenlunArgumentSkeleton
    templates?: ShenlunTemplateItem[]
  }) {
    return request<ShenlunMineLog>('/api/rmrb/mines', { method: 'POST', data })
  },
  updateRmrbMine(id: string, data: Partial<{
    articleId: string | null
    articleTitle: string
    sourceExcerpt: string
    argumentChain: string
    templateSentence: string
    terms: Array<ShenlunMineTermItem | string>
    quotes: ShenlunQuoteItem[]
    verbs: ShenlunVerbItem[]
    argument: ShenlunArgumentSkeleton
    templates: ShenlunTemplateItem[]
  }>) {
    return request<ShenlunMineLog>(`/api/rmrb/mines/${id}`, { method: 'PUT', data })
  },
  deleteRmrbMine(id: string) {
    return request<{ ok: boolean }>(`/api/rmrb/mines/${id}`, { method: 'DELETE' })
  },
  listRmrbMines() {
    return request<ShenlunMineLog[]>('/api/rmrb/mines')
  },
  listRmrbTerms(status?: 'learning' | 'mastered', category?: string) {
    const query = [
      status ? `status=${encodeURIComponent(status)}` : '',
      category ? `category=${encodeURIComponent(category)}` : '',
    ].filter(Boolean).join('&')
    return request<ShenlunNormTerm[]>(`/api/rmrb/terms${query ? `?${query}` : ''}`)
  },
  addRmrbTerm(data: {
    term: string
    category?: string
    usageNote?: string
    sourceTitle?: string
    exampleSentence?: string
    articleId?: string | null
  }) {
    return request<ShenlunNormTerm>('/api/rmrb/terms', { method: 'POST', data })
  },
  updateRmrbTerm(id: string, data: Partial<{
    category: string
    usageNote: string
    exampleSentence: string
    familiarity: number
    mastered: boolean
    sourceTitle: string
  }>) {
    return request<ShenlunNormTerm>(`/api/rmrb/terms/${id}`, { method: 'PUT', data })
  },
  deleteRmrbTerm(id: string) {
    return request<{ ok: boolean }>(`/api/rmrb/terms/${id}`, { method: 'DELETE' })
  },
  listRmrbDrills(drillType?: 'sentence' | 'imitate' | 'oral') {
    const query = drillType ? `?drill_type=${encodeURIComponent(drillType)}` : ''
    return request<ShenlunDrillLog[]>(`/api/rmrb/drills${query}`)
  },
  addRmrbDrill(data: {
    drillType: 'sentence' | 'imitate' | 'oral'
    content: string
    prompt?: string
    refMineId?: string | null
    refTermIds?: string[]
  }) {
    return request<ShenlunDrillLog>('/api/rmrb/drills', { method: 'POST', data })
  },
  getCorpusStats() {
    return request<CorpusStats>('/api/corpus/stats')
  },
  getCorpusItem(id: string) {
    return request<CorpusItem>(`/api/corpus/items/${id}`)
  },
  createCorpusItem(data: {
    original: string
    kind?: string
    sourceType?: string
    sourceTitle?: string
    tags?: string[]
    plainNote?: string
    rewrite?: string
    practice?: string
    knowledgeNodeId?: string | null
    knowledgeTreeKey?: string
    knowledgePath?: string
  }) {
    return request<CorpusItem>('/api/corpus/items', { method: 'POST', data })
  },
  updateCorpusItem(id: string, data: Partial<{
    original: string
    kind: string
    sourceType: string
    sourceTitle: string
    tags: string[]
    plainNote: string
    rewrite: string
    practice: string
    markUsed: boolean
    knowledgeNodeId: string | null
    knowledgeTreeKey: string
    knowledgePath: string
  }>) {
    return request<CorpusItem>(`/api/corpus/items/${id}`, { method: 'PUT', data })
  },
  deleteCorpusItem(id: string) {
    return request<{ ok: boolean }>(`/api/corpus/items/${id}`, { method: 'DELETE' })
  },
  promoteCorpusToTerm(id: string) {
    return request<CorpusItem>(`/api/corpus/items/${id}/promote-term`, { method: 'POST' })
  },
  getKnowledgeTrees() {
    return request<KnowledgeTree[]>('/api/knowledge/trees')
  },
  getKnowledgeTree(treeKey: string) {
    return request<KnowledgeTree>(`/api/knowledge/tree/${encodeURIComponent(treeKey)}`)
  },
  listLearningArticles() {
    return request<ShenlunLearningArticle[]>('/api/shenlun/learning/articles', { auth: false })
  },
  getLearningArticle(id: string) {
    return request<ShenlunLearningBundle>(`/api/shenlun/learning/articles/${encodeURIComponent(id)}`, { auth: false })
  },
  listArticles() { return request<RmrbArticle[]>('/api/rmrb/articles') },
  getArticle(id: string) { return request<RmrbArticle>(`/api/rmrb/articles/${id}`) },
  saveMine(data: {
    articleId: string
    articleTitle: string
    sourceExcerpt: string
    argumentChain: string
    templateSentence: string
    terms: string[]
  }) { return request<{ id: string }>('/api/rmrb/mines', { method: 'POST', data }) },
  listMines() { return request<ShenlunMine[]>('/api/rmrb/mines') },
  listDrills() { return request<ShenlunDrill[]>('/api/rmrb/drills') },
  addDrill(data: {
    drillType: 'sentence' | 'imitate' | 'oral'
    content: string
    prompt: string
    refMineId?: string | null
    refTermIds?: string[]
  }) { return request<ShenlunDrill>('/api/rmrb/drills', { method: 'POST', data }) },
}
