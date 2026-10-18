import * as d from '../_shared'

export const apiZiliao = {
  // ===== 资料分析 =====

  listQuickCalcMethods() {
    return d.request<Array<{ id: string; code: string; name: string; category: string; scene: string; knowledgePath: string; nodeTitle: string; nodeParent: string; config: Record<string, number>; version: number }>>('/api/ziliao/quick-calc/methods')
  },

  getQuickCalcHistory(limit = 10) {
    return d.request<{ sessions: Array<{ id: string; mode: string; date: string; correct: number; total: number; seconds: number }>; recommendations: Array<{ code: string; name: string; accuracy: number; attempts: number }> }>(`/api/ziliao/quick-calc/history?limit=${limit}`)
  },

  retryQuickCalcWrong(sessionId: string, questionIds: string[]) {
    return d.request<{ id: string; mode: string; questions: Array<Omit<import('@/utils/quickCalc').QuickQuestion, 'answer' | 'check' | 'steps' | 'pitfall'> & { id: string }> }>(`/api/ziliao/quick-calc/sessions/${encodeURIComponent(sessionId)}/retry-wrong`, { method: 'POST', data: { questionIds } })
  },

  createQuickCalcSession(data: { mode: string; count: number }) {
    return d.request<{ id: string; mode: string; questions: Array<Omit<import('@/utils/quickCalc').QuickQuestion, 'answer' | 'check' | 'steps' | 'pitfall'> & { id: string }> }>('/api/ziliao/quick-calc/sessions', { method: 'POST', data })
  },

  answerQuickCalcQuestion(sessionId: string, data: { questionId: string; selected: number; seconds: number }) {
    return d.request<{ correct: boolean; correctOption: string; steps: import('@/utils/quickCalc').QuickStep[]; pitfall: string; optionFeedback: string[] }>(`/api/ziliao/quick-calc/sessions/${encodeURIComponent(sessionId)}/answers`, { method: 'POST', data })
  },

  completeQuickCalcSession(sessionId: string, data: { totalSeconds: number }) {
    return d.request<{ sessionId: string; total: number; correct: number; seconds: number; completed: boolean }>(`/api/ziliao/quick-calc/sessions/${encodeURIComponent(sessionId)}/complete`, { method: 'POST', data })
  },

  getZiliaoOverview(): Promise<d.ApiRes<d.ZiliaoOverview>> {
    return d.isMock ? d.mockService.getZiliaoOverview() : d.request('/api/ziliao/overview')
  },

  listZiliaoFormulas(): Promise<d.ApiRes<d.ZiliaoFormula[]>> {
    return d.isMock ? d.mockService.listZiliaoFormulas() : d.request('/api/ziliao/formulas')
  },

  getZiliaoFormula(id: string): Promise<d.ApiRes<d.ZiliaoFormula>> {
    return d.isMock ? d.mockService.getZiliaoFormula(id) : d.request(`/api/ziliao/formulas/${id}`)
  },

  listZiliaoTypes(): Promise<d.ApiRes<d.ZiliaoQuestionType[]>> {
    return d.isMock ? d.mockService.listZiliaoTypes() : d.request('/api/ziliao/types')
  },

  getZiliaoType(id: string): Promise<d.ApiRes<d.ZiliaoQuestionType>> {
    return d.isMock ? d.mockService.getZiliaoType(id) : d.request(`/api/ziliao/types/${id}`)
  },

  listZiliaoTricks(): Promise<d.ApiRes<d.ZiliaoTrick[]>> {
    return d.isMock ? d.mockService.listZiliaoTricks() : d.request('/api/ziliao/tricks')
  },

  getZiliaoTrick(id: string): Promise<d.ApiRes<d.ZiliaoTrick>> {
    return d.isMock ? d.mockService.getZiliaoTrick(id) : d.request(`/api/ziliao/tricks/${id}`)
  },

  listZiliaoDrillSets(
    typeCode?: string,
    includeSample?: boolean,
  ): Promise<d.ApiRes<d.ZiliaoDrillSet[]>> {
    if (d.isMock) return d.mockService.listZiliaoDrillSets(typeCode)
    const qs: string[] = []
    if (typeCode) qs.push(`typeCode=${encodeURIComponent(typeCode)}`)
    if (includeSample !== undefined) qs.push(`includeSample=${includeSample ? 'true' : 'false'}`)
    const q = qs.length ? `?${qs.join('&')}` : ''
    return d.request(`/api/ziliao/drill/sets${q}`)
  },

  getZiliaoDrillSet(setId: string): Promise<d.ApiRes<d.ZiliaoDrillSetDetail>> {
    return d.isMock
      ? d.mockService.getZiliaoDrillSet(setId)
      : d.request(`/api/ziliao/drill/set/${encodeURIComponent(setId)}`)
  },

  submitZiliaoDrill(data: {
    setId: string
    answers: { questionId: string; userAnswer: string | string[] }[]
    timeUsedSec?: number
    typeCode?: string
    saveWrongs?: boolean
  }): Promise<d.ApiRes<d.ZiliaoDrillSubmitResult>> {
    return d.isMock
      ? d.mockService.submitZiliaoDrill(data)
      : d.request('/api/ziliao/drill/submit', { method: 'POST', data })
  },

  getCountdown(): Promise<d.ApiRes<d.ExamCountdown | null>> {
    return d.isMock ? d.mockService.getCountdown() : d.request('/api/countdown')
  },

  saveCountdown(data: {
    examName: string
    examDate: string
    note?: string
  }): Promise<d.ApiRes<d.ExamCountdown>> {
    return d.isMock
      ? d.mockService.saveCountdown(data)
      : d.request('/api/countdown', { method: 'PUT', data })
  },

  deleteCountdown(): Promise<d.ApiRes<{ deleted: boolean }>> {
    return d.isMock
      ? d.mockService.deleteCountdown()
      : d.request('/api/countdown', { method: 'DELETE' })
  },
}
