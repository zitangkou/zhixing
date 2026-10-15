import http, { getData } from './http'
export interface VocabularyItem {
  id: string; phrase: string; kind: string; issueDate: string; meaning: string
  topics: string[]; useCases: string[]; sample: string; usageNote: string; exactContext: string
  sourceTitle: string; sourceUrl: string; pageNo: string; pageName: string
  reviewStatus: string; reviewNote: string; reviewedBy: string
  sources: { title: string; url: string; pageNo: string; pageName: string; exactContext: string }[]
}
export interface VocabularyJob { id: string; issueDate: string; status: string; attempts: number; error: string; progress: { pages?: number; articles?: number; processed?: number; added?: number; duplicates?: number; invalid?: number; shenlunAdded?: number; shenlunDuplicates?: number; shenlunInvalid?: number; shenlunQualityRejected?: number; analysisCacheHits?: number; analysisCacheWriteFailures?: number; failures?: string[] } }
export const listVocabulary = (params: Record<string, unknown>) => getData<{ items: VocabularyItem[]; total: number }>(http.get('/admin/rmrb-vocabulary', { params }))
export const listVocabularyJobs = () => getData<VocabularyJob[]>(http.get('/admin/rmrb-vocabulary/jobs'))
export const collectVocabulary = (issue_date: string) => getData<VocabularyJob>(http.post('/admin/rmrb-vocabulary/collect', { issue_date }))
export const reviewVocabulary = (ids: string[], status: string, note: string) => getData(http.put('/admin/rmrb-vocabulary/review', { ids, status, note }))
export const vocabularyRules = () => getData<{ version: string; selection: string[]; exclude: string[]; validation: string[] }>(http.get('/admin/rmrb-vocabulary/rules'))
export const editVocabulary = (id: string, data: Record<string, unknown>) => getData<VocabularyItem>(http.put(`/admin/rmrb-vocabulary/${id}`, data))
