import { defineStore } from 'pinia'
import { api } from '@/api'
import type { KnowledgeNode, KnowledgeReviewResult, KnowledgeTree } from '@/types'

export const useKnowledgeStore = defineStore('knowledge', {
  state: () => ({
    trees: [] as KnowledgeTree[],
    current: null as KnowledgeTree | null,
    loading: false,
  }),
  actions: {
    async fetchTrees() {
      this.loading = true
      try {
        const res = await api.getKnowledgeTrees()
        if (res.code === 0 && res.data) this.trees = res.data
      } finally {
        this.loading = false
      }
    },
    async fetchTree(treeKey: string) {
      this.loading = true
      try {
        const res = await api.getKnowledgeTree(treeKey)
        if (res.code === 0 && res.data) this.current = res.data
      } finally {
        this.loading = false
      }
    },
    async sync() {
      const res = await api.syncKnowledge()
      if (res.code === 0) {
        await this.fetchTrees()
      }
      return res
    },
    async updateNode(id: string, data: { myNote?: string; isStarred?: boolean; content?: string }) {
      const res = await api.updateKnowledgeNode(id, data)
      if (res.code === 0) {
        // 局部更新 current 树里的节点
        if (this.current) {
          const updateInChildren = (nodes: KnowledgeNode[]): boolean => {
            for (const n of nodes) {
              if (n.id === id) {
                if (data.myNote !== undefined) n.myNote = data.myNote
                if (data.isStarred !== undefined) n.isStarred = data.isStarred
                if (data.content !== undefined) n.content = data.content
                return true
              }
              if (n.children && updateInChildren(n.children)) return true
            }
            return false
          }
          updateInChildren(this.current.nodes)
        }
      }
      return res
    },
    async answerNode(nodeId: string, result: KnowledgeReviewResult) {
      const res = await api.answerKnowledgeReview(nodeId, result)
      if (res.code === 0 && this.current) {
        const updateInChildren = (nodes: KnowledgeNode[]): boolean => {
          for (const n of nodes) {
            if (n.id === nodeId) {
              n.lastReviewedAt = new Date().toISOString()
              n.masteryLevel = result
              if (res.data) {
                if (res.data.masteryLevel) n.masteryLevel = res.data.masteryLevel
                if (res.data.nextReviewAt !== undefined) n.nextReviewAt = res.data.nextReviewAt
              }
              return true
            }
            if (n.children && updateInChildren(n.children)) return true
          }
          return false
        }
        updateInChildren(this.current.nodes)
      }
      return res
    },
  },
})
