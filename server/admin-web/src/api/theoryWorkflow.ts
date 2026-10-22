import http, { getData } from './http'

export interface TheoryPaper {
  id: string
  articleId: string
  version: number
  title: string
  status: string
  questionCount: number
  approvedCount: number
  report: { validCount?: number; typeCounts?: Record<string, number>; focusTypeCounts?: Record<string, number>; numericRecallCount?: number; answerDistribution?: Record<string, number>; distractorTrickCounts?: Record<string, number>; uniqueTopicCount?: number; uniqueTagCount?: number; rubricSources?: string[]; errors?: string[] }
  error: string
  rulesVersion: string
  pointId?: string
}

export interface TheorySource {
  id: string
  title: string
  date: string
  pageNo: string
  pageName: string
  url: string
  bodyStatus: string
  reviewStatus: string
  signal: string
  valueScore: number
  reasons: string[]
  reviewNote: string
  papers: TheoryPaper[]
}

export interface TheoryQuestion {
  subtype: 'direct' | 'combo' | 'count'
  focusType: 'general' | 'core' | 'metric' | 'deployment' | 'background'
  numericRecall: boolean
  stem: string
  options: string[]
  answer: string
  analysis: string
  sourceSentence: string
  sourceRef?: string
  topic: string
  tag?: string
  difficulty?: number
  distractors?: Record<string, { type: string; note: string }>
  reviewStatus: 'pending' | 'approved' | 'rejected'
  reviewNote: string
}

export interface TheoryQuestionReviewEvent {
  questionIndex: number
  reviewer: string
  status: string
  note: string
  at: string
  before?: Record<string, unknown>
  after?: Record<string, unknown>
}

export interface TheoryCollection {
  id: string
  issueDate: string
  status: string
  discovered: number
  created: number
  failedPages: number
  failedSources: number
  error: string
}

export function fetchTheorySources(params: { issue_date?: string; status?: string; page?: number; page_size?: number }) {
  return getData<{ items: TheorySource[]; total: number }>(http.get('/admin/theory-workflow/sources', { params }))
}

export function fetchTheoryCollections() {
  return getData<TheoryCollection[]>(http.get('/admin/theory-workflow/collections'))
}

export function collectTheorySources(issueDate: string) {
  return getData<{ id: string; status: string }>(http.post('/admin/theory-workflow/collect', { issueDate }))
}

export function fetchTheorySource(id: string) {
  return getData<{ bodyText?: string; displayTitle: string; primarySourceUrl: string }>(http.get(`/admin/theory-workflow/sources/${id}`))
}

export function reviewTheorySource(id: string, status: string, note = '') {
  return getData(http.put(`/admin/theory-workflow/sources/${id}/review`, { status, note }))
}

export function generateTheoryPaper(id: string, title: string) {
  return getData<TheoryPaper>(http.post(`/admin/theory-workflow/sources/${id}/papers`, { title }))
}

export function fetchTheoryPaper(id: string) {
  return getData<TheoryPaper & { questions: TheoryQuestion[]; reviewHistory: TheoryQuestionReviewEvent[] }>(http.get(`/admin/theory-workflow/papers/${id}`))
}

export function saveTheoryQuestionReview(paperId: string, index: number, data: Partial<TheoryQuestion>) {
  return getData<TheoryPaper>(http.put(`/admin/theory-workflow/papers/${paperId}/questions/${index}`, data))
}

export function publishTheoryPaper(id: string) {
  return getData<TheoryPaper>(http.post(`/admin/theory-workflow/papers/${id}/publish`))
}
