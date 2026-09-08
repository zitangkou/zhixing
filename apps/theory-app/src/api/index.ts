import Taro from '@tarojs/taro'
import { getToken } from '@/utils/auth'
import type {
  CorpusItem,
  CorpusStats,
  KnowledgeTree,
  MindMapNode,
  QuizCompleteResult,
  ReviewTask,
  StudyRecord,
  WrongQuestionRecord,
} from '@/types'

export interface ApiResponse<T> {
  code: number
  data: T | null
  message: string
}

export type DailyTaskState = 'not_started' | 'in_progress' | 'submitted' | 'reviewed' | 'completed'
export type DailyTaskEvent = 'start' | 'save' | 'submit' | 'review' | 'complete'

export interface DailyLearningTask {
  id: string
  productKey: 'theory'
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
  progress: {
    state: DailyTaskState
    currentStep: number
    totalSteps: number
    draft: Record<string, unknown>
    updatedAt?: string
  }
}

export interface DailyTaskList {
  date: string
  productKey: 'theory'
  completion: number
  completedCount: number
  totalCount: number
  estimatedMinutes: number
  tasks: DailyLearningTask[]
}

export interface TopicItem {
  no: string
  title: string
  desc: string
}

export interface TopicList {
  productKey: string
  items: TopicItem[]
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

export interface ArticleSection {
  id: string
  title: string
  level: number
  content?: string
  highlight?: string
  children?: ArticleSection[]
}

export interface Article {
  id: string
  title: string
  source: string
  publishDate: string
  summary: string
  content: string
  sections: ArticleSection[]
  tags: string[]
  mindMap: MindMapNode
}

export interface Question {
  id: string
  articleId: string
  type: 'single' | 'multiple' | 'judge'
  stem: string
  options?: string[]
  correctAnswer: string | string[]
  analysis: string
  sourceSentence: string
}

export interface AnswerResult {
  correct: boolean
  analysis: string
  correctAnswer: string | string[]
  pointsEarned: number
}

export interface LearningBundle {
  article: Article
  revision: string
  collectionComplete: boolean
  questions: Omit<Question, 'correctAnswer' | 'analysis' | 'sourceSentence'>[]
  parts: { number: number; title?: string; questionIds: string[] }[]
}

export interface TheoryLearningEntry {
  id: string
  articleId: string
  articleTitle: string
  title: string
  description: string
  source: string
  publishDate: string
  tags: string[]
  isDaily: boolean
  isEvergreen: boolean
  parts: { number: number; title: string; questionIds: string[] }[]
  questionCount: number
  collectionEnabled: boolean
}

export interface GuestLearningRecord {
  recordType: 'theory_article_quiz'
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

interface AuthResult { access_token: string; token_type: string; user: UserMe }

async function request<T>(path: string, options: { method?: 'GET' | 'POST' | 'PUT' | 'DELETE'; data?: unknown; auth?: boolean } = {}): Promise<ApiResponse<T>> {
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
      return { code: response.statusCode, data: null, message: '登录后同步你的今日学习包' }
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      const detail = (response.data as unknown as { detail?: unknown })?.detail
      if (typeof detail === 'string') return { code: response.statusCode, data: null, message: detail }
      return { code: response.statusCode, data: null, message: `服务暂不可用（${response.statusCode}）` }
    }
    return response.data
  } catch {
    return { code: -1, data: null, message: '暂时无法连接学习服务' }
  }
}

