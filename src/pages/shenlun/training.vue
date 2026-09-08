<template>
  <view class="page-training" :class="themeClass">
    <view v-if="loading" class="state-card">正在恢复训练…</view>
    <view v-else-if="!task" class="state-card">
      <text class="state-title">没有找到今日任务</text>
      <text class="state-desc">请返回申论首页重新进入。</text>
    </view>

    <template v-else-if="task.progress.state === 'completed'">
      <view class="complete-mark">✓</view>
      <text class="complete-title">今天的训练，真正留下了</text>
      <text class="complete-desc">比读过更重要的是，能把表达带到下一次作答里。</text>
      <view class="result-card">
        <text class="result-label">今日沉淀</text>
        <text class="result-value">{{ expression || '已完成表达沉淀' }}</text>
      </view>
      <nut-button type="primary" block @click="backHome">回到今日</nut-button>
    </template>

    <template v-else-if="stage === 'answer'">
      <view class="step-head">
        <text class="step-kicker">第 3 步 · {{ question.type }}</text>
        <text class="step-heading">把读懂的，写成答案</text>
        <text class="step-lead">{{ question.prompt }}</text>
      </view>
      <view class="answer-card">
        <nut-textarea
          v-model="answer"
          :rows="8"
          :maxlength="question.maxLength"
          placeholder="先写对象，再写核心问题或成效，最后压缩主要做法…"
        />
        <view class="count-row">
          <text class="save-state">{{ savingDraft ? '正在保存…' : '草稿自动保存' }}</text>
          <text :class="{ over: answerLength > question.maxLength }">
            {{ answerLength }}/{{ question.maxLength }}
          </text>
        </view>
      </view>
      <view class="check-card">
        <text class="check-title">提交前，用规则自检</text>
        <text class="check-note">至少确认 2 项，不做模糊的“感觉还行”</text>
        <view
          v-for="(item, index) in question.checks"
          :key="item"
          class="check-item"
          @tap="toggleCheck(index)"
        >
          <text class="check-box" :class="{ checked: checkedIndexes.includes(index) }">
            {{ checkedIndexes.includes(index) ? '✓' : '' }}
          </text>
          <text class="check-copy">{{ item }}</text>
        </view>
      </view>
      <nut-button type="primary" block :loading="submitting" @click="submitAnswer">
        完成自检，继续沉淀
      </nut-button>
    </template>

    <template v-else>
      <view class="step-head">
        <text class="step-kicker">第 4 步 · 表达沉淀</text>
        <text class="step-heading">只留下一句真正会用的</text>
        <text class="step-lead">{{ depositPrompt }}</text>
      </view>
      <view class="deposit-card">
        <text class="field-label">规范表达</text>
        <nut-textarea
          v-model="expression"
          :rows="4"
          :maxlength="100"
          placeholder="如：把群众的“需求清单”转化为干部的“履职清单”"
        />
        <text class="field-label second">下次准备怎么用（可选）</text>
        <nut-textarea
          v-model="application"
          :rows="3"
          :maxlength="160"
          placeholder="可写适用主题、句子位置或替换对象"
        />
      </view>
      <view class="closing-note">
        <text>今日收获</text>
        <text>一篇材料 · 一次作答 · 一个可迁移表达</text>
      </view>
      <nut-button type="primary" block :loading="submitting" @click="finishTraining">
        完成今日训练
      </nut-button>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton, Textarea as NutTextarea } from '@nutui/nutui-taro'
import { api } from '@/api'
import { useDailyTaskStore } from '@/store/dailyTask'
import { useThemeClass } from '@/utils/brandColor'
import { showToast } from '@/utils/platform'

definePageConfig({ navigationBarTitleText: '今日申论训练' })

interface QuestionConfig {
  type: string
  prompt: string
  maxLength: number
  checks: string[]
}

const defaultQuestion: QuestionConfig = {
  type: '概括练习',
  prompt: '请用不超过120字，概括文章关注的核心问题与主要解决思路。',
  maxLength: 120,
  checks: ['对象和主题明确', '核心问题或成效清楚', '做法、原因有材料依据'],
}

