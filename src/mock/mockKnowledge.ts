import * as m from './_core'

export const mockKnowledge = {
  // ===== 知识框架（mock，简单返回内置树） =====
  async getKnowledgeTrees(): Promise<import('@/types').ApiRes<import('@/types').KnowledgeTree[]>> {
    await m.delay(200)
    return m.ok([
      {
        treeKey: '申论',
        title: '申论',
        nodes: [
          {
            id: 'k1',
            treeKey: '申论',
            parentId: null,
            title: '提出对策题',
            content: '',
            depth: 0,
            sortOrder: 0,
            path: '申论/提出对策题',
            children: [
              {
                id: 'k1-1',
                treeKey: '申论',
                parentId: 'k1',
                title: '单一型对策',
                content: '仅提出解决措施',
                depth: 1,
                sortOrder: 0,
                path: '申论/提出对策题/单一型对策',
                children: null,
              },
              {
                id: 'k1-2',
                treeKey: '申论',
                parentId: 'k1',
                title: '复合型对策',
                content: '先概括问题或原因，再提出对策',
                depth: 1,
                sortOrder: 1,
                path: '申论/提出对策题/复合型对策',
                children: null,
              },
            ],
          },
          {
            id: 'k2',
            treeKey: '申论',
            parentId: null,
            title: '归纳概括题',
            content: '',
            depth: 0,
            sortOrder: 1,
            path: '申论/归纳概括题',
            children: null,
          },
        ],
      },
    ] as unknown as import('@/types').KnowledgeTree[])
  },
  async getKnowledgeTree(
    treeKey: string,
  ): Promise<import('@/types').ApiRes<import('@/types').KnowledgeTree>> {
    const r = await this.getKnowledgeTrees()
    const t = r.data?.find((x) => x.treeKey === treeKey)
    return t
      ? m.ok(t)
      : { code: 404, data: null as unknown as import('@/types').KnowledgeTree, message: '不存在' }
  },
  async syncKnowledge(): Promise<import('@/types').ApiRes<Record<string, number>>> {
    await m.delay(200)
    return m.ok({ 申论: 514, 判断推理: 350 })
  },
  async updateKnowledgeNode(
    id: string,
    data: { myNote?: string; isStarred?: boolean },
  ): Promise<import('@/types').ApiRes<import('@/types').KnowledgeNode>> {
    await m.delay(100)
    return m.ok({
      id,
      treeKey: '申论',
      parentId: null,
      title: '测试',
      content: '',
      myNote: data.myNote || '',
      isStarred: data.isStarred || false,
      depth: 0,
      sortOrder: 0,
      path: '测试',
      children: null,
    })
  },

  async getReviewHub(): Promise<import('@/types').ApiRes<import('@/types').ReviewHub>> {
    await m.delay(100)
    const manualWrongCount = m.mockState.manualWrongs.filter((w) => !w.mastered).length
    return m.ok({
      knowledgeDueCount: 2,
      articleReviewCount: 0,
      corpusInboxCount: 0,
      articleWrongCount: 1,
      manualWrongCount,
      wrongReviewCount: 1,
      wrongWaitingCount: 2,
      wrongRecommendCount: 1,
      totalCount: 3 + manualWrongCount,
    })
  },

  async getKnowledgeReviewDue(): Promise<
    import('@/types').ApiRes<import('@/types').KnowledgeReviewDue>
  > {
    await m.delay(100)
    return m.ok({
      dueCount: 2,
      candidates: [
        {
          id: 'k1-1',
          title: '单一型对策',
          path: '申论/提出对策题/单一型对策',
          treeKey: '申论',
          content: '仅提出解决措施',
          myNote: '',
          masteryLevel: 'new',
          hint: '仅提出解决…',
        },
      ],
    })
  },

  async createKnowledgeReviewSession(
    count = 5,
  ): Promise<import('@/types').ApiRes<import('@/types').KnowledgeReviewSession>> {
    await m.delay(100)
    const due = await this.getKnowledgeReviewDue()
    return m.ok({ cards: (due.data?.candidates || []).slice(0, count) })
  },

  async answerKnowledgeReview(
    nodeId: string,
    result: import('@/types').KnowledgeReviewResult,
  ): Promise<import('@/types').ApiRes<import('@/types').KnowledgeReviewAnswer>> {
    await m.delay(100)
    const mastery = result === 'easy' ? 'mastered' : result === 'good' ? 'familiar' : 'learning'
    return m.ok({
      id: nodeId,
      masteryLevel: mastery,
      nextReviewAt: new Date().toISOString(),
      reviewCount: 1,
      lastReviewedAt: new Date().toISOString(),
    })
  },
}
