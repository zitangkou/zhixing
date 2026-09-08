<template>
  <view class="page learning-page">
    <view class="learning-head">
      <view class="eyebrow">{{ stageKicker }}</view>
      <view class="page-title">{{ stageTitle }}</view>
      <view class="mini-progress"><view class="mini-progress-fill" :style="{ width: `${progress}%` }" /></view>
    </view>

    <view v-if="loading" class="card state-card">正在加载今日学习内容…</view>
    <template v-else-if="article && questions.length">
      <template v-if="stage === 'orient'">
        <view class="card guide-card"><view class="card-title">先凭已有认知判断</view><view class="card-desc">不显示答案，不追求全对。完成后带着分歧进入原文。</view></view>
        <view class="card question-card">
          <view class="question-count">预检 {{ pretestIndex + 1 }} / {{ pretestQuestions.length }}</view>
          <view class="question-stem">{{ pretestQuestion.stem }}</view>
          <view v-for="option in pretestQuestion.options" :key="option" class="option" :class="{ selected: selectedIncludes(option) }" @tap="selectOption(option)">{{ option }}</view>
          <view class="primary-action" :class="{ disabled: !hasSelection }" @tap="nextPretest">{{ pretestIndex + 1 === pretestQuestions.length ? '带着问题读原文' : '下一题' }}</view>
        </view>
      </template>

      <template v-else-if="stage === 'read'">
        <view class="article-meta">{{ article.source }} · {{ article.publishDate }}</view>
        <view class="article-title">{{ article.title }}</view>
        <view class="article-summary">{{ article.summary }}</view>
        <view class="focus-row"><view v-for="tag in article.tags.slice(0, 3)" :key="tag" class="focus-tag">{{ tag }}</view></view>
        <view class="card article-card"><view v-for="(paragraph, index) in paragraphs" :key="index" class="paragraph">{{ paragraph }}</view></view>
        <view class="sticky-action"><view class="primary-action" @tap="finishReading">我已读懂，进入证据练习</view></view>
      </template>

      <template v-else-if="stage === 'quiz'">
        <view class="card question-card">
          <view class="question-count">正式作答 {{ quizIndex + 1 }} / {{ questions.length }}</view>
          <view class="question-stem">{{ quizQuestion.stem }}</view>
          <view v-for="option in quizQuestion.options" :key="option" class="option" :class="{ selected: selectedIncludes(option) }" @tap="selectOption(option)">{{ option }}</view>
          <view class="primary-action" :class="{ disabled: !hasSelection || submitting }" @tap="submitCurrent">{{ submitting ? '正在提交…' : '确认答案' }}</view>
        </view>
      </template>

      <template v-else-if="stage === 'review'">
        <view class="score-card"><view class="score">{{ correctCount }}/{{ questions.length }}</view><view><view class="card-title">本次正确</view><view class="card-desc">复盘重点是找到表述变化，不是只记选项。</view></view></view>
        <view v-for="(question, index) in questions" :key="question.id" class="card review-card">
          <view class="review-status" :class="{ wrong: !resultFor(question.id)?.correct }">{{ resultFor(question.id)?.correct ? '判断准确' : '需要回收' }}</view>
          <view class="question-stem">{{ index + 1 }}. {{ question.stem }}</view>
          <view class="answer-line">你的答案：{{ answerText(question.id) }}；正确答案：{{ correctText(question.id) }}</view>
          <view class="evidence"><view class="evidence-label">原文依据</view>{{ question.sourceSentence }}</view>
          <view class="analysis">{{ resultFor(question.id)?.analysis || question.analysis }}</view>
        </view>
        <view class="primary-action finish-action" @tap="finishReview">完成今日学习</view>
      </template>

      <view v-else class="card complete-card"><view class="complete-mark">✓</view><view class="article-title">今日学习已闭环</view><view class="card-desc">预检、精读、作答与证据复盘均已保存。</view><view class="primary-action" @tap="backToday">返回今日</view></view>
    </template>
    <view v-else class="card state-card">{{ message || '今日内容暂不可用，请稍后再试。' }}</view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api, type AnswerResult, type Article, type Question } from '@/api'
import { useDailyTaskStore } from '@/store/dailyTask'
import { isLoggedIn } from '@/utils/auth'
import { showToast } from '@/utils/platform'

type Stage = 'orient' | 'read' | 'quiz' | 'review' | 'complete'
interface SavedResult extends AnswerResult { userAnswer: string | string[] }

const store = useDailyTaskStore()
const loading = ref(true)
const message = ref('')
const article = ref<Article | null>(null)
const questions = ref<Question[]>([])
const stage = ref<Stage>('orient')
const pretestIndex = ref(0)
const quizIndex = ref(0)
const selection = ref<string[]>([])
const pretestAnswers = ref<Record<string, string | string[]>>({})
const results = ref<Record<string, SavedResult>>({})
const submitting = ref(false)

