import { defineStore } from 'pinia'
import { api } from '@/api'
import type { Article, StudyRecord } from '@/types'
import { normalizeArticle } from '@/utils/articleContent'

export const useArticleStore = defineStore('theory-article', {
  state: () => ({
    currentArticle: null as Article | null,
    dailyArticles: [] as Article[],
    recommendedList: [] as Article[],
    articleHistory: [] as string[],
    studyRecords: [] as StudyRecord[],
    sectionReadMap: {} as Record<string, string[]>,
  }),
  actions: {
    async syncStudyData() {
      const response = await api.getStudyRecords()
      if (response.code === 0 && response.data) {
        this.studyRecords = response.data
        this.articleHistory = response.data.map((item) => item.articleId)
      }
      return this.studyRecords
    },
    async fetchDailyArticles() {
      const response = await api.getDailyArticles()
      if (response.code === 0 && response.data) {
        this.dailyArticles = response.data.map((item) => normalizeArticle(item as Article))
      }
      return this.dailyArticles
    },
    async fetchRecommendedArticles(reset = false) {
      const response = await api.getRecommendedArticles(0, 20)
      if (response.code === 0 && response.data) {
        const items = response.data.items.map((item) => normalizeArticle(item as Article))
        this.recommendedList = reset ? items : [...this.recommendedList, ...items]
      }
      return this.recommendedList
    },
    async syncSectionReads() {
      const response = await api.getSectionReads()
      if (response.code === 0 && response.data) this.sectionReadMap = response.data
    },
    async getArticleDetail(id: string) {
      const response = await api.getArticle(id)
      if (response.code !== 0 || !response.data) return null
      const article = normalizeArticle(response.data as Article)
      this.currentArticle = article
      await this.syncSectionReads()
      return article
    },
    async markAsRead(articleId: string) {
      if (!this.articleHistory.includes(articleId)) this.articleHistory.push(articleId)
      const response = await api.markArticleRead(articleId)
      return response.data?.points || 0
    },
    isRead(articleId: string) {
      return this.articleHistory.includes(articleId)
    },
    getReadSectionIds(articleId: string): string[] {
      return this.sectionReadMap[articleId] || []
    },
    isSectionRead(articleId: string, sectionId: string) {
      return this.getReadSectionIds(articleId).includes(sectionId)
    },
    async markSectionRead(articleId: string, sectionId: string) {
      const current = this.getReadSectionIds(articleId)
      if (!current.includes(sectionId)) {
        this.sectionReadMap[articleId] = [...current, sectionId]
        await api.markSectionRead(articleId, sectionId)
      }
    },
    getSectionReadProgress(articleId: string, totalReadable: number) {
      if (!totalReadable) return 0
      return Math.round((this.getReadSectionIds(articleId).length / totalReadable) * 100)
    },
    isAllSectionsRead(articleId: string, readableSectionIds: string[]) {
      const read = this.getReadSectionIds(articleId)
      return readableSectionIds.length > 0 && readableSectionIds.every((id) => read.includes(id))
    },
  },
})
