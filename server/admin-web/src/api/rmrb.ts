import http, { getData } from './http'

export interface RmrbArticle {
  id: string
  title: string
  source: string
  sourceUrl: string
  publishDate: string
  summary: string
  content: string
  contentHtml?: string
  tags: string[]
  isPublished: boolean
  isDaily?: boolean
  hasParse?: boolean
  sortOrder: number
  readCount: number
  createdAt: string
  updatedAt: string
}

export interface ShenlunSkeletonFieldDef {
  key: string
  label: string
  placeholder?: string
}

export interface ShenlunSkeletonStructure {
  mode: 'linear' | 'points' | string
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

export interface ShenlunArgumentMethod {
  id: string
  name: string
  scope: 'overview' | 'point' | string
  note: string
  template: string
  sortOrder: number
  isEnabled: boolean
}

export function fetchRmrbArticles(tag?: string) {
  return getData<RmrbArticle[]>(
    http.get('/admin/rmrb/articles', { params: tag ? { tag } : undefined }),
  )
}

export function createRmrbArticle(data: {
  title?: string
  source?: string
  sourceUrl?: string
  publishDate?: string
  summary?: string
  content?: string
  contentHtml?: string
  tags?: string[]
  isPublished?: boolean
  isDaily?: boolean
  sortOrder?: number
}) {
  return getData<RmrbArticle>(http.post('/admin/rmrb/article', data))
}

export function previewRmrbHtml(html: string) {
  return getData<{
    title: string
    source: string
    sourceUrl: string
    publishDate: string
    summary: string
    tags: string[]
    stats: { chapters: number; sections: number; paragraphs: number; chars?: number }
    parse_warnings: string[]
  }>(http.post('/admin/rmrb/preview-html', { html }))
}

export function updateRmrbArticle(id: string, data: Partial<RmrbArticle>) {
  return getData<RmrbArticle>(http.put(`/admin/rmrb/article/${id}`, data))
}

export function deleteRmrbArticle(id: string) {
  return getData<{ ok: boolean }>(http.delete(`/admin/rmrb/article/${id}`))
}

export function fetchTermCategories() {
  return getData<ShenlunTermCategory[]>(http.get('/admin/rmrb/term-categories'))
}

export function createTermCategory(data: {
  name: string
  kind?: string
  sortOrder?: number
  isEnabled?: boolean
}) {
  return getData<ShenlunTermCategory>(http.post('/admin/rmrb/term-categories', data))
}

export function updateTermCategory(id: string, data: Partial<ShenlunTermCategory>) {
  return getData<ShenlunTermCategory>(http.put(`/admin/rmrb/term-categories/${id}`, data))
}

export function deleteTermCategory(id: string) {
  return getData<{ ok: boolean }>(http.delete(`/admin/rmrb/term-categories/${id}`))
}

export function fetchSkeletonTemplates() {
  return getData<ShenlunSkeletonTemplate[]>(http.get('/admin/rmrb/skeleton-templates'))
}

export function createSkeletonTemplate(data: {
  name: string
  description?: string
  mode?: string
  structure?: ShenlunSkeletonStructure
  sortOrder?: number
  isEnabled?: boolean
}) {
  return getData<ShenlunSkeletonTemplate>(http.post('/admin/rmrb/skeleton-templates', data))
}

export function updateSkeletonTemplate(id: string, data: Partial<{
  name: string
  description: string
  mode: string
  structure: ShenlunSkeletonStructure
  sortOrder: number
  isEnabled: boolean
}>) {
  return getData<ShenlunSkeletonTemplate>(http.put(`/admin/rmrb/skeleton-templates/${id}`, data))
}

export function deleteSkeletonTemplate(id: string) {
  return getData<{ ok: boolean }>(http.delete(`/admin/rmrb/skeleton-templates/${id}`))
}

export function fetchSentenceTypes() {
  return getData<ShenlunSentenceType[]>(http.get('/admin/rmrb/sentence-types'))
}

export function createSentenceType(data: {
  code: string
  name: string
  tip?: string
  sortOrder?: number
  isEnabled?: boolean
}) {
  return getData<ShenlunSentenceType>(http.post('/admin/rmrb/sentence-types', data))
}

export function updateSentenceType(id: string, data: Partial<ShenlunSentenceType>) {
  return getData<ShenlunSentenceType>(http.put(`/admin/rmrb/sentence-types/${id}`, data))
}

export function deleteSentenceType(id: string) {
  return getData<{ ok: boolean }>(http.delete(`/admin/rmrb/sentence-types/${id}`))
}

export function fetchArgumentMethods() {
  return getData<ShenlunArgumentMethod[]>(http.get('/admin/rmrb/argument-methods'))
}

export function createArgumentMethod(data: {
  name: string
  scope?: string
  note?: string
  template?: string
  sortOrder?: number
  isEnabled?: boolean
}) {
  return getData<ShenlunArgumentMethod>(http.post('/admin/rmrb/argument-methods', data))
}

export function updateArgumentMethod(id: string, data: Partial<ShenlunArgumentMethod>) {
  return getData<ShenlunArgumentMethod>(http.put(`/admin/rmrb/argument-methods/${id}`, data))
}

export function deleteArgumentMethod(id: string) {
  return getData<{ ok: boolean }>(http.delete(`/admin/rmrb/argument-methods/${id}`))
}

// ---- 三刀解剖导入 ----

export interface ThreeKnifeSummary {
  articleTitle: string
  mineDate: string
  termsCount: number
  quotesCount: number
  verbsCount: number
  pointsCount: number
  templatesCount: number
  incompleteReasons: string[]
}

export interface ThreeKnifePreviewResult {
  parsed: Record<string, unknown>
  summary: ThreeKnifeSummary
}

export interface ThreeKnifeImportResult {
  articleId: string
  exampleId: string
  example: Record<string, unknown>
  summary: ThreeKnifeSummary
}

export function previewThreeKnife(markdown: string, sourceUrl?: string) {
  return getData<ThreeKnifePreviewResult>(
    http.post('/admin/rmrb/preview-three-knife', { markdown, sourceUrl }),
  )
}

export function importThreeKnife(data: {
  articleId: string
  displayHtml?: string
  markdown?: string
  sourceUrl?: string
}) {
  return getData<ThreeKnifeImportResult>(
    http.post('/admin/rmrb/import-three-knife', data),
  )
}

export interface VocabInboxItem {
  id: string
  kind: string
  name: string
  status: string
  hitCount: number
  sourceArticleId: string
  sourceTitle: string
}

export function fetchRmrbVocabInbox(kind?: string) {
  return getData<VocabInboxItem[]>(
    http.get('/admin/rmrb/vocab-inbox', { params: kind ? { kind } : undefined }),
  )
}

export function promoteRmrbVocabInbox(id: string) {
  return getData<VocabInboxItem>(http.post(`/admin/rmrb/vocab-inbox/${id}/promote`))
}

export function ignoreRmrbVocabInbox(id: string) {
  return getData<VocabInboxItem>(http.post(`/admin/rmrb/vocab-inbox/${id}/ignore`))
}
