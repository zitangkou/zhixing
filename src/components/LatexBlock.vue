<template>
  <view class="latex-block" :class="[`size-${size}`]">
    <view v-if="nodes.length" class="latex-render">
      <rich-text :nodes="nodes" :selectable="true" />
    </view>
    <view v-else-if="html" class="latex-render">
      <!-- eslint-disable-next-line vue/no-v-html, vue/no-v-text-v-html-on-component -->
      <view v-html="html" />
    </view>
    <text v-else class="latex-fallback">
      {{ fallbackText }}
    </text>
    <text v-if="showPlain && plain && (html || nodes.length)" class="latex-plain">
      {{ plain }}
    </text>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useBrandColor } from '@/utils/brandColor'
import { normalizeLatex } from '@/utils/mathText'
import { themeTextColor } from '@/utils/theme'
import { renderFormula } from '@/utils/formulaRenderer'
import type { FormulaNode } from '@/utils/latexMini'

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

const html = ref('')
const nodes = ref<FormulaNode[]>([])
const { darkMode } = useBrandColor()
// 与主题正文 token 一致；SVG 图片不能继承 CSS currentColor。
const formulaColor = computed(() => themeTextColor(!!darkMode.value))
watch(
  () => [props.latex, props.displayMode, formulaColor.value],
  () => {
    html.value = ''
    nodes.value = []
    const source = normalizeLatex(props.latex || '')
    if (!source) return
    try {
      const rendered = renderFormula(source, props.displayMode, formulaColor.value)
      html.value = rendered.html
      nodes.value = rendered.nodes
    } catch {
      // 不支持或不合法的公式保留可读式，避免整页中断。
    }
  },
  { immediate: true },
)
const fallbackText = computed(() => props.plain || props.latex || '')
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
  font-size: 14px;
  color: $text-secondary;
  line-height: 1.5;
}
.latex-plain {
  display: block;
  margin-top: 6px;
  font-size: 12px;
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
.latex-render :deep(.katex-display) {
  margin: 0.35em 0;
  overflow-x: auto;
  overflow-y: hidden;
}
</style>
