import { defineStore } from 'pinia'
import Taro from '@tarojs/taro'
import { api } from '@/api'
import type { Question, ReviewTask, WrongQuestionRecord } from '@/types'
import { showToast } from '@/utils/platform'

export const useQuestionStore = defineStore('theory-question', {
  state: () => ({
    currentQuestions: [] as Question[],
    wrongQuestions: [] as WrongQuestionRecord[],
    reviewTasks: [] as ReviewTask[],
    reviewLoadError: '',
    wrongLoading: false,
    answeredToday: 0,
    dailyWrongReviewDone: false,
  }),
  getters: {
    wrongCount: (state) => state.wrongQuestions.length,
  },
  actions: {
    async generateQuestions(articleId: string) {
      const response = await api.getQuestions(articleId)
      this.currentQuestions = response.code === 0 && response.data
        ? response.data as Question[]
        : []
      return this.currentQuestions
    },
    async loadQuizByMode(mode: string, count = 10) {
      const response = await api.getQuizByMode(mode, count)
      this.currentQuestions = response.code === 0 && response.data
        ? response.data as Question[]
        : []
      return this.currentQuestions
    },
    async submitAnswer(questionId: string, answer: string | string[], _question?: Question) {
      const response = await api.submitAnswer(questionId, answer)
      if (response.code !== 0 || !response.data) {
        showToast(response.message || '提交答案失败', 'error')
        return null
      }
      this.answeredToday += 1
      if (!response.data.correct) await this.loadWrongQuestions('all')
      return response.data
    },
    async loadWrongQuestions(status: 'review' | 'waiting' | 'all' = 'review') {
      this.wrongLoading = true
      try {
        const response = await api.getWrongQuestions(status)
        if (response.code !== 0 || !response.data) {
          showToast(response.message || '加载错题失败', 'error')
          return false
        }
        this.wrongQuestions = response.data
        return true
      } finally {
        this.wrongLoading = false
      }
    },
    async fetchReviewTasks() {
      const response = await api.getReviewTasks()
      if (response.code !== 0 || !response.data) {
        this.reviewLoadError = response.message || '加载复习任务失败'
        this.reviewTasks = []
        return false
      }
      this.reviewLoadError = ''
      this.reviewTasks = response.data
      return true
    },
    async completeReviewTask(articleId: string) {
      const response = await api.completeReview(articleId)
      if (response.code !== 0) {
        showToast(response.message || '完成复习失败', 'error')
        return false
      }
      await this.fetchReviewTasks()
      return true
    },
    async redoWrongQuestion(questionId: string, answer: string | string[]) {
      const response = await api.redoWrongQuestion(questionId, answer)
      if (response.code !== 0 || !response.data) {
        showToast(response.message || '提交失败', 'error')
        return null
      }
      await this.loadWrongQuestions('all')
      return response.data
    },
    async removeWrongQuestion(questionId: string) {
      const response = await api.removeWrongQuestion(questionId)
      if (response.code !== 0) return false
      this.wrongQuestions = this.wrongQuestions.filter((item) => item.question.id !== questionId)
      return true
    },
    async submitQuizComplete(payload: {
      articleId?: string
      mode: string
      total: number
      correct: number
    }) {
      const response = await api.completeQuiz(payload)
      return response.code === 0 ? response.data : null
    },
    completeDailyWrongReview() {
      const today = new Date().toISOString().slice(0, 10)
      this.dailyWrongReviewDone = true
      Taro.setStorageSync(`wrongReview_${today}`, true)
    },
  },
})
