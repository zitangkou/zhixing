/** 统一 API 响应格式 */
export interface ApiRes<T> {
  code: number
  data: T
  message: string
}

export interface MindMapNode {
  id: string
  title: string
  content?: string
  children?: MindMapNode[]
}

/** 文章多层级小节（支持章 / 节 / 段） */
export interface ArticleSection {
  id: string
  title: string
  /** 1=章 2=节 3=段 */
  level: 1 | 2 | 3
  content?: string
  /** 本小节金句或要点 */
  highlight?: string
  children?: ArticleSection[]
}

export interface ArticleCategory {
  id: string
  name: string
  parentId?: string | null
  sortOrder?: number
  children?: ArticleCategory[]
}

export interface Article {
  id: string
  title: string
  source: string
  publishDate: string
  summary: string
  /** 多层级正文结构（推荐阅读） */
  sections: ArticleSection[]
  /** 扁平正文，可由 sections 生成；保留用于兼容与全文检索 */
  content: string
  tags: string[]
  mindMap: MindMapNode
  readCount?: number
  /** 首页置顶重点文章 */
  isFeatured?: boolean
  categoryId?: string
  categoryName?: string
  categoryPath?: string[]
  importance?: number
  importanceLabel?: string
  status?: string
  allowQuiz?: boolean
}

export type QuizMode = 'daily' | 'article' | 'random' | 'timeline' | 'key' | 'wrong'

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

export interface StudyRecord {
  articleId: string
  studyDate: string
  reviewCount: number
  lastReviewDate?: string
  mastered: boolean
  /** 最近学习活动时间，用于「最近在学」 */
  updatedAt?: string
}

export interface ReviewTask {
  id: string
  articleId: string
  articleTitle: string
  reviewIndex: number
  dueDate: string
  urgency: number
  type: 'article' | 'question'
}

export interface WrongQuestionRecord {
  question: Question
  wrongCount: number
  lastWrongAt: string
  userAnswer?: string | string[]
  articleTitle: string
  tag: string
  reviewStage?: number
  nextReviewAt?: string | null
  due?: boolean
}

export interface PointsLog {
  id: string
  amount: number
  type: 'income' | 'expense'
  source: string
  description: string
  createdAt: string
}

export interface RankItem {
  rank: number
  userId: string
  nickname: string
  avatar: string
  score: number
  isSelf?: boolean
}

export interface QuizCompleteResult {
  accuracy: number
  rank: number
  totalParticipants: number
  bestAccuracy?: number
}

export interface QuizRankItem {
  rank: number
  userId: string
  nickname: string
  avatar: string
  accuracy: number
  correctCount: number
  totalCount: number
  isSelf?: boolean
}

export interface QuizAnswerRecord {
  correct: boolean
  analysis: string
  userAnswer: string | string[]
}

export interface UserInfo {
  id: string
  username?: string
  nickname: string
  avatar: string
  email?: string
  phone?: string
  isMember: boolean
  memberExpireAt?: string
}

export interface SignStatus {
  [date: string]: boolean
}

export interface AnswerResult {
  correct: boolean
  analysis: string
  correctAnswer: string | string[]
  pointsEarned: number
}

export interface ArticleListPage {
  items: Article[]
  total: number
  hasMore: boolean
}

// ===== 每日学习清单 =====

export interface PlanTask {
  id: string
  planDate: string
  timeSlot: string
  subject: string
  content: string
  priority: number
  expectedMinutes: number
  actualMinutes: number
  status: 'pending' | 'done' | 'skipped'
  sortOrder: number
  note: string
}

export interface DailyReview {
  reviewDate: string
  completion: number
  totalMinutes: number
  weakPoint: string
  tomorrowFocus: string
  mood: '' | 'good' | 'ok' | 'bad'
  note: string
}

export interface DayPlan {
  date: string
  isWeekend: boolean
  tasks: PlanTask[]
  completion: number
  doneCount: number
  totalCount: number
  expectedMinutes: number
  actualMinutes: number
  review: DailyReview | null
}

// ===== 知识框架 =====

export interface KnowledgeNode {
  id: string
  treeKey: string
  parentId: string | null
  title: string
  content: string
  myNote: string
  isStarred: boolean
  masteryLevel?: string
  nextReviewAt?: string | null
  reviewCount?: number
  lastReviewedAt?: string | null
  depth: number
  sortOrder: number
  path: string
  sourceFile?: string
  children: KnowledgeNode[] | null
}

export interface KnowledgeTree {
  treeKey: string
  title: string
  nodes: KnowledgeNode[]
}

