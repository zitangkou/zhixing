/** API 根地址（不含尾斜杠） */
export const API_BASE = typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : 'http://127.0.0.1:8001'

/** 将相对资源路径转为可访问的绝对 URL */
export function resolveMediaUrl(path?: string | null): string {
  if (!path) return ''
  if (/^https?:\/\//i.test(path) || path.startsWith('data:') || path.startsWith('blob:')) {
    return path
  }
  if (path.startsWith('/')) return `${API_BASE}${path}`
  return `${API_BASE}/${path}`
}
