<template>
  <view class="page-taking" v-if="started" :class="themeClass">
    <view class="top-bar">
      <view class="timer" :class="{ urgent: remainSec < 300 }">
        <text class="timer-icon">⏱</text>
        <text class="timer-text">{{ formatRemain }}</text>
      </view>
      <text class="progress">{{ currentIndex + 1 }} / {{ questions.length }}</text>
      <text class="nav-btn" @tap="showGrid = !showGrid">题号</text>
    </view>

    <view v-if="showGrid" class="grid-panel">
      <view class="grid">
        <view
          v-for="(q, idx) in questions"
          :key="q.id"
          class="grid-cell"
          :class="{ answered: isAnswered(q), marked: q.marked, current: idx === currentIndex }"
          @tap="jumpTo(idx)"
        >{{ idx + 1 }}</view>
      </view>
      <view class="grid-legend">
        <text class="legend-item"><view class="dot answered" />已答</text>
        <text class="legend-item"><view class="dot marked" />标记</text>
        <text class="legend-item"><view class="dot current" />当前</text>
      </view>
      <nut-button type="primary" block class="primary-btn submit-btn" @click="confirmSubmit">交卷</nut-button>
    </view>

    <view v-else class="question-panel">
      <view v-if="currentQ.material" class="material">
        <text class="material-label">材料</text>
        <text class="material-text">{{ currentQ.material }}</text>
      </view>

      <view class="stem-block">
        <text class="stem-tag">{{ typeLabel(currentQ.type) }} · {{ currentQ.section }} · 第{{ currentQ.sortOrder }}题</text>
        <text class="stem">{{ currentQ.stem }}</text>
      </view>

      <view class="options">
        <view
          v-for="(opt, i) in currentQ.options"
          :key="i"
          class="option"
          :class="{ selected: isSelected(opt) }"
          @tap="onSelect(opt)"
        >
          <text class="option-letter">{{ letter(i) }}</text>
          <text class="option-text">{{ opt }}</text>
        </view>
      </view>

      <view class="q-actions">
        <text class="q-action" @tap="toggleMark">{{ currentQ.marked ? '取消标记' : '标记存疑' }}</text>
      </view>

      <view class="nav-buttons">
        <nut-button plain type="primary" :disabled="currentIndex === 0" @click="goPrev">上一题</nut-button>
        <nut-button v-if="currentIndex < questions.length - 1" type="primary" @click="goNext">下一题</nut-button>
        <nut-button v-else type="primary" @click="confirmSubmit">交卷</nut-button>
      </view>
    </view>
  </view>
  <view v-else class="loading" :class="themeClass">加载中...</view>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import { api } from '@/api'
import { showConfirm, showToast } from '@/utils/platform'
import type { ExamTakingQuestion } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '答题中' })

const { themeClass } = useThemeClass()
const router = useRouter()
const paperId = ref(router.params?.paperId || '')
const started = ref(false)
const attemptId = ref('')
const timeLimitMin = ref(120)
const startedAt = ref(0)
const questions = ref<ExamTakingQuestion[]>([])
const currentIndex = ref(0)
const showGrid = ref(false)
const submitting = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const remainSec = ref(0)

const currentQ = computed(() => questions.value[currentIndex.value])