export interface KnowledgeReviewCard {
  id: string
  title: string
  path: string
  treeKey: string
  content: string
  myNote: string
  masteryLevel: string
  hint?: string | null
}

export interface KnowledgeReviewDue {
  dueCount: number
  candidates: KnowledgeReviewCard[]
}

export interface KnowledgeReviewSession {
  cards: KnowledgeReviewCard[]
}

export interface KnowledgeReviewAnswer {
  id: string
  masteryLevel: string
  nextReviewAt?: string | null
  reviewCount: number
  lastReviewedAt?: string | null
}

export type KnowledgeReviewResult = 'again' | 'hard' | 'good' | 'easy'

export interface ReviewHub {
  knowledgeDueCount: number
  articleReviewCount: number
  corpusInboxCount: number
  articleWrongCount: number
  manualWrongCount: number
  wrongReviewCount: number
  /** 未到期错题，今日可跳过 */
  wrongWaitingCount: number
  /** 今日智能推荐题量 */
  wrongRecommendCount: number
  /** 今日复习总预算 */
  todayBudget?: number
  /** 今日推荐完成量 */
  todayRecommended?: number
  /** 到期但今天不强推的积压量 */
  backlogCount?: number
  /** 按当前预算预计清理天数 */
  estimatedClearDays?: number
  /** 分模块预算计划 */
  reviewPlan?: Array<{
    key: string
    label: string
    due: number
    recommended: number
    backlog: number
    cap: number
  }>
  totalCount: number
}

export interface RmrbArticle {
  id: string
  title: string
  source: string
  publishDate: string
  summary: string
  content: string
  /** 主题标签：政绩观、社会治理、乡村振兴等 */
  tags: string[]
  isPublished: boolean
  sortOrder: number
  readCount: number
  createdAt: string
  updatedAt: string
}

export interface ShenlunMineTermItem {
  term: string
  category: string
  plainWord: string
}

export interface ShenlunQuoteItem {
  text: string
  /** 来源，如：清代万斯大 */
  source: string
  /** 释义 */
  meaning?: string
}

export interface ShenlunVerbItem {
  verb: string
  usage: string
  category: string
}

export interface ShenlunArgumentFieldValue {
  key: string
  label: string
  content: string
}

export interface ShenlunArgumentPoint {
  /** 分论点标题 */
  title: string
  /** 旧字段，兼容读取后并入 title */
  claim: string
  /** 论据（可选） */
  evidence: string
  /** 小结（可选） */
  summary: string
  /** 论证方法名，如：时间推进法 */
  method?: string
  /** 方法说明（可选） */
  methodNote?: string
  /** 套用模板 */
  template?: string
}

export interface ShenlunArgumentSkeleton {
  templateId: string
  templateName: string
  mode: string
  /** 总论点 */
  overview: string
  /** 总结 */
  conclusion: string
  /** 总论点论证方法 */
  overviewMethod?: string
  /** 总论点论证模板 */
  overviewTemplate?: string
  fields: ShenlunArgumentFieldValue[]
  points: ShenlunArgumentPoint[]
}

export interface ShenlunTemplateItem {
  type: string
  typeName?: string
  original: string
  template: string
  imitate: string
}

export interface ShenlunSkeletonFieldDef {
  key: string
  label: string
  placeholder?: string
}

export interface ShenlunSkeletonStructure {
  mode: string
  fields: ShenlunSkeletonFieldDef[]
  overviewLabel?: string
  overviewPlaceholder?: string
  pointFields: ShenlunSkeletonFieldDef[]
}

export interface ShenlunTermCategory {
  id: string
  name: string
  kind?: 'term' | 'verb' | string
  sortOrder: number
  isEnabled: boolean
}

export interface ShenlunArgumentMethodPreset {
  id?: string
  name: string
  scope: 'overview' | 'point' | string
  note: string
  template: string
  sortOrder?: number
  isEnabled?: boolean
}

export interface ShenlunSkeletonTemplate {
  id: string
  name: string
  description: string
  mode: string
  structure: ShenlunSkeletonStructure
  sortOrder: number
  isEnabled: boolean
}

export interface ShenlunSentenceType {
  id: string
  code: string
  name: string
  tip: string
  sortOrder: number
  isEnabled: boolean
}

export interface ShenlunMeta {
  termCategories: ShenlunTermCategory[]
  verbCategories?: ShenlunTermCategory[]
  skeletonTemplates: ShenlunSkeletonTemplate[]
  sentenceTypes: ShenlunSentenceType[]
  argumentMethodPresets?: ShenlunArgumentMethodPreset[]
}

