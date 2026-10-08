import Taro from '@tarojs/taro'

export interface ApiResponse<T> {
  code: number
  data: T
  message: string
}

export interface LibraryDocument {
  id: string
  fileName: string
  title: string
  category: string
  description: string
  format: string
  contentType: string
  fileSize: number
  sha256: string
  extractionStatus: 'ready' | 'truncated' | 'needs_ocr' | string
  extractionError: string
  isPublished: boolean
  createdAt: string
  extractedText?: string
}

const API_BASE = (process.env.TARO_APP_API_BASE_URL || '').replace(/\/$/, '')
const PRODUCT_KEY = 'zhiku'

function apiUrl(path: string): string {
  if (!API_BASE) throw new Error('请先配置知库服务地址')
  return `${API_BASE}${path}`
}

function request<T>(path: string, method: 'GET' | 'POST' | 'PATCH' | 'DELETE', data?: unknown) {
  return Taro.request<ApiResponse<T>>({
    url: apiUrl(path),
    method,
    data,
    header: {
      'X-Product-Key': PRODUCT_KEY,
      Authorization: `Bearer ${Taro.getStorageSync('zhiku_token') || ''}`,
    },
  }).then((response) => {
    const body = response.data
    if (response.statusCode === 401) {
      Taro.removeStorageSync('zhiku_token')
      throw new Error('请先登录')
    }
    if (response.statusCode >= 400 || body.code !== 0) throw new Error(body.message || '请求失败')
    return body.data
  })
}

export const libraryApi = {
  listCatalog(q = '') {
    const query = q ? `?q=${encodeURIComponent(q)}` : ''
    return request<LibraryDocument[]>(`/api/library/catalog${query}`, 'GET')
  },
  getCatalogDocument(id: string) {
    return request<LibraryDocument>(`/api/library/catalog/${encodeURIComponent(id)}`, 'GET')
  },
  listMyDocuments() {
    return request<LibraryDocument[]>('/api/library/documents', 'GET')
  },
  getMyDocument(id: string) {
    return request<LibraryDocument>(`/api/library/documents/${encodeURIComponent(id)}`, 'GET')
  },
  deleteMyDocument(id: string) {
    return request<{ id: string; deleted: boolean }>(`/api/library/documents/${encodeURIComponent(id)}`, 'DELETE')
  },
  uploadMyDocument(filePath: string, fileName: string) {
    const token = Taro.getStorageSync('zhiku_token') || ''
    return Taro.uploadFile<ApiResponse<LibraryDocument>>({
      url: apiUrl('/api/library/documents'),
      filePath,
      name: 'file',
      header: { 'X-Product-Key': PRODUCT_KEY, Authorization: `Bearer ${token}` },
    }).then((response) => {
      const body = typeof response.data === 'string' ? JSON.parse(response.data) : response.data
      if (response.statusCode === 401) {
        Taro.removeStorageSync('zhiku_token')
        throw new Error('请先登录')
      }
      if (response.statusCode >= 400 || body.code !== 0) throw new Error(body.message || `${fileName} 上传失败`)
      return body.data as LibraryDocument
    })
  },
}

export const authApi = {
  wechatLogin(code: string) {
    return request<{ access_token: string; user: { nickname?: string; username?: string } }>(
      '/api/auth/wechat/login',
      'POST',
      { code },
    )
  },
}
