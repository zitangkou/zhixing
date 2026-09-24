import * as d from '../_shared'
import type { AnswerResult, Question, XingceCatalog } from '@/types'

export const apiXingce = {
  getXingceCatalog(params?: { year?: number; paperType?: string }): Promise<d.ApiRes<XingceCatalog>> {
    if (d.isMock) {
      return Promise.resolve({
        code: 0,
        message: 'ok',
        data: { modules: [], years: [], paperTypes: [], papers: [] },
      })
    }
    const qs = new URLSearchParams()
    if (params?.year) qs.set('year', String(params.year))
    if (params?.paperType) qs.set('paperType', params.paperType)
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    return d.request(`/api/xingce/catalog${suffix}`, { auth: false })
  },

  getXingceQuiz(params: {
    module: string
    year?: number
    paperType?: string
    count?: number
  }): Promise<d.ApiRes<Question[]>> {
    if (d.isMock) {
      return Promise.resolve({ code: 0, message: 'ok', data: [] })
    }
    const qs = new URLSearchParams()
    qs.set('module', params.module)
    if (params.year) qs.set('year', String(params.year))
    if (params.paperType) qs.set('paperType', params.paperType)
    qs.set('count', String(params.count || 10))
    return d.request(`/api/xingce/quiz?${qs.toString()}`, { auth: false })
  },

  submitXingceAnswer(
    questionId: string,
    answer: string | string[],
  ): Promise<d.ApiRes<AnswerResult>> {
    if (d.isMock) {
      return Promise.resolve({
        code: 1,
        message: '演示模式无真题库',
        data: { correct: false, analysis: '', correctAnswer: '', pointsEarned: 0 },
      })
    }
    return d.request('/api/xingce/answer', {
      method: 'POST',
      data: { questionId, answer },
      auth: false,
    })
  },
}