export interface ShenlunMineLog {
  id: string
  mineDate: string
  articleId: string | null
  articleTitle: string
  sourceExcerpt: string
  argumentChain: string
  templateSentence: string
  terms: ShenlunMineTermItem[]
  quotes?: ShenlunQuoteItem[]
  verbs?: ShenlunVerbItem[]
  argument: ShenlunArgumentSkeleton
  templates: ShenlunTemplateItem[]
  createdAt: string
  updatedAt: string
}

export interface ShenlunNormTerm {
  id: string
  term: string
  category: string
  usageNote: string
  sourceTitle: string
  exampleSentence: string
  articleId: string | null
  familiarity: number
  mastered: boolean
  createdAt: string
}

export interface ShenlunStats {
  weekMineDays: number
  weekMineTarget: number
  termCount: number
  learningTermCount: number
  todayMined: boolean
  weekDrillCount: number
}

export interface ShenlunDrillLog {
  id: string
  drillType: 'sentence' | 'imitate' | 'oral' | string
  content: string
  prompt: string
  refMineId: string | null
  refTermIds: string[]
  createdAt: string
}

/** 知行足迹 / 成长总览 */
export interface GrowthDayBar {
  date: string
  label: string
  minutes: number
  isToday: boolean
}

export interface GrowthDomainProgress {
  key: string
  name: string
  percent: number
  detail: string
}

export interface GrowthOverview {
  signStreak: number
  signDays: number
  points: number
  weekMinutes: number
  weekQuizTotal: number
  weekQuizCorrect: number
  articleReadCount: number
  examFinishedCount: number
  weekBars: GrowthDayBar[]
  domains: GrowthDomainProgress[]
}

export interface ExamPaper {
  id: string
  title: string
  examType: 'real' | 'custom' | 'mock'
  subject: string
  year?: number
  region: string
  level: string
  totalCount: number
  timeLimitMin: number
  tags: string[]
  isPublished: boolean
  isFree: boolean
  sortOrder: number
  description: string
  createdAt: string
}

export interface ExamQuestion {
  id: string
  paperId: string
  section: string
  sectionIndex: number
  sortOrder: number
  type: 'single' | 'multiple' | 'judge'
  material: string
  stem: string
  options: string[]
  correctAnswer: string | string[]
  analysis: string
  difficulty: number
  knowledgeTags: string[]
  knowledgeNodeId?: string | null
  knowledgeTreeKey?: string
  knowledgePath?: string
  isActive: boolean
}

export interface ExamPaperDetail {
  id: string
  title: string
  examType: string
  subject: string
  year?: number
  region: string
  level: string
  totalCount: number
  timeLimitMin: number
  tags: string[]
  isPublished: boolean
  isFree: boolean
  description: string
  sections: { section: string; questions: ExamQuestion[] }[]
}

export interface ExamTakingQuestion {
  id: string
  section: string
  sortOrder: number
  type: string
  material: string
  stem: string
  options: string[]
  myAnswer: string | string[]
  marked: boolean
  timeUsedSec: number
}

export interface ExamStartResult {
  attemptId: string
  paperId: string
  paperTitle: string
  timeLimitMin: number
  totalCount: number
  startedAt: string
  questions: ExamTakingQuestion[]
}

export interface ExamAttempt {
  id: string
  paperId: string
  paperTitle: string
  startedAt: string
  finishedAt: string | null
  timeUsedSec: number
  totalCount: number
  answeredCount: number
  correctCount: number
  score: number
  isFinished: boolean
}

export interface ExamAttemptAnswer {
  questionId: string
  section: string
  sortOrder: number
  stem: string
  options: string[]
  correctAnswer: string | string[]
  analysis: string
  userAnswer: string | string[]
  isCorrect: boolean
  answered: boolean
  timeUsedSec: number
  marked: boolean
}

export interface ExamAttemptDetail extends ExamAttempt {
  answers: ExamAttemptAnswer[]
  sectionStats: {
    section: string
    total: number
    correct: number
    answered: number
    accuracy: number
  }[]
}

// ===== 手动错题 =====

export interface ManualWrong {
  id: string
  subject: string
  questionType: string
  stem: string
  options: string
  myAnswer: string
  correctAnswer: string
  analysis: string
  wrongReason: string
  note: string
  images: string[]
  source: 'manual' | 'photo' | 'ocr'
  knowledgeNodeId?: string | null
  knowledgeTreeKey?: string
  knowledgePath?: string
  reviewCount: number
  reviewStage?: number
  nextReviewAt?: string | null
  due?: boolean
  mastered: boolean
  lastWrongAt: string
  createdAt: string
}

/** 记账模块 */

