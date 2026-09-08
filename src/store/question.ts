import { defineStore } from 'pinia'
import Taro from '@tarojs/taro'
import { api, isMock } from '@/api'
import { mockService } from '@/mock/service'
import type { Question, RankItem, ReviewTask, WrongQuestionRecord } from '@/types'
import type { RankType } from '@/constants'
import { showToast } from '@/utils/platform'
import { useUserStore } from './user'
import { useArticleStore } from './article'

export const useQuestionStore = defineStore('question', {
  state: () => ({
    currentQuestions: [] as Question[],
    currentIndex: 0,
    wrongQuestions: [] as WrongQuestionRecord[],
    wrongLoading: false,
    reviewTasks: [] as ReviewTask[],
    rankList: [] as RankItem[],
    answeredToday: 0,
    showDailyWrongReview: false,
    dailyWrongReviewDone: false,
  }),

  getters: {
    currentQuestion: (state) => state.currentQuestions[state.currentIndex] || null,
    isLastQuestion: (state) => state.currentIndex >= state.currentQuestions.length - 1,
    progress: (state) => {
      if (state.currentQuestions.length === 0) return 0
      return Math.round(((state.currentIndex + 1) / state.currentQuestions.length) * 100)
    },
    wrongCount: (state) => state.wrongQuestions.length,
  },

  actions: {
    async generateQuestions(articleId: string) {
      const res = await api.getQuestions(articleId)
      if (res.code === 0 && res.data) {
        this.currentQuestions = res.data
        this.currentIndex = 0
        return res.data
      }
      this.currentQuestions = []
      return []
    },

    async loadQuizByMode(mode: string, count = 10) {
      const res = await api.getQuizByMode(mode, count)
      if (res.code === 0 && res.data) {
        this.currentQuestions = res.data
        this.currentIndex = 0
        return res.data
      }
      this.currentQuestions = []
      return []
    },

    async submitAnswer(questionId: string, answer: string | string[], question?: Question) {
      const res = await api.submitAnswer(questionId, answer)
      const userStore = useUserStore()

      if (res.code !== 0 || !res.data) {
        if (res.code === 401 || res.code === 403) {
          showToast('登录已失效，请重新登录', 'error')
          userStore.logout()
        } else {
          showToast(res.message || '提交答案失败', 'error')
        }
        return null
      }

      if (res.data.correct) {
        if (isMock) userStore.addPoints(res.data.pointsEarned)
        else await userStore.fetchPoints()
        this.answeredToday++
      } else {
        await this.loadWrongQuestions()
        if (question) {
          this.upsertLocalWrong(question, answer)
        }
      }
      return res.data
    },

    upsertLocalWrong(question: Question, userAnswer?: string | string[]) {
      const articleStore = useArticleStore()
      const article =
        articleStore.dailyArticles.find((a) => a.id === question.articleId) ||
        articleStore.currentArticle
      const existing = this.wrongQuestions.find((w) => w.question.id === question.id)
      if (existing) {
        existing.wrongCount += 1
        existing.lastWrongAt = new Date().toISOString()
        if (userAnswer !== undefined) existing.userAnswer = userAnswer
        return
      }
      this.wrongQuestions = [
        {
          question,
          wrongCount: 1,
          lastWrongAt: new Date().toISOString(),
          userAnswer,
          articleTitle: article?.title || '未知文章',
          tag: article?.tags[0] || '综合',
        },
        ...this.wrongQuestions,
      ]
    },

    syncWrongFromMock() {
      const articleStore = useArticleStore()
      const wrongMap = mockService.getWrongQuestionsMap()
      this.wrongQuestions = Array.from(wrongMap.entries()).map(([, record]) => {
        const article = articleStore.dailyArticles.find((a) => a.id === record.question.articleId)
        return {
          question: record.question,
          wrongCount: record.wrongCount,
          lastWrongAt: record.lastWrongAt,
          userAnswer: record.userAnswer,
          articleTitle: article?.title || '未知文章',
          tag: article?.tags[0] || '综合',
        }
      })
    },

    nextQuestion() {
      if (this.currentIndex < this.currentQuestions.length - 1) {
        this.currentIndex++
      }
    },

    resetQuiz() {
      this.currentIndex = 0
    },

    async fetchReviewTasks() {
      const articleStore = useArticleStore()
      const res = await api.getReviewTasks(articleStore.studyRecords)
      if (res.code === 0) this.reviewTasks = res.data
      return res.data
    },

    async completeReviewTask(articleId: string) {
      await api.completeReview(articleId)
      const articleStore = useArticleStore()
      if (isMock) {
        const record = articleStore.studyRecords.find((r) => r.articleId === articleId)
        if (record) {
          record.reviewCount++
          record.lastReviewDate = new Date().toISOString().slice(0, 10)
        }
      } else {
        await articleStore.syncStudyData()
      }
      await this.fetchReviewTasks()
    },

    async fetchRankList(type: RankType = 'weekly') {
      const res = await api.getRankList(type)
      if (res.code === 0) this.rankList = res.data
      return res.data
    },

    async submitQuizComplete(payload: {
      articleId?: string
      mode: string
      total: number
      correct: number
    }) {
      const res = await api.completeQuiz(payload)
      if (res.code === 0) return res.data
      return null
    },

    getWrongByTag(tag: string) {
      if (!tag) return this.wrongQuestions
      return this.wrongQuestions.filter((w) => w.tag === tag)
    },

    async redoWrongQuestion(questionId: string, answer: string | string[]) {
      if (isMock) {
        const res = await mockService.redoWrongQuestion(questionId, answer)
        if (res.code !== 0) return null
        if (res.data.correct) {
          await this.loadWrongQuestions()
          const userStore = useUserStore()
          userStore.addPoints(res.data.pointsEarned)
        }
        return res.data
      }

      const res = await api.redoWrongQuestion(questionId, answer)
      if (res.code !== 0) return null
      if (res.data.correct) {
        await this.loadWrongQuestions()
        const userStore = useUserStore()
        await userStore.fetchPoints()
      }
      return res.data
    },

    async removeWrongQuestion(questionId: string) {
      const res = await api.removeWrongQuestion(questionId)
      if (res.code !== 0) {
        showToast(res.message || '移除失败', 'error')
        return false
      }
      this.wrongQuestions = this.wrongQuestions.filter((w) => w.question.id !== questionId)
      return true
    },

    checkDailyWrongReview() {
      const today = new Date().toISOString().slice(0, 10)
      const key = `wrongReview_${today}`
      const done = Taro.getStorageSync(key)
      if (!done && this.wrongQuestions.length > 0) {
        this.showDailyWrongReview = true
      }
    },

    completeDailyWrongReview() {
      const today = new Date().toISOString().slice(0, 10)
      this.dailyWrongReviewDone = true
      this.showDailyWrongReview = false
      Taro.setStorageSync(`wrongReview_${today}`, true)
    },

    async loadWrongQuestions(status: 'review' | 'waiting' | 'all' = 'review') {
      if (isMock) {
        this.syncWrongFromMock()
        return true
      }
      this.wrongLoading = true
      try {
        const res = await api.getWrongQuestions(status)
        if (res.code === 401 || res.code === 403) {
          showToast('登录已失效，请重新登录', 'error')
          useUserStore().logout()
          return false
        }
        if (res.code !== 0) {
          showToast(res.message || '加载错题失败', 'error')
          return false
        }
        if (Array.isArray(res.data)) {
          this.wrongQuestions = res.data
        }
        return true
      } finally {
        this.wrongLoading = false
      }
    },
  },

  persist: {
    pick: ['answeredToday', 'dailyWrongReviewDone'],
  },
})
