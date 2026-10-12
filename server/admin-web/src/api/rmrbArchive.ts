import http, { getData } from './http'

export interface RmrbArchiveArticle {
  id: string
  issueDate: string
  pageNo: string
  pageName: string
  pageRefs: Array<{ pageNo: string; pageName: string; directoryUrl: string; articleUrl: string; relation: string }>
  primarySourceUrl: string
  sourceChannel: string
  displayTitle: string
  headline: string
  subtitle: string
  columnLabel: string
  seriesLabel: string
  eyebrow: string
  authorLine: string
  editorLine: string
  authors: Array<Record<string, unknown>>
  publicationTime: string
  recordClass: string
  sourceArticleType: string
  expressionModes: string[]
  topics: string[]
  examRelevance: string
  examRelevanceReasons: string[]
  classificationSuggestion: { sourceArticleType: string; examRelevance: string; confidence: number; method: string; reasons: string[]; featureKey?: string }
  classificationMethod: string
  classificationHistory: Array<Record<string, unknown>>
  latestEvaluation: RmrbArticleEvaluation | null
  retentionTier: string
  bodyStatus: string
  sourceStatus: string
  rightsStatus: string
  reviewStatus: string
  currentRevision: number
  bodyText?: string | null
  bodySizeBytes: number
  bodySha256: string
  sources: Array<{ id: string; sourceChannel: string; sourceUrl: string; sourceRelation: string; sourceDisplayTitle: string; evidenceType: string; fetchedAt: string }>
  revisions: Array<{ id: string; revisionNo: number; bodyStorageKey: string; bodySha256: string; bodySizeBytes: number; bodyStatus: string; parserVersion: string; changeNote: string; createdAt: string }>
  createdAt: string
  updatedAt: string
}

export interface RmrbArticleEvaluation {
  id: string
  status: string
  reviewStatus: string
  promptVersion: string
  modelName: string
  bodySha256: string
  bodyCharCount: number
  result: Record<string, any>
  errorMessage: string
  reviewNote: string
  reviewedBy: string
  reviewedAt: string | null
  startedAt: string | null
  finishedAt: string | null
  createdAt: string
}

export interface RmrbArchivePage {
  items: RmrbArchiveArticle[]
  total: number
  page: number
  pageSize: number
}

export interface RmrbArchiveFilters {
  issue_date?: string
  date_from?: string
  date_to?: string
  page_no?: string
  page_name?: string
  title?: string
  article_type?: string
  record_class?: string
  exam_relevance?: string
  retention_tier?: string
  author?: string
  editor?: string
  body_status?: string
  review_status?: string
  evaluation_status?: string
  source_channel?: string
  page?: number
  page_size?: number
}

export function listRmrbArchiveArticles(params: RmrbArchiveFilters) {
  return getData<RmrbArchivePage>(http.get('/admin/rmrb-archive/articles', { params }))
}

export function getRmrbArchiveArticle(id: string) {
  return getData<RmrbArchiveArticle>(http.get(`/admin/rmrb-archive/articles/${id}`))
}

export function createRmrbArchiveArticle(data: Record<string, unknown>) {
  return getData<RmrbArchiveArticle>(http.post('/admin/rmrb-archive/articles', data))
}

export function updateRmrbArchiveArticle(id: string, data: Record<string, unknown>) {
  return getData<RmrbArchiveArticle>(http.put(`/admin/rmrb-archive/articles/${id}`, data))
}

export function archiveRmrbArchiveArticle(id: string) {
  return getData<{ ok: boolean }>(http.delete(`/admin/rmrb-archive/articles/${id}`))
}

export interface RmrbArchiveBatch {
  id: string
  issueDate: string
  triggerMode: string
  status: string
  expectedPageCount: number
  completedPageCount: number
  discoveredArticleCount: number
  createdArticleCount: number
  failedPageCount: number
  failedSourceCount: number
  errorSummary: string
  startedAt?: string | null
  finishedAt?: string | null
  createdAt: string
}

export function listRmrbArchiveBatches() {
  return getData<RmrbArchiveBatch[]>(http.get('/admin/rmrb-archive/batches'))
}

export function runRmrbArchiveBatch(issueDate: string) {
  return getData<RmrbArchiveBatch>(http.post('/admin/rmrb-archive/batches/run', { issueDate }))
}

export function runRmrbEvaluations(data: { issueDate?: string; dateFrom?: string; dateTo?: string; articleIds?: string[]; force?: boolean }) {
  return getData<{ queued: number; evaluationIds: string[] }>(http.post('/admin/rmrb-archive/evaluations/run', data))
}

export function getRmrbEvaluation(articleId: string) {
  return getData<RmrbArticleEvaluation>(http.get(`/admin/rmrb-archive/articles/${articleId}/evaluation`))
}

export function reviewRmrbEvaluation(articleId: string, data: { decision: string; result?: Record<string, any>; note?: string }) {
  return getData<RmrbArticleEvaluation>(http.put(`/admin/rmrb-archive/articles/${articleId}/evaluation/review`, data))
}