const pretestQuestions = computed(() => questions.value.slice(0, 2))
const pretestQuestion = computed(() => pretestQuestions.value[pretestIndex.value] || questions.value[0])
const quizQuestion = computed(() => questions.value[quizIndex.value] || questions.value[0])
const activeQuestion = computed(() => stage.value === 'orient' ? pretestQuestion.value : quizQuestion.value)
const hasSelection = computed(() => selection.value.length > 0)
const paragraphs = computed(() => (article.value?.content || '').split(/\n+/).map((item) => item.trim()).filter(Boolean))
const progress = computed(() => ({ orient: 15, read: 35, quiz: 65, review: 90, complete: 100 }[stage.value]))
const stageKicker = computed(() => ({ orient: '第 1 步 · 读前定向', read: '第 2 步 · 原文精读', quiz: '第 3 步 · 证据练习', review: '第 4 步 · 错因回收', complete: '今日完成' }[stage.value]))
const stageTitle = computed(() => ({ orient: '先判断，再验证', read: '读懂规范表述', quiz: '用证据辨析表述', review: '把每道题落回原文', complete: '理解已经沉淀' }[stage.value]))
const correctCount = computed(() => Object.values(results.value).filter((item) => item.correct).length)

function selectedIncludes(option: string) { return selection.value.includes(option) }
function selectOption(option: string) {
  const question = activeQuestion.value
  if (!question) return
  if (question.type !== 'multiple') selection.value = [option]
  else selection.value = selection.value.includes(option) ? selection.value.filter((item) => item !== option) : [...selection.value, option]
}
function selectedAnswer(question: Question): string | string[] { return question.type === 'multiple' ? [...selection.value] : selection.value[0] }
function restoreStage() {
  const task = store.task
  if (!task) return
  const draft = task.progress.draft || {}
  pretestAnswers.value = (draft.pretestAnswers as Record<string, string | string[]>) || {}
  results.value = (draft.quizResults as Record<string, SavedResult>) || {}
  if (task.progress.state === 'completed') stage.value = 'complete'
  else if (task.progress.state === 'submitted' || task.progress.state === 'reviewed') stage.value = 'review'
  else if (task.progress.currentStep >= 2) stage.value = 'quiz'
  else if (task.progress.currentStep >= 1) stage.value = 'read'
}
async function nextPretest() {
  if (!hasSelection.value) return
  pretestAnswers.value[pretestQuestion.value.id] = selectedAnswer(pretestQuestion.value)
  selection.value = []
  if (pretestIndex.value + 1 < pretestQuestions.value.length) { pretestIndex.value++; return }
  if (await store.transition('save', 1, { ...store.task?.progress.draft, pretestAnswers: pretestAnswers.value })) stage.value = 'read'
  else showToast(store.message || '进度保存失败')
}
async function finishReading() {
  if (!article.value) return
  const read = await api.markArticleRead(article.value.id)
  if (read.code !== 0) { showToast(read.message); return }
  if (await store.transition('save', 2, { ...store.task?.progress.draft, pretestAnswers: pretestAnswers.value, readCompleted: true })) stage.value = 'quiz'
}
async function submitCurrent() {
  if (!hasSelection.value || submitting.value) return
  const question = quizQuestion.value
  const answer = selectedAnswer(question)
  submitting.value = true
  const response = await api.submitAnswer(question.id, answer)
  submitting.value = false
  if (response.code !== 0 || !response.data) { showToast(response.message); return }
  results.value[question.id] = { ...response.data, userAnswer: answer }
  selection.value = []
  if (quizIndex.value + 1 < questions.value.length) { quizIndex.value++; return }
  const wrongQuestionIds = Object.entries(results.value)
    .filter(([, result]) => !result.correct)
    .map(([questionId]) => questionId)
  const ok = await store.transition('submit', 3, {
    ...store.task?.progress.draft,
    pretestAnswers: pretestAnswers.value,
    readCompleted: true,
    quizResults: results.value,
    quizAnswers: results.value,
    wrongQuestionIds,
    quizCorrect: correctCount.value,
    quizTotal: questions.value.length,
  })
  if (ok) Taro.redirectTo({ url: `/pages/learning/review?taskId=${encodeURIComponent(store.task?.id || '')}` })
}
function resultFor(id: string) { return results.value[id] }
function toText(value: string | string[] | undefined) { return Array.isArray(value) ? value.join('、') : value || '未作答' }
function answerText(id: string) { return toText(results.value[id]?.userAnswer) }
function correctText(id: string) { return toText(results.value[id]?.correctAnswer) }
async function finishReview() {
  if (store.task?.progress.state === 'submitted' && !(await store.transition('review', 4, store.task.progress.draft))) return
  if (store.task?.progress.state === 'reviewed' && await store.transition('complete', 4, store.task.progress.draft)) stage.value = 'complete'
}
function backToday() { Taro.switchTab({ url: '/pages/today/index' }) }
async function load() {
  if (!isLoggedIn()) { Taro.redirectTo({ url: '/pages/auth/login' }); return }
  await store.load()
  if (!store.task) { message.value = store.message; loading.value = false; return }
  if (store.task.progress.state === 'not_started') await store.start()
  const [articleResponse, questionResponse] = await Promise.all([api.getArticle(store.task.contentId), api.getQuestions(store.task.contentId)])
  if (articleResponse.code === 0 && articleResponse.data) article.value = articleResponse.data
  if (questionResponse.code === 0 && questionResponse.data) questions.value = questionResponse.data
  message.value = articleResponse.message || questionResponse.message
  restoreStage()
  if (store.task.progress.state === 'submitted' || store.task.progress.state === 'reviewed') {
    Taro.redirectTo({ url: `/pages/learning/review?taskId=${encodeURIComponent(store.task.id)}` })
    return
  }
  loading.value = false
}
onMounted(load)
</script>
