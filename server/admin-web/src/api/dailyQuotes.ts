import http, { getData } from './http'
export interface QuoteExample { topic: string; text: string; shortText: string; highlights: string[] }
export interface DailyQuote {
  history?: {at:string;actor:string;fields:string[]}[]; id: string; text: string; collectedDate: string; articleDate: string; articleTitle: string; sourceUrl: string
  source: string; author: string; component: string; quoteType: string; topics: string[]; use: string; formula: string
  why: string; guidance: string; pitfall: string; evidence: string; evidenceLocation: string
  highlights: string[]; examples: QuoteExample[]; examplesStatus?: string; reviewStatus: string; auditStatus: string; enabled: boolean; selected: boolean
}
export const listQuotes = (params: Record<string, unknown>) => getData<{items: DailyQuote[];total:number;stats:Record<string,number>}>(http.get('/admin/daily-quotes', {params}))
export const saveQuote = (item: DailyQuote) => getData<DailyQuote>(item.id ? http.put(`/admin/daily-quotes/${item.id}`, {collected_date:item.collectedDate,item}) : http.post('/admin/daily-quotes', {collected_date:item.collectedDate,item}))
export const deleteQuote = (id:string) => getData<{deleted:string}>(http.delete(`/admin/daily-quotes/${id}`))
export interface DailyQuoteJob {
  status: string; error: string; attempts: number; updatedAt: string
  metrics?: Record<string, number | boolean | string>; zeroReason?: string
  failures?: {url?:string;source?:string;stage?:string;code?:string;error?:string}[]
  warnings?: {url?:string;source?:string;code?:string;message?:string}[]
}
export const getQuoteJob = (issue_date:string) => getData<{job: null | DailyQuoteJob; enabled:boolean;llmConfigured:boolean;schedule:string}>(http.get('/admin/daily-quotes/job',{params:{issue_date}}))
export const runQuoteJob = (issue_date:string) => getData(http.post('/admin/daily-quotes/run',{issue_date}))
export const previewQuotes = (items:unknown[],collected_date:string) => getData<{index:number;text?:string;status:string;error?:string;evidenceMissing?:boolean}[]>(http.post('/admin/daily-quotes/import-preview',{items,collected_date}))
export const importQuotes = (items:unknown[],collected_date:string) => getData<{added:number;skipped:number}>(http.post('/admin/daily-quotes/import',{items,collected_date}))
export const getSelection = (issue_date:string) => getData<string[]>(http.get('/admin/daily-quotes/selection',{params:{issue_date}}))
export const saveSelection = (issue_date:string,quote_ids:string[]) => getData(http.put('/admin/daily-quotes/selection',{issue_date,quote_ids}))
export const generateExamples = (id:string) => getData<{generated:boolean;queued?:boolean;existing?:boolean}>(http.post(`/admin/daily-quotes/${id}/examples`))
export const exportQuotes = (params:Record<string,unknown>) => getData<DailyQuote[]>(http.get('/admin/daily-quotes/export',{params}))
