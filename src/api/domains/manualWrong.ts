import * as d from '../_shared'

export const apiManualWrong = {
  // ===== 手动错题 =====

  listManualWrongs(
    subject?: string,
    mastered?: boolean,
    status?: 'review' | 'waiting' | 'all',
  ): Promise<d.ApiRes<d.ManualWrong[]>> {
    const qs = new URLSearchParams()
    if (subject) qs.set('subject', subject)
    if (mastered !== undefined) qs.set('mastered', String(mastered))
    if (status) qs.set('status', status)
    const q = qs.toString()
    return d.isMock
      ? d.mockService.listManualWrongs()
      : d.request(`/api/manual-wrong${q ? `?${q}` : ''}`)
  },

  reviewManualWrong(
    id: string,
    result: 'good' | 'again' = 'good',
  ): Promise<d.ApiRes<d.ManualWrong>> {
    return d.isMock
      ? d.mockService.updateManualWrong(id, { reviewCount: 1 })
      : d.request(`/api/manual-wrong/${id}/review?result=${result}`, { method: 'POST' })
  },

  createManualWrong(data: {
    subject?: string
    questionType?: string
    stem?: string
    options?: string
    myAnswer?: string
    correctAnswer?: string
    analysis?: string
    wrongReason?: string
    note?: string
    source?: string
    images?: string[]
    knowledgeNodeId?: string | null
    knowledgeTreeKey?: string
    knowledgePath?: string
  }): Promise<d.ApiRes<d.ManualWrong>> {
    return d.isMock
      ? d.mockService.createManualWrong(data)
      : d.request('/api/manual-wrong', { method: 'POST', data })
  },

  updateManualWrong(
    id: string,
    data: {
      subject?: string
      questionType?: string
      stem?: string
      options?: string
      myAnswer?: string
      correctAnswer?: string
      analysis?: string
      wrongReason?: string
      note?: string
      mastered?: boolean
      reviewCount?: number
      images?: string[]
      knowledgeNodeId?: string | null
      knowledgeTreeKey?: string
      knowledgePath?: string
    },
  ): Promise<d.ApiRes<d.ManualWrong>> {
    return d.isMock
      ? d.mockService.updateManualWrong(id, data)
      : d.request(`/api/manual-wrong/${id}`, { method: 'PUT', data })
  },

  deleteManualWrong(id: string): Promise<d.ApiRes<{ ok: boolean }>> {
    return d.isMock
      ? d.mockService.deleteManualWrong(id)
      : d.request(`/api/manual-wrong/${id}`, { method: 'DELETE' })
  },

  uploadWrongImage(filePath: string, file?: File): Promise<d.ApiRes<{ url: string }>> {
    if (d.isMock) {
      return Promise.resolve({ code: 0, data: { url: filePath }, message: 'mock' })
    }
    return d.uploadFile<{ url: string }>(`${d.BASE_URL}/api/manual-wrong/upload`, filePath, {
      file,
    })
  },
}
