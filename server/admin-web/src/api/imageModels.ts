import http, { getData } from './http'

export interface ImageModel {
  id: string
  name: string
  provider: 'dashscope' | 'volcengine' | 'openai-compatible'
  model: string
  baseUrl: string
  credentialEnv: string
  enabled: boolean
  isDefault: boolean
  supportsImageEdit: boolean
  timeoutSeconds: number
  parameters: Record<string, unknown>
  credentialConfigured?: boolean
}

export interface ImageModelConfig {
  schemaVersion: number
  defaultModelId: string
  items: ImageModel[]
}

export function fetchImageModels() {
  return getData<ImageModelConfig>(http.get('/admin/image-models'))
}

export function saveImageModels(items: ImageModel[]) {
  return getData<ImageModelConfig>(http.put('/admin/image-models', { items }))
}