/** 语料本 · 跨来源词句素材 */
export type CorpusStatus = 'inbox' | 'clarified' | 'owned' | 'used' | string

export interface CorpusItem {
  id: string
  original: string
  kind: string
  sourceType: string
  sourceTitle: string
  tags: string[]
  plainNote: string
  rewrite: string
  practice: string
  status: CorpusStatus
  usedCount: number
  promotedTermId: string | null
  knowledgeNodeId?: string | null
  knowledgeTreeKey?: string
  knowledgePath?: string
  createdAt: string
  updatedAt: string
}

export interface CorpusStats {
  inboxCount: number
  clarifiedCount: number
  ownedCount: number
  usedCount: number
  total: number
  kinds: string[]
  sourceTypes: string[]
  tagPresets: string[]
}

/** 财富 / 投资大脑 */

/** 时事新闻 · 事件印象 */
export interface EventImpression {
  id: string
  title: string
  eventDate: string
  place: string
  coreContent: string
  note: string
  knowledgeNodeId?: string | null
  knowledgeTreeKey: string
  knowledgePath: string
  createdAt: string
  updatedAt: string
}

export interface EventFrameworkGroup {
  treeKey: string
  path: string
  label: string
  count: number
  items: EventImpression[]
}

export interface EventHub {
  total: number
  linkedCount: number
  unlinkedCount: number
  recentCount: number
  frameworkGroups: EventFrameworkGroup[]
}

// ===== 资料分析 =====

export interface ZiliaoOverview {
  formulaCount: number
  typeCount: number
  trickCount: number
  drillSetCount: number
  todaySets: number
  todayCorrect: number
  todayTotal: number
  weekSets: number
  hasRealDrill?: boolean
  usingSampleOnly?: boolean
  weakTypes?: ZiliaoWeakType[]
}

export interface ZiliaoWeakType {
  id: string
  code: string
  name: string
  category: string
  attemptCount: number
  correctCount: number
  totalCount: number
  accuracy: number | null
  reason: string
}

export interface ZiliaoFormula {
  id: string
  code: string
  name: string
  category: string
  definition: string
  latex: string
  formulaPlain: string
  scenarios: string
  pitfalls: string
  relatedTypeCodes: string[]
  relatedTrickCodes: string[]
  keywords: string[]
  examFreq: number
  sortOrder: number
  isPublished: boolean
}

export interface ZiliaoQuestionType {
  id: string
  code: string
  name: string
  category: string
  description: string
  ability: string
  difficulty: number
  examFreq: number
  formulaCodes: string[]
  trickCodes: string[]
  keywords: string[]
  sortOrder: number
  isPublished: boolean
}

export interface ZiliaoTrick {
  id: string
  code: string
  name: string
  category: string
  principle: string
  whenToUse: string
  whenNot: string
  errorNote: string
  formulaCodes: string[]
  example: string
  sortOrder: number
  isPublished: boolean
}

export interface ZiliaoDrillSet {
  setId: string
  paperId: string
  paperTitle: string
  materialPreview: string
  questionCount: number
  section: string
  typeHints: string[]
  isSample?: boolean
}

export interface ZiliaoDrillQuestion {
  id: string
  section: string
  sortOrder: number
  type: string
  material: string
  stem: string
  options: string[]
  difficulty: number
}

export interface ZiliaoDrillSetDetail {
  setId: string
  paperId: string
  paperTitle: string
  material: string
  questions: ZiliaoDrillQuestion[]
}

export interface ZiliaoDrillSubmitResult {
  setId: string
  totalCount: number
  correctCount: number
  timeUsedSec: number
  wrongs: {
    questionId: string
    stem: string
    material: string
    options: string[]
    userAnswer: string | string[]
    correctAnswer: string | string[]
    analysis: string
  }[]
  savedWrongCount: number
}

// ===== 考试倒计时 =====

export interface ExamCountdown {
  id: string
  examName: string
  examDate: string
  note: string
  daysLeft: number
  createdAt?: string
  updatedAt?: string
}

// ===== 数据导出/导入 =====

/** 核心学习进度导出体（后端 snake_case 原样透传，前端不做字段映射） */
export interface DataExport {
  version: number
  exportedAt: string
  wrongAnswers: Record<string, unknown>[]
  manualWrongs: Record<string, unknown>[]
  corpusItems: Record<string, unknown>[]
  planTasks: Record<string, unknown>[]
  dailyReviews: Record<string, unknown>[]
  pointsLogs: Record<string, unknown>[]
}

export interface DataImportResult {
  wrongAnswers: number
  manualWrongs: number
  corpusItems: number
  planTasks: number
  dailyReviews: number
  pointsLogs: number
}
