import { nextTick } from 'vue'

/**
 * 保存前让当前输入失焦，确保中文 IME 组字结果写入 v-model。
 * （nut-input 在 composing 期间不会 emit update:modelValue）
 */
export function flushActiveInput() {
  try {
    if (typeof document === 'undefined') return
    const el = document.activeElement as HTMLElement | null
    el?.blur?.()
  } catch {
    /* ignore */
  }
}

/** flush + 等一帧，供 async onSave 开头调用 */
export async function flushFormBeforeSave() {
  flushActiveInput()
  await nextTick()
}

