import http, { getData } from './http'

export interface ImageStylePreset {
  id: string
  slug: string
  name: string
  category: string
  productKey: string
  modelId: string
  description: string
  status: 'draft' | 'active' | 'archived'
  version: string
  sortOrder: number
  promptTemplate: string
  negativePrompt: string
  rules: Record<string, unknown>
  controls: Record<string, unknown>
  providerParameters: Record<string, unknown>
  maintainerNotes: string
}

export interface ImageStyleConfig {
  schemaVersion: number
  items: ImageStylePreset[]
}

export interface ImageStyleImportPreview {
  style: ImageStylePreset
  canImport: boolean
  conflict: string
}

export function fetchImageStyles() {
  return getData<ImageStyleConfig>(http.get('/admin/image-styles'))
}

export function createImageStyle(style: ImageStylePreset) {
  return getData<ImageStyleConfig>(http.post('/admin/image-styles', style))
}

export function updateImageStyle(id: string, style: ImageStylePreset) {
  return getData<ImageStyleConfig>(http.put(`/admin/image-styles/${id}`, style))
}

export function deleteImageStyle(id: string) {
  return getData<ImageStyleConfig>(http.delete(`/admin/image-styles/${id}`))
}

export function previewImageStyleMarkdown(markdown: string) {
  return getData<ImageStyleImportPreview>(http.post('/admin/image-styles/import/preview', { markdown }))
}

export function importImageStyleMarkdown(markdown: string) {
  return getData<{ style: ImageStylePreset; config: ImageStyleConfig }>(http.post('/admin/image-styles/import', { markdown }))
}
