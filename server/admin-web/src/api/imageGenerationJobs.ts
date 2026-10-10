import http, { getData } from './http'

export type ImageGenerationStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export interface ImageGenerationJob {
  id: string
  userId: string
  userName: string
  productKey: string
  styleId: string
  modelId: string | null
  provider: string | null
  status: ImageGenerationStatus
  resultId: string | null
  errorCode: string | null
  errorMessage: string | null
  createdAt: string | null
  startedAt: string | null
  completedAt: string | null
}

export function fetchImageGenerationJobs(params: { status?: string; page: number; size: number }) {
  return getData<{ items: ImageGenerationJob[]; total: number; page: number; size: number }>(
    http.get('/admin/image-generation-jobs', { params }),
  )
}

export function startImageStyleTest(styleId: string, file: File) {
  const data = new FormData()
  data.append('style_id', styleId)
  data.append('file', file)
  return getData<{ taskId: string; status: ImageGenerationStatus }>(http.post('/admin/image-generation-jobs/test', data))
}

export function fetchImageStyleTest(taskId: string) {
  return getData<{
    id: string
    status: ImageGenerationStatus
    styleId: string
    modelId: string | null
    provider: string | null
    resultId: string | null
    errorCode: string | null
    errorMessage: string | null
  }>(http.get(`/admin/image-generation-jobs/${taskId}`))
}

export function downloadImageStyleTest(taskId: string) {
  return http.get<Blob>(`/admin/image-generation-jobs/${taskId}/result`, { responseType: 'blob' })
}
