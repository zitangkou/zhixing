import * as d from '../_shared'

export const apiLearning = {
  getDailyArticles(): Promise<d.ApiRes<d.Article[]>> {
    return d.isMock
      ? d.mockService.getDailyArticles()
      : d.request('/api/articles/daily', { auth: false })
  },

  getRecommendedArticles(offset = 0, limit = 5): Promise<d.ApiRes<d.ArticleListPage>> {
    return d.isMock
      ? d.mockService.getRecommendedArticles(offset, limit)
      : d.request(`/api/articles/recommended?offset=${offset}&limit=${limit}`, { auth: false })
  },

  getArticleDetail(id: string): Promise<d.ApiRes<d.Article | null>> {
    return d.isMock
      ? d.mockService.getArticleDetail(id)
      : d.request(`/api/articles/${id}`, { auth: false })
  },

  getQuestions(articleId: string): Promise<d.ApiRes<d.Question[]>> {
    return d.isMock
      ? d.mockService.getQuestions(articleId)
      : d.request(`/api/questions?articleId=${articleId}`)
  },

  getQuizByMode(mode: string, count = 10): Promise<d.ApiRes<d.Question[]>> {
    return d.isMock
      ? d.mockService.getQuizByMode(mode, count)
      : d.request(`/api/quiz?mode=${mode}&count=${count}`)
  },

  submitAnswer(questionId: string, answer: string | string[]): Promise<d.ApiRes<d.AnswerResult>> {
    return d.isMock
      ? d.mockService.submitAnswer(questionId, answer)
      : d.request('/api/answer', { method: 'POST', data: { questionId, answer } })
  },

  getWrongQuestions(
    status: 'review' | 'waiting' | 'all' = 'review',
  ): Promise<d.ApiRes<d.WrongQuestionRecord[]>> {
    return d.isMock ? d.mockService.getWrongQuestions() : d.request(`/api/wrong?status=${status}`)
  },

  redoWrongQuestion(
    questionId: string,
    answer: string | string[],
  ): Promise<d.ApiRes<d.AnswerResult>> {
    return d.isMock
      ? d.mockService.redoWrongQuestion(questionId, answer)
      : d.request('/api/wrong/redo', { method: 'POST', data: { questionId, answer } })
  },

  removeWrongQuestion(questionId: string): Promise<d.ApiRes<null>> {
    return d.isMock
      ? d.mockService.removeWrongQuestion(questionId)
      : d.request(`/api/wrong/${questionId}`, { method: 'DELETE' })
  },

  getStudyRecords(): Promise<d.ApiRes<d.StudyRecord[]>> {
    return d.isMock ? d.mockService.getStudyRecords() : d.request('/api/study/records')
  },

  getSectionReads(): Promise<d.ApiRes<Record<string, string[]>>> {
    return d.isMock ? d.mockService.getSectionReads() : d.request('/api/study/section-reads')
  },

  markSectionRead(articleId: string, sectionId: string): Promise<d.ApiRes<null>> {
    return d.isMock
      ? d.mockService.markSectionRead(articleId, sectionId)
      : d.request('/api/study/sections/read', {
          method: 'POST',
          data: { articleId, sectionId },
        })
  },

  getReviewTasks(_records?: d.StudyRecord[]): Promise<d.ApiRes<d.ReviewTask[]>> {
    return d.isMock ? d.mockService.getReviewTasks(_records || []) : d.request('/api/review')
  },

  getReviewHub(): Promise<d.ApiRes<d.ReviewHub>> {
    return d.isMock ? d.mockService.getReviewHub() : d.request('/api/review/hub')
  },

  signIn(): Promise<d.ApiRes<{ points: number; streak: number }>> {
    return d.isMock ? d.mockService.signIn() : d.request('/api/signin', { method: 'POST' })
  },

  getPointsLog(): Promise<d.ApiRes<d.PointsLog[]>> {
    return d.isMock ? d.mockService.getPointsLog() : d.request('/api/points/log')
  },

  getPoints(): Promise<d.ApiRes<number>> {
    return d.isMock ? d.mockService.getPoints() : d.request('/api/points')
  },

  getRankList(type: d.RankType): Promise<d.ApiRes<d.RankItem[]>> {
    return d.isMock ? d.mockService.getRankList(type) : d.request(`/api/rank?type=${type}`)
  },

  completeQuiz(data: {
    articleId?: string
    mode: string
    total: number
    correct: number
  }): Promise<d.ApiRes<d.QuizCompleteResult>> {
    return d.isMock
      ? d.mockService.completeQuiz(data)
      : d.request('/api/quiz/complete', { method: 'POST', data })
  },

  getQuizRank(articleId?: string, mode = 'article'): Promise<d.ApiRes<d.QuizRankItem[]>> {
    const qs = new URLSearchParams({ mode })
    if (articleId) qs.set('articleId', articleId)
    return d.isMock
      ? d.mockService.getQuizRank(articleId, mode)
      : d.request(`/api/quiz/rank?${qs.toString()}`)
  },

  markArticleRead(articleId: string): Promise<d.ApiRes<{ points: number }>> {
    return d.isMock
      ? d.mockService.markArticleRead(articleId)
      : d.request(`/api/articles/${articleId}/read`, { method: 'POST' })
  },

  completeReview(articleId: string): Promise<d.ApiRes<void>> {
    return d.isMock
      ? d.mockService.completeReview(articleId)
      : d.request('/api/review/complete', { method: 'POST', data: { articleId } })
  },

  submitFeedback(content: string): Promise<d.ApiRes<{ adopted: boolean }>> {
    return d.isMock
      ? d.mockService.submitFeedback(content)
      : d.request('/api/feedback', { method: 'POST', data: { content } })
  },
}
