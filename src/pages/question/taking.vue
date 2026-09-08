<template>
  <view class="page-taking" :class="themeClass">
    <view v-if="loading" class="empty-tip">加载题目中...</view>

    <view v-else-if="finished && !reviewFromResults" class="result-panel">
      <text class="result-title">答题完成</text>
      <text class="result-score">正确 {{ correctCount }} / {{ totalCount }} 题</text>
      <text class="result-accuracy">正确率 {{ accuracyPercent }}%</text>
      <text v-if="quizStats.rank" class="result-rank">
        本套题排名第 {{ quizStats.rank }} 名
        <text v-if="quizStats.totalParticipants > 1" class="rank-meta">
          （共 {{ quizStats.totalParticipants }} 人参与）
        </text>
      </text>
      <text class="result-points">获得积分 +{{ earnedPoints }}</text>

      <view class="result-list">
        <text class="result-list-title">答题明细（点击可回看）</text>
        <view
          v-for="(q, idx) in questions"
          :key="q.id"
          class="result-item"
          @tap="goReviewQuestion(idx)"
        >
          <text class="result-num">{{ idx + 1 }}</text>
          <text class="result-type">{{ typeShort(q.type) }}</text>
          <text class="result-stem">{{ truncateStem(q.stem) }}</text>
          <text
            class="result-badge"
            :class="answerRecords[q.id]?.correct ? 'ok' : answerRecords[q.id] ? 'bad' : 'skip'"
          >
            {{ answerRecords[q.id]?.correct ? '✓' : answerRecords[q.id] ? '✗' : '—' }}
          </text>
        </view>
      </view>

      <nut-button
        type="primary"
        block
        class="primary-btn"
        :loading="syncingResult"
        :disabled="syncingResult"
        @click="leavePage"
      >
        {{ resultActionText }}
      </nut-button>
      <view v-if="isWrongSession && sessionSummary" class="wrong-session-summary">
        <text>掌握 {{ sessionSummary.mastered }} · 已安排下次 {{ sessionSummary.scheduled }} · 仍需复习 {{ sessionSummary.reset }}</text>
      </view>
    </view>

    <view v-else-if="currentQuestion" class="quiz-panel">
      <view class="quiz-toolbar">
        <text class="toolbar-btn" @tap="reviewFromResults ? backToResults() : exitQuiz()">
          {{ reviewFromResults ? '返回结果' : '退出' }}
        </text>
        <text v-if="!reviewFromResults" class="toolbar-btn primary" @tap="restartQuiz">重新开始</text>
      </view>
      <view class="progress-header">
        <text>{{ currentIndex + 1 }} / {{ questions.length }}</text>
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
        <nut-button
          plain
          type="primary"
          class="nav-btn"
          :disabled="currentIndex <= 0"
          @click="goPrev"
        >
          上一题
        </nut-button>
        <nut-button
          type="primary"
          class="nav-btn"
          :disabled="nextDisabled"
          @click="goNext"
        >
          {{ nextLabel }}
        </nut-button>
      </view>
    </view>

    <view v-else class="empty-tip">暂无题目</view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import QuestionItem from '@/components/QuestionItem.vue'
import { useQuestionStore } from '@/store/question'
import { useDailyTaskStore } from '@/store/dailyTask'
import type { QuizAnswerRecord, Question, QuizMode } from '@/types'
import { showConfirm, showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '刷题' })

const { themeClass } = useThemeClass()
const CORRECT_AUTO_NEXT_MS = 2000

const router = useRouter()
const questionStore = useQuestionStore()
const dailyTaskStore = useDailyTaskStore()
const taskId = (router.params?.taskId || '').trim()

const loading = ref(true)
const questions = ref<Question[]>([])
const currentIndex = ref(0)
const showResult = ref(false)
const analysisText = ref('')
const correctCount = ref(0)
const earnedPoints = ref(0)
const finished = ref(false)
const syncingResult = ref(false)
const reviewFromResults = ref(false)
const lastAnswerCorrect = ref(false)
const answerRecords = ref<Record<string, QuizAnswerRecord>>({})
const pendingMulti = ref<string[]>([])
const quizStats = ref({ rank: 0, totalParticipants: 0, accuracy: 0, bestAccuracy: 0 })
const quizSession = ref<
  | { kind: 'article'; articleId: string }
  | { kind: 'mode'; mode: QuizMode }
  | { kind: 'wrong'; questionId: string }
  | { kind: 'wrong-session' }
  | null
>(null)
const sessionSummary = ref({ mastered: 0, scheduled: 0, reset: 0 })
const WRONG_SESSION_CAP = 15
let autoNextTimer: ReturnType<typeof setTimeout> | null = null

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
  // 多选：选够选项后可用「下一题」提交；单选点选项即提交
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
const isWrongRedo = computed(() => quizSession.value?.kind === 'wrong')
const isWrongSession = computed(() => quizSession.value?.kind === 'wrong-session')
const isWrongMode = computed(() => isWrongRedo.value || isWrongSession.value)
const dailyTask = computed(() => dailyTaskStore.tasks.find((item) => item.id === taskId) || null)
const resultActionText = computed(() => {
  if (taskId) return '回收错因与依据'
  return isWrongMode.value ? '返回复习' : '返回练习'
})