const formatRemain = computed(() => {
  const s = Math.max(0, remainSec.value)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`
})

function letter(i: number) {
  return String.fromCharCode(65 + i)
}

function typeLabel(type?: string) {
  const map: Record<string, string> = {
    single: '单选',
    multiple: '多选',
    judge: '判断',
  }
  return map[type || ''] || '题目'
}

function isAnswered(q: ExamTakingQuestion) {
  if (Array.isArray(q.myAnswer)) return q.myAnswer.length > 0
  return !!q.myAnswer
}

function isSelected(opt: string) {
  const a = currentQ.value.myAnswer
  if (Array.isArray(a)) return a.includes(opt)
  return a === opt
}

function onSelect(opt: string) {
  const q = currentQ.value
  if (q.type === 'multiple') {
    let cur = Array.isArray(q.myAnswer) ? [...q.myAnswer] : []
    if (cur.includes(opt)) {
      cur = cur.filter((x) => x !== opt)
    } else {
      cur.push(opt)
    }
    q.myAnswer = cur
  } else {
    q.myAnswer = opt
  }
  submitCurrent()
}

async function submitCurrent() {
  const q = currentQ.value
  await api.submitExamAnswer(attemptId.value, {
    questionId: q.id,
    answer: q.myAnswer,
    marked: q.marked,
    timeUsedSec: 0,
  })
}

function toggleMark() {
  currentQ.value.marked = !currentQ.value.marked
  submitCurrent()
}

function jumpTo(idx: number) {
  currentIndex.value = idx
  showGrid.value = false
}

function goPrev() {
  if (currentIndex.value > 0) currentIndex.value--
}

function goNext() {
  if (currentIndex.value < questions.value.length - 1) currentIndex.value++
}

async function confirmSubmit() {
  const answered = questions.value.filter(isAnswered).length
  const marked = questions.value.filter((q) => q.marked).length
  const ok = await showConfirm(
    '交卷确认',
    `已答 ${answered} / ${questions.value.length}，标记 ${marked}，确定交卷？`,
  )
  if (!ok) return
  submitting.value = true
  const res = await api.submitExam(attemptId.value)
  submitting.value = false
  if (res.code !== 0 || !res.data) {
    showToast(res.message || '交卷失败', 'error')
    return
  }
  // 跳到结果页
  Taro.redirectTo({ url: `/pages/exam/result?attemptId=${attemptId.value}` })
}

function tick() {
  const nowSec = Math.floor(Date.now() / 1000)
  const elapsed = nowSec - Math.floor(startedAt.value / 1000)
  remainSec.value = timeLimitMin.value * 60 - elapsed
  if (remainSec.value <= 0) {
    if (timer) clearInterval(timer)
    showToast('时间到，自动交卷', 'none')
    confirmSubmit()
  }
}

onMounted(async () => {
  const res = await api.startExam(paperId.value)
  if (res.code !== 0 || !res.data) {
    showToast(res.message || '开考失败', 'error')
    setTimeout(() => Taro.navigateBack(), 1500)
    return
  }
  attemptId.value = res.data.attemptId
  timeLimitMin.value = res.data.timeLimitMin
  questions.value = res.data.questions.map((q) => ({ ...q, myAnswer: q.myAnswer || (q.type === 'multiple' ? [] : '') }))
  startedAt.value = new Date(res.data.startedAt).getTime() || Date.now()
  started.value = true
  remainSec.value = timeLimitMin.value * 60
  timer = setInterval(tick, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-taking {
  min-height: 100vh;
  background: $page-bg;
}

.loading {
  text-align: center;
  padding: 40px 0;
  color: $text-muted;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: $card-bg;
  border-bottom: 1px solid $border-color;
  .timer {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 16px;
    font-weight: 700;
    color: $primary-color;
    &.urgent { color: $danger; animation: pulse 1s infinite; }
  }
  .progress { font-size: 13px; color: $text-secondary; }
  .nav-btn {
    @include hit-target(44px);
    font-size: 12px;
    color: $primary-color;
    padding: 0 10px;
    border: 1px solid $primary-soft;
    border-radius: 8px;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.grid-panel {
  background: $card-bg;
  padding: 16px;
  .grid {
    display: grid;
    grid-template-columns: repeat(8, 1fr);
    gap: 8px;
  }
  .grid-cell {
    @include hit-target(44px);
    aspect-ratio: 1;
    font-size: 13px;
    border-radius: 6px;
    background: $page-bg;
    color: $text-secondary;
    &.answered { background: $primary-soft; color: $primary-color; font-weight: 600; }
    &.marked { border: 2px solid $accent-amber; }
    &.current { background: $primary-color; color: $on-primary; }
  }
  .grid-legend {
    display: flex;
    gap: 14px;
    margin: 14px 0;
    font-size: 11px;
    color: $text-muted;
    .legend-item { display: flex; align-items: center; gap: 4px; }
    .dot { width: 10px; height: 10px; border-radius: 2px; background: $page-bg; &.answered { background: $primary-soft; } &.marked { border: 2px solid $accent-amber; } &.current { background: $primary-color; } }
  }
  .submit-btn { margin-top: 10px; }
}

.question-panel {
  padding: 12px 16px 100px;
}

.material {
  background: rgba($accent-blue, 0.06);
  border-left: 3px solid $accent-blue;
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 14px;
  .material-label { display: block; font-size: 11px; color: $accent-blue; font-weight: 600; margin-bottom: 6px; }
  .material-text { display: block; font-size: 13px; color: $text-primary; line-height: 1.6; white-space: pre-wrap; }
}

.stem-block {
  margin-bottom: 16px;
  .stem-tag { display: block; font-size: 11px; color: $text-muted; margin-bottom: 8px; }
  .stem { display: block; font-size: 16px; line-height: 1.6; color: $text-primary; white-space: pre-wrap; }
}

.options {
  margin-bottom: 14px;
}

.option {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  background: $card-bg;
  border-radius: $radius-md;
  margin-bottom: 8px;
  border: 1px solid $border-color;
  &:active { background: $page-bg; }
  &.selected { border-color: $primary-color; background: $primary-faint; }
  .option-letter {
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    line-height: 22px;
    text-align: center;
    background: $page-bg;
    color: $text-secondary;
    border-radius: 50%;
    font-size: 12px;
    font-weight: 600;
  }
  &.selected .option-letter { background: $primary-color; color: $on-primary; }
  .option-text { flex: 1; font-size: 14px; line-height: 1.5; color: $text-primary; }
}

.q-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
  .q-action {
    @include hit-target(44px);
    font-size: 12px;
    color: $text-muted;
    padding: 0 10px;
    border: 1px solid $border-color;
    border-radius: 8px;
  }
}

.nav-buttons {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  .nut-button { flex: 1; }
}
</style>
