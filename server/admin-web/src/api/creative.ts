import http, { getData } from './http'
export type IdeaStatus = 'inbox' | 'to_validate' | 'in_progress' | 'settled' | 'paused'
export interface Idea { id:string; title:string; originalText:string; description:string; ideaType:string; status:IdeaStatus; priority:string; starred:boolean; parentId?:string|null; ownerId:number; visibility:'private'|'shared'; nextAction:string; plannedAt?:string|null; reviewAt?:string|null; conclusion:string; pauseReason:string; version:number; archivedAt?:string|null; createdAt:string; updatedAt:string; tags:string[] }
export interface Material { canWrite:boolean; attachments:Array<{id:string;name:string;size:number;mime:string}>; id:string; kind:string; title:string; sourceName:string; author:string; url:string; excerpt:string; insight:string; locator:string; visibility:string; referenceType:string; referenceId:string; ownerId:number; version:number; createdAt:string }
export interface Practice { id:string; ideaId:string; kind:string; title:string; occurredAt:string; action:string; expectation:string; result:string; decision:string; nextAction:string; minutes?:number|null; cost?:number|null; metrics:Array<Record<string,unknown>>; resultLinks:Array<Record<string,unknown>>; version:number }
export interface Detail { canWrite:boolean; idea:Idea; materials:Array<Material&{linkInsight:string}>; children:Idea[]; related:Idea[]; practices:Practice[]; events:Array<{id:string;type:string;payload:Record<string,unknown>;createdAt:string}>; timeline:Array<{id:string;type:string;eventType?:string;payload?:Record<string,unknown>;createdAt:string;practice?:Practice}> }
export const overview = () => getData<Record<string,any>>(http.get('/admin/creative/overview'))
export const listIdeas = (params:Record<string,unknown>) => getData<{items:Idea[];total:number;page:number;pageSize:number}>(http.get('/admin/creative/ideas',{params}))
export const getIdea = (id:string) => getData<Detail>(http.get(`/admin/creative/ideas/${id}`))
export const createIdea = (data:Record<string,unknown>) => getData<Idea>(http.post('/admin/creative/ideas',data))
export const capture = (text:string,title:string,url:string,idempotencyKey:string) => getData<Idea>(http.post('/admin/creative/captures',{text,title,url,idempotencyKey}))
export const updateIdea = (id:string,data:Record<string,unknown>) => getData<Idea>(http.patch(`/admin/creative/ideas/${id}`,data))
export const transition = (id:string,status:IdeaStatus,reason:string,version:number) => getData<Idea>(http.post(`/admin/creative/ideas/${id}/transition`,{status,reason,version}))
export const archiveIdea = (id:string) => getData<Idea>(http.post(`/admin/creative/ideas/${id}/archive`))
export const deleteIdea = (id:string) => getData<{id:string}>(http.delete(`/admin/creative/ideas/${id}`))
export const restoreIdea = (id:string) => getData<Idea>(http.post(`/admin/creative/ideas/${id}/restore`))
export const addPractice = (id:string,data:Record<string,unknown>) => getData<Practice>(http.post(`/admin/creative/ideas/${id}/practices`,data))
export const listMaterials = (params:Record<string,unknown>) => getData<{items:Material[];total:number}>(http.get('/admin/creative/materials',{params}))
export const createMaterial = (data:Record<string,unknown>) => getData<Material>(http.post('/admin/creative/materials',data))
export const linkMaterial = (ideaId:string,materialId:string) => getData(http.post(`/admin/creative/ideas/${ideaId}/materials/${materialId}`))
export const recycleBin = () => getData<{ideas:Idea[];materials:Material[]}>(http.get('/admin/creative/recycle-bin'))

export const unarchiveIdea = (id:string) => getData<Idea>(http.post(`/admin/creative/ideas/${id}/unarchive`))
export const deleteMaterial = (id:string) => getData(http.delete(`/admin/creative/materials/${id}`))
export const restoreMaterial = (id:string) => getData<Material>(http.post(`/admin/creative/materials/${id}/restore`))
export const uploadAttachment = (id:string,file:File) => { const data=new FormData(); data.append('file',file); return getData<{id:string;name:string;size:number;mime:string}>(http.post(`/admin/creative/materials/${id}/attachments`,data)) }
export const exportIdea = (id:string) => getData<{filename:string;content:string}>(http.get(`/admin/creative/ideas/${id}/export`))
export const unrelateIdea = (id:string,targetId:string) => getData(http.delete(`/admin/creative/ideas/${id}/relations/${targetId}`))
export const downloadAttachment = async (id:string,name:string) => { const res=await http.get(`/admin/creative/attachments/${id}/download`,{responseType:'blob'}); const url=URL.createObjectURL(res.data as Blob); const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url) }
export const updatePractice = (id:string,data:Record<string,unknown>) => getData<Practice>(http.patch(`/admin/creative/practices/${id}`,data))
export const deletePractice = (id:string) => getData(http.delete(`/admin/creative/practices/${id}`))
export const unrelate = (id:string,targetId:string) => getData(http.delete(`/admin/creative/ideas/${id}/relations/${targetId}`))
export const unlinkMaterial = (id:string,materialId:string) => getData(http.delete(`/admin/creative/ideas/${id}/materials/${materialId}`))
export const updateMaterial = (id:string,data:Record<string,unknown>) => getData<Material>(http.patch(`/admin/creative/materials/${id}`,data))
export const listTags = () => getData<Array<{id:string;name:string}>>(http.get('/admin/creative/tags'))
export const deleteAttachment = (id:string) => getData(http.delete(`/admin/creative/attachments/${id}`))
