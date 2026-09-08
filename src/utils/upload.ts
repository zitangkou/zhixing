import Taro from '@tarojs/taro'
import { clearToken, getToken } from '@/utils/auth'
import { getPlatform } from '@/utils/platform'
import type { ApiRes } from '@/types'
import { CURRENT_PRODUCT_KEY } from '@/constants/product'

type UploadResult<T> = ApiRes<T>

/**
 * 生成空 data 的错误响应。
 * 类型断言收敛在同步函数里，避免 weapp 构建时 regenerator 对 async 内 TSAsExpression 报错。
 */
function errorResult<T>(code: number, message: string): UploadResult<T> {
  return { code, data: null as unknown as T, message }
}

/** 从任意错误对象提取 errMsg（断言集中于此，同步函数不受 regenerator 影响） */
function errMessage(e: unknown): string {
  return (e as { errMsg?: string })?.errMsg || '上传失败'
}

/**
 * 跨端文件上传：H5 用 FormData+fetch（避免 blob 路径导致 uploadFile 失败），
 * 小程序用 Taro.uploadFile。
 */
export async function uploadFile<T>(
  url: string,
  filePath: string,
  options?: {
    name?: string
    /** H5 chooseImage 返回的原始 File，优先使用 */
    file?: File
  },
): Promise<UploadResult<T>> {
  const field = options?.name || 'file'
  const token = getToken()
  const headers: Record<string, string> = { 'X-Product-Key': CURRENT_PRODUCT_KEY }
  if (token) headers.Authorization = `Bearer ${token}`

  if (getPlatform() === 'h5') {
    try {
      let file = options?.file
      if (!file) {
        const blob = await fetch(filePath).then((r) => r.blob())
        const ext = (blob.type.split('/')[1] || 'jpeg').replace('jpeg', 'jpg')
        file = new File([blob], `upload.${ext}`, { type: blob.type || 'image/jpeg' })
      }
      const form = new FormData()
      form.append(field, file)
      const res = await fetch(url, { method: 'POST', headers, body: form })
      if (res.status === 401) {
        clearToken()
        return errorResult<T>(401, '登录已过期，请重新登录')
      }
      const body: ApiRes<T> = await res.json()
      return body
    } catch (e) {
      return errorResult<T>(-1, e instanceof Error ? e.message : '上传失败')
    }
  }

  return new Promise((resolve) => {
    Taro.uploadFile({
      url,
      filePath,
      name: field,
      header: headers,
      success(res) {
        try {
          const body: ApiRes<T> = JSON.parse(res.data)
          if (res.statusCode === 401) {
            clearToken()
            resolve(errorResult<T>(401, '登录已过期，请重新登录'))
            return
          }
          resolve(body)
        } catch {
          resolve(errorResult<T>(-1, '上传响应解析失败'))
        }
      },
      fail(err) {
        resolve(errorResult<T>(-1, errMessage(err)))
      },
    })
  })
}
