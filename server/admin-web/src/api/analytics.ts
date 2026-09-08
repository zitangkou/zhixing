import http, { getData } from './http'

// ── 通用类型 ──────────────────────────────────────────
export interface AccuracySummary {
  total_attempts: number
  correct_count: number
  accuracy_rate: number
  avg_time_ms: number
  by_module: Array<{ module: string; attempts: number; correct_count: number; accuracy: number }>
  by_subtype: Array<{ subtype: string; attempts: number; correct_count: number; accuracy: number }>
}

export interface QuestionAccuracy {
  question_id: string
  total_attempts: number
  correct_count: number
  accuracy_rate: number
  avg_time_ms: number
}

export interface OptionDistribution {
  question_id: string
  total_attempts: number
  correct_answer: string
  option_distribution: Array<{
    label: string
    text: string
    count: number
    percentage: number
    is_correct: boolean
  }>
  anomalies: string[]
}

export interface ErrorPathSummary {
  total_errors: number
  by_error_path: Array<{
    type: string
    count: number
    percentage: number
    involved_question_count: number
    example_question_ids: string[]
  }>
}

export interface QuestionErrorPaths {
  question_id: string
  total_wrong: number
  error_path_distribution: Array<{ type: string; count: number; percentage: number }>
  distractor_trace: Array<{
    option: string
    type: string
    error_formula: string
    computed_value: string
  }>
}

export interface DashboardData {
  total_attempts: number
  correct_count: number
  overall_accuracy: number
  avg_time_ms: number
  active_question_count: number
  top_error_paths: Array<{ type: string; count: number; percentage: number }>
  low_accuracy_top10: Array<{
    question_id: string
    module: string
    subtype: string
    difficulty: number
    attempts: number
    correct_count: number
    accuracy: number
  }>
  ambiguous_questions: Array<{
    question_id: string
    module: string
    subtype: string
    attempts: number
    accuracy: number
    anomalies: string[]
  }>
  disputed_questions: Array<{
    question_id: string
    module: string
    subtype: string
    attempts: number
    accuracy: number
    anomalies: string[]
  }>
}

// ── API 方法 ──────────────────────────────────────────
export const getAccuracy = (params?: Record<string, string>) =>
  getData<AccuracySummary>(http.get('/admin/analytics/accuracy', { params }))

export const getQuestionAccuracy = (questionId: string, source?: string) =>
  getData<QuestionAccuracy>(
    http.get(`/admin/analytics/accuracy/questions/${questionId}`, { params: source ? { source } : {} }),
  )

export const getOptionDistribution = (questionId: string, source?: string) =>
  getData<OptionDistribution>(
    http.get(`/admin/analytics/options/${questionId}`, { params: source ? { source } : {} }),
  )

export const getOptionDistributionBatch = (questionIds: string[], source?: string) =>
  getData<{ results: OptionDistribution[] }>(
    http.post('/admin/analytics/options/batch', { question_ids: questionIds }, { params: source ? { source } : {} }),
  )

export const getErrorPaths = (params?: Record<string, string>) =>
  getData<ErrorPathSummary>(http.get('/admin/analytics/error-paths', { params }))

export const getQuestionErrorPaths = (questionId: string, source?: string) =>
  getData<QuestionErrorPaths>(
    http.get(`/admin/analytics/error-paths/questions/${questionId}`, { params: source ? { source } : {} }),
  )

export const getDashboard = (source?: string) =>
  getData<DashboardData>(http.get('/admin/analytics/dashboard', { params: source ? { source } : {} }))