const router = useRouter()
const { themeClass } = useThemeClass()
const dailyTaskStore = useDailyTaskStore()
const taskId = (router.params?.taskId || '').trim()
const loading = ref(true)
const hydrated = ref(false)
const savingDraft = ref(false)
const submitting = ref(false)
const answer = ref('')
const expression = ref('')
const application = ref('')
const checkedIndexes = ref<number[]>([])
let saveTimer: ReturnType<typeof setTimeout> | null = null

const task = computed(() => dailyTaskStore.tasks.find((item) => item.id === taskId) || null)
const question = computed<QuestionConfig>(() => {
  const value = task.value?.metadata?.question as Partial<QuestionConfig> | undefined
  return {
    type: String(value?.type || defaultQuestion.type),
    prompt: String(value?.prompt || defaultQuestion.prompt),
    maxLength: Number(value?.maxLength || defaultQuestion.maxLength),
    checks: Array.isArray(value?.checks) && value.checks.length ? value.checks : defaultQuestion.checks,
  }
})
const depositPrompt = computed(() =>
  String(task.value?.metadata?.depositPrompt || '写下今天最值得迁移的一个规范表达。'),
)
const answerLength = computed(() => answer.value.replace(/\s/g, '').length)
const stage = computed(() => (task.value?.progress.draft?.answerReady ? 'deposit' : 'answer'))

function taskDraft() {
  return task.value?.progress.draft || {}
}

function hydrateDraft() {
  const draft = taskDraft()
  answer.value = String(draft.answer || '')
  expression.value = String(draft.expression || '')
  application.value = String(draft.application || '')
  checkedIndexes.value = Array.isArray(draft.checkedIndexes)
    ? draft.checkedIndexes.map(Number).filter(Number.isInteger)
    : []
  hydrated.value = true
}

function toggleCheck(index: number) {
  checkedIndexes.value = checkedIndexes.value.includes(index)
    ? checkedIndexes.value.filter((item) => item !== index)
    : [...checkedIndexes.value, index]
}

async function saveAnswerDraft() {
  if (!task.value || task.value.progress.state !== 'in_progress') return
  savingDraft.value = true
  try {
    await dailyTaskStore.saveDraft(
      task.value.id,
      {
        ...taskDraft(),
        answer: answer.value,
        checkedIndexes: checkedIndexes.value,
      },
      Math.max(task.value.progress.currentStep, 2),
      task.value.totalSteps,
    )
  } catch {
    // 自动保存失败不打断输入，显式提交时会再次保存并给出反馈。
  } finally {
    savingDraft.value = false
  }
}

watch([answer, checkedIndexes], () => {
  if (!hydrated.value || stage.value !== 'answer') return
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(saveAnswerDraft, 700)
}, { deep: true })

async function submitAnswer() {
  if (!task.value) return
  if (answerLength.value < 20) {
    showToast('请至少写 20 字，形成完整概括')
    return
  }
  if (answerLength.value > question.value.maxLength) {
    showToast(`请压缩到 ${question.value.maxLength} 字以内`)
    return
  }
  if (checkedIndexes.value.length < 2) {
    showToast('请至少完成 2 项规则自检')
    return
  }
  if (saveTimer) clearTimeout(saveTimer)
  submitting.value = true
  try {
    await dailyTaskStore.saveDraft(
      task.value.id,
      {
        ...taskDraft(),
        answer: answer.value.trim(),
        checkedIndexes: checkedIndexes.value,
        answerReady: true,
      },
      3,
      task.value.totalSteps,
    )
    showToast('作答与自检已保存', 'success')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '作答保存失败', 'error')
  } finally {
    submitting.value = false
  }
}

