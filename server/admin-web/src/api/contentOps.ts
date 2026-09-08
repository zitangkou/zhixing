import http, { getData } from './http'

export type ContentOpsStatus = 'draft' | 'teaching_review' | 'ops_review' | 'ready' | 'published' | 'rejected'
export type ReviewStage = 'teaching' | 'operations'
export interface ReviewChecklistItem { key: string; label: string }
export interface ReviewStageConfig { key: ReviewStage; label: string; checklist: ReviewChecklistItem[] }
export interface ContentReviewRecord { id: string; stage: ReviewStage; decision: 'approved' | 'rejected'; checklist: Record<string, boolean>; note: string; reviewerId?: number; reviewerUsername: string; reviewerName: string; createdAt: string }
export interface ContentOpsTemplate { id: string; code: string; productKey: string; name: string; description: string; slots: string[]; channels: string[]; sortOrder: number; status: string }
export interface ContentVariant { title?: string; body?: string; [key: string]: unknown }
export interface ContentEntryTarget { topicType: 'daily' | 'evergreen' | 'review'; entryId: string; h5Path: string; miniappPath: string; qrScene: string; officialAccountKeyword: string }
export interface PublishableTarget { entryId: string; sourceId: string; sourceType: string; title: string; publishDate: string; topicTypes: ContentEntryTarget['topicType'][]; h5Path: string; miniappPath: string; officialAccountKeyword: string }
export interface PreflightCheck { key: string; label: string; passed: boolean; level: 'error' | 'warning'; message: string }
export interface ContentPreflight { passed: boolean; checks: PreflightCheck[]; errorCount: number; warningCount: number; resolvedEntry?: PublishableTarget }
export interface ContentPackage { id: string; productKey: string; templateId: string; sourceType: string; sourceId: string; sourceTitle: string; campaignKey: string; deepLink: string; entryTarget: ContentEntryTarget; slotValues: Record<string, string>; variants: Record<string, ContentVariant>; reviewNote: string; reviewHistory: ContentReviewRecord[]; status: ContentOpsStatus; plannedAt?: string; publishedAt?: string; createdAt: string; updatedAt: string }
export interface ContentPackageExport { schemaVersion: string; generatedAt: string; template: ContentOpsTemplate; package: ContentPackage; entryTarget: ContentEntryTarget; preflight: ContentPreflight; channels: Array<{ channel: string; content: ContentVariant; deepLink: string; plannedAt?: string; manualPublishRequired: boolean }>; checklist: string[] }
export interface ContentOpsOverview { windowDays: number; scheduledCount: number; readyInventory: number; reviewBacklog: number; unplannedDrafts: number; productMix: { shenlun: number; theory: number }; statusCounts: Record<string, number>; alerts: Array<{ level: 'info' | 'warning'; code: string; message: string }>; healthy: boolean }
export interface ContentReferencePlatform { key: string; name: string; sourceStatus: string; sourceStatusLabel: string; format: string; structure: string[]; deliverables: string[]; example: { title: string; hook: string; sections: string[] } }
export interface ContentReferenceLibrary { schemaVersion: string; updatedAt: string; title: string; sources: Array<{ kind: string; label: string; path: string }>; platforms: ContentReferencePlatform[] }

export const fetchContentTemplates = (productKey?: string) => getData<ContentOpsTemplate[]>(http.get('/admin/content-ops/templates', { params: { productKey } }))
export const fetchPublishableTargets = (productKey: string) => getData<PublishableTarget[]>(http.get('/admin/content-ops/entry-targets', { params: { productKey } }))
export const fetchContentReviewConfig = () => getData<{ stages: ReviewStageConfig[] }>(http.get('/admin/content-ops/review-config'))
export const fetchContentReferenceLibrary = () => getData<ContentReferenceLibrary>(http.get('/admin/content-ops/reference-library'))
export const fetchContentPackages = (params?: { productKey?: string; status?: string }) => getData<ContentPackage[]>(http.get('/admin/content-ops/packages', { params }))
export const fetchContentOpsOverview = (days = 7) => getData<ContentOpsOverview>(http.get('/admin/content-ops/overview', { params: { days } }))
export const createContentPackage = (data: Record<string, unknown>) => getData<ContentPackage>(http.post('/admin/content-ops/packages', data))
export const generateContentPackageFromArticle = (data: Record<string, unknown>) => getData<ContentPackage>(http.post('/admin/content-ops/packages/generate-from-article', data))
export const updateContentPackage = (id: string, data: Record<string, unknown>) => getData<ContentPackage>(http.put(`/admin/content-ops/packages/${id}`, data))
export const updateContentPackageStatus = (id: string, status: ContentOpsStatus, reviewNote = '', checklist: Record<string, boolean> = {}) => getData<ContentPackage>(http.post(`/admin/content-ops/packages/${id}/status`, { status, reviewNote, checklist }))
export const exportContentPackage = (id: string) => getData<ContentPackageExport>(http.get(`/admin/content-ops/packages/${id}/export`))
export const fetchContentPackagePreflight = (id: string) => getData<ContentPreflight>(http.get(`/admin/content-ops/packages/${id}/preflight`))
