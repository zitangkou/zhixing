import http, { getData } from './http'

// ===== 类型定义 =====

export interface GenStats {
  total_generated: number
  auto_pass_rate: number
  auto_passed: number
  auto_failed: number
  pending_review: number
  approved: number
  rejected: number
  published: number
  batch_count: number
  by_engine: Record<string, { total: number; passed: number; failed: number }>
}

export interface GenBatchSummary {
  batch_id: string
  engine_type: string
  label: string
  template_version: string
  seed: number | null
  total_questions: number
  passed_count: number
  failed_count: number
  pass_rate: number
  created_at: string
  status: string
  source_file: string
}

export interface GenBatchListResult {
  items: GenBatchSummary[]
  total: number
  page: number
  page_size: number
}

export interface GenQuestionSummary {
  question_id: string
  origin_type: string
  module: string
  subtype: string
  difficulty: number
  answer: string
  dual_solve_match: boolean
  distractor_count: number
  stem_summary: string
  review_status: string
  review_comment?: string
  reviewer?: string
  reviewed_at?: string | null
  batch_id?: string
  engine_type?: string
}

export interface GenBatchDetail extends GenBatchSummary {
  dual_solve_method: string
  questions: GenQuestionSummary[]
}

export interface GenTemplate {
  template_id: string
  engine_type: string
  skill: string
  version: string
  description: string
  param_schema: Record<string, unknown>
  created_at: string
}

export interface GenTemplateHistoryItem {
  version: string
  date: string
  changes: string
  file: string
}

export interface GenValidationChecks {
  dual_solve_match: boolean
  options_distinct: boolean
  answer_unique: boolean
  data_consistent: boolean
  distractors_traced: boolean
}

export interface GenValidationItem {
  question_id: string
  subtype: string
  difficulty: number
  checks: GenValidationChecks
  all_passed: boolean
  failed_checks: string[]
}

export interface GenValidationReport {
  batch_id: string
  total: number
  passed: number
  failed: number
  pass_rate: number
  failure_distribution: Record<string, number>
  failed_questions: string[]
  per_question: GenValidationItem[]
}

export interface GenQuestionDetail {
  question_id: string
  batch_id: string
  engine_type: string
  origin_type: string
  module: string
  subtype: string
  difficulty: number
  stem: string
  material: Record<string, unknown> | null
  options: Record<string, string>
  answer: string
  explanation: string
  calc_tree: Array<Record<string, unknown>>
  distractors: Record<string, Record<string, unknown>>
  dual_solve: Record<string, unknown>
  generation_meta: Record<string, unknown>
  validation: GenValidationItem
  review: {
    status: string
    comment: string
    reviewer: string
    reviewed_at: string | null
  }
  question_item_id: string | null
  lifecycle_status: string | null
}

export interface GenReviewTaskResult {
  items: GenQuestionSummary[]
  total: number
  page: number
  page_size: number
  stats: {
    total: number
    pending: number
    approved: number
    rejected: number
  }
}

export interface GenReviewResult {
  question_id: string
  action: string
  review_record_id: string
  question_item_id: string | null
  lifecycle_status: string | null
  message: string
}

export interface GenBatchRunResult {
  batch_id: string
  status: string
  message: string
}

// ===== API 函数 =====

export function fetchGenStats() {
  return getData<GenStats>(http.get('/admin/generation/stats'))
}

export function fetchGenBatches(params?: { page?: number; page_size?: number; engine_type?: string }) {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.page_size) qs.set('page_size', String(params.page_size))
  if (params?.engine_type) qs.set('engine_type', params.engine_type)
  const q = qs.toString()
  return getData<GenBatchListResult>(http.get(`/admin/generation/batches${q ? `?${q}` : ''}`))
}

export function fetchGenBatchDetail(batchId: string) {
  return getData<GenBatchDetail>(http.get(`/admin/generation/batches/${batchId}`))
}

export function runGenBatch(body: { engine_type: string; skill?: string; count: number; seed: number }) {
  return getData<GenBatchRunResult>(http.post('/admin/generation/batches/run', body))
}

export function fetchGenTemplates() {
  return getData<GenTemplate[]>(http.get('/admin/generation/templates'))
}

export function fetchGenTemplateHistory(templateId: string) {
  return getData<GenTemplateHistoryItem[]>(http.get(`/admin/generation/templates/${templateId}/history`))
}

export function fetchGenValidation(batchId: string) {
  return getData<GenValidationReport>(http.get(`/admin/generation/batches/${batchId}/validation`))
}

export function fetchGenReviewTasks(params?: {
  status?: string
  engine_type?: string
  module?: string
  subtype?: string
  difficulty?: number
  page?: number
  page_size?: number
}) {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.engine_type) qs.set('engine_type', params.engine_type)
  if (params?.module) qs.set('module', params.module)
  if (params?.subtype) qs.set('subtype', params.subtype)
  if (params?.difficulty !== undefined) qs.set('difficulty', String(params.difficulty))
  if (params?.page) qs.set('page', String(params.page))
  if (params?.page_size) qs.set('page_size', String(params.page_size))
  const q = qs.toString()
  return getData<GenReviewTaskResult>(http.get(`/admin/generation/review-tasks${q ? `?${q}` : ''}`))
}

export function fetchGenQuestionDetail(questionId: string) {
  return getData<GenQuestionDetail>(http.get(`/admin/generation/questions/${questionId}`))
}

export function reviewGenQuestion(questionId: string, body: {
  action: 'approve' | 'reject'
  comment?: string
  reviewer?: string
  batch_id?: string
}) {
  return getData<GenReviewResult>(http.post(`/admin/generation/questions/${questionId}/review`, body))
}

export function batchReviewGenQuestions(body: {
  action: 'approve' | 'reject'
  comment?: string
  reviewer?: string
  question_ids: string[]
}) {
  return getData<{ processed: number; action: string; results: Array<{ question_id: string; action: string }> }>(
    http.post('/admin/generation/questions/batch-review', body),
  )
}

// ===== 常量 =====

export const ENGINE_TYPE_LABELS: Record<string, string> = {
  qa_data_analysis: '资料分析',
  qa_quantity: '数量关系',
}

export const REVIEW_STATUS_LABELS: Record<string, string> = {
  pending: '待审核',
  approve: '已通过',
  reject: '已驳回',
}

export const REVIEW_STATUS_TYPES: Record<string, string> = {
  pending: 'warning',
  approve: 'success',
  reject: 'danger',
}

export const VALIDATION_CHECK_LABELS: Record<string, string> = {
  dual_solve_match: '双求解一致',
  options_distinct: '选项互异',
  answer_unique: '答案唯一',
  data_consistent: '数据一致',
  distractors_traced: '干扰项可追溯',
}