async function finishTraining() {
  if (!task.value) return
  if (expression.value.trim().length < 4) {
    showToast('请留下一条可迁移的规范表达')
    return
  }
  submitting.value = true
  try {
    let state = task.value.progress.state
    if (state === 'in_progress') {
      await dailyTaskStore.saveDraft(
        task.value.id,
        {
          ...taskDraft(),
          expression: expression.value.trim(),
          application: application.value.trim(),
        },
        4,
        task.value.totalSteps,
      )
      const deposited = await api.addRmrbTerm({
        term: expression.value.trim(),
        category: '其他',
        usageNote: application.value.trim(),
        sourceTitle: task.value.title,
        articleId: task.value.contentId || null,
      })
      if (deposited.code !== 0) throw new Error(deposited.message || '表达沉淀失败')
      await dailyTaskStore.submit(task.value.id)
      state = 'submitted'
    }
    if (state === 'submitted') {
      await dailyTaskStore.markReviewed(task.value.id)
      state = 'reviewed'
    }
    if (state === 'reviewed') await dailyTaskStore.complete(task.value.id)
  } catch (error) {
    showToast(error instanceof Error ? error.message : '训练完成状态同步失败', 'error')
  } finally {
    submitting.value = false
  }
}

function backHome() {
  Taro.reLaunch({ url: '/pages/rmrb/index' })
}

onMounted(async () => {
  if (!task.value) await dailyTaskStore.load()
  hydrateDraft()
  loading.value = false
})

onUnmounted(() => {
  if (saveTimer) clearTimeout(saveTimer)
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-training { @include page-padding; padding-bottom: 36px; }
.state-card { @include card; color: $text-muted; margin-top: 24px; text-align: center; padding: 36px 20px; }
.state-title, .state-desc, .step-kicker, .step-heading, .step-lead, .check-title,
.check-note, .field-label, .complete-title, .complete-desc, .result-label,
.result-value { display: block; }
.state-title { color: $text-primary; font-size: 17px; font-weight: 700; }
.state-desc { margin-top: 8px; font-size: 13px; }
.step-head { padding: 14px 2px 20px; }
.step-kicker { color: $primary-color; font-size: 12px; font-weight: 600; margin-bottom: 8px; }
.step-heading { color: $text-primary; font-size: 23px; font-weight: 700; line-height: 1.4; }
.step-lead { color: $text-secondary; font-size: 14px; line-height: 1.7; margin-top: 10px; }
.answer-card, .check-card, .deposit-card { @include card; padding: 18px; }
.count-row { display: flex; justify-content: space-between; color: $text-muted; font-size: 11px; margin-top: 8px; }
.save-state { color: $text-muted; }
.over { color: $danger; }
.check-title { color: $text-primary; font-size: 15px; font-weight: 700; }
.check-note { color: $text-muted; font-size: 12px; margin: 5px 0 10px; }
.check-item { @include hit-target; width: 100%; justify-content: flex-start; gap: 10px; border-top: 1px solid $border-color; }
.check-box { width: 20px; height: 20px; border: 1px solid $border-color; border-radius: 6px; text-align: center; line-height: 20px; color: $on-primary; font-size: 12px; }
.check-box.checked { background: $primary-color; border-color: $primary-color; }
.check-copy { color: $text-secondary; font-size: 13px; }
.field-label { color: $text-primary; font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.field-label.second { margin-top: 18px; }
.closing-note { display: flex; justify-content: space-between; color: $text-muted; font-size: 11px; padding: 2px 2px 18px; }
.complete-mark { width: 52px; height: 52px; margin: 52px auto 18px; border-radius: 50%; background: $primary-light; color: $primary-color; text-align: center; line-height: 52px; font-size: 26px; font-weight: 700; }
.complete-title { color: $text-primary; font-size: 23px; font-weight: 700; text-align: center; }
.complete-desc { color: $text-muted; font-size: 13px; line-height: 1.65; text-align: center; margin: 10px 20px 24px; }
.result-card { @include card; padding: 20px; margin-bottom: 18px; }
.result-label { color: $primary-color; font-size: 11px; font-weight: 600; margin-bottom: 8px; }
.result-value { color: $text-primary; font-size: 16px; line-height: 1.7; }
</style>
