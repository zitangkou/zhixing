import { defineStore } from 'pinia'
import { api } from '@/api'
import type {
  KnowledgeMapDetail,
  KnowledgeMapListItem,
  KnowledgeNode,
  KnowledgeReviewResult,
  KnowledgeTree,
} from '@/types'

export const useKnowledgeStore = defineStore('knowledge', {
  state: () => ({
    maps: [] as KnowledgeMapListItem[],
    mapDetail: null as KnowledgeMapDetail | null,
    trees: [] as KnowledgeTree[],
    current: null as KnowledgeTree | null,
    loading: false,
  }),
  actions: {
    async fetchMaps() {
      this.loading = true
      try {
        const res = await api.getKnowledgeMaps()
        if (res.code === 0 && res.data) this.maps = res.data
      } finally {
        this.loading = false
      }
    },
    async fetchMap(treeKey: string) {
      this.loading = true
      try {
        const res = await api.getKnowledgeMap(treeKey)
        if (res.code === 0 && res.data) this.mapDetail = res.data
        else this.mapDetail = null
      } finally {
        this.loading = false
      }
    },
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
    async updateNode(id: string, data: { myNote?: string; isStarred?: boolean }) {
      const res = await api.updateKnowledgeNode(id, data)
      if (res.code === 0 && this.current) {
        const updateInChildren = (nodes: KnowledgeNode[]): boolean => {
          for (const n of nodes) {
            if (n.id === id) {
              if (data.myNote !== undefined) n.myNote = data.myNote
              if (data.isStarred !== undefined) n.isStarred = data.isStarred
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
