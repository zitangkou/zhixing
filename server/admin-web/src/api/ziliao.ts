import http, { getData } from './http'

export interface ZiliaoFormula {
  id: string
  code: string
  name: string
  category: string
  definition: string
  latex: string
  formulaPlain: string
  scenarios: string
  pitfalls: string
  relatedTypeCodes: string[]
  relatedTrickCodes: string[]
  keywords: string[]
  examFreq: number
  sortOrder: number
  isPublished: boolean
}

export interface ZiliaoFormulaImportResult {
  total: number
  inserted: number
  updated: number
  skipped: number
  errors: string[]
}

export interface ZiliaoQuestionType {
  id: string
  code: string
  name: string
  category: string
  description: string
  ability: string
  difficulty: number
  examFreq: number
  formulaCodes: string[]
  trickCodes: string[]
  keywords: string[]
  sortOrder: number
  isPublished: boolean
}

export interface ZiliaoTrick {
  id: string
  code: string
  name: string
  category: string
  principle: string
  whenToUse: string
  whenNot: string
  errorNote: string
  formulaCodes: string[]
  example: string
  sortOrder: number
  isPublished: boolean
}

export const listFormulas = () => getData<ZiliaoFormula[]>(http.get('/admin/ziliao/formulas'))
export const createFormula = (data: Partial<ZiliaoFormula>) =>
  getData<ZiliaoFormula>(http.post('/admin/ziliao/formulas', data))
export const updateFormula = (id: string, data: Partial<ZiliaoFormula>) =>
  getData<ZiliaoFormula>(http.put(`/admin/ziliao/formulas/${id}`, data))
export const deleteFormula = (id: string) => getData(http.delete(`/admin/ziliao/formulas/${id}`))
export const importFormulasJson = (data: {
  content: string
  overwrite: boolean
  publishDefault: boolean
}) => getData<ZiliaoFormulaImportResult>(http.post('/admin/ziliao/formulas/import-json', data))
export const uploadFormulasJson = (file: File, overwrite: boolean, publishDefault: boolean) => {
  const form = new FormData()
  form.append('file', file)
  return getData<ZiliaoFormulaImportResult>(
    http.post(
      `/admin/ziliao/formulas/upload-json?overwrite=${overwrite ? 'true' : 'false'}&publish_default=${publishDefault ? 'true' : 'false'}`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ),
  )
}

export const listTypes = () => getData<ZiliaoQuestionType[]>(http.get('/admin/ziliao/types'))
export const createType = (data: Partial<ZiliaoQuestionType>) =>
  getData<ZiliaoQuestionType>(http.post('/admin/ziliao/types', data))
export const updateType = (id: string, data: Partial<ZiliaoQuestionType>) =>
  getData<ZiliaoQuestionType>(http.put(`/admin/ziliao/types/${id}`, data))
export const deleteType = (id: string) => getData(http.delete(`/admin/ziliao/types/${id}`))

export const listTricks = () => getData<ZiliaoTrick[]>(http.get('/admin/ziliao/tricks'))
export const createTrick = (data: Partial<ZiliaoTrick>) =>
  getData<ZiliaoTrick>(http.post('/admin/ziliao/tricks', data))
export const updateTrick = (id: string, data: Partial<ZiliaoTrick>) =>
  getData<ZiliaoTrick>(http.put(`/admin/ziliao/tricks/${id}`, data))
export const deleteTrick = (id: string) => getData(http.delete(`/admin/ziliao/tricks/${id}`))

export const seedZiliao = (force = false) =>
  getData<{ formulas: number; types: number; tricks: number; samplePaper: boolean }>(
    http.post(`/admin/ziliao/seed?force=${force ? 'true' : 'false'}`),
  )

export const fetchImportGuide = () =>
  getData<{ markdown: string; examplePath: string }>(http.get('/admin/ziliao/import-guide'))
