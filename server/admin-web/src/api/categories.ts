import http, { getData } from './http'
import type { Category } from '@/types'

export function fetchCategories() {
  return getData<Category[]>(http.get('/admin/categories'))
}

export function createCategory(data: { name: string; parent_id?: string | null; sort_order?: number }) {
  return getData<Category>(http.post('/admin/categories', data))
}

export function updateCategory(id: string, data: Record<string, unknown>) {
  return getData<Category>(http.put(`/admin/categories/${id}`, data))
}

export function deleteCategory(id: string) {
  return getData<null>(http.delete(`/admin/categories/${id}`))
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

export function fetchCategoryVocabInbox() {
  return getData<VocabInboxItem[]>(http.get('/admin/categories/vocab-inbox'))
}

export function promoteCategoryVocabInbox(id: string) {
  return getData<VocabInboxItem>(http.post(`/admin/categories/vocab-inbox/${id}/promote`))
}

export function ignoreCategoryVocabInbox(id: string) {
  return getData<VocabInboxItem>(http.post(`/admin/categories/vocab-inbox/${id}/ignore`))
}
