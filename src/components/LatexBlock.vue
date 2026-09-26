<template>
  <view class="latex-block" :class="[`size-${size}`]">
    <view v-if="html" class="latex-render">
      <!-- eslint-disable-next-line vue/no-v-html, vue/no-v-text-v-html-on-component -->
      <view v-html="html" />
    </view>
    <!-- 小程序：不渲染 KaTeX，公式直接显示可读纯文本（同一文本不再在下方重复） -->
    <text v-else-if="!isH5" class="latex-text">{{ weappText }}</text>
    <text v-else class="latex-fallback">
      {{ fallbackText }}
    </text>
    <text v-if="showPlain && plain && html" class="latex-plain">
      {{ plain }}
    </text>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
// 相对路径导入，Taro 多端文件才生效：weapp 解析到 latex.weapp.ts（不含 KaTeX），H5 用 latex.ts
import { renderLatex } from '../utils/latex'
import { latexToPlain } from '@/utils/latexPlain'

const props = withDefaults(
  defineProps<{
    latex?: string
    plain?: string
    showPlain?: boolean
    size?: 'sm' | 'md' | 'lg'
    displayMode?: boolean
  }>(),
  {
    latex: '',
    plain: '',
    showPlain: true,
    size: 'md',
    displayMode: true,
  },
)

const html = computed(() => renderLatex(props.latex || '', { displayMode: props.displayMode }))
const fallbackText = computed(() => props.plain || props.latex || '')

const isH5 = process.env.TARO_ENV === 'h5'
const weappText = computed(() => (props.plain || '').trim() || latexToPlain(props.latex || ''))
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.latex-block {
  width: 100%;
}
.latex-render {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  /* KaTeX 字形走 currentColor，颜色必须跟主题变量，暗色下否则不可见 */
  color: $text-primary;
}
.latex-fallback {
  display: block;
  font-size: 28rpx;
  color: $text-secondary;
  line-height: 1.5;
}
.latex-plain {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: $text-muted;
  line-height: 1.45;
}
.size-sm .latex-render {
  font-size: 14px;
}
.size-md .latex-render {
  font-size: 17px;
}
.size-lg .latex-render {
  font-size: 20px;
}
/* 小程序纯文本公式 */
.latex-text {
  display: block;
  color: $text-primary;
  font-weight: 500;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.size-sm .latex-text {
  font-size: 14px;
}
.size-md .latex-text {
  font-size: 16px;
}
.size-lg .latex-text {
  font-size: 18px;
}
.latex-render :deep(.katex-display) {
  margin: 0.35em 0;
  overflow-x: auto;
  overflow-y: hidden;
}
</style>
