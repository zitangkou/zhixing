import Taro from '@tarojs/taro'
import type { Lesson, RoadmapStage } from '@/data/lessons'

type ApiResponse<T> = { code: number; data: T; message?: string }
export type PhotographyCase = {
  id: string; title: string; imageUrl: string; sourceUrl: string; author: string; licenseType: string; licenseNote: string
  category: string; level: string; observations: string[]; exif: Record<string, string | number | null>
  inferences: { statement: string; evidence: string; confidence: string }[]
  practiceTitle: string; practiceGoal: string; practiceSteps: string[]; practiceVariable: string; criteria: string[]; durationMin: number
}
export type PhotographyCatalog = { lessons: Lesson[]; stages: RoadmapStage[]; cases: PhotographyCase[] }
export type PhotographyLogin = { access_token: string; user: { id: string; nickname: string; avatar?: string | null } }

const API_BASE = (process.env.TARO_APP_API_BASE_URL || '').replace(/\/$/, '')
const TOKEN_KEY = 'sheying-access-token'
const USER_KEY = 'sheying-user'

export function readPhotographyUser(): PhotographyLogin['user'] | null {
  return Taro.getStorageSync(USER_KEY) || null
}

export async function loginPhotographyWithWechat(): Promise<PhotographyLogin['user']> {
  if (!API_BASE) throw new Error('服务地址未配置')
  const login = await Taro.login()
  if (!login.code) throw new Error('未获取到微信登录凭证，请重试')
  const response = await Taro.request<ApiResponse<PhotographyLogin>>({
    url: `${API_BASE}/api/auth/wechat/login`,
    method: 'POST',
    data: { code: login.code },
    header: { 'Content-Type': 'application/json', 'X-Product-Key': 'general', 'X-Wechat-App-Key': 'sheying' },
  })
  if (response.statusCode >= 400 || response.data.code !== 0) {
    throw new Error(response.data.message || '微信登录失败')
  }
  Taro.setStorageSync(TOKEN_KEY, response.data.data.access_token)
  Taro.setStorageSync(USER_KEY, response.data.data.user)
  return response.data.data.user
}

export async function fetchPhotographyCatalog(): Promise<PhotographyCatalog | null> {
  if (!API_BASE) return null
  const response = await Taro.request<ApiResponse<PhotographyCatalog>>({
    url: `${API_BASE}/api/photography/catalog`,
    method: 'GET',
    header: { 'X-Product-Key': 'general', ...authHeader() },
  })
  if (response.statusCode >= 400 || response.data.code !== 0) {
    throw new Error(response.data.message || '摄影课程暂时无法加载')
  }
  const catalog = response.data.data
  catalog.cases = (catalog.cases || []).map((item) => ({ ...item, imageUrl: item.imageUrl.startsWith('/') ? `${API_BASE}${item.imageUrl}` : item.imageUrl }))
  return catalog
}

function authHeader(): Record<string, string> {
  const token = Taro.getStorageSync(TOKEN_KEY)
  return token ? { Authorization: `Bearer ${token}` } : {}
}
