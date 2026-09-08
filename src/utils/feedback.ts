/**
 * 全局反馈层状态（Toast / 确认框 / 输入框）。
 * UI 由 AppFeedback 渲染，样式走主题 CSS 变量。
 */
import { reactive } from 'vue'
import Taro from '@tarojs/taro'
import { brandPrimary } from '@/constants/theme'

export type ToastIcon = 'success' | 'error' | 'none'

export interface ToastState {
  visible: boolean
  title: string
  icon: ToastIcon
  duration: number
  key: number
}

export interface DialogState {
  visible: boolean
  mode: 'confirm' | 'prompt'
  title: string
  content: string
  placeholder: string
  defaultValue: string
  confirmText: string
  cancelText: string
  inputValue: string
  resolve: ((value: boolean | string | null) => void) | null
}

export const feedbackState = reactive({
  toast: {
    visible: false,
    title: '',
    icon: 'none' as ToastIcon,
    duration: 2000,
    key: 0,
  } as ToastState,
  dialog: {
    visible: false,
    mode: 'confirm' as 'confirm' | 'prompt',
    title: '',
    content: '',
    placeholder: '',
    defaultValue: '',
    confirmText: '确定',
    cancelText: '取消',
    inputValue: '',
    resolve: null as DialogState['resolve'],
  },
  hostReady: false,
  /** 当前页面树里挂着的 AppFeedback 实例数（小程序用） */
  rendererCount: 0,
})

function themeConfirmColor(): string {
  try {
    const raw = Taro.getStorageSync('settings')
    const data = typeof raw === 'string' ? JSON.parse(raw || '{}') : raw
    return brandPrimary(!!data?.darkMode, data?.brandTheme)
  } catch {
    return brandPrimary(false)
  }
}

function hasRenderer(): boolean {
  // H5 由 body 宿主承接；小程序需页面内有 <AppFeedback />
  if (process.env.TARO_ENV === 'h5')
    return feedbackState.hostReady || feedbackState.rendererCount > 0
  return feedbackState.rendererCount > 0
}

let toastTimer: ReturnType<typeof setTimeout> | null = null
let hostEnsure: (() => void) | null = null

/** 由 AppFeedback / ensureFeedbackHost 注册，保证调用时宿主已挂载 */
export function registerFeedbackHostEnsure(fn: () => void) {
  hostEnsure = fn
}

export function ensureFeedbackHost() {
  hostEnsure?.()
}

export function pushToast(title: string, icon: ToastIcon = 'none', duration = 2000) {
  ensureFeedbackHost()
  if (!hasRenderer()) {
    Taro.showToast({
      title: String(title || '').slice(0, 40),
      icon: icon === 'error' ? 'error' : icon,
      duration,
    })
    return
  }
  if (toastTimer) {
    clearTimeout(toastTimer)
    toastTimer = null
  }
  feedbackState.toast.visible = false
  // 下一帧再开，便于重复触发时重启动画
  const show = () => {
    feedbackState.toast = {
      visible: true,
      title: String(title || '').slice(0, 40),
      icon,
      duration,
      key: Date.now(),
    }
    toastTimer = setTimeout(() => {
      feedbackState.toast.visible = false
      toastTimer = null
    }, duration)
  }
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(show)
  else setTimeout(show, 16)
}

export function hideToast() {
  if (toastTimer) {
    clearTimeout(toastTimer)
    toastTimer = null
  }
  feedbackState.toast.visible = false
}

function openDialog(partial: Partial<DialogState> & { mode: 'confirm' | 'prompt' }) {
  ensureFeedbackHost()
  if (!hasRenderer()) {
    return new Promise<boolean | string | null>((resolve) => {
      Taro.showModal({
        title: partial.title || '',
        content: partial.mode === 'prompt' ? partial.defaultValue || '' : partial.content || '',
        editable: partial.mode === 'prompt',
        placeholderText: partial.placeholder || '',
        confirmText: partial.confirmText || '确定',
        cancelText: partial.cancelText || '取消',
        confirmColor: themeConfirmColor(),
        success: (res) => {
          if (partial.mode === 'prompt') {
            resolve(res.confirm ? (res.content ?? '') : null)
          } else {
            resolve(!!res.confirm)
          }
        },
        fail: () => resolve(partial.mode === 'prompt' ? null : false),
      })
    })
  }
  return new Promise<boolean | string | null>((resolve) => {
    // 若已有弹窗，先以取消结束
    if (feedbackState.dialog.visible && feedbackState.dialog.resolve) {
      feedbackState.dialog.resolve(partial.mode === 'prompt' ? null : false)
    }
    feedbackState.dialog = {
      visible: true,
      mode: partial.mode,
      title: partial.title || '',
      content: partial.content || '',
      placeholder: partial.placeholder || '',
      defaultValue: partial.defaultValue || '',
      confirmText: partial.confirmText || '确定',
      cancelText: partial.cancelText || '取消',
      inputValue: partial.defaultValue || '',
      resolve,
    }
  })
}

export function askConfirm(
  title: string,
  content: string,
  options?: { confirmText?: string; cancelText?: string },
): Promise<boolean> {
  return openDialog({
    mode: 'confirm',
    title,
    content,
    confirmText: options?.confirmText,
    cancelText: options?.cancelText,
  }) as Promise<boolean>
}

export function askPrompt(
  title: string,
  options?: {
    placeholder?: string
    defaultValue?: string
    confirmText?: string
    cancelText?: string
  },
): Promise<string | null> {
  return openDialog({
    mode: 'prompt',
    title,
    placeholder: options?.placeholder,
    defaultValue: options?.defaultValue,
    confirmText: options?.confirmText,
    cancelText: options?.cancelText,
  }) as Promise<string | null>
}

export function resolveDialog(ok: boolean) {
  const d = feedbackState.dialog
  const resolve = d.resolve
  const mode = d.mode
  const inputValue = d.inputValue
  if (!resolve) {
    d.visible = false
    return
  }
  d.visible = false
  d.resolve = null
  if (mode === 'prompt') {
    resolve(ok ? inputValue : null)
  } else {
    resolve(ok)
  }
}
