import * as d from '../_shared'

export const apiKnowledge = {
  // ===== 知识框架 =====

  getKnowledgeTrees(): Promise<d.ApiRes<d.KnowledgeTree[]>> {
    return d.isMock ? d.mockService.getKnowledgeTrees() : d.request('/api/knowledge/trees')
  },

  getKnowledgeTree(treeKey: string): Promise<d.ApiRes<d.KnowledgeTree>> {
    return d.isMock
      ? d.mockService.getKnowledgeTree(treeKey)
      : d.request(`/api/knowledge/tree/${treeKey}`)
  },

  syncKnowledge(treeKey?: string): Promise<d.ApiRes<Record<string, number>>> {
    return d.isMock
      ? d.mockService.syncKnowledge()
      : d.request(`/api/knowledge/sync${treeKey ? `?tree_key=${treeKey}` : ''}`, { method: 'POST' })
  },

  updateKnowledgeNode(
    id: string,
    data: { myNote?: string; isStarred?: boolean; content?: string },
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
