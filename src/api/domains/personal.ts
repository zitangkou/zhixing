import * as d from '../_shared'

export const apiPersonal = {
  // ===== 知行足迹 =====

  getGrowthOverview(): Promise<d.ApiRes<d.GrowthOverview>> {
    return d.isMock ? d.mockService.getGrowthOverview() : d.request('/api/growth/overview')
  },

  // ===== 语料本 =====

  getCorpusStats(): Promise<d.ApiRes<d.CorpusStats>> {
    return d.isMock ? d.mockService.getCorpusStats() : d.request('/api/corpus/stats')
  },

  listCorpusItems(status?: string): Promise<d.ApiRes<d.CorpusItem[]>> {
    if (d.isMock) return d.mockService.listCorpusItems(status)
    const q = status ? `?status=${encodeURIComponent(status)}` : ''
    return d.request(`/api/corpus/items${q}`)
  },

  getCorpusItem(id: string): Promise<d.ApiRes<d.CorpusItem>> {
    return d.isMock ? d.mockService.getCorpusItem(id) : d.request(`/api/corpus/items/${id}`)
  },

  createCorpusItem(data: {
    original: string
    kind?: string
    sourceType?: string
    sourceTitle?: string
    tags?: string[]
    plainNote?: string
    rewrite?: string
    practice?: string
    knowledgeNodeId?: string | null
    knowledgeTreeKey?: string
    knowledgePath?: string
  }): Promise<d.ApiRes<d.CorpusItem>> {
    return d.isMock
      ? d.mockService.createCorpusItem(data)
      : d.request('/api/corpus/items', { method: 'POST', data })
  },

  updateCorpusItem(
    id: string,
    data: Partial<{
      original: string
      kind: string
      sourceType: string
      sourceTitle: string
      tags: string[]
      plainNote: string
      rewrite: string
      practice: string
      markUsed: boolean
      knowledgeNodeId: string | null
      knowledgeTreeKey: string
      knowledgePath: string
    }>,
  ): Promise<d.ApiRes<d.CorpusItem>> {
    return d.isMock
      ? d.mockService.updateCorpusItem(id, data)
      : d.request(`/api/corpus/items/${id}`, { method: 'PUT', data })
  },

  deleteCorpusItem(id: string): Promise<d.ApiRes<{ ok: boolean }>> {
    return d.isMock
      ? d.mockService.deleteCorpusItem(id)
      : d.request(`/api/corpus/items/${id}`, { method: 'DELETE' })
  },

  promoteCorpusToTerm(id: string): Promise<d.ApiRes<d.CorpusItem>> {
    return d.isMock
      ? d.mockService.promoteCorpusToTerm(id)
      : d.request(`/api/corpus/items/${id}/promote-term`, { method: 'POST' })
  },

  // ===== 时事事件 =====

  getEventHub(): Promise<d.ApiRes<d.EventHub>> {
    return d.isMock ? d.mockService.getEventHub() : d.request('/api/events/hub')
  },

  listEvents(params?: {
    treeKey?: string
    path?: string
    unlinked?: boolean
  }): Promise<d.ApiRes<d.EventImpression[]>> {
    if (d.isMock) return d.mockService.listEvents(params)
    const qs = new URLSearchParams()
    if (params?.treeKey) qs.set('treeKey', params.treeKey)
    if (params?.path) qs.set('path', params.path)
    if (params?.unlinked) qs.set('unlinked', 'true')
    const q = qs.toString()
    return d.request(`/api/events${q ? `?${q}` : ''}`)
  },

  getEvent(id: string): Promise<d.ApiRes<d.EventImpression>> {
    return d.isMock ? d.mockService.getEvent(id) : d.request(`/api/events/${id}`)
  },

  createEvent(data: {
    title: string
    eventDate?: string
    place?: string
    coreContent?: string
    note?: string
    knowledgeNodeId?: string | null
    knowledgeTreeKey?: string
    knowledgePath?: string
  }): Promise<d.ApiRes<d.EventImpression>> {
    return d.isMock
      ? d.mockService.createEvent(data)
      : d.request('/api/events', { method: 'POST', data })
  },

  updateEvent(
    id: string,
    data: Partial<{
      title: string
      eventDate: string
      place: string
      coreContent: string
      note: string
      knowledgeNodeId: string | null
      knowledgeTreeKey: string
      knowledgePath: string
    }>,
  ): Promise<d.ApiRes<d.EventImpression>> {
    return d.isMock
      ? d.mockService.updateEvent(id, data)
      : d.request(`/api/events/${id}`, { method: 'PUT', data })
  },

  deleteEvent(id: string): Promise<d.ApiRes<{ ok: boolean }>> {
    return d.isMock
      ? d.mockService.deleteEvent(id)
      : d.request(`/api/events/${id}`, { method: 'DELETE' })
  },

  // ===== 数据导出/导入 =====

  exportCoreData(): Promise<d.ApiRes<d.DataExport>> {
    return d.isMock ? d.mockService.exportCoreData() : d.request('/api/data/export')
  },

  importCoreData(data: d.DataExport): Promise<d.ApiRes<d.DataImportResult>> {
    return d.isMock
      ? d.mockService.importCoreData(data)
      : d.request('/api/data/import', { method: 'POST', data })
  },
}
