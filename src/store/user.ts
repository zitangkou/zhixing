import { defineStore } from 'pinia'
import Taro from '@tarojs/taro'
import { api, initUserFromMock, isMock } from '@/api'
import { clearToken, setToken } from '@/utils/auth'
import { calcSignStreak, formatDate } from '@/utils/memoryCurve'
import type { PointsLog, SignStatus, UserInfo } from '@/types'

const initial = isMock
  ? initUserFromMock()
  : { userInfo: null as UserInfo | null, points: 0, signStatus: {} as SignStatus }

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: initial.userInfo,
    points: initial.points,
    signStatus: initial.signStatus as SignStatus,
    pointsLogs: [] as PointsLog[],
    signedToday: false,
  }),

  getters: {
    signStreak: (state) => calcSignStreak(state.signStatus, formatDate()),
    hasSignedToday: (state) => !!state.signStatus[formatDate()],
    isLoggedIn: (state) => !!state.userInfo?.id,
  },

  actions: {
    applyUserMe(data: import('@/api').UserMeData) {
      this.userInfo = {
        id: data.id,
        username: data.username,
        nickname: data.nickname,
        avatar: data.avatar,
        email: data.email || '',
        phone: data.phone || '',
        isMember: data.isMember,
      }
      this.points = data.points
      this.signStatus = Object.fromEntries(data.signDates.map((d) => [d, true]))
      this.signedToday = data.hasSignedToday
    },

    async bootstrap() {
      if (isMock) return true
      const res = await api.getUserMe()
      if (res.code !== 0 || !res.data) return false
      this.applyUserMe(res.data)
      await this.fetchPointsLog()
      return true
    },

    async updateProfile(data: { nickname?: string; email?: string; phone?: string }) {
      const res = await api.updateProfile(data)
      if (res.code !== 0 || !res.data) {
        throw new Error(res.message || '保存失败')
      }
      this.applyUserMe(res.data)
      return res.data
    },

    async changePassword(data: {
      oldPassword: string
      newPassword: string
      newPasswordConfirm: string
    }) {
      const res = await api.changePassword(data)
      if (res.code !== 0) {
        throw new Error(res.message || '修改密码失败')
      }
    },

    async uploadAvatar(filePath: string, file?: File) {
      const res = await api.uploadAvatar(filePath, file)
      if (res.code !== 0 || !res.data) {
        throw new Error(res.message || '头像上传失败')
      }
      this.applyUserMe(res.data)
      return res.data
    },

    async login(username: string, password: string) {
      const res = await api.login(username, password)
      if (res.code !== 0 || !res.data) {
        throw new Error(res.message || '登录失败')
      }
      setToken(res.data.access_token)
      this.applyUserMe(res.data.user)
      await this.fetchPointsLog()
      return res.data
    },

    async register(username: string, password: string, passwordConfirm: string) {
      const res = await api.register(username, password, passwordConfirm)
      if (res.code !== 0 || !res.data) {
        throw new Error(res.message || '注册失败')
      }
      setToken(res.data.access_token)
      this.applyUserMe(res.data.user)
      await this.fetchPointsLog()
      return res.data
    },

    clearSession() {
      clearToken()
      this.userInfo = null
      this.points = 0
      this.signStatus = {}
      this.pointsLogs = []
      this.signedToday = false
    },

    logout() {
      this.clearSession()
      Taro.switchTab({ url: '/pages/today/index' })
    },

    async signIn() {
      const res = await api.signIn()
      if (res.code === 0) {
        this.signStatus[formatDate()] = true
        await this.fetchPoints()
        this.signedToday = true
        await this.fetchPointsLog()
      }
      return res
    },

    async fetchPoints() {
      const res = await api.getPoints()
      if (res.code === 0) this.points = res.data
    },

    async fetchPointsLog() {
      const res = await api.getPointsLog()
      if (res.code === 0) this.pointsLogs = res.data
    },

    addPoints(amount: number) {
      if (isMock) this.points += amount
    },
  },

  persist: {
    pick: isMock ? ['userInfo', 'points', 'signStatus'] : ['userInfo'],
  },
})
