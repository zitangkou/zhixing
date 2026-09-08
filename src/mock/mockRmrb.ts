import * as m from './_core'

export const mockRmrb = {
  // ===== 人民日报 mock =====
  async getRmrbMeta(): Promise<import('@/types').ApiRes<import('@/types').ShenlunMeta>> {
    await m.delay(100)
    return m.ok({
      termCategories: [
        { id: 'c1', name: '问题与积弊', kind: 'term', sortOrder: 5, isEnabled: true },
        { id: 'c2', name: '治理方法与理念', kind: 'term', sortOrder: 8, isEnabled: true },
        { id: 'c3', name: '成效与目标', kind: 'term', sortOrder: 12, isEnabled: true },
        { id: 'c4', name: '其他', kind: 'term', sortOrder: 99, isEnabled: true },
      ],
      verbCategories: [
        { id: 'v1', name: '治理动作', kind: 'verb', sortOrder: 10, isEnabled: true },
        { id: 'v2', name: '分析评价', kind: 'verb', sortOrder: 20, isEnabled: true },
        { id: 'v3', name: '动词其他', kind: 'verb', sortOrder: 99, isEnabled: true },
      ],
      skeletonTemplates: [
        {
          id: 'sk1',
          name: '总分论点型',
          description: '总论点 → 分论点 → 总结',
          mode: 'points',
          structure: {
            mode: 'points',
            fields: [],
            overviewLabel: '总论点',
            pointFields: [{ key: 'title', label: '分论点', placeholder: '' }],
          },
          sortOrder: 0,
          isEnabled: true,
        },
      ],
      sentenceTypes: [
        {
          id: 'st1',
          code: 'dialectic',
          name: '对比转折型',
          tip: '',
          sortOrder: 0,
          isEnabled: true,
        },
        { id: 'st2', code: 'quote', name: '金句型', tip: '', sortOrder: 1, isEnabled: true },
      ],
      argumentMethodPresets: [
        {
          name: '点例排比 + 类比延伸',
          scope: 'point',
          note: '点例各一句话；3个排比',
          template: '提出分论点 → 列举3个案例 → 提炼共性 → 类比延伸 → 总结',
        },
        {
          name: '总—分—分—总',
          scope: 'overview',
          note: '全文结构',
          template: '现象引题 → 总论点 → 分论点 → 总结升华',
        },
      ],
    })
  },
  async createRmrbSkeletonTemplate(data: {
    name: string
    description?: string
    mode?: string
    structure?: import('@/types').ShenlunSkeletonStructure
    sortOrder?: number
    isEnabled?: boolean
  }): Promise<import('@/types').ApiRes<import('@/types').ShenlunSkeletonTemplate>> {
    await m.delay(100)
    return m.ok({
      id: `sk-${Date.now()}`,
      name: data.name,
      description: data.description || '',
      mode: data.mode || 'default',
      structure: data.structure || { mode: 'default', fields: [], pointFields: [] },
      sortOrder: data.sortOrder ?? 0,
      isEnabled: data.isEnabled !== false,
    })
  },
  async createRmrbTermCategory(data: {
    name: string
    kind?: string
    sortOrder?: number
    isEnabled?: boolean
  }): Promise<import('@/types').ApiRes<import('@/types').ShenlunTermCategory>> {
    await m.delay(100)
    return m.ok({
      id: `cat-${Date.now()}`,
      name: data.name,
      kind: data.kind || 'term',
      sortOrder: data.sortOrder ?? 0,
      isEnabled: data.isEnabled !== false,
    })
  },
  async getRmrbStats(): Promise<import('@/types').ApiRes<import('@/types').ShenlunStats>> {
    await m.delay(100)
    return m.ok({
      weekMineDays: 3,
      weekMineTarget: 7,
      termCount: m.mockRmrb.terms.length,
      learningTermCount: m.mockRmrb.terms.filter((t) => !t.mastered).length,
      todayMined: m.mockRmrb.mines.some(
        (m) => m.mineDate === new Date().toISOString().slice(0, 10),
      ),
      weekDrillCount: m.mockRmrb.drills.length,
    })
  },
  async listRmrbArticles(
    tag?: string,
  ): Promise<import('@/types').ApiRes<import('@/types').RmrbArticle[]>> {
    await m.delay(100)
    const all: import('@/types').RmrbArticle[] = [
      {
        id: 'rmrb1',
        title: '示例时评：以实干开新局',
        source: '人民日报',
        publishDate: '2026-07-01',
        summary: 'Mock 文章摘要',
        content: '这是一篇用于本地 Mock 的人民日报示例正文。',
        tags: ['政绩观', '高质量发展'],
        isPublished: true,
        sortOrder: 0,
        readCount: 0,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ]
    return m.ok(tag ? all.filter((a) => (a.tags || []).includes(tag)) : all)
  },
  async getRmrbArticle(
    id: string,
  ): Promise<import('@/types').ApiRes<import('@/types').RmrbArticle>> {
    await m.delay(100)
    const list = await this.listRmrbArticles()
    const hit = list.data?.find((a) => a.id === id) || list.data?.[0]
    return hit
      ? m.ok(hit)
      : { code: 404, data: null as unknown as import('@/types').RmrbArticle, message: 'not found' }
  },
  async listRmrbMines(): Promise<import('@/types').ApiRes<import('@/types').ShenlunMineLog[]>> {
    await m.delay(100)
    return m.ok([...m.mockRmrb.mines])
  },
  async getRmrbMine(
    id: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ShenlunMineLog>> {
    await m.delay(100)
    const hit = m.mockRmrb.mines.find((m) => m.id === id)
    return hit
      ? m.ok(hit)
      : {
          code: 404,
          data: null as unknown as import('@/types').ShenlunMineLog,
          message: 'not found',
        }
  },
  async getRmrbMineByDate(
    date: string,
  ): Promise<import('@/types').ApiRes<import('@/types').ShenlunMineLog>> {
    await m.delay(100)
    const hit = m.mockRmrb.mines.find((m) => m.mineDate === date)
    return hit
      ? m.ok(hit)
      : {
          code: 404,
          data: null as unknown as import('@/types').ShenlunMineLog,
          message: 'not found',
        }
  },
  async upsertRmrbMine(
    data: Record<string, unknown>,
  ): Promise<import('@/types').ApiRes<import('@/types').ShenlunMineLog>> {
    await m.delay(100)
    const now = new Date().toISOString()
    const mineDate = String(data.mineDate || now.slice(0, 10))
    let row = m.mockRmrb.mines.find((m) => m.mineDate === mineDate)
    if (!row) {
      row = {
        id: `mine-${Date.now()}`,
        mineDate,
        articleId: (data.articleId as string) || null,
        articleTitle: String(data.articleTitle || ''),
        sourceExcerpt: String(data.sourceExcerpt || ''),
        argumentChain: String(data.argumentChain || ''),
        templateSentence: String(data.templateSentence || ''),
        terms: (data.terms as import('@/types').ShenlunMineTermItem[]) || [],
        quotes: (data.quotes as import('@/types').ShenlunQuoteItem[]) || [],
        verbs: (data.verbs as import('@/types').ShenlunVerbItem[]) || [],
        argument: (data.argument as import('@/types').ShenlunArgumentSkeleton) || {
          templateId: '',
          templateName: '',
          mode: 'default',
          overview: '',
          conclusion: '',
          fields: [],
          points: [],
        },
        templates: (data.templates as import('@/types').ShenlunTemplateItem[]) || [],
        createdAt: now,
        updatedAt: now,
      }
      m.mockRmrb.mines.unshift(row)
    } else {
      Object.assign(row, data, { updatedAt: now })
    }
    return m.ok(row)
  },
  async updateRmrbMine(
    id: string,
    data: Record<string, unknown>,
  ): Promise<import('@/types').ApiRes<import('@/types').ShenlunMineLog>> {
    await m.delay(100)
    const row = m.mockRmrb.mines.find((m) => m.id === id)
    if (!row)
      return {
        code: 404,
        data: null as unknown as import('@/types').ShenlunMineLog,
        message: 'not found',
      }
    Object.assign(row, data, { updatedAt: new Date().toISOString() })
    return m.ok(row)
  },
  async deleteRmrbMine(id: string): Promise<import('@/types').ApiRes<{ ok: boolean }>> {
    await m.delay(100)
    m.mockRmrb.mines = m.mockRmrb.mines.filter((m) => m.id !== id)
    return m.ok({ ok: true })
  },
  async listRmrbTerms(): Promise<import('@/types').ApiRes<import('@/types').ShenlunNormTerm[]>> {
    await m.delay(100)
    return m.ok([...m.mockRmrb.terms])
  },
  async addRmrbTerm(data: {
    term: string
    category?: string
    usageNote?: string
    sourceTitle?: string
    exampleSentence?: string
    articleId?: string | null
  }): Promise<import('@/types').ApiRes<import('@/types').ShenlunNormTerm>> {
    await m.delay(100)
    const row: import('@/types').ShenlunNormTerm = {
      id: `term-${Date.now()}`,
      term: data.term,
      category: data.category || 'norm',
      usageNote: data.usageNote || '',
      sourceTitle: data.sourceTitle || '',
      exampleSentence: data.exampleSentence || '',
      articleId: data.articleId ?? null,
      familiarity: 1,
      mastered: false,
      createdAt: new Date().toISOString(),
    }
    m.mockRmrb.terms.unshift(row)
    return m.ok(row)
  },
  async updateRmrbTerm(
    id: string,
    data: Record<string, unknown>,
  ): Promise<import('@/types').ApiRes<import('@/types').ShenlunNormTerm>> {
    await m.delay(100)
    const row = m.mockRmrb.terms.find((t) => t.id === id)
    if (!row)
      return {
        code: 404,
        data: null as unknown as import('@/types').ShenlunNormTerm,
        message: 'not found',
      }
    Object.assign(row, data)
    return m.ok(row)
  },
  async deleteRmrbTerm(id: string): Promise<import('@/types').ApiRes<{ ok: boolean }>> {
    await m.delay(100)
    m.mockRmrb.terms = m.mockRmrb.terms.filter((t) => t.id !== id)
    return m.ok({ ok: true })
  },
  async listRmrbDrills(): Promise<import('@/types').ApiRes<import('@/types').ShenlunDrillLog[]>> {
    await m.delay(100)
    return m.ok([...m.mockRmrb.drills])
  },
  async addRmrbDrill(data: {
    drillType: 'sentence' | 'imitate' | 'oral'
    content: string
    prompt?: string
    refMineId?: string | null
    refTermIds?: string[]
  }): Promise<import('@/types').ApiRes<import('@/types').ShenlunDrillLog>> {
    await m.delay(100)
    const row: import('@/types').ShenlunDrillLog = {
      id: `drill-${Date.now()}`,
      drillType: data.drillType,
      content: data.content,
      prompt: data.prompt || '',
      refMineId: data.refMineId ?? null,
      refTermIds: data.refTermIds || [],
      createdAt: new Date().toISOString(),
    }
    m.mockRmrb.drills.unshift(row)
    return m.ok(row)
  },
}
