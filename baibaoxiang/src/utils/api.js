import Taro from '@tarojs/taro'
import { storage } from './storage'

const baseUrl = API_BASE_URL

export async function request(path, { method = 'GET', data } = {}) {
  if (!baseUrl) throw new Error('后端地址尚未配置，当前可继续以访客模式浏览')
  const token = storage.token()
  const response = await Taro.request({
    url: `${baseUrl}${path}`,
    method,
    data,
    header: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      'X-Product-Key': 'general',
    },
  })
  const body = response.data || {}
  if (response.statusCode < 200 || response.statusCode >= 300 || body.code !== 0) {
    throw new Error(body.message || '请求暂时失败，请稍后重试')
  }
  return body.data
}

export async function loginWithWechat() {
  const { code } = await Taro.login()
  if (!code) throw new Error('暂未获取到微信登录凭证，请重试')
  return request('/api/auth/wechat/login', { method: 'POST', data: { code } })
}

export function saveRemoteProfile(nickname) {
  return request('/api/user/me', { method: 'PUT', data: { nickname } })
}

export function sendFeedback(content) {
  return request('/api/feedback', { method: 'POST', data: { content } })
}
