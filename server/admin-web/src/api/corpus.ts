import http, { getData } from './http'

export interface CorpusItem {
  id: string
  userId: string
  kind: string
  sourceType: string
  sourceTitle: string
  original: string
  plainNote: string
  rewrite: string
  practice: string
  tags: string[]
  status: string
  createdAt: string
  updatedAt: string
}

export interface CorpusStats {
  total: number
  inbox: number
  clarified: number
  owned: number
  used: number
}

export const listCorpusItems = (params?: {
  userId?: string
  status?: string
  kind?: string
  q?: string
}) => getData<CorpusItem[]>(http.get('/admin/corpus/items', { params }))

export const getCorpusStats = (userId?: string) =>
  getData<CorpusStats>(http.get('/admin/corpus/stats', { params: { userId } }))

export const updateCorpusItem = (id: string, data: Record<string, unknown>) =>
  getData<CorpusItem>(http.put(`/admin/corpus/item/${id}`, data))

export const deleteCorpusItem = (id: string) =>
  getData(http.delete(`/admin/corpus/item/${id}`))