onMounted(() => {
  void boot()
})

onUnmounted(() => {
  clearAutoNext()
})

async function boot() {
  if (taskId && !dailyTask.value) await dailyTaskStore.load()
  const { mode, articleId, wrongId, wrongSession } = router.params || {}
  if (wrongSession === '1' || wrongSession === 'true') {
    await startWrongSession()
  } else if (wrongId) {
    await startWrongRedo(String(wrongId))
  } else if (articleId) {
    await startQuiz(String(articleId))
  } else if (mode) {
    await startModeQuiz(String(mode) as QuizMode)
  } else {
    loading.value = false
    showToast('参数无效', 'error')
  }
}

function truncateStem(stem: string) {
  const text = stem.replace(/\s+/g, ' ').trim()
  return text.length > 36 ? `${text.slice(0, 36)}…` : text
}

function typeShort(type?: string) {
  const map: Record<string, string> = {
    single: '单',
    multiple: '多',
    judge: '判',
  }
  return map[type || ''] || '题'
}

function clearAutoNext() {
  if (autoNextTimer) {
    clearTimeout(autoNextTimer)
    autoNextTimer = null
  }
}

function resetQuizState() {
  clearAutoNext()
  finished.value = false
  reviewFromResults.value = false
  currentIndex.value = 0
  correctCount.value = 0
  earnedPoints.value = 0
  showResult.value = false
  analysisText.value = ''
  lastAnswerCorrect.value = false
  answerRecords.value = {}
  pendingMulti.value = []
  quizStats.value = { rank: 0, totalParticipants: 0, accuracy: 0, bestAccuracy: 0 }
  sessionSummary.value = { mastered: 0, scheduled: 0, reset: 0 }
  questions.value = []
}

function leavePage() {
  if (syncingResult.value) return
  if (taskId) {
    Taro.redirectTo({ url: `/pages/theory/review?taskId=${encodeURIComponent(taskId)}` })
    return
  }
  const pages = Taro.getCurrentPages()
  if (pages.length > 1) {
    Taro.navigateBack()
  } else {
    Taro.switchTab({ url: '/pages/question/index' })
  }
}

function restoreQuestionState() {
  const q = currentQuestion.value
  pendingMulti.value = []
  if (!q) return
  const rec = answerRecords.value[q.id]
  if (rec) {
    showResult.value = true
    analysisText.value = rec.analysis
    lastAnswerCorrect.value = rec.correct
  } else {
    showResult.value = false
    analysisText.value = ''
    lastAnswerCorrect.value = false
  }
}

function onMultiChange(answer: string[]) {
  if (showResult.value || reviewFromResults.value) return
  pendingMulti.value = answer
}

async function exitQuiz() {
  const ok = await showConfirm('退出答题', '当前进度不会保存，确定退出吗？')
  if (!ok) return
  leavePage()
}

async function restartQuiz() {
  if (!quizSession.value) return
  const ok = await showConfirm('重新开始', '当前进度将清零，是否重新开始本组题目？')
  if (!ok) return
  const session = quizSession.value
  if (session.kind === 'article') {
    await startQuiz(session.articleId)
  } else if (session.kind === 'wrong') {
    await startWrongRedo(session.questionId)
  } else if (session.kind === 'wrong-session') {
    await startWrongSession()
  } else {
    await startModeQuiz(session.mode)
  }
}

async function startModeQuiz(mode: QuizMode) {
  quizSession.value = { kind: 'mode', mode }
  loading.value = true
  resetQuizState()
  try {
    const qs = await questionStore.loadQuizByMode(mode, 10)
    if (!qs?.length) {
      showToast('暂无可用题目', 'error')
      leavePage()
      return
    }
    questions.value = qs
  } finally {
    loading.value = false
  }
}

async function startQuiz(articleId: string) {
  quizSession.value = { kind: 'article', articleId }
  loading.value = true
  resetQuizState()
  try {
    const qs = await questionStore.generateQuestions(articleId)
    if (!qs?.length) {
      showToast('该文章暂无题目', 'error')
      leavePage()
      return
    }
    questions.value = qs
  } finally {
    loading.value = false
  }
}

async function startWrongRedo(questionId: string) {
  quizSession.value = { kind: 'wrong', questionId }
  loading.value = true
  resetQuizState()
  try {
    if (!questionStore.wrongQuestions.length) {
      await questionStore.loadWrongQuestions()
    }
    const record = questionStore.wrongQuestions.find((w) => w.question.id === questionId)
    if (!record) {
      showToast('错题不存在或已移除', 'error')
      leavePage()
      return
    }
    questions.value = [record.question]
  } finally {
    loading.value = false
  }
}

