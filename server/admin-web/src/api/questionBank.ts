import http, { getData } from './http'

// ===== 类型定义 =====

export interface QBQuestionSummary {
  id: string
  origin_type: 'real' | 'generated' | 'manual'
  subject: string
  module: string
  subtype: string
  response_type: string
  stem_summary: string
  answer: string
  has_answer: boolean
  difficulty: number
  lifecycle_status: 'active' | 'retired' | 'disputed'
  paper_count: number
  created_at: string | null
  updated_at: string | null
}

export interface QBQuestionListResult {
  items: QBQuestionSummary[]
  total: number
  page: number
  page_size: number
}

export interface QBVersionBrief {
  id: string
  version_no: number
  stem_summary: string
  content_hash: string
  change_summary: string
  created_at: string | null
}

export interface QBPosition {
  position_id: string
  paper_id: string
  paper_title: string
  exam_year: number | null
  paper_type: string
  section_name: string
  number: number
  section_index: number
  source_key: string
  provenance: Record<string, unknown> | null
  quality_flags: string[] | Record<string, unknown>[]
}

export interface QBMaterial {
  id: string
  title: string
  material_type: string
  content_summary: string
  role: string
  sort_order: number
}

export interface QBQuestionDetail {
  id: string
  origin_type: string
  subject: string
  module: string
  subtype: string
  response_type: string
  difficulty: number
  lifecycle_status: string
  canonical_hash: string
  current_version_id: string | null
  created_at: string | null
  updated_at: string | null
  current_version: {
    id: string
    version_no: number
    stem: string
    items: unknown[] | null
    options: Record<string, string> | null
    correct_answer: string | string[] | null
    explanation: string
    analysis_payload: Record<string, unknown> | null
    answer_source: string
    media: unknown[] | null
    formulas: unknown[] | null
    topic: string
    tag: string
    content_hash: string
    change_summary: string
  } | null
  versions: QBVersionBrief[]
  positions: QBPosition[]
  materials: QBMaterial[]
  quality_flags: string[]
  has_high_risk_flag: boolean
  high_risk_flags: string[]
  paper_count: number
}

export interface QBPaperSummary {
  id: string
  exam_year: number
  exam_kind: string
  paper_type: string
  title: string
  total_questions: number
  position_count: number
  answer_coverage: number
  import_batch_id: string | null
  import_status: string
  import_time: string | null
  created_at: string | null
}

export interface QBPaperSection {
  id: string
  name: string
  sort_order: number
  number_start: number
  number_end: number
  question_count: number
}

export interface QBPaperDetail {
  id: string
  exam_year: number
  exam_kind: string
  paper_type: string
  title: string
  source_document: string
  schema_version: string
  total_questions: number
  position_count: number
  import_batch_id: string | null
  import_status: string
  sections: QBPaperSection[]
  created_at: string | null
  updated_at: string | null
}

export interface QBPositionItem {
  position_id: string
  number: number
  section_index: number
  question_id: string
  stem_summary: string
  answer: string
  has_answer: boolean
  quality_flags: string[] | Record<string, unknown>[]
  provenance: Record<string, unknown> | null
  source_key: string
  lifecycle_status: string
}

export interface QBPositionGroup {
  section_id: string
  section_name: string
  number_start: number
  number_end: number
  question_count: number
  positions: QBPositionItem[]
}

export interface QBReconcileReport {
  paper_id: string
  paper_title: string
  exam_year: number
  paper_type: string
  total_positions: number
  expected_total: number
  answer_coverage: number
  with_answer: number
  without_answer: number
  without_explanation: number
  missing_numbers: number[]
  missing_count: number
  shared_question_count: number
  shared_questions: { question_id: string; paper_count: number }[]
  flag_stats: Record<string, number>
  high_risk_flag_count: number
  sections: {
    section_name: string
    expected_count: number
    actual_count: number
    answer_count: number
    number_range: string
  }[]
}

// ===== API 函数 =====

export function fetchQBQuestions(params: {
  page?: number
  page_size?: number
  origin_type?: string
  module?: string
  subtype?: string
  exam_year?: number
  paper_type?: string
  has_answer?: boolean
  review_status?: string
  quality_flag?: string
}) {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  if (params.origin_type) qs.set('origin_type', params.origin_type)
  if (params.module) qs.set('module', params.module)
  if (params.subtype) qs.set('subtype', params.subtype)
  if (params.exam_year !== undefined) qs.set('exam_year', String(params.exam_year))
  if (params.paper_type) qs.set('paper_type', params.paper_type)
  if (params.has_answer !== undefined) qs.set('has_answer', String(params.has_answer))
  if (params.review_status) qs.set('review_status', params.review_status)
  if (params.quality_flag) qs.set('quality_flag', params.quality_flag)
  const q = qs.toString()
  return getData<QBQuestionListResult>(http.get(`/admin/question-bank/questions${q ? `?${q}` : ''}`))
}

export function fetchQBQuestionDetail(id: string) {
  return getData<QBQuestionDetail>(http.get(`/admin/question-bank/questions/${id}`))
}

export function publishQBQuestion(id: string) {
  return getData<{ id: string; lifecycle_status: string; published: boolean; warnings: string[] }>(
    http.post(`/admin/question-bank/questions/${id}/publish`),
  )
}

export function unpublishQBQuestion(id: string) {
  return getData<{ id: string; lifecycle_status: string; unpublished: boolean }>(
    http.post(`/admin/question-bank/questions/${id}/unpublish`),
  )
}

export function fetchQBPapers(params?: { exam_year?: number; paper_type?: string }) {
  const qs = new URLSearchParams()
  if (params?.exam_year !== undefined) qs.set('exam_year', String(params.exam_year))
  if (params?.paper_type) qs.set('paper_type', params.paper_type)
  const q = qs.toString()
  return getData<QBPaperSummary[]>(http.get(`/admin/question-bank/papers${q ? `?${q}` : ''}`))
}

export function fetchQBPaperDetail(id: string) {
  return getData<QBPaperDetail>(http.get(`/admin/question-bank/papers/${id}`))
}

export function fetchQBPaperPositions(id: string) {
  return getData<QBPositionGroup[]>(http.get(`/admin/question-bank/papers/${id}/positions`))
}

export function fetchQBPaperReconcile(id: string) {
  return getData<QBReconcileReport>(http.get(`/admin/question-bank/papers/${id}/reconcile`))
}

// ===== 常量 =====

export const ORIGIN_TYPE_OPTIONS = [
  { value: 'real', label: '真题' },
  { value: 'generated', label: 'AI生成' },
  { value: 'manual', label: '教研原创' },
]

export const REVIEW_STATUS_OPTIONS = [
  { value: 'approved', label: '已发布' },
  { value: 'pending', label: '待审核/争议' },
  { value: 'retired', label: '已下线' },
]

export const LIFECYCLE_LABELS: Record<string, string> = {
  active: '已发布',
  retired: '已下线',
  disputed: '争议',
}

export const MODULE_OPTIONS = [
  '政治理论',
  '言语理解与表达',
  '数量关系',
  '判断推理',
  '资料分析',
  '常识判断',
]
