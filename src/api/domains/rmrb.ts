import * as d from '../_shared'

export interface ShenlunExerciseCard {
  id: string; question_type: 'summary' | 'countermeasure' | 'implementation' | 'essay'; title: string
  source_title: string; source_url: string; source_date: string; source_excerpt: string; prompt: string
  requirements: string; max_chars: number; hint: string; difficulty: string; estimated_minutes: number
  is_featured: boolean; key_points: {point:string;evidence:string}[]; rubric: {name:string;description:string}[]
  sample_answer: string; analysis: string; related_assets: {type:string;id:string;title:string}[]
  attempt: {id:string;answer:string;revision:string;reflection:string} | null
}

export const apiRmrb = {
  // ===== 人民日报 / 申论 =====

  listShenlunExercises(questionType?: string): Promise<d.ApiRes<ShenlunExerciseCard[]>> {
    if (d.isMock) return Promise.resolve({ code: 0, data: [] } as d.ApiRes<ShenlunExerciseCard[]>)
    const query = questionType ? `?question_type=${encodeURIComponent(questionType)}` : ''
    return d.request(`/api/rmrb/exercises${query}`)
  },

  getShenlunExercise(id: string): Promise<d.ApiRes<ShenlunExerciseCard>> {
    return d.isMock
      ? Promise.resolve({ code: 404, data: null as unknown as ShenlunExerciseCard, message: '暂无可用练习' })
      : d.request(`/api/rmrb/exercises/${id}`)
  },

  submitShenlunExercise(id: string, answer: string): Promise<d.ApiRes<ShenlunExerciseCard>> {
    return d.isMock
      ? Promise.resolve({ code: 404, data: null as unknown as ShenlunExerciseCard, message: '暂无可用练习' })
      : d.request(`/api/rmrb/exercises/${id}/answers`, { method: 'POST', data: { answer } })
  },

  reviseShenlunExercise(id: string, attemptId: string, revision: string, reflection = ''): Promise<d.ApiRes<ShenlunExerciseCard>> {
    return d.isMock
      ? Promise.resolve({ code: 404, data: null as unknown as ShenlunExerciseCard, message: '暂无可用练习' })
      : d.request(`/api/rmrb/exercises/${id}/answers/${attemptId}`, { method: 'PUT', data: { revision, reflection } })
  },

  getRmrbMeta(): Promise<d.ApiRes<d.ShenlunMeta>> {
    return d.isMock ? d.mockService.getRmrbMeta() : d.request('/api/rmrb/meta')
  },

  createRmrbSkeletonTemplate(data: {
    name: string
    description?: string
    mode?: string
    structure?: d.ShenlunSkeletonStructure
    sortOrder?: number
    isEnabled?: boolean
  }): Promise<d.ApiRes<d.ShenlunSkeletonTemplate>> {
    return d.isMock
      ? d.mockService.createRmrbSkeletonTemplate(data)
      : d.request('/api/rmrb/skeleton-templates', { method: 'POST', data })
  },

  createRmrbTermCategory(data: {
    name: string
    kind?: 'term' | 'verb' | string
    sortOrder?: number
    isEnabled?: boolean
  }): Promise<d.ApiRes<d.ShenlunTermCategory>> {
    return d.isMock
      ? d.mockService.createRmrbTermCategory(data)
      : d.request('/api/rmrb/term-categories', { method: 'POST', data })
  },

  getRmrbStats(): Promise<d.ApiRes<d.ShenlunStats>> {
    return d.isMock ? d.mockService.getRmrbStats() : d.request('/api/rmrb/stats')
  },

  listRmrbArticles(tag?: string): Promise<d.ApiRes<d.RmrbArticle[]>> {
    if (d.isMock) return d.mockService.listRmrbArticles(tag)
    const q = tag ? `?tag=${encodeURIComponent(tag)}` : ''
    return d.request(`/api/rmrb/articles${q}`, { auth: false })
  },

  listRmrbToday(): Promise<d.ApiRes<d.RmrbArticle[]>> {
    if (d.isMock) return d.mockService.listRmrbToday()
    return d.request('/api/rmrb/articles/today', { auth: false })
  },

  getRmrbArticle(id: string): Promise<d.ApiRes<d.RmrbArticle>> {
    return d.isMock
      ? d.mockService.getRmrbArticle(id)
      : d.request(`/api/rmrb/articles/${id}`, { auth: false })
  },

  listRmrbMines(): Promise<d.ApiRes<d.ShenlunMineLog[]>> {
    return d.isMock ? d.mockService.listRmrbMines() : d.request('/api/rmrb/mines')
  },

  getRmrbMine(id: string): Promise<d.ApiRes<d.ShenlunMineLog>> {
    return d.isMock ? d.mockService.getRmrbMine(id) : d.request(`/api/rmrb/mines/${id}`)
  },

  getRmrbMineByDate(date: string): Promise<d.ApiRes<d.ShenlunMineLog>> {
    return d.isMock
      ? d.mockService.getRmrbMineByDate(date)
      : d.request(`/api/rmrb/mines/by-date/${date}`)
  },

  upsertRmrbMine(data: {
    mineDate?: string
    articleId?: string | null
    articleTitle?: string
    sourceExcerpt?: string
    argumentChain?: string
    templateSentence?: string
    terms?: Array<d.ShenlunMineTermItem | string>
    quotes?: d.ShenlunQuoteItem[]
    verbs?: d.ShenlunVerbItem[]
    argument?: d.ShenlunArgumentSkeleton
    templates?: d.ShenlunTemplateItem[]
  }): Promise<d.ApiRes<d.ShenlunMineLog>> {
    return d.isMock
      ? d.mockService.upsertRmrbMine(data)
      : d.request('/api/rmrb/mines', { method: 'POST', data })
  },

  updateRmrbMine(
    id: string,
    data: Partial<{
      articleId: string | null
      articleTitle: string
      sourceExcerpt: string
      argumentChain: string
      templateSentence: string
      terms: Array<d.ShenlunMineTermItem | string>
      quotes: d.ShenlunQuoteItem[]
      verbs: d.ShenlunVerbItem[]
      argument: d.ShenlunArgumentSkeleton
      templates: d.ShenlunTemplateItem[]
    }>,
  ): Promise<d.ApiRes<d.ShenlunMineLog>> {
    return d.isMock
      ? d.mockService.updateRmrbMine(id, data)
      : d.request(`/api/rmrb/mines/${id}`, { method: 'PUT', data })
  },

  deleteRmrbMine(id: string): Promise<d.ApiRes<{ ok: boolean }>> {
    return d.isMock
      ? d.mockService.deleteRmrbMine(id)
      : d.request(`/api/rmrb/mines/${id}`, { method: 'DELETE' })
  },

  listRmrbTerms(
    status?: 'learning' | 'mastered',
    category?: string,
  ): Promise<d.ApiRes<d.ShenlunNormTerm[]>> {
    if (d.isMock) return d.mockService.listRmrbTerms()
    const qs = new URLSearchParams()
    if (status) qs.set('status', status)
    if (category) qs.set('category', category)
    const q = qs.toString() ? `?${qs}` : ''
    return d.request(`/api/rmrb/terms${q}`)
  },

  addRmrbTerm(data: {
    term: string
    category?: string
    usageNote?: string
    sourceTitle?: string
    exampleSentence?: string
    articleId?: string | null
  }): Promise<d.ApiRes<d.ShenlunNormTerm>> {
    return d.isMock
      ? d.mockService.addRmrbTerm(data)
      : d.request('/api/rmrb/terms', { method: 'POST', data })
  },

  updateRmrbTerm(
    id: string,
    data: Partial<{
      category: string
      usageNote: string
      exampleSentence: string
      familiarity: number
      mastered: boolean
      sourceTitle: string
    }>,
  ): Promise<d.ApiRes<d.ShenlunNormTerm>> {
    return d.isMock
      ? d.mockService.updateRmrbTerm(id, data)
      : d.request(`/api/rmrb/terms/${id}`, { method: 'PUT', data })
  },

  deleteRmrbTerm(id: string): Promise<d.ApiRes<{ ok: boolean }>> {
    return d.isMock
      ? d.mockService.deleteRmrbTerm(id)
      : d.request(`/api/rmrb/terms/${id}`, { method: 'DELETE' })
  },

  listRmrbDrills(
    drillType?: 'sentence' | 'imitate' | 'oral',
  ): Promise<d.ApiRes<d.ShenlunDrillLog[]>> {
    if (d.isMock) return d.mockService.listRmrbDrills()
    const q = drillType ? `?drill_type=${drillType}` : ''
    return d.request(`/api/rmrb/drills${q}`)
  },

  addRmrbDrill(data: {
    drillType: 'sentence' | 'imitate' | 'oral'
    content: string
    prompt?: string
    refMineId?: string | null
    refTermIds?: string[]
  }): Promise<d.ApiRes<d.ShenlunDrillLog>> {
    return d.isMock
      ? d.mockService.addRmrbDrill(data)
      : d.request('/api/rmrb/drills', { method: 'POST', data })
  },
}
