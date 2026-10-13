import http, { getData } from './http'

export interface RmrbCommentItem {
  id: string
  articleId: string
  issueDate: string
  pageNo: string
  pageName: string
  title: string
  subtitle: string
  columnLabel: string
  author: string
  sourceUrl: string
  bodyStatus: string
  inclusionReason: string
  workflowStatus: string
  articleReviewStatus: 'pending' | 'approved' | 'excluded'
  articleReviewNote: string
  articleReviewedBy: string
  analysisStatus: string
  reviewStatus: string
  analysisError: string
  originalMdKey: string
  originalHtmlKey: string
  analysisMdKey: string
  analysisHtmlKey: string
  reviewNote: string
}

export function listRmrbComments(params: Record<string, unknown>) {
  return getData<{ items: RmrbCommentItem[]; total: number }>(http.get('/admin/rmrb-comments', { params }))
}
export function scanRmrbComments(issueDate: string) {
  return getData<{ issueDate: string; discovered: number; created: number; originalReady: number; failed: number }>(http.post('/admin/rmrb-comments/scan', null, { params: { issue_date: issueDate } }))
}
export function listPeopleappOpinionComments(page = 1, pageSize = 20) {
  return getData<{ items: RmrbCommentItem[]; total: number; page: number; pageSize: number; windowStart: string; windowEnd: string }>(http.get('/admin/rmrb-comments/peopleapp-opinion', { params: { page, page_size: pageSize } }))
}
export function collectPeopleappOpinionComments() {
  return getData<{ windowStart: string; windowEnd: string; discovered: number; created: number; linked: number; issueDates: string[] }>(http.post('/admin/rmrb-comments/peopleapp-opinion/collect'))
}
export function reviewPeopleappOpinionArticle(id: string, decision: 'approved' | 'excluded', note = '') {
  return getData<{ id: string; articleReviewStatus: string; exclusionTitlePrefix: string; filteredArticles: number; deletedQuotes: number }>(http.put(`/admin/rmrb-comments/peopleapp-opinion/${id}/article-review`, { decision, note }))
}
export interface RmrbCommentQuote {
  id: string
  commentArticleId: string
  text: string
  quoteType: string
  topics: string[]
  useCases: string[]
  applicationExample: string
  sourceEvidence: string
  collectionMethod: 'ai' | 'bold' | 'manual'
  reviewStatus: string
  reviewNote: string
}
export function listRmrbCommentQuotes(recordId: string) {
  return getData<RmrbCommentQuote[]>(http.get(`/admin/rmrb-comments/${recordId}/quotes`))
}
export function collectAiRmrbCommentQuotes(recordId: string) {
  return getData<RmrbCommentQuote[]>(http.post(`/admin/rmrb-comments/${recordId}/quotes/collect-ai`))
}
export function createRmrbCommentQuote(recordId: string, data: Record<string, unknown>) {
  return getData<RmrbCommentQuote>(http.post(`/admin/rmrb-comments/${recordId}/quotes`, data))
}
export function updateRmrbCommentQuote(id: string, data: Record<string, unknown>) {
  return getData<RmrbCommentQuote>(http.put(`/admin/rmrb-comments/quotes/${id}`, data))
}
export function deleteRmrbCommentQuote(id: string) {
  return getData<{ deleted: boolean }>(http.delete(`/admin/rmrb-comments/quotes/${id}`))
}
export function reviewRmrbCommentQuote(id: string, data: Record<string, unknown>) {
  return getData<RmrbCommentQuote | { id: string; deleted: boolean }>(http.put(`/admin/rmrb-comments/quotes/${id}/review`, data))
}
export interface RmrbOpsQuote extends RmrbCommentQuote {
  articleTitle: string; articleDate: string; author: string; sourceUrl: string; used: boolean
}
export interface RmrbOpsPackage {
  id: string; issueDate: string; topic: string; title: string; channels: string[]
  xhsTitle: string; xhsContent: string; wechatTitle: string; wechatSummary: string; wechatContent: string
  status: string; xhsPublishedAt?: string | null; wechatPublishedAt?: string | null; quotes: RmrbOpsQuote[]
}
export function listRmrbOpsQuotes(params: Record<string, unknown> = {}) {
  return getData<RmrbOpsQuote[]>(http.get('/admin/rmrb-quotes/operations/pool', { params }))
}
export function listRmrbQuoteLibrary(params: Record<string, unknown> = {}) {
  return getData<{ items: RmrbOpsQuote[]; total: number; page: number; pageSize: number }>(http.get('/admin/rmrb-quotes/library', { params }))
}
export function listRmrbOpsPackages() {
  return getData<RmrbOpsPackage[]>(http.get('/admin/rmrb-quotes/operations/packages'))
}
export function createRmrbOpsPackage(data: Record<string, unknown>) {
  return getData<RmrbOpsPackage>(http.post('/admin/rmrb-quotes/operations/packages', data))
}
export function updateRmrbOpsPackage(id: string, data: Record<string, unknown>) {
  return getData<RmrbOpsPackage>(http.put(`/admin/rmrb-quotes/operations/packages/${id}`, data))
}
export function generateRmrbOpsCopy(id: string) {
  return getData<RmrbOpsPackage>(http.post(`/admin/rmrb-quotes/operations/packages/${id}/generate`))
}
export function markRmrbOpsPublished(id: string, channel: string) {
  return getData<RmrbOpsPackage>(http.post(`/admin/rmrb-quotes/operations/packages/${id}/publish`, { channel }))
}
export function analyzeRmrbComment(id: string) {
  return getData<{ id: string; analysisStatus: string }>(http.post(`/admin/rmrb-comments/${id}/analyze`))
}
export function reviewRmrbComment(id: string, data: Record<string, unknown>) {
  return getData<RmrbCommentItem>(http.put(`/admin/rmrb-comments/${id}/review`, data))
}
export function getRmrbCommentArtifact(id: string, kind: string) {
  return http.get(`/admin/rmrb-comments/${id}/artifact`, { params: { kind }, responseType: 'blob' }).then((response) => response.data.text())
}
