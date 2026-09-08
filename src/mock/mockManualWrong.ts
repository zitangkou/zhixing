import * as m from './_core'

export const mockManualWrong = {
  // ===== 手动错题（mock） =====
  async listManualWrongs(): Promise<import('@/types').ApiRes<import('@/types').ManualWrong[]>> {
    await m.delay(200)
    return m.ok([...m.mockState.manualWrongs])
  },
  async createManualWrong(data: {
    subject?: string
    questionType?: string
    stem?: string
    options?: string
    myAnswer?: string
    correctAnswer?: string
    analysis?: string
    note?: string
    wrongReason?: string
    images?: string[]
    source?: string
    knowledgeNodeId?: string | null
    knowledgeTreeKey?: string
    knowledgePath?: string
  }): Promise<import('@/types').ApiRes<import('@/types').ManualWrong>> {
    await m.delay(200)
    const row: import('@/types').ManualWrong = {
      id: `mw-${Date.now()}`,
      subject: data.subject || '',
      questionType: data.questionType || '',
      stem: data.stem || '',
      options: data.options || '',
      myAnswer: data.myAnswer || '',
      correctAnswer: data.correctAnswer || '',
      analysis: data.analysis || '',
      wrongReason: data.wrongReason || '',
      note: data.note || '',
      images: data.images || [],
      source: (data.source as 'manual' | 'photo' | 'ocr') || 'manual',
      knowledgeNodeId: data.knowledgeNodeId || null,
      knowledgeTreeKey: data.knowledgeTreeKey || '',
      knowledgePath: data.knowledgePath || '',
      reviewCount: 0,
      mastered: false,
      lastWrongAt: new Date().toISOString(),
      createdAt: new Date().toISOString(),
    }
    m.mockState.manualWrongs.unshift(row)
    return m.ok(row)
  },
  async updateManualWrong(
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
  ): Promise<import('@/types').ApiRes<import('@/types').ManualWrong>> {
    await m.delay(100)
    const idx = m.mockState.manualWrongs.findIndex((w) => w.id === id)
    if (idx < 0) {
      return {
        code: 404,
        data: null as unknown as import('@/types').ManualWrong,
        message: '不存在',
      }
    }
    const cur = m.mockState.manualWrongs[idx]
    const next: import('@/types').ManualWrong = {
      ...cur,
      ...(data.subject !== undefined ? { subject: data.subject } : {}),
      ...(data.questionType !== undefined ? { questionType: data.questionType } : {}),
      ...(data.stem !== undefined ? { stem: data.stem } : {}),
      ...(data.options !== undefined ? { options: data.options } : {}),
      ...(data.myAnswer !== undefined ? { myAnswer: data.myAnswer } : {}),
      ...(data.correctAnswer !== undefined ? { correctAnswer: data.correctAnswer } : {}),
      ...(data.analysis !== undefined ? { analysis: data.analysis } : {}),
      ...(data.wrongReason !== undefined ? { wrongReason: data.wrongReason } : {}),
      ...(data.note !== undefined ? { note: data.note } : {}),
      ...(data.mastered !== undefined ? { mastered: data.mastered } : {}),
      ...(data.reviewCount !== undefined
        ? { reviewCount: (cur.reviewCount || 0) + (data.reviewCount || 0) }
        : {}),
      ...(data.images !== undefined ? { images: data.images } : {}),
      ...(data.knowledgeNodeId !== undefined ? { knowledgeNodeId: data.knowledgeNodeId } : {}),
      ...(data.knowledgeTreeKey !== undefined ? { knowledgeTreeKey: data.knowledgeTreeKey } : {}),
      ...(data.knowledgePath !== undefined ? { knowledgePath: data.knowledgePath } : {}),
      lastWrongAt: new Date().toISOString(),
    }
    m.mockState.manualWrongs[idx] = next
    return m.ok(next)
  },
  async deleteManualWrong(id: string): Promise<import('@/types').ApiRes<{ ok: boolean }>> {
    await m.delay(100)
    const idx = m.mockState.manualWrongs.findIndex((w) => w.id === id)
    if (idx >= 0) m.mockState.manualWrongs.splice(idx, 1)
    return m.ok({ ok: true })
  },
}
