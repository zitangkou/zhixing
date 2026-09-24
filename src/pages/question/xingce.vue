<template>
  <view class="page-taking" :class="themeClass">
    <view v-if="loading" class="empty-tip">加载题目中...</view>

    <view v-else-if="finished && !reviewFromResults" class="result-panel">
      <text class="result-title">答题完成</text>
      <text class="result-score">正确 {{ correctCount }} / {{ totalCount }} 题</text>
      <text class="result-accuracy">正确率 {{ accuracyPercent }}%</text>
      <view class="result-list">
        <text class="result-list-title">答题明细</text>
        <view
          v-for="(q, idx) in questions"
          :key="q.id"
          class="result-item"
          @tap="goReviewQuestion(idx)"
        >
          <text class="result-num">{{ idx + 1 }}</text>
          <text class="result-stem">{{ truncateStem(q.stem) }}</text>
          <text
            class="result-badge"
            :class="answerRecords[q.id]?.correct ? 'ok' : answerRecords[q.id] ? 'bad' : 'skip'"
          >
            {{ answerRecords[q.id]?.correct ? '✓' : answerRecords[q.id] ? '✗' : '—' }}
          </text>
        </view>
      </view>
      <nut-button type="primary" block class="primary-btn" @click="restartQuiz">再练一组</nut-button>
      <nut-button plain type="primary" block class="ghost-btn" @click="leavePage">返回模块</nut-button>
    </view>

    <view v-else-if="currentQuestion" class="quiz-panel">
      <view v-if="paperLabel" class="paper-badge">
        <text>{{ paperLabel }}</text>
      </view>
      <view class="quiz-toolbar">
        <text class="toolbar-btn" @tap="reviewFromResults ? backToResults() : leavePage()">
          {{ reviewFromResults ? '返回结果' : '退出' }}
        </text>
        <text v-if="!reviewFromResults" class="toolbar-btn primary" @tap="restartQuiz">换一组</text>
      </view>
      <view class="progress-header">
        <text>{{ currentIndex + 1 }} / {{ questions.length }} · {{ moduleName }}</text>
        <view class="bar"><view class="fill" :style="{ width: progress + '%' }" /></view>
      </view>
      <QuestionItem
        :key="`${currentQuestion.id}-${reviewFromResults}`"
        :question="currentQuestion"
        :show-result="showResult"
        :analysis-text="analysisText"
        :selected-answer="currentSelectedAnswer"
        @answer="onAnswer"
        @change="onMultiChange"
      />
      <view class="nav-buttons">
        <nut-button plain type="primary" class="nav-btn" :disabled="currentIndex <= 0" @click="goPrev">
          上一题
        </nut-button>
        <nut-button type="primary" class="nav-btn" :disabled="nextDisabled" @click="goNext">
          {{ nextLabel }}
        </nut-button>
      </view>
    </view>

    <view v-else class="empty-tip">暂无题目</view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import QuestionItem from '@/components/QuestionItem.vue'
import { api } from '@/api'
import type { Question, QuizAnswerRecord } from '@/types'
import { showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '行测刷题' })

const { themeClass } = useThemeClass()
const CORRECT_AUTO_NEXT_MS = 2000
const router = useRouter()

const moduleName = decodeURIComponent(String(router.params?.module || ''))
const lockedYear = Number(router.params?.year || 0)
const lockedPaperType = decodeURIComponent(String(router.params?.paperType || ''))
const loading = ref(true)
const questions = ref<Question[]>([])
const currentIndex = ref(0)
const showResult = ref(false)
const analysisText = ref('')
const correctCount = ref(0)
const finished = ref(false)
const reviewFromResults = ref(false)
const answerRecords = ref<Record<string, QuizAnswerRecord>>({})
const pendingMulti = ref<string[]>([])
let autoNextTimer: ReturnType<typeof setTimeout> | null = null

const paperLabel = computed(() => {
  if (!lockedYear || !lockedPaperType) return ''
  const suffix =
    lockedPaperType === '省级'
      ? '省级'
      : lockedPaperType === '市地级'
        ? '市地'
        : lockedPaperType === '行政执法类'
          ? '执法'
          : lockedPaperType
  return `${lockedYear} 国考行测·${suffix}`
})

const currentQuestion = computed(() => questions.value[currentIndex.value])
const isLast = computed(() => currentIndex.value >= questions.value.length - 1)
const totalCount = computed(() => questions.value.length)
const progress = computed(() =>
  questions.value.length ? Math.round(((currentIndex.value + 1) / questions.value.length) * 100) : 0,
)
const accuracyPercent = computed(() =>
  totalCount.value ? Math.round((correctCount.value / totalCount.value) * 100) : 0,
)
const currentSelectedAnswer = computed(() => {
  const q = currentQuestion.value
  if (!q || !showResult.value) return undefined
  return answerRecords.value[q.id]?.userAnswer
})
const nextDisabled = computed(() => {
  if (reviewFromResults.value) return isLast.value
  if (showResult.value) return false
  if (currentQuestion.value?.type === 'multiple') {
    return pendingMulti.value.length < 2
  }
  if (isLast.value) return true
  return false
})
const nextLabel = computed(() => {
  if (reviewFromResults.value) return '下一题'
  if (!showResult.value && currentQuestion.value?.type === 'multiple') {
    return isLast.value ? '提交答案' : '下一题'
  }
  if (isLast.value && showResult.value) return '查看结果'
  return '下一题'
})

onMounted(() => {
  void boot()
})
onUnmounted(() => {
  clearAutoNext()
})

async function boot() {
  if (!moduleName || !lockedYear || !lockedPaperType) {
    loading.value = false
    showToast('请从套卷模块进入', 'error')
    return
  }
  await loadQuiz()
}

