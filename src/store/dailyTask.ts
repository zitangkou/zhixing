import { defineStore } from 'pinia'
import { api, type DailyLearningTask, type DailyTaskEvent } from '@/api'

interface ProgressPayload {
  event: DailyTaskEvent
  currentStep?: number
  totalSteps?: number
  draft?: Record<string, unknown>
}

export const useDailyTaskStore = defineStore('daily-task', {
  state: () => ({
    date: '',
    productKey: '',
    completion: 0,
    completedCount: 0,
    totalCount: 0,
    estimatedMinutes: 0,
    tasks: [] as DailyLearningTask[],
    loading: false,
    error: '',
  }),

  getters: {
    activeTask: (state) =>
      state.tasks.find((task) => task.progress.state === 'in_progress') ||
      state.tasks.find((task) => task.progress.state !== 'completed') ||
      null,
    allCompleted: (state) => state.totalCount > 0 && state.completedCount === state.totalCount,
  },

  actions: {
    async load(date?: string) {
      this.loading = true
      this.error = ''
      const res = await api.getDailyTasks(date)
      this.loading = false
      if (res.code !== 0 || !res.data) {
        this.error = res.message || '今日任务加载失败'
        return false
      }
      this.date = res.data.date
      this.productKey = res.data.productKey
      this.completion = res.data.completion
      this.completedCount = res.data.completedCount
      this.totalCount = res.data.totalCount
      this.estimatedMinutes = res.data.estimatedMinutes
      this.tasks = res.data.tasks
      return true
    },

    async transition(taskId: string, payload: ProgressPayload) {
      const res = await api.updateDailyTaskProgress(taskId, payload)
      if (res.code !== 0 || !res.data) {
        this.error = res.message || '任务进度保存失败'
        throw new Error(this.error)
      }
      const index = this.tasks.findIndex((task) => task.id === taskId)
      if (index >= 0) this.tasks[index] = res.data
      this.recalculate()
      this.error = ''
      return res.data
    },

    start(taskId: string) {
      return this.transition(taskId, { event: 'start' })
    },

    saveDraft(
      taskId: string,
      draft: Record<string, unknown>,
      currentStep?: number,
      totalSteps?: number,
    ) {
      return this.transition(taskId, { event: 'save', draft, currentStep, totalSteps })
    },

    submit(taskId: string, draft?: Record<string, unknown>) {
      return this.transition(taskId, { event: 'submit', draft })
    },

    markReviewed(taskId: string) {
      return this.transition(taskId, { event: 'review' })
    },

    complete(taskId: string) {
      return this.transition(taskId, { event: 'complete' })
    },

    recalculate() {
      this.completedCount = this.tasks.filter((task) => task.progress.state === 'completed').length
      this.totalCount = this.tasks.length
      this.completion = this.totalCount ? Math.round((this.completedCount * 100) / this.totalCount) : 0
    },
  },

  persist: {
    pick: ['date', 'productKey', 'tasks'],
  },
})
