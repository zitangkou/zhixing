<template>
  <view v-if="visible" class="corpus-capture" :style="barStyle">
    <view class="preview">
      <text class="preview-label"> 已选 </text>
      <text class="preview-text">
        {{ preview }}
      </text>
    </view>
    <view class="actions">
      <view class="btn ghost" @tap="clear"> 取消 </view>
      <view class="btn primary" @tap="capture"> 记入语料 </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { buildCorpusEditUrl, guessCorpusKind } from '@/utils/corpus'
import { showToast } from '@/utils/platform'

const props = withDefaults(
  defineProps<{
    sourceType?: string
    sourceTitle?: string
    /** 固定在底部时，给页面 footer 留出的额外偏移（px） */
    bottomOffset?: number
  }>(),
  {
    sourceType: '其他',
    sourceTitle: '',
    bottomOffset: 0,
  },
)

const selected = ref('')
const visible = computed(() => selected.value.length > 0)

const preview = computed(() => {
  const t = selected.value
  return t.length > 36 ? `${t.slice(0, 36)}…` : t
})

const barStyle = computed(() => ({
  bottom: `${12 + (props.bottomOffset || 0)}px`,
}))

function readSelection(): string {
  try {
    if (typeof window === 'undefined' || !window.getSelection) return ''
    return (window.getSelection()?.toString() || '').trim()
  } catch {
    return ''
  }
}

function onSelectionChange() {
  const text = readSelection()
  if (!text) return
  // 过长多半是误选整段，忽略
  if (text.length > 200) {
    showToast('选区过长，请缩短后再记')
    return
  }
  selected.value = text
}

function clear() {
  selected.value = ''
  try {
    window.getSelection()?.removeAllRanges()
  } catch {
    /* ignore */
  }
}

function capture() {
  const text = selected.value.trim()
  if (!text) {
    showToast('请先选中文字')
    return
  }
  const url = buildCorpusEditUrl({
    original: text,
    kind: guessCorpusKind(text),
    sourceType: props.sourceType || '其他',
    sourceTitle: props.sourceTitle || '',
  })
  clear()
  Taro.navigateTo({ url })
}

onMounted(() => {
  if (typeof document === 'undefined') return
  document.addEventListener('selectionchange', onSelectionChange)
})

onUnmounted(() => {
  if (typeof document === 'undefined') return
  document.removeEventListener('selectionchange', onSelectionChange)
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.corpus-capture {
  position: fixed;
  left: 12px;
  right: 12px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 14px;
  border-radius: $radius-lg;
  background: $card-bg;
  border: 1px solid $border-color;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.12);
}

.preview {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
  .preview-label {
    flex-shrink: 0;
    font-size: 11px;
    font-weight: 600;
    color: $primary-color;
    background: $primary-light;
    padding: 2px 6px;
    border-radius: 4px;
    margin-top: 1px;
  }
  .preview-text {
    flex: 1;
    min-width: 0;
    font-size: 14px;
    line-height: 1.4;
    color: $text-primary;
    word-break: break-all;
  }
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  &.ghost {
    color: $text-muted;
    background: $page-bg;
  }
  &.primary {
    color: $on-primary;
    background: $primary-color;
  }
  &:active {
    opacity: 0.88;
  }
}

html.theme-dark .corpus-capture {
  box-shadow: none;
}
</style>