async function loadQuiz() {
  loading.value = true
  finished.value = false
  reviewFromResults.value = false
  currentIndex.value = 0
  correctCount.value = 0
  showResult.value = false
  analysisText.value = ''
  answerRecords.value = {}
  pendingMulti.value = []
  const res = await api.getXingceQuiz({
    module: moduleName,
    year: lockedYear,
    paperType: lockedPaperType,
    count: 10,
  })
  loading.value = false
  if (res.code !== 0) {
    questions.value = []
    showToast(res.message || '暂无可练真题', 'error')
    return
  }
  questions.value = res.data || []
}

function truncateStem(stem: string) {
  const text = stem.replace(/\s+/g, ' ').trim()
  return text.length > 36 ? `${text.slice(0, 36)}…` : text
}

function clearAutoNext() {
  if (autoNextTimer) {
    clearTimeout(autoNextTimer)
    autoNextTimer = null
  }
}

function restoreQuestionState() {
  const q = currentQuestion.value
  pendingMulti.value = []
  const record = q ? answerRecords.value[q.id] : undefined
  showResult.value = Boolean(record)
  analysisText.value = record?.analysis || ''
}

function onMultiChange(answer: string[]) {
  pendingMulti.value = answer
}

async function onAnswer(answer: string | string[]) {
  const q = currentQuestion.value
  if (!q || showResult.value) return
  const res = await api.submitXingceAnswer(q.id, answer)
  if (res.code !== 0 || !res.data) {
    showToast(res.message || '判分失败', 'error')
    return
  }
  const result = res.data
  showResult.value = true
  analysisText.value = result.analysis
  answerRecords.value[q.id] = {
    correct: result.correct,
    analysis: result.analysis,
    userAnswer: answer,
  }
  pendingMulti.value = []
  if (result.correct) {
    correctCount.value++
    clearAutoNext()
    autoNextTimer = setTimeout(() => {
      void goNext()
    }, CORRECT_AUTO_NEXT_MS)
  }
}

function goPrev() {
  if (currentIndex.value <= 0) return
  clearAutoNext()
  currentIndex.value--
  restoreQuestionState()
}

async function goNext() {
  clearAutoNext()
  if (reviewFromResults.value) {
    if (isLast.value) return
    currentIndex.value++
    restoreQuestionState()
    return
  }
  if (!showResult.value && currentQuestion.value?.type === 'multiple') {
    if (pendingMulti.value.length < 2) {
      showToast('请至少选择两个选项')
      return
    }
    await onAnswer([...pendingMulti.value])
    return
  }
  if (isLast.value) {
    if (showResult.value) finished.value = true
    return
  }
  currentIndex.value++
  restoreQuestionState()
}

function goReviewQuestion(index: number) {
  reviewFromResults.value = true
  finished.value = false
  currentIndex.value = index
  restoreQuestionState()
}

function backToResults() {
  reviewFromResults.value = false
  finished.value = true
  clearAutoNext()
}

function restartQuiz() {
  void loadQuiz()
}

function leavePage() {
  const modulesUrl = `/pages/question/xingce-hub?year=${lockedYear}&paperType=${encodeURIComponent(lockedPaperType)}`
  const pages = Taro.getCurrentPages()
  if (pages.length > 1) {
    Taro.navigateBack()
  } else {
    Taro.navigateTo({ url: modulesUrl })
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-taking {
  @include page-padding;
  padding-bottom: 40px;
  .empty-tip {
    text-align: center;
    color: $text-muted;
    padding: 40px 0;
  }
  .paper-badge {
    margin-bottom: 10px;
    text {
      font-size: 12px;
      color: $text-muted;
    }
  }
  .quiz-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    .toolbar-btn {
      font-size: 13px;
      color: $text-muted;
      padding: 4px 0;
      &.primary { color: $primary-color; }
    }
  }
  .progress-header {
    margin-bottom: 20px;
    font-size: 13px;
    color: $text-muted;
    .bar {
      height: 4px;
      background: $border-color;
      border-radius: 2px;
      margin-top: 8px;
      overflow: hidden;
      .fill { height: 100%; background: $primary-color; transition: width 0.3s; }
    }
  }
  .nav-buttons {
    display: flex;
    gap: 12px;
    margin-top: 20px;
    .nav-btn { flex: 1; }
  }
  .ghost-btn {
    margin-top: 10px;
  }
  .result-panel {
    padding: 24px 0 40px;
    .result-title { display: block; text-align: center; font-size: 22px; font-weight: 700; margin-bottom: 12px; }
    .result-score,
    .result-accuracy {
      display: block;
      text-align: center;
      margin-bottom: 8px;
    }
    .result-score { font-size: 16px; color: $text-secondary; }
    .result-accuracy { font-size: 18px; font-weight: 600; color: $primary-color; margin-bottom: 16px; }
    .result-list {
      margin-bottom: 24px;
      .result-list-title {
        display: block;
        font-size: 15px;
        font-weight: 600;
        margin-bottom: 12px;
      }
      .result-item {
        @include card;
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 14px;
        margin-bottom: 8px;
        .result-num {
          flex-shrink: 0;
          width: 24px;
          height: 24px;
          line-height: 24px;
          text-align: center;
          border-radius: 50%;
          background: $page-bg;
          font-size: 12px;
          color: $text-muted;
        }
        .result-stem {
          flex: 1;
          font-size: 14px;
          line-height: 1.5;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .result-badge {
          flex-shrink: 0;
          font-size: 16px;
          font-weight: 700;
          &.ok { color: var(--zk-success); }
          &.bad { color: #ee0a24; }
          &.skip { color: $text-muted; }
        }
      }
    }
  }
}
</style>
