<template>
  <view class="voice-btn-wrap">
    <view class="voice-btn" :class="{ on: listening, busy }" @tap="onTap">
      <text class="icon">
        {{ listening ? '⏹' : '🎙' }}
      </text>
      <text class="label">
        {{ labelText }}
      </text>
    </view>
    <text v-if="preview" class="preview">
      {{ preview }}
    </text>
  </view>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { showToast } from '@/utils/platform'
import {
  appendSpeechText,
  applyHotwords,
  startSmartSpeech,
  type SpeechSession,
} from '@/utils/speechInput'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    mode?: 'append' | 'replace'
    hotwords?: string[]
  }>(),
  {
    modelValue: '',
    mode: 'append',
    hotwords: () => [],
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'result', v: string): void
}>()

const listening = ref(false)
const busy = ref(false)
const preview = ref('')
let session: SpeechSession | null = null
/** 按下语音时字段原文 */
let baseText = ''
/** 本轮已确认的最终识别（相对 base 的增量） */
let sessionFinal = ''

const labelText = computed(() => {
  if (busy.value && !listening.value) return '识别中'
  if (listening.value) return '说完点停'
  return '语音'
})

function buildNext(spoken: string) {
  const cleaned = applyHotwords(spoken, props.hotwords)
  if (!cleaned) return props.modelValue || ''
  if (props.mode === 'replace') return cleaned
  return appendSpeechText(baseText, cleaned)
}

function flush(spoken: string) {
  const cleaned = applyHotwords(spoken, props.hotwords)
  if (!cleaned) return
  const next = buildNext(cleaned)
  emit('update:modelValue', next)
  emit('result', cleaned)
}

async function onTap() {
  if (busy.value && !listening.value) return

  if (listening.value) {
    session?.stop()
    session = null
    return
  }

  baseText = props.modelValue || ''
  sessionFinal = ''
  preview.value = ''
  busy.value = true

  session = await startSmartSpeech({
    onStart: () => {
      listening.value = true
      showToast('请说话，说完再点停止', 'none')
    },
    onInterim: (t) => {
      preview.value = t
    },
    onFinal: (t) => {
      sessionFinal = t
      preview.value = t
      // 边说边落最终句，停止时不再重复提交
      flush(sessionFinal)
    },
    onError: (msg) => {
      showToast(msg, 'error')
    },
    onEnd: () => {
      // 若只有 interim 没有 final（少见），补一次
      if (!sessionFinal && preview.value) flush(preview.value)
      listening.value = false
      busy.value = false
      preview.value = ''
      session = null
      sessionFinal = ''
    },
  })

  if (!session) {
    busy.value = false
  }
}

onBeforeUnmount(() => {
  session?.stop()
  session = null
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.voice-btn-wrap {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  flex-shrink: 0;
}
.voice-btn {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  border-radius: 6px;
  background: $page-bg;
  border: 1px solid $border-color;
  .icon {
    font-size: 12px;
    line-height: 1;
  }
  .label {
    font-size: 11px;
    color: $text-secondary;
    font-weight: 600;
  }
  &.on {
    background: $primary-soft;
    border-color: $primary-soft;
    .label {
      color: $primary-color;
    }
  }
  &.busy:not(.on) .label {
    color: $text-muted;
  }
}
.preview {
  max-width: 160px;
  font-size: 10px;
  color: $text-muted;
  line-height: 1.3;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
