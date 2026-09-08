import * as m from './_core'

export const mockPersonal = {
  async getGrowthOverview(): Promise<import('@/types').ApiRes<import('@/types').GrowthOverview>> {
    await m.delay(200)
    const today = new Date()
    const monday = new Date(today)
    monday.setDate(today.getDate() - ((today.getDay() + 6) % 7))
    const labels = ['一', '二', '三', '四', '五', '六', '日']
    const mins = [45, 60, 30, 90, 50, 20, 40]
    const weekBars = labels.map((label, i) => {
      const d = new Date(monday)
      d.setDate(monday.getDate() + i)
      const date = d.toISOString().slice(0, 10)
      return {
        date,
        label,
        minutes: mins[i],
        isToday: date === today.toISOString().slice(0, 10),
      }
    })
    return m.ok({
      signStreak: 5,
      signDays: 28,
      points: m.mockState.points,
      weekMinutes: mins.reduce((a, b) => a + b, 0),
      weekQuizTotal: 40,
      weekQuizCorrect: 32,
      articleReadCount: 12,
      examFinishedCount: 2,
      weekBars,
      domains: [
        { key: 'plan', name: '计划执行', percent: 70, detail: '本周 7/10 项' },
        { key: 'shenlun', name: '申论·人民日报', percent: 57, detail: '本周开采 4 天 · 词库 36' },
        { key: 'ziliao', name: '资料分析', percent: 50, detail: '今日 5/10 · 本周 3 套' },
        { key: 'wrong', name: '错题消化', percent: 40, detail: '行测掌握 4/10 · 文章错题 6' },
        { key: 'signin', name: '连续签到', percent: 83, detail: '连续 25 天' },
      ],
    })
  },

  // 音标 mock

  // ===== 语料本（内存） =====
  async getCorpusStats(): Promise<import('@/types').ApiRes<import('@/types').CorpusStats>> {
    await m.delay(40)
    const items = m.mockCorpusItems
    const counts = { inbox: 0, clarified: 0, owned: 0, used: 0 }
    items.forEach((i) => {
      const k = i.status in counts ? (i.status as keyof typeof counts) : 'inbox'
      counts[k] += 1
    })
    return m.ok({
      inboxCount: counts.inbox,
      clarifiedCount: counts.clarified,
      ownedCount: counts.owned,
      usedCount: counts.used,
      total: items.length,
      kinds: ['词', '专名', '成语', '诗典', '短语', '句', '结构'],
      sourceTypes: ['报纸', '视频', '播客', '书', '聊天', '其他'],
      tagPresets: ['民生', '治理', '收束', '过渡', '对比', '金句', '问题', '对策', '其他'],
    })
  },
  async listCorpusItems(
    status?: string,
  ): Promise<import('@/types').ApiRes<import('@/types').CorpusItem[]>> {
    await m.delay(40)
    let rows = [...m.mockCorpusItems]
    if (status && status !== 'all') rows = rows.filter((i) => i.status === status)
    return m.ok(rows)
  },
  async getCorpusItem(id: string): Promise<import('@/types').ApiRes<import('@/types').CorpusItem>> {
    await m.delay(30)
    const item = m.mockCorpusItems.find((i) => i.id === id)
    if (!item) return { code: 404, data: null as any, message: '不存在' }
    return m.ok(item)
  },
  async createCorpusItem(
    data: Record<string, unknown>,
  ): Promise<import('@/types').ApiRes<import('@/types').CorpusItem>> {
    await m.delay(50)
    const now = new Date().toISOString()
    const rewrite = String(data.rewrite || '')
    const practice = String(data.practice || '')
    const plainNote = String(data.plainNote || '')
    const tags = (data.tags as string[]) || []
    let status: import('@/types').CorpusStatus = 'inbox'
    if (practice.trim()) status = 'used'
    else if (rewrite.trim()) status = 'owned'
    else if (plainNote.trim() || tags.length) status = 'clarified'
    const item: import('@/types').CorpusItem = {
      id: `cps-${Date.now()}`,
      original: String(data.original || ''),
      kind: String(data.kind || '句'),
      sourceType: String(data.sourceType || '其他'),
      sourceTitle: String(data.sourceTitle || ''),
      tags,
      plainNote,
      rewrite,
      practice,
      status,
      usedCount: 0,
      promotedTermId: null,
      knowledgeNodeId: (data.knowledgeNodeId as string) || null,
      knowledgeTreeKey: String(data.knowledgeTreeKey || ''),
      knowledgePath: String(data.knowledgePath || ''),
      createdAt: now,
      updatedAt: now,
    }
    m.mockCorpusItems.unshift(item)
    return m.ok(item)
  },
  async updateCorpusItem(
    id: string,
    data: Record<string, unknown>,
  ): Promise<import('@/types').ApiRes<import('@/types').CorpusItem>> {
    await m.delay(50)
    const idx = m.mockCorpusItems.findIndex((i) => i.id === id)
    if (idx < 0) return { code: 404, data: null as any, message: '不存在' }
    const cur = {
      ...m.mockCorpusItems[idx],
      ...data,
      updatedAt: new Date().toISOString(),
    } as import('@/types').CorpusItem
    if (data.markUsed) cur.usedCount = (cur.usedCount || 0) + 1
    if (cur.usedCount > 0 || (cur.practice || '').trim()) cur.status = 'used'
    else if ((cur.rewrite || '').trim()) cur.status = 'owned'
    else if ((cur.plainNote || '').trim() || (cur.tags || []).length) cur.status = 'clarified'
    else cur.status = 'inbox'
    m.mockCorpusItems[idx] = cur
    return m.ok(cur)
  },
  async deleteCorpusItem(id: string): Promise<import('@/types').ApiRes<{ ok: boolean }>> {
    await m.delay(40)
    const idx = m.mockCorpusItems.findIndex((i) => i.id === id)
    if (idx >= 0) m.mockCorpusItems.splice(idx, 1)
    return m.ok({ ok: true })
  },
  async promoteCorpusToTerm(
    id: string,
  ): Promise<import('@/types').ApiRes<import('@/types').CorpusItem>> {
    return this.updateCorpusItem(id, { markUsed: true, promotedTermId: `snt-mock-${id}` })
  },

  async getEventHub(): Promise<import('@/types').ApiRes<import('@/types').EventHub>> {
    await m.delay(80)
    const list = (await this.listEvents()).data || []
    const linked = list.filter((e) => e.knowledgePath || e.knowledgeTreeKey)
    return m.ok({
      total: list.length,
      linkedCount: linked.length,
      unlinkedCount: list.length - linked.length,
      recentCount: list.length,
      frameworkGroups: linked.length
        ? [
            {
              treeKey: linked[0].knowledgeTreeKey,
              path: linked[0].knowledgePath,
              label: `${linked[0].knowledgeTreeKey} / ${linked[0].knowledgePath}`,
              count: linked.length,
              items: linked,
            },
          ]
        : [],
    })
  },

  _ensureMockEvents() {
    if (!m.mockState.events) {
      const now = new Date().toISOString()
      m.mockState.events = [
        {
          id: 'ei-demo-1',
          title: '神舟十号飞船发射成功',
          eventDate: '2013-06-11',
          place: '酒泉卫星发射中心',
          coreContent: '载人飞船发射成功，聂海胜、张晓光、王亚平执行任务；王亚平完成首次太空授课。',
          note: '可与神舟系列、载人航天工程对照记忆。',
          knowledgeNodeId: null,
          knowledgeTreeKey: '航天常识',
          knowledgePath: '神舟系列',
          createdAt: now,
          updatedAt: now,
        },
      ] as import('@/types').EventImpression[]
    }
    return m.mockState.events as import('@/types').EventImpression[]
  },

  async listEvents(params?: {
    treeKey?: string
    path?: string
    unlinked?: boolean
  }): Promise<import('@/types').ApiRes<import('@/types').EventImpression[]>> {
    await m.delay(80)
    let rows = [...this._ensureMockEvents()]
    if (params?.unlinked) {
      rows = rows.filter((e) => !e.knowledgePath && !e.knowledgeTreeKey)
    } else {
      if (params?.treeKey) rows = rows.filter((e) => e.knowledgeTreeKey === params.treeKey)
      if (params?.path) {
        const p = params.path
        rows = rows.filter((e) => e.knowledgePath === p || e.knowledgePath?.startsWith(`${p}/`))
      }
    }
    return m.ok(rows)
  },

  async getEvent(id: string): Promise<import('@/types').ApiRes<import('@/types').EventImpression>> {
    const hit = this._ensureMockEvents().find((e) => e.id === id)
    return hit
      ? m.ok(hit)
      : { code: 404, data: null as unknown as import('@/types').EventImpression, message: '不存在' }
  },

  async createEvent(data: {
    title: string
    eventDate?: string
    place?: string
    coreContent?: string
    note?: string
    knowledgeNodeId?: string | null
    knowledgeTreeKey?: string
    knowledgePath?: string
  }): Promise<import('@/types').ApiRes<import('@/types').EventImpression>> {
    const now = new Date().toISOString()
    const item: import('@/types').EventImpression = {
      id: `ei-${Date.now()}`,
      title: data.title,
      eventDate: data.eventDate || now.slice(0, 10),
      place: data.place || '',
      coreContent: data.coreContent || '',
      note: data.note || '',
      knowledgeNodeId: data.knowledgeNodeId || null,
      knowledgeTreeKey: data.knowledgeTreeKey || '',
      knowledgePath: data.knowledgePath || '',
      createdAt: now,
      updatedAt: now,
    }
    this._ensureMockEvents().unshift(item)
    return m.ok(item)
  },

  async updateEvent(id: string, data: Record<string, unknown>) {
    const list = this._ensureMockEvents()
    const idx = list.findIndex((e) => e.id === id)
    if (idx < 0) {
      return {
        code: 404,
        data: null as unknown as import('@/types').EventImpression,
        message: '不存在',
      }
    }
    list[idx] = {
      ...list[idx],
      ...data,
      updatedAt: new Date().toISOString(),
    } as import('@/types').EventImpression
    return m.ok(list[idx])
  },

  async deleteEvent(id: string): Promise<import('@/types').ApiRes<{ ok: boolean }>> {
    const list = this._ensureMockEvents()
    const idx = list.findIndex((e) => e.id === id)
    if (idx >= 0) list.splice(idx, 1)
    return m.ok({ ok: true })
  },

  getWrongQuestionsMap() {
    return m.mockState.wrongQuestions
  },

  getSignStatus() {
    return m.mockState.signStatus
  },

  getUserInfo(): import('@/types').UserInfo {
    return m.mockState.userInfo
  },

  getPointsState(): number {
    return m.mockState.points
  },

  // ===== 数据导出/导入 =====

  async exportCoreData(): Promise<import('@/types').ApiRes<import('@/types').DataExport>> {
    await m.delay(40)
    const now = new Date().toISOString()
    return m.ok({
      version: 1,
      exportedAt: now,
      wrongAnswers: [],
      manualWrongs: [],
      corpusItems: m.mockCorpusItems,
      planTasks: [],
      dailyReviews: [],
      pointsLogs: [
        {
          id: `pl-${Date.now()}`,
          amount: 10,
          log_type: 'income',
          source: 'sign',
          description: '签到',
          created_at: now,
        },
      ],
    })
  },

  async importCoreData(
    data: import('@/types').DataExport,
  ): Promise<import('@/types').ApiRes<import('@/types').DataImportResult>> {
    await m.delay(60)
    const count = (rows: Record<string, unknown>[] | undefined) => (rows || []).length
    return m.ok({
      wrongAnswers: count(data.wrongAnswers),
      manualWrongs: count(data.manualWrongs),
      corpusItems: count(data.corpusItems),
      planTasks: count(data.planTasks),
      dailyReviews: count(data.dailyReviews),
      pointsLogs: count(data.pointsLogs),
    })
  },
}
