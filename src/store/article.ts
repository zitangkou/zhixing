import { defineStore } from 'pinia'
import { api, isMock } from '@/api'
import type { Article, StudyRecord } from '@/types'
import { formatDate } from '@/utils/memoryCurve'
import { normalizeArticle } from '@/utils/articleContent'
import { useUserStore } from './user'

export const useArticleStore = defineStore('article', {
  state: () => ({
    dailyArticles: [] as Article[],
    articleHistory: [] as string[],
    currentArticle: null as Article | null,
    studyRecords: [] as StudyRecord[],
    /** articleId -> 已读小节 id 列表 */
    sectionReadMap: {} as Record<string, string[]>,
    /** 学习页列表首次加载 */
    dailyLoading: false,
    /** 文章详情加载（与学习页分离，避免 tab 切换闪烁） */
    detailLoading: false,
    /** 推荐阅读分页 */
    recommendedList: [] as Article[],
    recommendedTotal: 0,
    recommendedHasMore: true,
    recommendedLoading: false,
    recommendedOffset: 0,
  }),

  getters: {
    todayMustRead: (state) => {
      const featured = state.dailyArticles.filter((a) => a.isFeatured)
      if (featured.length) return featured
      return state.dailyArticles.slice(0, 1)
    },
    featuredArticles: (state) => {
      const featured = state.dailyArticles.filter((a) => a.isFeatured)
      if (featured.length) return featured
      return state.dailyArticles.slice(0, 1)
    },
    /** 最近有学习活动的文章 id（按 updatedAt / 学习日期） */
    lastStudyingArticleId: (state): string | null => {
      if (!state.studyRecords.length) return null
      const scored = state.studyRecords.map((r) => {
        const t =
          Date.parse(r.updatedAt || '') ||
          Date.parse(r.lastReviewDate || '') ||
          Date.parse(r.studyDate || '') ||
          0
        return { id: r.articleId, t }
      })
      scored.sort((a, b) => b.t - a.t)
      return scored[0]?.id || null
    },
    recommendedArticles: (state) => state.recommendedList,
    readProgress: (state) => {
      if (state.dailyArticles.length === 0) return 0
      const read = state.dailyArticles.filter((a) => state.articleHistory.includes(a.id)).length
      return Math.round((read / state.dailyArticles.length) * 100)
    },
  },

  actions: {
    async syncStudyData() {
      if (isMock) return
      const [recordsRes, sectionsRes] = await Promise.all([
        api.getStudyRecords(),
        api.getSectionReads(),
      ])
      if (recordsRes.code === 0) {
        this.studyRecords = recordsRes.data
        this.articleHistory = recordsRes.data.map((r) => r.articleId)
      }
      if (sectionsRes.code === 0) {
        this.sectionReadMap = sectionsRes.data
      }
    },

    async fetchDailyArticles() {
      const hasCache = this.dailyArticles.length > 0
      if (!hasCache) this.dailyLoading = true
      try {
        const res = await api.getDailyArticles()
        if (res.code === 0) this.dailyArticles = res.data.map(normalizeArticle)
      } finally {
        this.dailyLoading = false
      }
    },

    async fetchRecommendedArticles(reset = false) {
      if (this.recommendedLoading) return
      if (!reset && !this.recommendedHasMore) return
      if (reset) {
        this.recommendedOffset = 0
        this.recommendedList = []
        this.recommendedHasMore = true
        this.recommendedTotal = 0
      }
      this.recommendedLoading = true
      try {
        const res = await api.getRecommendedArticles(this.recommendedOffset, 5)
        if (res.code === 0 && res.data) {
          const items = res.data.items.map(normalizeArticle)
          this.recommendedList = reset ? items : [...this.recommendedList, ...items]
          this.recommendedOffset = this.recommendedList.length
          this.recommendedTotal = res.data.total
          this.recommendedHasMore = res.data.hasMore
        }
      } finally {
        this.recommendedLoading = false
      }
    },

    async getArticleDetail(id: string) {
      this.detailLoading = true
      try {
        const res = await api.getArticleDetail(id)
        if (res.code === 0 && res.data) {
          this.currentArticle = normalizeArticle(res.data)
        }
        return res.data ? normalizeArticle(res.data) : null
      } finally {
        this.detailLoading = false
      }
    },

    async markAsRead(articleId: string) {
      if (!this.articleHistory.includes(articleId)) {
        this.articleHistory.push(articleId)
      }
      const existing = this.studyRecords.find((r) => r.articleId === articleId)
      const nowIso = new Date().toISOString()
      if (!existing) {
        this.studyRecords.push({
          articleId,
          studyDate: formatDate(),
          reviewCount: 0,
          mastered: false,
          updatedAt: nowIso,
        })
      } else {
        existing.updatedAt = nowIso
      }
      const res = await api.markArticleRead(articleId)
      if (!isMock) {
        const userStore = useUserStore()
        await userStore.fetchPoints()
        await this.syncStudyData()
      }
      return res.data?.points || 0
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
      const list = this.getReadSectionIds(articleId)
      const already = list.includes(sectionId)
      if (!already) {
        this.sectionReadMap[articleId] = [...list, sectionId]
      }
      const nowIso = new Date().toISOString()
      const rec = this.studyRecords.find((r) => r.articleId === articleId)
      if (rec) {
        rec.updatedAt = nowIso
      } else {
        this.studyRecords.push({
          articleId,
          studyDate: formatDate(),
          reviewCount: 0,
          mastered: false,
          updatedAt: nowIso,
        })
        if (!this.articleHistory.includes(articleId)) {
          this.articleHistory.push(articleId)
        }
      }
      if (!isMock) {
        // 已读段落也会打到后端，用于刷新「最近在学」
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

  persist: {
    pick: isMock ? ['articleHistory', 'studyRecords', 'sectionReadMap'] : [],
  },
})
