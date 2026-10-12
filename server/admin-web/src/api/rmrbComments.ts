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
export function analyzeRmrbComment(id: string) {
  return getData<{ id: string; analysisStatus: string }>(http.post(`/admin/rmrb-comments/${id}/analyze`))
}
export function reviewRmrbComment(id: string, data: Record<string, unknown>) {
  return getData<RmrbCommentItem>(http.put(`/admin/rmrb-comments/${id}/review`, data))
}
export function getRmrbCommentArtifact(id: string, kind: string) {
  return http.get(`/admin/rmrb-comments/${id}/artifact`, { params: { kind }, responseType: 'blob' }).then((response) => response.data.text())
}
