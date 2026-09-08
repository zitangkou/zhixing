import { defineStore } from 'pinia'
import { api, type DailyLearningTask, type ShenlunStats } from '@/api'

export const useDailyTaskStore = defineStore('shenlun-daily-task', {
  state: () => ({
    task: null as DailyLearningTask | null,
    stats: null as ShenlunStats | null,
    loading: false,
    starting: false,
    message: '',
  }),
  getters: {
    tasks: (state) => state.task ? [state.task] : [],
    progressPercent: (state) => {
      if (!state.task) return 0
      if (state.task.progress.state === 'completed') return 100
      return Math.round((state.task.progress.currentStep * 100) / Math.max(state.task.progress.totalSteps, 1))
    },
  },
  actions: {
    async load() {
      this.loading = true
      this.message = ''
      const [taskResponse, statsResponse] = await Promise.all([api.getDailyTasks(), api.getStats()])
      this.loading = false
      if (taskResponse.code === 0 && taskResponse.data) {
        this.task =
          taskResponse.data.tasks.find((item) => item.progress.state === 'in_progress') ||
          taskResponse.data.tasks.find((item) => item.progress.state !== 'completed') ||
          taskResponse.data.tasks[0] ||
          null
      } else {
        this.message = taskResponse.message
      }
      if (statsResponse.code === 0 && statsResponse.data) this.stats = statsResponse.data
    },
    async start() {
      if (!this.task || this.task.progress.state !== 'not_started') return true
      this.starting = true
      const response = await api.updateDailyTask(this.task.id, { event: 'start' })
      this.starting = false
      if (response.code !== 0 || !response.data) {
        this.message = response.message
        return false
      }
      this.task = response.data
      return true
    },
    async transition(event: 'save' | 'submit' | 'review' | 'complete', draft?: Record<string, unknown>, currentStep?: number) {
      if (!this.task) return false
      const response = await api.updateDailyTask(this.task.id, { event, draft, currentStep })
      if (response.code !== 0 || !response.data) {
        this.message = response.message
        return false
      }
      this.task = response.data
      return true
    },
    async saveDraft(
      taskId: string,
      draft: Record<string, unknown>,
      currentStep?: number,
      _totalSteps?: number,
    ) {
      if (!this.task || this.task.id !== taskId) throw new Error('今日任务不存在')
      const response = await api.updateDailyTask(taskId, { event: 'save', draft, currentStep })
      if (response.code !== 0 || !response.data) {
        this.message = response.message || '任务进度保存失败'
        throw new Error(this.message)
      }
      this.task = response.data
      return response.data
    },
    async submit(taskId: string, draft?: Record<string, unknown>) {
      return this.applyEvent(taskId, 'submit', draft)
    },
    async markReviewed(taskId: string) {
      return this.applyEvent(taskId, 'review')
    },
    async complete(taskId: string) {
      return this.applyEvent(taskId, 'complete')
    },
    async applyEvent(
      taskId: string,
      event: 'submit' | 'review' | 'complete',
      draft?: Record<string, unknown>,
    ) {
      if (!this.task || this.task.id !== taskId) throw new Error('今日任务不存在')
      const response = await api.updateDailyTask(taskId, { event, draft })
      if (response.code !== 0 || !response.data) {
        this.message = response.message || '任务状态同步失败'
        throw new Error(this.message)
      }
      this.task = response.data
      return response.data
    },
  },
})
