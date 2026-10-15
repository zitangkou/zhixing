import http, { getData } from './http'
export interface ShenlunMaterial {
  id?: string; type: string; text: string; theme_code: string; theme_element: string[] | string; scene_code: string
  aux_scene_code?: string; usage_note: string; example_topic: string; example_body: string; source_date: string
  source_title: string; source_section: string; source_url?: string; quality_score: number | null; veto: boolean
  review_status: string; fact?: string; result?: string; proves?: string; do_not_use_for?: string
  source_evidence?: string; source_anchor?: string; speaker?: string; context_15?: string; quality_breakdown?: Record<string, number>
  [key: string]: unknown
}
export const list = (params: Record<string, unknown>) => getData<{items:ShenlunMaterial[];total:number;stats:Record<string,number>}>(http.get('/admin/shenlun-materials',{params}))
export const getRules = () => getData<Record<string,any>>(http.get('/admin/shenlun-materials/rules'))
export const save = (item:ShenlunMaterial) => getData<ShenlunMaterial>(item.id ? http.put(`/admin/shenlun-materials/${item.id}`,{collected_date:item.collected_date,item}) : http.post('/admin/shenlun-materials',{collected_date:item.collected_date,item}))
export const remove = (id:string) => getData(http.delete(`/admin/shenlun-materials/${id}`))
export const previewImport = (items:unknown[],collected_date:string) => getData<{index:number;status:string;error?:string;title?:string;score?:number}[]>(http.post('/admin/shenlun-materials/import-preview',{items,collected_date}))
export const importItems = (items:unknown[],collected_date:string) => getData<{added:number;skipped:number}>(http.post('/admin/shenlun-materials/import',{items,collected_date}))
export const exportItems = () => getData<ShenlunMaterial[]>(http.get('/admin/shenlun-materials/export'))
