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

export const fetchPhotographySummary = () => getData<PhotographySummary>(http.get('/admin/photography/summary'))
export const fetchPhotographyStages = () => getData<PhotographyStage[]>(http.get('/admin/photography/stages'))
export const fetchPhotographyLessons = () => getData<PhotographyLesson[]>(http.get('/admin/photography/lessons'))
export const savePhotographyStage = (data: Omit<PhotographyStage, 'id'>, id?: string) => getData<PhotographyStage>(id ? http.put(`/admin/photography/stages/${id}`, data) : http.post('/admin/photography/stages', data))
export const deletePhotographyStage = (id: string) => getData<{ ok: boolean }>(http.delete(`/admin/photography/stages/${id}`))
export const savePhotographyLesson = (data: Omit<PhotographyLesson, 'id'>, id?: string) => getData<PhotographyLesson>(id ? http.put(`/admin/photography/lessons/${id}`, data) : http.post('/admin/photography/lessons', data))
export const deletePhotographyLesson = (id: string) => getData<{ ok: boolean }>(http.delete(`/admin/photography/lessons/${id}`))
