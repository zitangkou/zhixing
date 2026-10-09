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

export function fetchImageStyles() {
  return request('/api/image-styles')
}

export async function generateImageStyle(filePath, styleId) {
  if (!baseUrl) throw new Error('后端地址尚未配置')
  const token = storage.token()
  if (!token) throw new Error('请先登录后再生成图片')
  const upload = await Taro.uploadFile({
    url: `${baseUrl}/api/image-generations`,
    filePath,
    name: 'file',
    formData: { style_id: styleId },
    timeout: 180000,
    header: { Authorization: `Bearer ${token}`, 'X-Product-Key': 'general' },
  })
  let body = upload.data
  if (typeof body === 'string') {
    try { body = JSON.parse(body) } catch { throw new Error('图片服务返回格式异常') }
  }
  if (upload.statusCode < 200 || upload.statusCode >= 300 || body?.code !== 0) {
    throw new Error(body?.message || '图片生成失败，请稍后重试')
  }
  const resultId = body?.data?.resultId
  if (!resultId) throw new Error('图片服务没有返回生成结果')
  const result = await Taro.downloadFile({
    url: `${baseUrl}/api/image-generations/${resultId}/result`,
    header: { Authorization: `Bearer ${token}`, 'X-Product-Key': 'general' },
    timeout: 60000,
  })
  if (result.statusCode < 200 || result.statusCode >= 300 || !result.tempFilePath) {
    throw new Error('生成结果下载失败，请稍后重试')
  }
  return result.tempFilePath
}
