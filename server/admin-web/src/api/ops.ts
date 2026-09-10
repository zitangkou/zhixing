import http, { getData } from './http'

export interface OpsStep {
  id: string
  key: string
  name: string
  product: string
  stepType: string
  command: string
  cwdRel: string
  enabled: boolean
  sortHint: number
  notes: string
  inPipelineEnabled?: boolean
  sortOrder?: number
  linkId?: string
}

export interface OpsPipeline {
  id: string
  key: string
  name: string
  product: string
  enabled: boolean
  cron: string
  timezone: string
  notes: string
  cronNote?: string
  steps: OpsStep[]
}

export interface OpsRun {
  id: string
  pipelineId: string
  pipelineName: string
  status: string
  currentIndex: number
  log: string
  startedAt: string
  finishedAt: string
  materialRoot: string
  steps: { id: string; stepName: string; status: string; exitCode: number | null; output: string }[]
}

export function fetchOpsSteps() {
  return getData<OpsStep[]>(http.get('/admin/ops/steps'))
}

export function patchOpsStep(id: string, data: Partial<OpsStep> & { notes?: string; command?: string }) {
  return getData<OpsStep>(http.patch(`/admin/ops/steps/${id}`, data))
}

export function runOpsStep(id: string) {
  return getData<{ stepId: string; name: string; exitCode: number; output: string; ok: boolean }>(
    http.post(`/admin/ops/steps/${id}/run`),
  )
}

export function fetchOpsPipelines() {
  return getData<OpsPipeline[]>(http.get('/admin/ops/pipelines'))
}

export function patchOpsPipeline(
  id: string,
  data: {
    name?: string
    enabled?: boolean
    cron?: string
    notes?: string
    steps?: { linkId: string; enabled?: boolean; sortOrder?: number }[]
  },
) {
  return getData<OpsPipeline>(http.patch(`/admin/ops/pipelines/${id}`, data))
}

export function runOpsPipeline(id: string) {
  return getData<OpsRun>(http.post(`/admin/ops/pipelines/${id}/run`))
}

export function fetchOpsRuns(pipelineId?: string) {
  return getData<OpsRun[]>(http.get('/admin/ops/runs', { params: pipelineId ? { pipeline_id: pipelineId } : undefined }))
}

export function confirmOpsRun(id: string) {
  return getData<OpsRun>(http.post(`/admin/ops/runs/${id}/confirm`))
}
