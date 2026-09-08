import { defineStore } from 'pinia'
import { api, isMock } from '@/api'
import type { ManualWrong } from '@/types'

export const useManualWrongStore = defineStore('manualWrong', {
  state: () => ({
    list: [] as ManualWrong[],
    loading: false,
    loadError: '',
    filterSubject: '' as string,
    showMastered: true as boolean,
  }),
  getters: {
    filtered: (s) => {
      let arr = s.list
      if (s.filterSubject) arr = arr.filter((w) => w.subject === s.filterSubject)
      if (!s.showMastered) arr = arr.filter((w) => !w.mastered)
      return arr
    },
    bySubject: (s) => {
      const map: Record<string, number> = {}
      for (const w of s.list) {
        if (w.mastered) continue
        map[w.subject] = (map[w.subject] || 0) + 1
      }
      return map
    },
    totalCount: (s) => s.list.length,
    unmasteredCount: (s) => s.list.filter((w) => !w.mastered).length,
  },
  actions: {
    async fetch() {
      this.loading = true
      this.loadError = ''
      try {
        const res = await api.listManualWrongs()
        if (res.code === 0 && res.data) {
          this.list = res.data
        } else {
          this.loadError = res.message || '加载失败'
        }
      } catch {
        this.loadError = '网络异常，请稍后重试'
      } finally {
        this.loading = false
      }
    },
    async create(data: {
      subject?: string
      questionType?: string
      stem?: string
      options?: string
      myAnswer?: string
      correctAnswer?: string
      analysis?: string
      wrongReason?: string
      note?: string
      source?: string
      images?: string[]
    }) {
      const res = await api.createManualWrong(data)
      if (res.code === 0 && res.data) {
        this.list.unshift(res.data)
      }
      return res
    },
    async update(
      id: string,
      data: {
        mastered?: boolean
        reviewCount?: number
        note?: string
        images?: string[]
      },
    ) {
      const res = await api.updateManualWrong(id, data)
      if (res.code === 0 && res.data) {
        const idx = this.list.findIndex((w) => w.id === id)
        if (idx >= 0) this.list[idx] = res.data
      }
      return res
    },
    async remove(id: string) {
      const res = await api.deleteManualWrong(id)
      if (res.code === 0) {
        this.list = this.list.filter((w) => w.id !== id)
      }
      return res
    },
    setFilter(subject: string) {
      this.filterSubject = subject
    },
    toggleMasteredFilter() {
      this.showMastered = !this.showMastered
    },
  },
  persist: {
    pick: isMock ? ['list'] : [],
  },
})
