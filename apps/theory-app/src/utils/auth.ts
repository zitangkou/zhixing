import Taro from '@tarojs/taro'

const TOKEN_KEY = 'zhixing_token'

export function getToken(): string { return Taro.getStorageSync(TOKEN_KEY) || '' }
export function setToken(token: string) {
  Taro.setStorageSync(TOKEN_KEY, token)
  void import('@/utils/guestSync').then(({ syncGuestLearning }) => syncGuestLearning()).catch(() => undefined)
}
export function clearToken() { Taro.removeStorageSync(TOKEN_KEY) }
export function isLoggedIn() { return !!getToken() }
