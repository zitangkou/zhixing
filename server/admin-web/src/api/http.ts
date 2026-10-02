import axios from 'axios'
import type { ApiRes } from '@/types'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const http = axios.create({
  baseURL: import.meta.env.DEV ? '' : '',
  timeout: 30000,
})

export class ApiRequestError extends Error {
  code?: number
  status?: number
  data: unknown

  constructor(message: string, options: { code?: number; status?: number; data?: unknown } = {}) {
    super(message)
    this.name = 'ApiRequestError'
    this.code = options.code
    this.status = options.status
    this.data = options.data
  }
}

http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => {
    const data = res.data as ApiRes<unknown>
    if (data.code !== 0) {
      return Promise.reject(new ApiRequestError(data.message || '请求失败', {
        code: data.code,
        status: res.status,
        data: data.data,
      }))
    }
    return res
  },
  (err) => {
    if (err.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      router.push('/login')
    }
    const body = err.response?.data as (ApiRes<unknown> & {
      detail?: Array<{ msg?: string; loc?: (string | number)[] }>
    }) | undefined
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((item: { msg?: string; loc?: (string | number)[] }) => `${item.loc?.slice(1).join('.') || '请求'}：${item.msg || '格式无效'}`).join('；')
      : undefined
    return Promise.reject(new ApiRequestError(body?.message || detail || err.message || '网络请求失败', {
      code: body?.code,
      status: err.response?.status,
      data: body?.data,
    }))
  },
)

export default http

export async function getData<T>(promise: Promise<{ data: ApiRes<T> }>): Promise<T> {
  const res = await promise
  return res.data.data
}
