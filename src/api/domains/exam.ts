import * as d from '../_shared'

export const apiExam = {
  // ===== 真题/题库 =====

  listExamPapers(params?: {
    examType?: string
    subject?: string
    year?: number
  }): Promise<d.ApiRes<d.ExamPaper[]>> {
    if (d.isMock) return d.mockService.listExamPapers()
    const qs = new URLSearchParams()
    if (params?.examType) qs.set('exam_type', params.examType)
    if (params?.subject) qs.set('subject', params.subject)
    if (params?.year) qs.set('year', String(params.year))
    const q = qs.toString()
    return d.request(`/api/exam/papers${q ? `?${q}` : ''}`)
  },

  getExamPaperDetail(paperId: string): Promise<d.ApiRes<d.ExamPaperDetail>> {
    return d.isMock
      ? d.mockService.getExamPaperDetail(paperId)
      : d.request(`/api/exam/paper/${paperId}`)
  },

  startExam(paperId: string): Promise<d.ApiRes<d.ExamStartResult>> {
    return d.isMock
      ? d.mockService.startExam(paperId)
      : d.request(`/api/exam/start/${paperId}`, { method: 'POST' })
  },

  submitExamAnswer(
    attemptId: string,
    data: { questionId: string; answer: string | string[]; timeUsedSec?: number; marked?: boolean },
  ): Promise<d.ApiRes<{ ok: boolean }>> {
    return d.isMock
      ? d.mockService.submitExamAnswer(attemptId, data)
      : d.request(`/api/exam/answer?attempt_id=${attemptId}`, { method: 'POST', data })
  },

  submitExam(attemptId: string): Promise<d.ApiRes<d.ExamAttemptDetail>> {
    return d.isMock
      ? d.mockService.submitExam(attemptId)
      : d.request(`/api/exam/submit?attempt_id=${attemptId}`, { method: 'POST' })
  },

  listExamAttempts(paperId?: string): Promise<d.ApiRes<d.ExamAttempt[]>> {
    if (d.isMock) return d.mockService.listExamAttempts(paperId)
    const q = paperId ? `?paper_id=${paperId}` : ''
    return d.request(`/api/exam/attempts${q}`)
  },

  getExamAttemptDetail(attemptId: string): Promise<d.ApiRes<d.ExamAttemptDetail>> {
    return d.isMock
      ? d.mockService.getExamAttemptDetail(attemptId)
      : d.request(`/api/exam/attempt/${attemptId}`)
  },
}