export const api = {
  listLearningEntries() {
    return request<TheoryLearningEntry[]>('/api/learning/entries', { auth: false })
  },
  mergeGuestRecords(deviceId: string, records: GuestLearningRecord[]) {
    return request<GuestLearningMergeResult>('/api/learning/guest-records/merge', {
      method: 'POST', data: { deviceId, records },
    })
  },
  getLearningBundle(articleId: string) {
    return request<LearningBundle>(`/api/learning/articles/${encodeURIComponent(articleId)}`, { auth: false })
  },
  checkLearningAnswer(articleId: string, revision: string, questionId: string, answer: string | string[]) {
    return request<AnswerResult & { sourceSentence: string }>(`/api/learning/articles/${encodeURIComponent(articleId)}/check`, {
      method: 'POST', auth: false, data: { revision, questionId, answer },
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
  getTopics() { return request<TopicList>('/api/product/topics') },
  submitFeedback(content: string) {
    return request<{ id: string; status: string; adopted: boolean }>('/api/feedback', { method: 'POST', data: { content } })
  },
  getDailyTasks(date?: string) {
    const query = date ? `?date=${encodeURIComponent(date)}` : ''
    return request<DailyTaskList>(`/api/product/daily-tasks${query}`)
  },
  updateDailyTask(taskId: string, payload: { event: DailyTaskEvent; currentStep?: number; draft?: Record<string, unknown> }) {
    return request<DailyLearningTask>(`/api/product/daily-tasks/${taskId}/progress`, { method: 'POST', data: payload })
  },
  getArticle(articleId: string) { return request<Article>(`/api/articles/${articleId}`) },
  getDailyArticles() { return request<Article[]>('/api/articles/daily', { auth: false }) },
  getRecommendedArticles(offset = 0, limit = 20) {
    return request<{ items: Article[]; total: number; hasMore: boolean }>(
      `/api/articles/recommended?offset=${offset}&limit=${limit}`,
      { auth: false },
    )
  },
  getQuestions(articleId: string) {
    return request<Question[]>(`/api/questions?articleId=${encodeURIComponent(articleId)}`)
  },
  markArticleRead(articleId: string) {
    return request<{ points: number }>(`/api/articles/${articleId}/read`, { method: 'POST' })
  },
  submitAnswer(questionId: string, answer: string | string[]) {
    return request<AnswerResult>('/api/answer', { method: 'POST', data: { questionId, answer } })
  },
  getQuizByMode(mode: string, count = 10) {
    return request<Question[]>(`/api/quiz?mode=${encodeURIComponent(mode)}&count=${count}`)
  },
  getWrongQuestions(status: 'review' | 'waiting' | 'all' = 'review') {
    return request<WrongQuestionRecord[]>(`/api/wrong?status=${encodeURIComponent(status)}`)
  },
  redoWrongQuestion(questionId: string, answer: string | string[]) {
    return request<AnswerResult>('/api/wrong/redo', {
      method: 'POST',
      data: { questionId, answer },
    })
  },
  removeWrongQuestion(questionId: string) {
    return request<null>(`/api/wrong/${encodeURIComponent(questionId)}`, { method: 'DELETE' })
  },
  completeQuiz(data: { articleId?: string; mode: string; total: number; correct: number }) {
    return request<QuizCompleteResult>('/api/quiz/complete', { method: 'POST', data })
  },
  getSectionReads() {
    return request<Record<string, string[]>>('/api/study/section-reads')
  },
  getStudyRecords() { return request<StudyRecord[]>('/api/study/records') },
  getReviewTasks() { return request<ReviewTask[]>('/api/review') },
  completeReview(articleId: string) {
    return request<null>('/api/review/complete', { method: 'POST', data: { articleId } })
  },
  markSectionRead(articleId: string, sectionId: string) {
    return request<null>('/api/study/sections/read', { method: 'POST', data: { articleId, sectionId } })
  },
  getCorpusStats() { return request<CorpusStats>('/api/corpus/stats') },
  getCorpusItem(id: string) { return request<CorpusItem>(`/api/corpus/items/${id}`) },
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
  }) { return request<CorpusItem>('/api/corpus/items', { method: 'POST', data }) },
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
  }>) { return request<CorpusItem>(`/api/corpus/items/${id}`, { method: 'PUT', data }) },
  deleteCorpusItem(id: string) {
    return request<{ ok: boolean }>(`/api/corpus/items/${id}`, { method: 'DELETE' })
  },
  promoteCorpusToTerm(id: string) {
    return request<CorpusItem>(`/api/corpus/items/${id}/promote-term`, { method: 'POST' })
  },
  getKnowledgeTrees() { return request<KnowledgeTree[]>('/api/knowledge/trees') },
  getKnowledgeTree(treeKey: string) {
    return request<KnowledgeTree>(`/api/knowledge/tree/${encodeURIComponent(treeKey)}`)
  },
}
