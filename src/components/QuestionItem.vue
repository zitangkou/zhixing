<template>
  <view class="question-item" :class="{ readonly: readonly }">
    <view class="stem-row">
      <text class="type-tag" :class="question.type">
        {{ typeLabel }}
      </text>
      <text class="stem">
        {{ question.stem }}
      </text>
    </view>

    <view v-if="question.type === 'judge' || question.type === 'single'" class="options">
      <view
        v-for="(opt, idx) in question.options"
        :key="idx"
        class="option"
        :class="optionClass(opt)"
        @tap="selectOption(opt)"
      >
        <text class="opt-label"> {{ String.fromCharCode(65 + idx) }}. </text>
        <text>{{ opt }}</text>
        <text v-if="showResult && isCorrectOpt(opt)" class="result-icon"> ✓ </text>
        <text v-if="showResult && isWrongOpt(opt)" class="result-icon wrong"> ✗ </text>
      </view>
    </view>

    <view v-else-if="question.type === 'multiple' && question.options?.length" class="options">
      <view
        v-for="(opt, idx) in question.options"
        :key="idx"
        class="option"
        :class="multiOptionClass(opt)"
        @tap="toggleMultiOption(opt)"
      >
        <text class="opt-label"> {{ String.fromCharCode(65 + idx) }}. </text>
        <text>{{ opt }}</text>
        <text v-if="showResult && isCorrectOpt(opt)" class="result-icon"> ✓ </text>
        <text v-if="showResult && isWrongMultiOpt(opt)" class="result-icon wrong"> ✗ </text>
      </view>
      <text v-if="!showResult && !readonly && selectedMulti.length" class="multi-hint">
        已选 {{ selectedMulti.length }} 项，点「下一题」提交
      </text>
    </view>

    <view v-if="showResult" class="analysis">
      <text class="analysis-label"> 解析 </text>
      <text>{{ analysisText }}</text>
      <view v-if="sourceText" class="source">
        <text class="source-label"> 原文： </text>
        <text>{{ sourceText }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Question } from '@/types'

const props = defineProps<{
  question: Question
  showResult?: boolean
  analysisText?: string
  selectedAnswer?: string | string[]
  readonly?: boolean
}>()

const emit = defineEmits<{
  answer: [answer: string | string[]]
  change: [answer: string[]]
}>()

const selected = ref<string>('')
const selectedMulti = ref<string[]>([])

const typeLabel = computed(() => {
  const map: Record<string, string> = {
    single: '单选',
    multiple: '多选',
    judge: '判断',
  }
  return map[props.question.type] || '题目'
})

watch(
  () => props.question.id,
  () => {
    if (props.showResult && props.selectedAnswer !== undefined) {
      restoreSelectedAnswer()
    } else {
      selected.value = ''
      selectedMulti.value = []
      emit('change', [])
    }
  },
)

watch(
  () => [props.showResult, props.selectedAnswer] as const,
  () => {
    if (props.showResult && props.selectedAnswer !== undefined) {
      restoreSelectedAnswer()
    }
  },
)

function restoreSelectedAnswer() {
  const ans = props.selectedAnswer
  if (ans === undefined) return
  if (Array.isArray(ans)) {
    selectedMulti.value = [...ans]
    selected.value = ''
  } else {
    selected.value = ans
    selectedMulti.value = []
  }
}

function selectOption(opt: string) {
  if (props.readonly || props.showResult) return
  selected.value = opt
  emit('answer', opt)
}

function toggleMultiOption(opt: string) {
  if (props.readonly || props.showResult) return
  const idx = selectedMulti.value.indexOf(opt)
  if (idx >= 0) {
    selectedMulti.value = selectedMulti.value.filter((o) => o !== opt)
  } else {
    selectedMulti.value = [...selectedMulti.value, opt]
  }
  emit('change', [...selectedMulti.value])
}

function isCorrectOpt(opt: string): boolean {
  const c = props.question.correctAnswer
  return Array.isArray(c) ? c.includes(opt) : c === opt
}

function isWrongOpt(opt: string): boolean {
  if (!props.showResult) return false
  return selected.value === opt && !isCorrectOpt(opt)
}

function isWrongMultiOpt(opt: string): boolean {
  if (!props.showResult) return false
  const picked = selectedMulti.value.includes(opt)
  const correct = isCorrectOpt(opt)
  return (picked && !correct) || (!picked && correct)
}

function optionClass(opt: string) {
  if (!props.showResult) {
    return selected.value === opt ? 'selected' : ''
  }
  if (isCorrectOpt(opt)) return 'correct'
  if (isWrongOpt(opt)) return 'wrong'
  return ''
}

function multiOptionClass(opt: string) {
  if (!props.showResult) {
    return selectedMulti.value.includes(opt) ? 'selected' : ''
  }
  if (isCorrectOpt(opt)) return 'correct'
  if (isWrongMultiOpt(opt)) return 'wrong'
  return ''
}

const analysisText = computed(() => props.analysisText || props.question.analysis)

const sourceText = computed(() => {
  const src = props.question.sourceSentence?.trim()
  if (src && src !== '见原文依据。') return src
  return ''
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.question-item {
  &.readonly .option {
    cursor: default;
  }
  .stem-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 16px;
  }
  .type-tag {
    flex-shrink: 0;
    margin-top: 3px;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 4px;
    background: $elevated;
    color: $text-secondary;
    &.single {
      background: rgba($accent-blue, 0.12);
      color: $accent-blue;
    }
    &.multiple {
      background: $primary-light;
      color: $primary-color;
    }
    &.judge {
      background: rgba($accent-amber, 0.14);
      color: $accent-amber;
    }
  }
  .stem {
    flex: 1;
    font-size: 16px;
    line-height: 1.7;
    font-weight: 500;
  }
  .options {
    .option {
      display: flex;
      align-items: flex-start;
      padding: 12px 14px;
      margin-bottom: 10px;
      background: $elevated;
      border-radius: 8px;
      border: 1px solid $border-color;
      color: $text-primary;
      font-size: 16px;
      line-height: 1.6;
      &.selected {
        border-color: $primary-color;
        background: $primary-light;
      }
      &.correct {
        border-color: var(--zk-success);
        background: rgba(7, 193, 96, 0.16);
      }
      &.wrong {
        border-color: var(--zk-danger);
        background: rgba(238, 10, 36, 0.16);
      }
      .opt-label {
        margin-right: 8px;
        font-weight: 600;
        color: $primary-color;
      }
      .result-icon {
        margin-left: auto;
        color: var(--zk-success);
        font-weight: bold;
        &.wrong {
          color: var(--zk-danger);
        }
      }
    }
    .multi-hint {
      display: block;
      margin-top: 2px;
      font-size: 12px;
      color: $text-muted;
    }
  }
  .analysis {
    margin-top: 16px;
    padding: 14px;
    background: $primary-light;
    border-radius: 8px;
    font-size: 14px;
    line-height: 1.6;
    .analysis-label {
      display: block;
      font-size: 14px;
      font-weight: 600;
      color: $primary-color;
      margin-bottom: 6px;
    }
    .source {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px dashed $border-color;
      .source-label {
        color: $text-muted;
      }
    }
  }
}
</style>
