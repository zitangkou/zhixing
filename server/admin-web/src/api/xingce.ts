import http, { getData } from './http'

export interface XingceModuleCount {
  key?: string
  name: string
  count: number
}

export interface XingcePaperRow {
  id: string
  year: number
  paperType: string
  title: string
  positionCount: number
  practiceableCount: number
  visibleOnHub: boolean
  modules: { name: string; count: number }[]
}

export interface XingceOverview {
  modules: XingceModuleCount[]
  years: number[]
  paperTypes: string[]
  studentPapers: { year: number; paperType: string; title: string; count: number }[]
  papers: XingcePaperRow[]
  practiceableTotal: number
  positionTotal: number
  dataDir: string
  dataDirReady: boolean
  allowedPaperTypes: string[]
}

export interface XingceImportStats {
  newQuestions: number
  reusedQuestions: number
  newPositions: number
  updatedPositions: number
  errors: string[]
  warnings: string[]
  perPaper: Record<string, { positions?: number }>
}

export const fetchXingceOverview = () => getData<XingceOverview>(http.get('/admin/xingce/overview'))

export const importXingceJson = (file: File, paperType?: string) => {
  const form = new FormData()
  form.append('file', file)
  const query = paperType ? `?paperType=${encodeURIComponent(paperType)}` : ''
  return getData<XingceImportStats>(
    http.post(`/admin/xingce/import${query}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  )
}

export const importXingceBundled = (papers?: string[]) =>
  getData<XingceImportStats>(http.post('/admin/xingce/import-bundled', { papers: papers || null }))
