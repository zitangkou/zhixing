<template>
  <picker
    mode="selector"
    :range="labels"
    :value="safeIndex"
    :disabled="disabled"
    @change="onPickerChange"
  >
    <view
      :id="domId"
      class="wheel-picker"
      :class="{ disabled }"
      :title="hint"
      @wheel.stop.prevent="onWheel"
    >
      <slot />
    </view>
  </picker>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 选项列表（字符串） */
    range: string[]
    /** 当前选中下标 */
    value?: number
    disabled?: boolean
    /** 滚轮是否循环（到头再滚回到另一端） */
    loop?: boolean
  }>(),
  {
    value: 0,
    disabled: false,
    loop: true,
  },
)

const emit = defineEmits<{
  change: [e: { detail: { value: number } }]
}>()

const domId = `wp-${Math.random().toString(36).slice(2, 9)}`

const labels = computed(() => props.range || [])
const safeIndex = computed(() => {
  const n = labels.value.length
  if (!n) return 0
  const v = Number(props.value) || 0
  return Math.min(Math.max(0, v), n - 1)
})

const hint = computed(() => (labels.value.length > 1 ? '点击选择 · 电脑端可滚轮切换' : ''))

let lastAt = 0
const THROTTLE_MS = 90
let nativeEl: HTMLElement | null = null

function emitIndex(index: number) {
  emit('change', { detail: { value: index } })
}

function onPickerChange(e: { detail?: { value?: string | number } }) {
  emitIndex(Number(e?.detail?.value ?? 0))
}

function stepByDelta(delta: number) {
  if (props.disabled) return
  const n = labels.value.length
  if (n <= 1 || !delta) return

  const now = Date.now()
  if (now - lastAt < THROTTLE_MS) return
  lastAt = now

  const dir = delta > 0 ? 1 : -1
  let next = safeIndex.value + dir
  if (props.loop) {
    next = ((next % n) + n) % n
  } else {
    next = Math.min(n - 1, Math.max(0, next))
  }
  if (next === safeIndex.value) return
  emitIndex(next)
}

function onWheel(e: WheelEvent) {
  stepByDelta(e.deltaY || e.deltaX)
}

function nativeWheel(e: Event) {
  const we = e as WheelEvent
  we.preventDefault()
  we.stopPropagation()
  stepByDelta(we.deltaY || we.deltaX)
}

onMounted(() => {
  if (typeof document === 'undefined') return
  nativeEl = document.getElementById(domId)
  nativeEl?.addEventListener('wheel', nativeWheel, { passive: false })
})

onUnmounted(() => {
  nativeEl?.removeEventListener('wheel', nativeWheel)
  nativeEl = null
})
</script>

<style lang="scss" scoped>
.wheel-picker {
  display: block;
  cursor: pointer;
  user-select: none;
  &.disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }
}
</style>
