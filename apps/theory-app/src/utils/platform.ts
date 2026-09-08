import Taro from '@tarojs/taro'

export type ToastIcon = 'success' | 'error' | 'loading' | 'none'

export function getPlatform(): 'weapp' | 'h5' | 'other' {
  const env = Taro.getEnv()
  if (env === Taro.ENV_TYPE.WEAPP) return 'weapp'
  if (env === Taro.ENV_TYPE.WEB) return 'h5'
  return 'other'
}
export function showToast(title: string, icon: ToastIcon = 'none', duration = 2200) {
  return Taro.showToast({ title, icon, duration })
}

export async function showConfirm(title: string, content?: string): Promise<boolean> {
  const result = await Taro.showModal({
    title: content === undefined ? '请确认' : title,
    content: content ?? title,
    confirmColor: '#D0021B',
  })
  return result.confirm
}

export async function promptText(
  title: string,
  options?: { placeholder?: string; defaultValue?: string },
): Promise<string | null> {
  if (getPlatform() === 'h5' && typeof window !== 'undefined') {
    return window.prompt(title, options?.defaultValue || '')
  }
  const modalOptions: any = {
    title,
    editable: true,
    placeholderText: options?.placeholder,
    content: options?.defaultValue || '',
    confirmColor: '#D0021B',
  }
  const result: any = await Taro.showModal(modalOptions)
  return result.confirm ? String(result.content || '') : null
}

export async function copyText(text: string, successTip = '已复制'): Promise<boolean> {
  const value = (text || '').trim()
  if (!value) {
    showToast('没有可复制内容')
    return false
  }
  try {
    await Taro.setClipboardData({ data: value })
    if (getPlatform() === 'h5') showToast(successTip, 'success')
    return true
  } catch {
    showToast('复制失败', 'error')
    return false
  }
}
