<template>
  <view class="page-review" :class="themeClass">
    <view v-if="loading" class="state-card">正在整理错因与依据…</view>
    <view v-else-if="!task" class="state-card">
      <text class="state-title">没有找到学习记录</text>
      <text class="state-desc">请从今日学习包重新进入。</text>
    </view>
    <template v-else-if="task.progress.state === 'completed'">
      <view class="complete-mark">✓</view>
      <text class="complete-title">今天的理论主题已学完</text>
      <text class="complete-desc">正确 {{ quizCorrect }}/{{ quizTotal }}，错因和原文依据已留在复习链路。</text>
      <view class="summary-card">
        <text class="summary-label">今日主题</text>
        <text class="summary-value">{{ task.title }}</text>
        <text class="summary-meta">下一次复习时，先回忆主体、行动和限定条件。</text>
      </view>
      <nut-button type="primary" block @click="backHome">回到今日</nut-button>
    </template>
    <template v-else>
      <view class="step-head">
        <text class="step-kicker">第 4 步 · 错因回收</text>
        <text class="step-title">{{ wrongIds.length ? '错在哪里，要说得具体' : '本次全对，再复核一次边界' }}</text>
        <text class="step-desc">
          {{ wrongIds.length ? '对照原文依据，为每道错题标记主要干扰方式。' : '不重复刷题，只看容易被偷换的主体、范围和程度词。' }}
        </text>
      </view>

      <view v-for="(question, index) in reviewQuestions" :key="question.id" class="review-card">
        <view class="review-meta">
          <text>{{ wrongIds.length ? '错题' : '边界复核' }} {{ index + 1 }}</text>
          <text>{{ typeLabel(question.type) }}</text>
        </view>
        <text class="review-stem">{{ question.stem }}</text>
        <view v-if="selectedAnswer(question.id)" class="answer-row">
          <text class="answer-label">你的选择</text>
          <text>{{ selectedAnswer(question.id) }}</text>
        </view>
        <view class="evidence-box">
          <text class="evidence-label">原文依据</text>
          <text class="evidence-copy">{{ question.sourceSentence }}</text>
        </view>
        <text class="analysis-copy">{{ question.analysis }}</text>

        <template v-if="wrongIds.length">
          <text class="reason-title">主要错因</text>
          <view class="reason-row">
            <text
              v-for="reason in reasonOptions"
              :key="reason"
              class="reason-chip"
              :class="{ selected: reasons[question.id] === reason }"
              @tap="selectReason(question.id, reason)"
            >
              {{ reason }}
            </text>
          </view>
        </template>
      </view>

      <view class="closing-note">
        <text>完成后</text>
        <text>错题已入复习 · 依据可随时回看</text>
      </view>
      <nut-button type="primary" block :loading="finishing" @click="finishReview">
        完成今日学习
      </nut-button>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import { api } from '@/api'
import { useDailyTaskStore } from '@/store/dailyTask'
import type { Question } from '@/types'
import { useThemeClass } from '@/utils/brandColor'
import { showToast } from '@/utils/platform'

definePageConfig({ navigationBarTitleText: '错因与依据' })

const reasonOptions = ['主体偷换', '范围变化', '程度变化', '因果倒置', '概念混淆', '记忆不牢']
const router = useRouter()
const { themeClass } = useThemeClass()
const dailyTaskStore = useDailyTaskStore()
const taskId = (router.params?.taskId || '').trim()
const loading = ref(true)
const finishing = ref(false)
const questions = ref<Question[]>([])
const reasons = ref<Record<string, string>>({})
const task = computed(() => dailyTaskStore.tasks.find((item) => item.id === taskId) || null)
const wrongIds = computed(() => {
  const raw = task.value?.progress.draft?.wrongQuestionIds
  return Array.isArray(raw) ? raw.map(String) : []
})
const reviewQuestions = computed(() => {
  if (wrongIds.value.length) return questions.value.filter((question) => wrongIds.value.includes(question.id))
  return questions.value.slice(0, 2)
})
const quizTotal = computed(() => Number(task.value?.progress.draft?.quizTotal || questions.value.length))
const quizCorrect = computed(() => Number(task.value?.progress.draft?.quizCorrect || 0))

function typeLabel(type: Question['type']) {
  return { single: '单选', multiple: '多选', judge: '判断' }[type]
}

function selectedAnswer(questionId: string) {
  const records = task.value?.progress.draft?.quizAnswers as
    | Record<string, { userAnswer?: string | string[] }>
    | undefined
  const value = records?.[questionId]?.userAnswer
  return Array.isArray(value) ? value.join('、') : String(value || '')
}

function selectReason(questionId: string, reason: string) {
  reasons.value = { ...reasons.value, [questionId]: reason }
}

