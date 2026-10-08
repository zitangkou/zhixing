import Taro from '@tarojs/taro'

export function showToast(title: string, icon: 'none' | 'success' | 'error' = 'none') {
  return Taro.showToast({ title, icon, duration: 2000 })
}

export async function showConfirm(title: string, content: string): Promise<boolean> {
  try {
    const result = await Taro.showModal({ title, content, confirmText: '确定', cancelText: '取消' })
    return result.confirm
  } catch {
    return false
  }
}
