import http, { getData } from './http'

export interface PracticeSkill {
  skill: string
  name: string
  formula: string
}

export interface CalcStep {
  step: number
  operation: string
  formula?: string
  inputs?: Record<string, string | number>
  result: string | number
}

export interface PracticeQuestion {
  question_id: string
  subtype: string
  difficulty: number
  difficulty_label: string
  stem: string
  options: Record<string, string>
  answer: string
  explanation: string
  calc_tree: CalcStep[]
  distractors: Record<string, { type: string; error_formula: string; computed_value?: string }>
  material: { material_id: string; content: string }
}

export interface DailyPackage {
  daily_id: string
  skill: string
  skill_name: string
  formula: string
  tip: string
  date: string
  method_example: PracticeQuestion | null
  progressive: PracticeQuestion[]
  material_set: PracticeQuestion[]
  material_content: string
  total_questions: number
}

export interface ErrorPath {
  type: string
  error_formula: string
  correct_formula: string
}

export interface SubmitResultItem {
  question_id: string
  correct_answer: string
  user_answer: string
  is_correct: boolean
  error_path: ErrorPath | null
  explanation: string
}

export interface SubmitResult {
  daily_id: string
  total: number
  correct_count: number
  wrong_count: number
  results: SubmitResultItem[]
}

export interface ReviewErrorPath {
  type: string
  count: number
  correct_formula: string
  error_formula: string
}

export interface ReviewQuestion {
  question_id: string
  user_answer: string
  correct_answer: string
  error_path: ErrorPath | null
  stem: string
  options: Record<string, string>
  explanation: string
}

export interface ReviewCard {
  daily_id: string
  total: number
  correct_count: number
  wrong_count: number
  error_paths: ReviewErrorPath[]
  review_questions: ReviewQuestion[]
}

export const listSkills = () => getData<PracticeSkill[]>(http.get('/api/practice/skills'))

export const getDaily = (skill: string, date: string) =>
  getData<DailyPackage>(http.get('/api/practice/daily', { params: { skill, date } }))

export const submitAnswers = (dailyId: string, answers: Array<{ question_id: string; user_answer: string }>) =>
  getData<SubmitResult>(http.post(`/api/practice/${dailyId}/submit`, { answers }))

export const getReview = (dailyId: string) =>
  getData<ReviewCard>(http.get(`/api/practice/${dailyId}/review`))
