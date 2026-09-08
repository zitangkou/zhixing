import * as m from './_core'

export const mockZiliao = {
  // ===== 资料分析 Mock =====

  async getZiliaoOverview(): Promise<import('@/types').ApiRes<import('@/types').ZiliaoOverview>> {
    await m.delay(100)
    return {
      code: 0,
      message: 'ok',
      data: {
        formulaCount: m.mockZiliao.formulas.length,
        typeCount: m.mockZiliao.types.length,
        trickCount: m.mockZiliao.tricks.length,
        drillSetCount: 1,
        todaySets: m.mockZiliao.todaySets,
        todayCorrect: m.mockZiliao.todayCorrect,
        todayTotal: m.mockZiliao.todayTotal,
        weekSets: m.mockZiliao.todaySets,
        hasRealDrill: false,
        usingSampleOnly: true,
        weakTypes: [
          {
            id: m.mockZiliao.types[0].id,
            code: m.mockZiliao.types[0].code,
            name: m.mockZiliao.types[0].name,
            category: m.mockZiliao.types[0].category,
            attemptCount: 0,
            correctCount: 0,
            totalCount: 0,
            accuracy: null,
            reason: '尚未专项练习',
          },
        ],
      },
    }
  },

  async listZiliaoFormulas(): Promise<import('@/types').ApiRes<import('@/types').ZiliaoFormula[]>> {
    await m.delay(100)
    return { code: 0, message: 'ok', data: m.mockZiliao.formulas }
  },

  async getZiliaoFormula(
    id: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ZiliaoFormula>> {
    await m.delay(80)
    const item = m.mockZiliao.formulas.find((f) => f.id === id)
    return item
      ? { code: 0, message: 'ok', data: item }
      : { code: 404, message: '不存在', data: null as any }
  },

  async listZiliaoTypes(): Promise<
    import('@/types').ApiRes<import('@/types').ZiliaoQuestionType[]>
  > {
    await m.delay(100)
    return { code: 0, message: 'ok', data: m.mockZiliao.types }
  },

  async getZiliaoType(
    id: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ZiliaoQuestionType>> {
    await m.delay(80)
    const item = m.mockZiliao.types.find((t) => t.id === id)
    return item
      ? { code: 0, message: 'ok', data: item }
      : { code: 404, message: '不存在', data: null as any }
  },

  async listZiliaoTricks(): Promise<import('@/types').ApiRes<import('@/types').ZiliaoTrick[]>> {
    await m.delay(100)
    return { code: 0, message: 'ok', data: m.mockZiliao.tricks }
  },

  async getZiliaoTrick(
    id: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ZiliaoTrick>> {
    await m.delay(80)
    const item = m.mockZiliao.tricks.find((t) => t.id === id)
    return item
      ? { code: 0, message: 'ok', data: item }
      : { code: 404, message: '不存在', data: null as any }
  },

  async listZiliaoDrillSets(
    _typeCode?: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ZiliaoDrillSet[]>> {
    await m.delay(100)
    return {
      code: 0,
      message: 'ok',
      data: [
        {
          setId: m.mockZiliao.drill.setId,
          paperId: m.mockZiliao.drill.paperId,
          paperTitle: m.mockZiliao.drill.paperTitle,
          materialPreview: m.mockZiliao.drill.material.slice(0, 80),
          questionCount: m.mockZiliao.drill.questions.length,
          section: '资料分析',
          typeHints: ['增长量', '比重'],
          isSample: true,
        },
      ],
    }
  },

  async getZiliaoDrillSet(
    setId: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ZiliaoDrillSetDetail>> {
    await m.delay(100)
    if (setId !== m.mockZiliao.drill.setId) {
      return { code: 404, message: '不存在', data: null as any }
    }
    return { code: 0, message: 'ok', data: m.mockZiliao.drill }
  },

  async submitZiliaoDrill(data: {
    setId: string
    answers: { questionId: string; userAnswer: string | string[] }[]
    timeUsedSec?: number
    typeCode?: string
    saveWrongs?: boolean
  }): Promise<import('@/types').ApiRes<import('@/types').ZiliaoDrillSubmitResult>> {
    await m.delay(150)
    const ansMap = Object.fromEntries(data.answers.map((a) => [a.questionId, a.userAnswer]))
    const wrongs: import('@/types').ZiliaoDrillSubmitResult['wrongs'] = []
    let correct = 0
    for (const q of m.mockZiliao.drill.questions) {
      const u = String(ansMap[q.id] || '').toUpperCase()
      const c = m.mockZiliao.correctMap[q.id]
      if (u === c) correct += 1
      else {
        wrongs.push({
          questionId: q.id,
          stem: q.stem,
          material: m.mockZiliao.drill.material,
          options: q.options,
          userAnswer: u,
          correctAnswer: c,
          analysis: m.mockZiliao.analysisMap[q.id] || '',
        })
      }
    }
    m.mockZiliao.todaySets += 1
    m.mockZiliao.todayCorrect += correct
    m.mockZiliao.todayTotal += m.mockZiliao.drill.questions.length
    return {
      code: 0,
      message: 'ok',
      data: {
        setId: data.setId,
        totalCount: m.mockZiliao.drill.questions.length,
        correctCount: correct,
        timeUsedSec: data.timeUsedSec || 0,
        wrongs,
        savedWrongCount: data.saveWrongs === false ? 0 : wrongs.length,
      },
    }
  },

  async getCountdown(): Promise<import('@/types').ApiRes<import('@/types').ExamCountdown | null>> {
    await m.delay(100)
    return m.ok(m.mockState.countdown)
  },

  async saveCountdown(data: {
    examName: string
    examDate: string
    note?: string
  }): Promise<import('@/types').ApiRes<import('@/types').ExamCountdown>> {
    await m.delay(100)
    const daysLeft = Math.max(
      0,
      Math.ceil((new Date(data.examDate).getTime() - Date.now()) / 86400000),
    )
    m.mockState.countdown = {
      id: 'ecd_mock',
      examName: data.examName,
      examDate: data.examDate,
      note: data.note || '',
      daysLeft,
      updatedAt: new Date().toISOString(),
    }
    return m.ok(m.mockState.countdown)
  },

  async deleteCountdown(): Promise<import('@/types').ApiRes<{ deleted: boolean }>> {
    await m.delay(100)
    m.mockState.countdown = null
    return m.ok({ deleted: true })
  },
}