async function startWrongSession() {
  quizSession.value = { kind: 'wrong-session' }
  loading.value = true
  resetQuizState()
  try {
    const ok = await questionStore.loadWrongQuestions('review')
    if (!ok) {
      leavePage()
      return
    }
    const due = [...questionStore.wrongQuestions].sort(
      (a, b) =>
        (a.reviewStage || 0) - (b.reviewStage || 0)
        || (b.wrongCount || 0) - (a.wrongCount || 0),
    )
    const picked = due.slice(0, WRONG_SESSION_CAP)
    if (!picked.length) {
      showToast('今日无到期错题', 'success')
      leavePage()
      return
    }
    questions.value = picked.map((w) => w.question)
    Taro.setNavigationBarTitle({ title: `错题复习 · ${picked.length} 题` })
  } finally {
    loading.value = false
  }
}

async function onAnswer(answer: string | string[]) {
  if (showResult.value || !currentQuestion.value || reviewFromResults.value) return
  const q = currentQuestion.value
  const wrongRedo = isWrongMode.value
  const result = wrongRedo
    ? await questionStore.redoWrongQuestion(q.id, answer)
    : await questionStore.submitAnswer(q.id, answer, q)
  if (!result) return
  showResult.value = true
  analysisText.value = result.analysis
  lastAnswerCorrect.value = result.correct
  answerRecords.value[q.id] = {
    correct: result.correct,
    analysis: result.analysis,
    userAnswer: answer,
  }
  pendingMulti.value = []
  if (result.correct) {
    correctCount.value++
    earnedPoints.value += result.pointsEarned
    if (wrongRedo) {
      if (result.pointsEarned >= 5) {
        sessionSummary.value.mastered += 1
        showToast('已掌握，移出错题本', 'success')
      } else {
        sessionSummary.value.scheduled += 1
        showToast('答对了，已安排下次复习', 'success')
      }
    }
    clearAutoNext()
    autoNextTimer = setTimeout(() => {
      void goNext()
    }, CORRECT_AUTO_NEXT_MS)
  } else if (wrongRedo) {
    sessionSummary.value.reset += 1
    showToast('已重置，明天再来')
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
  // 多选：用「下一题」代替确认提交
  if (!showResult.value && currentQuestion.value?.type === 'multiple') {
    if (pendingMulti.value.length < 2) {
      showToast('请至少选择两个选项')
      return
    }
    await onAnswer([...pendingMulti.value])
    return
  }
  if (isLast.value) {
    if (showResult.value) {
      await finishQuiz()
    }
    return
  }
  currentIndex.value++
  restoreQuestionState()
}

async function finishQuiz() {
  finished.value = true
  syncingResult.value = Boolean(taskId)
  reviewFromResults.value = false
  const session = quizSession.value
  if (session?.kind === 'wrong' || session?.kind === 'wrong-session') {
    questionStore.completeDailyWrongReview()
    syncingResult.value = false
    return
  }
  const mode = session?.kind === 'mode' ? session.mode : 'article'
  const articleId = session?.kind === 'article' ? session.articleId : undefined
  const stats = await questionStore.submitQuizComplete({
    articleId,
    mode,
    total: totalCount.value,
    correct: correctCount.value,
  })
  if (stats) {
    quizStats.value = {
      rank: stats.rank,
      totalParticipants: stats.totalParticipants,
      accuracy: stats.accuracy,
      bestAccuracy: stats.bestAccuracy ?? stats.accuracy,
    }
  }
  if (taskId && dailyTask.value?.progress.state === 'in_progress') {
    try {
      const wrongQuestionIds = questions.value
        .filter((question) => !answerRecords.value[question.id]?.correct)
        .map((question) => question.id)
      await dailyTaskStore.saveDraft(
        taskId,
        {
          ...dailyTask.value.progress.draft,
          quizCompleted: true,
          quizTotal: totalCount.value,
          quizCorrect: correctCount.value,
          wrongQuestionIds,
          quizAnswers: answerRecords.value,
        },
        3,
        dailyTask.value.totalSteps,
      )
    } catch (error) {
      showToast(error instanceof Error ? error.message : '测验结果同步失败', 'error')
    }
  }
  syncingResult.value = false
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
  .result-panel {
    padding: 24px 0 40px;
    .result-title { display: block; text-align: center; font-size: 22px; font-weight: 700; margin-bottom: 12px; }
    .result-score,
    .result-accuracy,
    .result-rank,
    .result-points {
      display: block;
      text-align: center;
      margin-bottom: 8px;
    }
    .result-score { font-size: 16px; color: $text-secondary; }
    .result-accuracy { font-size: 18px; font-weight: 600; color: $primary-color; }
    .result-rank { font-size: 14px; color: $text-secondary;
      .rank-meta { color: $text-muted; font-size: 12px; }
    }
    .result-points { font-size: 15px; color: $text-secondary; margin-bottom: 12px; }
    .wrong-session-summary {
      text-align: center;
      font-size: 13px;
      color: $text-muted;
      margin-bottom: 20px;
      line-height: 1.5;
    }
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
        .result-type {
          flex-shrink: 0;
          font-size: 11px;
          font-weight: 600;
          color: $primary-color;
          background: $primary-light;
          padding: 2px 5px;
          border-radius: 4px;
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
