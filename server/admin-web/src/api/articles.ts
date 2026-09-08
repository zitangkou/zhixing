import http, { getData } from './http'
import type { Article, PageResult, Question } from '@/types'

export function fetchArticles(params: {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
}) {
  return getData<PageResult<Article>>(http.get('/admin/articles', { params }))
}

export function fetchArticle(id: string) {
  return getData<Article>(http.get(`/admin/articles/${id}`))
}

export function createArticle(data: Record<string, unknown>) {
  return getData<Article>(http.post('/admin/articles', data))
}

export function inferArticleMetadata(data: { content: string; title?: string }) {
  return getData<{
    title: string
    content: string
    source: string
    sourceUrl?: string
    publishDate: string
    summary: string
    tags: string[]
    categoryId?: string | null
    categoryName?: string | null
    importance: number
  }>(http.post('/admin/articles/infer-metadata', data))
}

export function importArticleMarkdown(data: {
  markdown: string
  status?: string
  category_id?: string | null
  is_featured?: boolean
  source?: string
  publish_date?: string
  tags?: string[]
}) {
  return getData<Article & {
    stats?: { chapters: number; sections: number; paragraphs: number }
    parse_warnings?: string[]
  }>(http.post('/admin/articles/import-markdown', data))
}

export function updateArticle(id: string, data: Record<string, unknown>) {
  return getData<Article>(http.put(`/admin/articles/${id}`, data))
}

export function deleteArticle(id: string) {
  return getData<null>(http.delete(`/admin/articles/${id}`))
}

export function approveArticle(id: string) {
  return getData<Article>(http.post(`/admin/articles/${id}/approve`))
}

export function rejectArticle(id: string) {
  return getData<Article>(http.post(`/admin/articles/${id}/reject`))
}

export function approveArticleQuestions(id: string) {
  return getData<{ count: number }>(http.post(`/admin/articles/${id}/approve-questions`))
}

export function batchApproveArticles(articleIds: string[], approveQuestions = true) {
  return getData<{ article_count: number; question_count: number }>(
    http.post('/admin/articles/batch-approve', { article_ids: articleIds, approve_questions: approveQuestions }),
  )
}

export function batchRejectArticles(articleIds: string[]) {
  return getData<{ count: number }>(http.post('/admin/articles/batch-reject', { article_ids: articleIds }))
}

export function batchSetArticleCategory(articleIds: string[], categoryId: string | null) {
  return getData<{ count: number }>(
    http.post('/admin/articles/batch-category', { article_ids: articleIds, category_id: categoryId }),
  )
}

export function batchDeleteArticles(articleIds: string[]) {
  return getData<{ count: number }>(http.post('/admin/articles/batch-delete', { article_ids: articleIds }))
}

export function batchApproveQuestions(questionIds: string[]) {
  return getData<{ count: number }>(http.post('/admin/questions/batch-approve', { question_ids: questionIds }))
}

export function batchDeleteQuestions(questionIds: string[]) {
  return getData<{ count: number }>(http.post('/admin/questions/batch-delete', { question_ids: questionIds }))
}

export function generateQuestionsAi(
  id: string,
  data?: {
    section_ids?: string[]
    single?: number
    multiple?: number
    judge?: number
  },
) {
  return getData<{
    count: number
    validation_warnings?: string[]
    section_ids?: string[]
    breakdown?: { single: number; multiple: number; judge: number }
  }>(http.post(`/admin/articles/${id}/generate-questions-ai`, data ?? {}))
}

export function importQuestions(
  id: string,
  data: { markdown: string; pending?: boolean; replace_existing?: boolean },
) {
  return getData<{ count: number; parse_warnings?: string[] }>(
    http.post(`/admin/articles/${id}/import-questions`, data),
  )
}

export function fetchQuestions(articleId: string, page = 1, pageSize = 20) {
  return getData<PageResult<Question>>(
    http.get('/admin/questions', {
      params: { article_id: articleId, page, page_size: pageSize },
    }),
  )
}

export function createQuestion(data: Record<string, unknown>) {
  return getData<Question>(http.post('/admin/questions', data))
}

export function updateQuestion(id: string, data: Record<string, unknown>) {
  return getData<Question>(http.put(`/admin/questions/${id}`, data))
}

export function deleteQuestion(id: string) {
  return getData<null>(http.delete(`/admin/questions/${id}`))
}
