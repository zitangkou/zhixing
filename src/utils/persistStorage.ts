import Taro from '@tarojs/taro'

const isH5 = process.env.TARO_ENV === 'h5'

/** 把 Taro / 双重 JSON 编码收成 Pinia 要的字符串 */
export function unwrapToJsonString(value: unknown): string | null {
  if (value === '' || value === undefined || value === null) return null
  if (typeof value === 'object') return JSON.stringify(value)
  if (typeof value !== 'string') return JSON.stringify(value)
  try {
    let parsed: unknown = JSON.parse(value)
    while (typeof parsed === 'string') parsed = JSON.parse(parsed)
    if (parsed && typeof parsed === 'object') return JSON.stringify(parsed)
  } catch {
    return value
  }
  return value
}

export function readPersistJson(key: string): Record<string, unknown> | null {
  try {
    const raw = unwrapToJsonString(piniaPersistStorage.getItem(key))
    if (!raw) return null
    const data = JSON.parse(raw)
    return data && typeof data === 'object' ? (data as Record<string, unknown>) : null
  } catch {
    return null
  }
}

/** H5 直写 localStorage，避免 Taro 再 JSON.stringify 一层导致 Pinia 水合失败 */
export const piniaPersistStorage = {
  getItem(key: string): string | null {
    if (isH5 && typeof localStorage !== 'undefined') {
      const fromLs = unwrapToJsonString(localStorage.getItem(key))
      if (fromLs) return fromLs
    }
    try {
      return unwrapToJsonString(Taro.getStorageSync(key))
    } catch {
      return null
    }
  },
  setItem(key: string, value: string) {
    if (isH5 && typeof localStorage !== 'undefined') {
      localStorage.setItem(key, value)
    }
    try {
      Taro.setStorageSync(key, value)
    } catch {
      /* ignore */
    }
  },
}
