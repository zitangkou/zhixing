import Taro from '@tarojs/taro'
import { isGuestAllowedPath } from '@/constants/guestAccess'
import { askConfirm, askPrompt, pushToast, type ToastIcon } from '@/utils/feedback'
import { ensureFeedbackHost } from '@/utils/feedbackHost'
import { isLoggedIn, requireLogin } from '@/utils/auth'

/** 判断当前运行平台 */
export function getPlatform(): 'weapp' | 'h5' | 'other' {
  const env = Taro.getEnv()
  if (env === Taro.ENV_TYPE.WEAPP) return 'weapp'
  if (env === Taro.ENV_TYPE.WEB) return 'h5'
  return 'other'
}

/** H5 端尝试发送本地通知 */
export function tryNotify(title: string, body: string): void {
  if (getPlatform() !== 'h5') return
  if (typeof Notification === 'undefined') return
  if (Notification.permission === 'granted') {
    new Notification(title, { body })
  } else if (Notification.permission !== 'denied') {
    Notification.requestPermission().then((perm) => {
      if (perm === 'granted') new Notification(title, { body })
    })
  }
}

/** 显示 Toast（主题自适应） */
export function showToast(title: string, icon: ToastIcon = 'none', duration = 2000): void {
  ensureFeedbackHost()
  pushToast(title, icon, duration)
}

/** 确认对话框，返回用户是否点击确定 */
export function showConfirm(
  title: string,
  content: string,
  options?: { confirmText?: string; cancelText?: string },
): Promise<boolean> {
  ensureFeedbackHost()
  return askConfirm(title, content, options)
}

/**
 * 文本输入（主题自适应弹层）。
 * 取消返回 null。
 */
export async function promptText(
  title: string,
  options?: { placeholder?: string; defaultValue?: string },
): Promise<string | null> {
  ensureFeedbackHost()
  return askPrompt(title, options)
}

/** 复制到剪贴板 */
export async function copyText(text: string, successTip = '已复制'): Promise<boolean> {
  const value = (text || '').trim()
  if (!value) {
    showToast('没有可复制内容')
    return false
  }
  try {
    await Taro.setClipboardData({ data: value })
    // 微信端 setClipboardData 自带提示；H5 往往没有，补一条
    if (getPlatform() === 'h5') showToast(successTip, 'success')
    return true
  } catch {
    showToast('复制失败', 'error')
    return false
  }
}

/** 导航封装：绑定账号的功能未登录时先去登录 */
export function navigateTo(url: string): void {
  if (!isGuestAllowedPath(url) && !isLoggedIn()) {
    requireLogin(url)
    return
  }
  Taro.navigateTo({ url })
}

export function switchTab(url: string): void {
  Taro.switchTab({ url })
}
