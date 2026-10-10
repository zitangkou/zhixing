import Taro from '@tarojs/taro'
import { API_BASE_URL } from '@/config'

const tokenKey = 'yanyu-wechat-token-v1'
const userKey = 'yanyu-wechat-user-v1'
const tokenSavedAtKey = 'yanyu-wechat-token-saved-at-v1'
const tokenMaxAgeMs = 23 * 60 * 60 * 1000
let loginTask: Promise<string | null> | null = null

type LoginPayload = { code?: number; data?: { access_token?: string; user?: Record<string, unknown> }; message?: string }

export function getAccessToken(): string {
  return String(Taro.getStorageSync(tokenKey) || '')
}

export function getWechatUser(): Record<string, unknown> | null {
  try { return (Taro.getStorageSync(userKey) as Record<string, unknown>) || null } catch { return null }
}

/** 微信 code 仅短暂有效；每次重新登录并由后端换取会话，token 缓存在本机。 */
export function ensureWechatLogin(force = false): Promise<string | null> {
  if (Taro.getEnv() !== Taro.ENV_TYPE.WEAPP) return Promise.resolve(null)
  const savedAt = Number(Taro.getStorageSync(tokenSavedAtKey) || 0)
  if (!force && getAccessToken() && savedAt && Date.now() - savedAt < tokenMaxAgeMs) return Promise.resolve(getAccessToken())
  if (loginTask) return loginTask

  loginTask = (async () => {
    const login = await Taro.login()
    if (!login.code) throw new Error('微信登录失败，请稍后重试')
    const response = await Taro.request<LoginPayload>({
      url: `${API_BASE_URL}/auth/wechat/login`,
      method: 'POST',
      data: { code: login.code },
      header: { 'content-type': 'application/json', 'X-Product-Key': 'general', 'X-Wechat-App-Key': 'yanyu_english' },
    })
    const payload = response.data
    if (response.statusCode < 200 || response.statusCode >= 300 || payload?.code !== 0 || !payload.data?.access_token) {
      throw new Error(payload?.message || '微信登录暂不可用，请检查网络后重试')
    }
    Taro.setStorageSync(tokenKey, payload.data.access_token)
    Taro.setStorageSync(tokenSavedAtKey, Date.now())
    if (payload.data.user) Taro.setStorageSync(userKey, payload.data.user)
    return payload.data.access_token
  })().finally(() => { loginTask = null })

  return loginTask
}

export function clearWechatLogin(): void {
  Taro.removeStorageSync(tokenKey)
  Taro.removeStorageSync(userKey)
  Taro.removeStorageSync(tokenSavedAtKey)
}