async function finishReview() {
  if (!task.value) return
  const missing = wrongIds.value.some((questionId) => !reasons.value[questionId])
  if (missing) {
    showToast('请为每道错题选择主要错因')
    return
  }
  finishing.value = true
  try {
    let state = task.value.progress.state
    if (state === 'in_progress') {
      await dailyTaskStore.saveDraft(
        task.value.id,
        {
          ...task.value.progress.draft,
          errorReasons: reasons.value,
          evidenceReviewed: true,
        },
        4,
        task.value.totalSteps,
      )
      await dailyTaskStore.submit(task.value.id)
      state = 'submitted'
    }
    if (state === 'submitted') {
      await dailyTaskStore.markReviewed(task.value.id)
      state = 'reviewed'
    }
    if (state === 'reviewed') await dailyTaskStore.complete(task.value.id)
  } catch (error) {
    showToast(error instanceof Error ? error.message : '学习状态同步失败', 'error')
  } finally {
    finishing.value = false
  }
}

function backHome() {
  Taro.switchTab({ url: '/pages/theory/index' })
}

onMounted(async () => {
  if (!task.value) await dailyTaskStore.load()
  if (task.value) {
    const saved = task.value.progress.draft?.errorReasons
    if (saved && typeof saved === 'object') reasons.value = saved as Record<string, string>
    const result = await api.getQuestions(task.value.contentId)
    if (result.code === 0 && result.data) questions.value = result.data
  }
  loading.value = false
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-review { @include page-padding; padding-bottom: 36px; }
.state-card { @include card; text-align: center; color: $text-muted; margin-top: 24px; padding: 36px 20px; }
.state-title, .state-desc, .step-kicker, .step-title, .step-desc, .review-stem,
.evidence-label, .evidence-copy, .analysis-copy, .reason-title, .complete-title,
.complete-desc, .summary-label, .summary-value, .summary-meta { display: block; }
.state-title { color: $text-primary; font-size: 17px; font-weight: 700; }
.state-desc { margin-top: 8px; font-size: 13px; }
.step-head { padding: 14px 2px 20px; }
.step-kicker { color: $primary-color; font-size: 12px; font-weight: 600; margin-bottom: 8px; }
.step-title { color: $text-primary; font-size: 23px; font-weight: 700; line-height: 1.4; }
.step-desc { color: $text-muted; font-size: 13px; line-height: 1.65; margin-top: 8px; }
.review-card { @include card; padding: 18px; }
.review-meta { display: flex; justify-content: space-between; color: $primary-color; font-size: 11px; font-weight: 600; margin-bottom: 10px; }
.review-stem { color: $text-primary; font-size: 15px; line-height: 1.7; font-weight: 600; }
.answer-row { display: flex; gap: 10px; color: $text-secondary; font-size: 12px; margin-top: 12px; }
.answer-label { color: $text-muted; }
.evidence-box { background: $primary-faint; border-left: 3px solid $primary-color; border-radius: 0 7px 7px 0; padding: 11px 12px; margin-top: 14px; }
.evidence-label { color: $primary-color; font-size: 11px; font-weight: 700; margin-bottom: 5px; }
.evidence-copy { color: $text-primary; font-size: 13px; line-height: 1.65; }
.analysis-copy { color: $text-secondary; font-size: 12px; line-height: 1.65; margin-top: 10px; }
.reason-title { color: $text-primary; font-size: 12px; font-weight: 600; margin-top: 14px; }
.reason-row { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 8px; }
.reason-chip { color: $text-secondary; background: $elevated; border: 1px solid $border-color; border-radius: 6px; padding: 5px 9px; font-size: 11px; }
.reason-chip.selected { color: $primary-color; background: $primary-light; border-color: $primary-color; }
.closing-note { display: flex; justify-content: space-between; color: $text-muted; font-size: 11px; padding: 4px 2px 18px; }
.complete-mark { width: 52px; height: 52px; margin: 52px auto 18px; border-radius: 50%; background: $primary-light; color: $primary-color; text-align: center; line-height: 52px; font-size: 26px; font-weight: 700; }
.complete-title { color: $text-primary; font-size: 23px; font-weight: 700; text-align: center; }
.complete-desc { color: $text-muted; font-size: 13px; line-height: 1.65; text-align: center; margin: 10px 20px 24px; }
.summary-card { @include card; padding: 20px; margin-bottom: 18px; }
.summary-label { color: $primary-color; font-size: 11px; font-weight: 600; margin-bottom: 8px; }
.summary-value { color: $text-primary; font-size: 16px; line-height: 1.6; }
.summary-meta { color: $text-muted; font-size: 12px; line-height: 1.6; margin-top: 8px; }
</style>
