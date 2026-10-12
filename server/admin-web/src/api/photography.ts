import http, { getData } from './http'

export interface PhotographyStage {
  id: string
  title: string
  items: string
  description: string
  sortOrder: number
  isPublished: boolean
}

export interface PhotographyLesson {
  id: string
  stageId: string
  category: string
  title: string
  subtitle: string
  level: string
  durationMin: number
  principle: string
  steps: string[]
  task: string
  review: string
  sortOrder: number
  isPublished: boolean
}

export interface PhotographySummary { stages: number; lessons: number; publishedLessons: number }
export interface PhotographyCase {
  id: string; title: string; imageUrl: string; sourceUrl: string; author: string
  licenseType: string; licenseNote: string; category: string; level: string
  observations: string[]; exif: Record<string, string | number | null>; inferences: { statement: string; evidence: string; confidence: string }[]
  practiceTitle: string; practiceGoal: string; practiceSteps: string[]; practiceVariable: string
  criteria: string[]; durationMin: number; sortOrder: number; isPublished: boolean
}

export const fetchPhotographySummary = () => getData<PhotographySummary>(http.get('/admin/photography/summary'))
export const fetchPhotographyStages = () => getData<PhotographyStage[]>(http.get('/admin/photography/stages'))
export const fetchPhotographyLessons = () => getData<PhotographyLesson[]>(http.get('/admin/photography/lessons'))
export const savePhotographyStage = (data: Omit<PhotographyStage, 'id'>, id?: string) => getData<PhotographyStage>(id ? http.put(`/admin/photography/stages/${id}`, data) : http.post('/admin/photography/stages', data))
export const deletePhotographyStage = (id: string) => getData<{ ok: boolean }>(http.delete(`/admin/photography/stages/${id}`))
export const savePhotographyLesson = (data: Omit<PhotographyLesson, 'id'>, id?: string) => getData<PhotographyLesson>(id ? http.put(`/admin/photography/lessons/${id}`, data) : http.post('/admin/photography/lessons', data))
export const deletePhotographyLesson = (id: string) => getData<{ ok: boolean }>(http.delete(`/admin/photography/lessons/${id}`))
export const fetchPhotographyCases = () => getData<PhotographyCase[]>(http.get('/admin/photography/cases'))
export const savePhotographyCase = (data: Omit<PhotographyCase, 'id'>, id?: string) => getData<PhotographyCase>(id ? http.put(`/admin/photography/cases/${id}`, data) : http.post('/admin/photography/cases', data))
export const deletePhotographyCase = (id: string) => getData<{ ok: boolean }>(http.delete(`/admin/photography/cases/${id}`))
export const uploadPhotographyCaseImage = (file: File) => { const body = new FormData(); body.append('file', file); return getData<{ url: string }>(http.post('/admin/photography/cases/upload-image', body)) }
