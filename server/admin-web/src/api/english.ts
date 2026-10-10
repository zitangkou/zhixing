import http, { getData } from './http'

export interface EnglishScene {
  id: string
  title: string
  description: string
  level: string
  sortOrder: number
  isPublished: boolean
}
export interface EnglishUnit {
  id: string
  sceneId: string
  title: string
  level: string
  durationMin: number
  goal: string
  content: Record<string, unknown>
  sortOrder: number
  isPublished: boolean
}
export interface EnglishSummary { scenes: number; units: number; publishedUnits: number; completions: number }
export interface EnglishRecord { id: string; learner: string; unitTitle: string; completedAt: string; nextReviewAt: string }

export const fetchEnglishSummary = () => getData<EnglishSummary>(http.get('/admin/english/summary'))
export const fetchEnglishRecords = () => getData<EnglishRecord[]>(http.get('/admin/english/records'))
export const fetchEnglishScenes = () => getData<EnglishScene[]>(http.get('/admin/english/scenes'))
export const fetchEnglishUnits = () => getData<EnglishUnit[]>(http.get('/admin/english/units'))
export const saveEnglishScene = (data: Omit<EnglishScene, 'id'>, id?: string) => getData<EnglishScene>(id ? http.put(`/admin/english/scenes/${id}`, data) : http.post('/admin/english/scenes', data))
export const deleteEnglishScene = (id: string) => getData<{ ok: boolean }>(http.delete(`/admin/english/scenes/${id}`))
export const saveEnglishUnit = (data: Omit<EnglishUnit, 'id'>, id?: string) => getData<EnglishUnit>(id ? http.put(`/admin/english/units/${id}`, data) : http.post('/admin/english/units', data))
export const deleteEnglishUnit = (id: string) => getData<{ ok: boolean }>(http.delete(`/admin/english/units/${id}`))
