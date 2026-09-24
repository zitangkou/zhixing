import http, { getData } from './http'

export interface FeedbackItem {
  id: string
  userId: string
  username: string
  productKey: string
  content: string
  status: string
  note: string
  createdAt: string | null
  handledAt: string | null
}

export interface FeedbackPage {
  items: FeedbackItem[]
  total: number
  page: number
  size: number
}

export const listFeedbacks = (params?: { status?: string; productKey?: string; page?: number; size?: number }) =>
  getData<FeedbackPage>(http.get('/admin/feedbacks', { params }))

export const handleFeedback = (id: string, data: { action: 'adopted' | 'rejected'; note?: string; points?: number }) =>
  getData<FeedbackItem>(http.post(`/admin/feedbacks/${id}/handle`, data))
