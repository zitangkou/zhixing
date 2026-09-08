import { defineStore } from 'pinia'
import { api, type DailyLearningTask, type DailyTaskEvent } from '@/api'

export const useDailyTaskStore = defineStore('theory-daily-task', {
  state: () => ({ task: null as DailyLearningTask | null, loading: false, starting: false, message: '' }),
  getters: {
    tasks: (state) => state.task ? [state.task] : [],
    activeTask: (state) => state.task,
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
      const response = await api.getDailyTasks()
      this.loading = false
      if (response.code !== 0 || !response.data) {
        this.message = response.message
        return
      }
      this.task =
        response.data.tasks.find((item) => item.progress.state === 'in_progress') ||
        response.data.tasks.find((item) => item.progress.state !== 'completed') ||
        response.data.tasks[0] ||
        null
    },
    async start(_taskId?: string) {
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
    async transition(event: DailyTaskEvent, currentStep?: number, draft?: Record<string, unknown>) {
      if (!this.task) return false
      const response = await api.updateDailyTask(this.task.id, { event, currentStep, draft })
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
      currentStep: number,
      _totalSteps?: number,
    ) {
      if (!this.task || this.task.id !== taskId) await this.load()
      const ok = await this.transition('save', currentStep, draft)
      if (!ok) throw new Error(this.message || '进度保存失败')
      return this.task
    },
    async submit(taskId: string) {
      if (!this.task || this.task.id !== taskId) await this.load()
      const ok = await this.transition('submit', this.task?.progress.currentStep, this.task?.progress.draft)
      if (!ok) throw new Error(this.message || '提交失败')
      return this.task
    },
    async markReviewed(taskId: string) {
      if (!this.task || this.task.id !== taskId) await this.load()
      const ok = await this.transition('review', this.task?.progress.currentStep, this.task?.progress.draft)
      if (!ok) throw new Error(this.message || '复盘状态保存失败')
      return this.task
    },
    async complete(taskId: string) {
      if (!this.task || this.task.id !== taskId) await this.load()
      const ok = await this.transition('complete', this.task?.progress.currentStep, this.task?.progress.draft)
      if (!ok) throw new Error(this.message || '完成状态保存失败')
      return this.task
    },
  },
})
