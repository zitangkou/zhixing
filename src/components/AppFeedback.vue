<template>
  <!-- Toast：用 div，保证独立 createApp 挂载时也能渲染 -->
  <div
    v-if="toast.visible"
    :key="toast.key"
    class="zk-toast"
    :class="[`zk-toast--${toast.icon}`]"
    @click="dismissToast"
    @tap="dismissToast"
  >
    <div v-if="toast.icon !== 'none'" class="zk-toast__icon" :class="`is-${toast.icon}`">
      <span>{{ toast.icon === 'success' ? '✓' : '!' }}</span>
    </div>
    <div class="zk-toast__text">
      {{ toast.title }}
    </div>
  </div>

  <!-- Dialog / Prompt -->
  <div v-if="dialog.visible" class="zk-mask" @click="onMask" @tap="onMask">
    <div class="zk-dialog" @click.stop @tap.stop>
      <div v-if="dialog.title" class="zk-dialog__title">
        {{ dialog.title }}
      </div>
      <div v-if="dialog.mode === 'confirm' && dialog.content" class="zk-dialog__content">
        {{ dialog.content }}
      </div>
      <div v-if="dialog.mode === 'prompt'" class="zk-dialog__field">
        <input
          class="zk-dialog__input"
          :value="dialog.inputValue"
          :placeholder="dialog.placeholder || '请输入'"
          autofocus
          @input="onInput"
          @confirm="onConfirm"
          @keyup.enter="onConfirm"
        />
      </div>
      <div class="zk-dialog__actions">
        <button
          type="button"
          class="zk-dialog__btn zk-dialog__btn--cancel"
          @click.stop.prevent="onCancel"
          @tap.stop.prevent="onCancel"
        >
          {{ dialog.cancelText }}
        </button>
        <button
          type="button"
          class="zk-dialog__btn zk-dialog__btn--ok"
          @click.stop.prevent="onConfirm"
          @tap.stop.prevent="onConfirm"
        >
          {{ dialog.confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { feedbackState, hideToast, resolveDialog } from '@/utils/feedback'

const toast = computed(() => feedbackState.toast)
const dialog = computed(() => feedbackState.dialog)

function dismissToast() {
  hideToast()
}

onMounted(() => {
  feedbackState.rendererCount += 1
  feedbackState.hostReady = true
})
onUnmounted(() => {
  feedbackState.rendererCount = Math.max(0, feedbackState.rendererCount - 1)
})

function onInput(e: Event | { detail?: { value?: string } }) {
  const detailVal = (e as { detail?: { value?: string } }).detail?.value
  if (typeof detailVal === 'string') {
    feedbackState.dialog.inputValue = detailVal
    return
  }
  const target = (e as Event).target as HTMLInputElement | null
  feedbackState.dialog.inputValue = target?.value ?? ''
}

function finish(ok: boolean) {
  if (!feedbackState.dialog.visible || !feedbackState.dialog.resolve) return
  resolveDialog(ok)
}

function onCancel() {
  finish(false)
}

function onConfirm() {
  finish(true)
}

function onMask(e?: Event) {
  // 仅点击遮罩空白处取消；点到对话框内部用 stop 阻断
  const t = (e?.target || null) as HTMLElement | null
  const current = (e?.currentTarget || null) as HTMLElement | null
  if (t && current && t !== current) return
  finish(false)
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.zk-toast {
  position: fixed;
  left: 50%;
  top: auto;
  bottom: calc(88px + env(safe-area-inset-bottom, 0px));
  transform: translateX(-50%);
  z-index: 10050;
  max-width: min(78vw, 280px);
  min-width: 120px;
  padding: 14px 18px;
  border-radius: 14px;
  background: var(--zk-card-bg);
  color: var(--zk-text-primary);
  box-shadow:
    var(--zk-shadow-float),
    0 0 0 1px var(--zk-border-color);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  pointer-events: auto;
  cursor: pointer;
  animation: zk-toast-in 0.22s ease;
}

.zk-toast__icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  &.is-success {
    background: var(--zk-success);
  }
  &.is-error {
    background: var(--zk-danger);
  }
}

.zk-toast__text {
  font-size: 14px;
  line-height: 1.45;
  text-align: center;
  color: var(--zk-text-primary);
  word-break: break-word;
}

.zk-toast--none {
  padding: 12px 16px;
  .zk-toast__text {
    font-size: 13px;
  }
}

@keyframes zk-toast-in {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(8px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0) scale(1);
  }
}

.zk-mask {
  position: fixed;
  inset: 0;
  z-index: 10040;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
  pointer-events: auto;
  animation: zk-mask-in 0.18s ease;
}

html.theme-dark .zk-mask,
.theme-dark .zk-mask {
  background: rgba(0, 0, 0, 0.62);
}

@keyframes zk-mask-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.zk-dialog {
  width: min(86vw, 320px);
  background: var(--zk-card-bg);
  color: var(--zk-text-primary);
  border-radius: 16px;
  box-shadow: var(--zk-shadow-float);
  border: 1px solid var(--zk-border-color);
  overflow: hidden;
  pointer-events: auto;
  animation: zk-dialog-in 0.22s ease;
}

@keyframes zk-dialog-in {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.zk-dialog__title {
  display: block;
  padding: 20px 20px 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--zk-text-primary);
  text-align: center;
  line-height: 1.35;
}

.zk-dialog__content {
  display: block;
  padding: 12px 20px 4px;
  font-size: 14px;
  line-height: 1.55;
  color: var(--zk-text-secondary);
  text-align: center;
  white-space: pre-wrap;
  word-break: break-word;
}

.zk-dialog__field {
  padding: 14px 20px 4px;
}

.zk-dialog__input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  font-size: 15px;
  color: var(--zk-text-primary);
  background: var(--zk-input-bg);
  border: 1px solid var(--zk-border-color);
  border-radius: 10px;
  outline: none;
  &:focus,
  &:focus-visible {
    border-color: var(--zk-primary);
    box-shadow: 0 0 0 2px var(--zk-primary-light);
  }
}

.zk-dialog__actions {
  display: flex;
  margin-top: 16px;
  border-top: 1px solid var(--zk-border-color);
}

.zk-dialog__btn {
  flex: 1;
  height: 48px;
  margin: 0;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  line-height: 1;
  color: var(--zk-text-secondary);
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  pointer-events: auto;
  &:active {
    background: var(--zk-hover-bg);
  }
  &--ok {
    border-left: 1px solid var(--zk-border-color);
    color: var(--zk-primary);
    font-weight: 600;
  }
}
</style>
