import { defineStore } from 'pinia'
import { api, isMock } from '@/api'
import type { DayPlan, DailyReview, PlanTask } from '@/types'

const todayStr = () => new Date().toISOString().slice(0, 10)

export const usePlanStore = defineStore('plan', {
  state: () => ({
    today: null as DayPlan | null,
    week: [] as DayPlan[],
    loading: false,
    weekLoading: false,
    loadError: '' as string,
    weekError: '' as string,
  }),
  getters: {
    todayCompletion: (s) => s.today?.completion || 0,
    pendingCount: (s) => s.today?.tasks.filter((t) => t.status === 'pending').length || 0,
  },
  actions: {
    async fetchToday() {
      this.loading = true
      this.loadError = ''
      try {
        const res = await api.getTodayPlan()
        if (res.code === 0 && res.data) this.today = res.data
        else this.loadError = res.message || '加载今日清单失败'
      } catch {
        this.loadError = '网络异常，请稍后重试'
      } finally {
        this.loading = false
      }
    },
    async fetchWeek() {
      this.weekLoading = true
      this.weekError = ''
      try {
        const res = await api.getWeekPlan()
        if (res.code === 0 && res.data) this.week = res.data
        else this.weekError = res.message || '加载本周计划失败'
      } catch {
        this.weekError = '网络异常，请稍后重试'
      } finally {
        this.weekLoading = false
      }
    },
    async toggleTask(task: PlanTask) {
      const newStatus = task.status === 'done' ? 'pending' : 'done'
      const actual = newStatus === 'done' ? task.expectedMinutes : 0
      const res = await api.updatePlanTask(task.id, { status: newStatus, actualMinutes: actual })
      if (res.code === 0 && res.data && this.today) {
        const idx = this.today.tasks.findIndex((t) => t.id === task.id)
        if (idx >= 0) this.today.tasks[idx] = res.data
        this.recalc()
      }
    },
    async setTaskNote(task: PlanTask, note: string) {
      const res = await api.updatePlanTask(task.id, { note })
      if (res.code === 0 && res.data && this.today) {
        const idx = this.today.tasks.findIndex((t) => t.id === task.id)
        if (idx >= 0) this.today.tasks[idx] = res.data
      }
    },
    async addTask(content: string, subject = '', timeSlot = '', expectedMinutes = 0) {
      const res = await api.addPlanTask({
        planDate: todayStr(),
        content,
        subject,
        timeSlot,
        expectedMinutes,
      })
      if (res.code === 0 && res.data && this.today) {
        this.today.tasks.push(res.data)
        this.recalc()
      }
    },
    async removeTask(taskId: string) {
      const res = await api.deletePlanTask(taskId)
      if (res.code === 0 && this.today) {
        this.today.tasks = this.today.tasks.filter((t) => t.id !== taskId)
        this.recalc()
      }
    },
    async saveReview(data: DailyReview) {
      const res = await api.upsertReview(data)
      return res.code === 0
    },
    recalc() {
      if (!this.today) return
      const ts = this.today.tasks
      const done = ts.filter((t) => t.status === 'done').length
      this.today.doneCount = done
      this.today.totalCount = ts.length
      this.today.completion = ts.length ? Math.round((done / ts.length) * 100) : 0
      this.today.actualMinutes = ts.reduce((s, t) => s + t.actualMinutes, 0)
      this.today.expectedMinutes = ts.reduce((s, t) => s + t.expectedMinutes, 0)
    },
  },
  persist: {
    pick: isMock ? ['today'] : [],
  },
})
