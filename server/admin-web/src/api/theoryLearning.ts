import http, { getData } from './http'

export interface LearningPart {
  number: number
  title: string
  questionIds: string[]
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
  parts: LearningPart[]
  questionCount: number
  collectionEnabled: boolean
  status: 'draft' | 'published'
  publishStart: string
  publishEnd: string
  sortOrder: number
  validationError?: string
}

export type TheoryLearningEntryInput = Omit<
  TheoryLearningEntry,
  'id' | 'articleId' | 'articleTitle' | 'source' | 'publishDate' | 'tags' | 'questionCount' | 'validationError'
>

export function fetchTheoryLearningEntries() {
  return getData<TheoryLearningEntry[]>(http.get('/admin/theory-learning/entries'))
}

export function saveTheoryLearningEntry(articleId: string, data: TheoryLearningEntryInput) {
  return getData<TheoryLearningEntry>(http.put(`/admin/theory-learning/entries/${articleId}`, data))
}

export function importT0cPack(payload: Record<string, unknown>, pending = false) {
  return getData<{ articleId: string; title: string; questionCount: number; entry: TheoryLearningEntry }>(
    http.post('/admin/theory-learning/import-t0c', { payload, pending }),
  )
}
