import http, { getData } from './http'

export interface ExamPaper {
  id: string
  title: string
  examType: 'real' | 'custom' | 'mock'
  subject: string
  year: number | null
  region: string
  level: string
  totalCount: number
  timeLimitMin: number
  tags: string[]
  isPublished: boolean
  isFree: boolean
  sortOrder: number
  description: string
  createdAt: string
}

export interface ExamQuestion {
  id: string
  paperId: string
  section: string
  sectionIndex: number
  sortOrder: number
  type: 'single' | 'multiple' | 'judge'
  material: string
  stem: string
  options: string[]
  correctAnswer: string | string[]
  analysis: string
  difficulty: number
  knowledgeTags: string[]
  knowledgeNodeId?: string | null
  knowledgeTreeKey?: string
  knowledgePath?: string
  isActive: boolean
}

export interface ExamImportPreview {
  fileName: string
  parsed: number
  errors: string[]
  preview: any[]
  totalCount: number
  questions: any[]
}

export function fetchExamPapers(params?: { examType?: string; subject?: string; year?: number; isPublished?: boolean }) {
  const qs = new URLSearchParams()
  if (params?.examType) qs.set('exam_type', params.examType)
  if (params?.subject) qs.set('subject', params.subject)
  if (params?.year) qs.set('year', String(params.year))
  if (params?.isPublished !== undefined) qs.set('is_published', String(params.isPublished))
  const q = qs.toString()
  return getData<ExamPaper[]>(http.get(`/admin/exam/papers${q ? `?${q}` : ''}`))
}

export function createExamPaper(data: {
  title: string
  examType?: string
  subject?: string
  year?: number | null
  region?: string
  level?: string
  timeLimitMin?: number
  tags?: string[]
  isPublished?: boolean
  isFree?: boolean
  sortOrder?: number
  description?: string
}) {
  return getData<ExamPaper>(http.post('/admin/exam/paper', data))
}

export function updateExamPaper(id: string, data: Partial<ExamPaper>) {
  return getData<ExamPaper>(http.put(`/admin/exam/paper/${id}`, data))
}

export function deleteExamPaper(id: string) {
  return getData<{ ok: boolean }>(http.delete(`/admin/exam/paper/${id}`))
}

export function importPreview(paperId: string, fileName: string, content: string) {
  return getData<{ parsed: number; errors: string[]; preview: any[]; totalCount: number }>(
    http.post(`/admin/exam/paper/${paperId}/import-preview`, { fileName, content }),
  )
}

export function importConfirm(paperId: string, fileName: string, content: string) {
  return getData<{ ok: boolean; inserted: number; errors: string[] }>(
    http.post(`/admin/exam/paper/${paperId}/import`, { fileName, content }),
  )
}

export function uploadExamFile(file: File) {
  const form = new FormData()
  form.append('file', file)
  return getData<ExamImportPreview>(
    http.post('/admin/exam/paper/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  )
}
