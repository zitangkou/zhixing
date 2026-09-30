import * as d from '../_shared'

export const apiKnowledge = {
  // ===== 知识框架 =====

  getKnowledgeMaps(): Promise<d.ApiRes<d.KnowledgeMapListItem[]>> {
    return d.isMock ? d.mockService.getKnowledgeMaps() : d.request('/api/knowledge/maps', { auth: false })
  },

  getKnowledgeMap(treeKey: string): Promise<d.ApiRes<d.KnowledgeMapDetail>> {
    return d.isMock
      ? d.mockService.getKnowledgeMap(treeKey)
      : d.request(`/api/knowledge/maps/${encodeURIComponent(treeKey)}`, { auth: false })
  },

  getKnowledgeTrees(): Promise<d.ApiRes<d.KnowledgeTree[]>> {
    return d.isMock ? d.mockService.getKnowledgeTrees() : d.request('/api/knowledge/trees')
  },

  getKnowledgeTree(treeKey: string): Promise<d.ApiRes<d.KnowledgeTree>> {
    return d.isMock
      ? d.mockService.getKnowledgeTree(treeKey)
      : d.request(`/api/knowledge/tree/${encodeURIComponent(treeKey)}`)
  },

  updateKnowledgeNode(
    id: string,
    data: { myNote?: string; isStarred?: boolean },
  ): Promise<d.ApiRes<d.KnowledgeNode>> {
    return d.isMock
      ? d.mockService.updateKnowledgeNode(id, data)
      : d.request(`/api/knowledge/node/${id}`, { method: 'PUT', data })
  },

  getKnowledgeReviewDue(): Promise<d.ApiRes<d.KnowledgeReviewDue>> {
    return d.isMock ? d.mockService.getKnowledgeReviewDue() : d.request('/api/knowledge/review/due')
  },

  createKnowledgeReviewSession(count = 5): Promise<d.ApiRes<d.KnowledgeReviewSession>> {
    return d.isMock
      ? d.mockService.createKnowledgeReviewSession(count)
      : d.request('/api/knowledge/review/session', { method: 'POST', data: { count } })
  },

  answerKnowledgeReview(
    nodeId: string,
    result: d.KnowledgeReviewResult,
  ): Promise<d.ApiRes<d.KnowledgeReviewAnswer>> {
    return d.isMock
      ? d.mockService.answerKnowledgeReview(nodeId, result)
      : d.request('/api/knowledge/review/answer', { method: 'POST', data: { nodeId, result } })
  },
}
