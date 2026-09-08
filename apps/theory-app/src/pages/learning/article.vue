<template>
  <view class="al-page">
    <view v-if="loading" class="al-state">正在加载学习内容…</view>
    <view v-else-if="error" class="al-state">
      <text>{{ error }}</text>
      <nut-button plain type="primary" @click="load">重新加载</nut-button>
    </view>
    <template v-else-if="bundle">
      <view class="al-head">
        <text class="al-kicker">时政学习 · {{ bundle.article.publishDate }}</text>
        <text class="al-title">{{ bundle.article.title }}</text>
        <text class="al-note">{{ bundle.article.source }} · 免费阅读与练习</text>
      </view>
      <view class="al-card">
        <text class="al-label">选择学习范围</text>
        <view class="al-choices">
          <button
            v-for="part in bundle.parts" :key="part.number" class="al-chip"
            :class="{ active: scope === String(part.number) }" :disabled="submitting"
            @tap="chooseScope(String(part.number))"
          >
            第 {{ part.number }} 辑 · {{ part.questionIds.length }} 题
          </button>
          <button
            v-if="bundle.collectionComplete" class="al-chip" :class="{ active: scope === 'all' }"
            :disabled="submitting" @tap="chooseScope('all')"
          >
            全文合集 · {{ bundle.questions.length }} 题
          </button>
        </view>
        <text v-if="!bundle.questions.length" class="al-note">题目审核准备中，可以先阅读。</text>
        <text v-else-if="!bundle.collectionComplete" class="al-note">当前仅开放已审核分辑，全文合集尚未就绪。</text>
        <view class="al-choices">
          <button class="al-chip" :class="{ active: view === 'full' }" @tap="view = 'full'">阅读全文</button>
          <button class="al-chip" :class="{ active: view === 'focus' }" @tap="view = 'focus'">读重点</button>
        </view>
        <nut-button v-if="selectedQuestions.length" type="primary" block :disabled="submitting" @click="start">
          {{ completed === selectedQuestions.length ? '查看本组结果' : completed ? '继续答题' : '开始答题' }}（{{ completed }}/{{ selectedQuestions.length }}）
        </nut-button>
      </view>
      <view v-if="view === 'full'" class="al-card">
        <text class="al-label">原文 · {{ bundle.article.source }}</text>
        <text class="al-body">{{ bundle.article.content || '暂未提供全文' }}</text>
      </view>
      <view v-if="view === 'focus'" class="al-card">
        <text class="al-label">学习重点 · 摘要</text>
        <text class="al-body">{{ bundle.article.summary || '暂无审核后的重点摘要，请阅读原文。' }}</text>
      </view>
      <view v-if="view === 'quiz' && current" class="al-card">
        <view class="al-row">
          <text class="al-label">{{ index + 1 }} / {{ selectedQuestions.length }}</text>
          <text class="al-note">{{ record ? (record.correct ? '回答正确' : '需要复习') : '选择后查看解析' }}</text>
        </view>
        <QuestionItem
          :key="`${current.id}-${Boolean(record)}`" :question="displayQuestion"
          :readonly="submitting" :show-result="Boolean(record)" :selected-answer="record?.answer ?? pending"
          @answer="answer" @change="savePending"
        />
        <view class="al-row">
          <nut-button plain type="primary" :disabled="index === 0 || submitting" @click="previous">上一题</nut-button>
          <nut-button type="primary" :loading="submitting" :disabled="submitting" @click="next">
            {{ !record && current.type === 'multiple' ? '提交答案' : index === selectedQuestions.length - 1 ? '查看结果' : '下一题' }}
          </nut-button>
        </view>
      </view>
      <view v-if="view === 'result'" class="al-card">
        <text class="al-label">本组已完成 {{ completed }} / {{ selectedQuestions.length }} 题 · 答对 {{ correctCount }} 题</text>
        <button v-for="(question, position) in selectedQuestions" :key="question.id" class="al-result" @tap="review(position)">
          {{ position + 1 }}. {{ records[question.id] ? records[question.id].correct ? '正确' : '待复习' : '未作答' }} · {{ question.stem }}
        </button>
        <nut-button plain type="primary" @click="restart">重新练习本组</nut-button>
      </view>
      <text class="al-note al-storage">{{ storageNote }}</text>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import QuestionItem from '@/components/QuestionItem.vue'
import { api, type AnswerResult, type LearningBundle } from '@/api'
import { showConfirm, showToast } from '@/utils/platform'

definePageConfig({ navigationBarTitleText: '时政学习' })
type RecordItem = AnswerResult & { sourceSentence: string; answer: string | string[] }
const router = useRouter()
const articleId = (router.params?.articleId || '').trim()
const bundle = ref<LearningBundle | null>(null)
const loading = ref(true)
const error = ref('')
const submitting = ref(false)
const scope = ref('1')
const view = ref<'full' | 'focus' | 'quiz' | 'result'>('focus')
const index = ref(0)
const drafts = ref<Record<string, string[]>>({})
const records = ref<Record<string, RecordItem>>({})
const storageNote = ref('练习记录仅保存在此设备，暂未接通账号同步；清理缓存会丢失记录。')
const storageKey = computed(() => `theory-learning:${articleId}:${bundle.value?.revision}`)
const selectedQuestions = computed(() => {
  if (!bundle.value) return []
  if (scope.value === 'all') return bundle.value.questions
  const ids = bundle.value.parts.find(part => String(part.number) === scope.value)?.questionIds || []
  return bundle.value.questions.filter(question => ids.includes(question.id))
})
const current = computed(() => selectedQuestions.value[index.value])
const pending = computed(() => current.value ? drafts.value[current.value.id] || [] : [])
const record = computed(() => current.value ? records.value[current.value.id] : undefined)
const displayQuestion = computed(() => ({
  ...current.value!, correctAnswer: record.value?.correctAnswer || '',
  analysis: record.value?.analysis || '', sourceSentence: record.value?.sourceSentence || '',
}))
const completed = computed(() => selectedQuestions.value.filter(question => records.value[question.id]).length)
const correctCount = computed(() => selectedQuestions.value.filter(question => records.value[question.id]?.correct).length)

function save() {
  try { Taro.setStorageSync(storageKey.value, { records: records.value, drafts: drafts.value, scope: scope.value, index: index.value, updatedAt: new Date().toISOString() }) }
  catch { storageNote.value = '本机存储失败，离开页面后可能丢失进度。请检查设备存储空间。' }
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    if (!articleId) throw new Error('学习链接缺少文章，请从文章列表进入')
    const response = await api.getLearningBundle(articleId)
    if (response.code !== 0 || !response.data) throw new Error(response.message)
    bundle.value = response.data
    records.value = {}
    drafts.value = {}
    let saved: { records?: Record<string, RecordItem>; drafts?: Record<string, string[]>; scope?: string; index?: number } = {}
    try { saved = Taro.getStorageSync(storageKey.value) || {} } catch { /* Reading remains available without storage. */ }
    for (const question of bundle.value.questions) {
      const draft = saved.drafts?.[question.id]
      if (Array.isArray(draft)) drafts.value[question.id] = draft.filter(value => question.options?.includes(value))
    }
    if (saved.records && typeof saved.records === 'object') {
      for (const question of bundle.value.questions) {
        const value = saved.records[question.id]
        if (value && typeof value.correct === 'boolean' && typeof value.analysis === 'string'
          && (typeof value.answer === 'string' || Array.isArray(value.answer))) records.value[question.id] = value
      }
    }
    const preferred = router.params?.scope || saved.scope || '1'
    scope.value = preferred === 'all' && bundle.value.collectionComplete ? 'all'
      : bundle.value.parts.some(part => String(part.number) === preferred) ? preferred : '1'
    index.value = Number.isInteger(saved.index) && saved.scope === scope.value
      ? Math.max(0, Math.min(saved.index!, selectedQuestions.value.length - 1)) : 0
    view.value = router.params?.view === 'full' ? 'full' : 'focus'
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '加载失败，请重试' }
  finally { loading.value = false }
}
function chooseScope(value: string) {
  if (submitting.value) return
  scope.value = value
  index.value = 0
  save()
}
function start() {
  if (completed.value === selectedQuestions.value.length) { view.value = 'result'; return }
  index.value = selectedQuestions.value.findIndex(question => !records.value[question.id])
  view.value = 'quiz'
  save()
}
async function answer(value: string | string[]) {
  if (!current.value || !bundle.value || record.value || submitting.value) return
  const questionId = current.value.id
  submitting.value = true
  try {
    const response = await api.checkLearningAnswer(articleId, bundle.value.revision, questionId, value)
    if (response.code !== 0 || !response.data) {
      if (response.code === 409 || response.code === 404) error.value = response.message
      showToast(response.message || '提交失败，请重试', 'error')
      return
    }
    records.value[questionId] = { ...response.data, answer: value }
    save()
  } finally { submitting.value = false }
}
function savePending(value: string[]) {
  if (!current.value || record.value || submitting.value) return
  drafts.value[current.value.id] = value
  save()
}
function previous() { if (index.value > 0) { index.value--; save() } }
function review(position: number) { index.value = position; view.value = 'quiz'; save() }
async function next() {
  if (!record.value) {
    if (current.value?.type === 'multiple' && pending.value.length >= 2) await answer([...pending.value])
    else showToast('请先完成当前题目')
    return
  }
  if (index.value === selectedQuestions.value.length - 1) view.value = 'result'
  else index.value++
  save()
}
async function restart() {
  if (!await showConfirm('重新练习', '将清除本机本组作答；同一题在其他分辑或合集中的结果也会重置。继续吗？')) return
  for (const question of selectedQuestions.value) {
    delete records.value[question.id]
    delete drafts.value[question.id]
  }
  index.value = 0
  view.value = 'quiz'
  save()
}
onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
.al-page { @include page-padding; padding-bottom: calc(32px + env(safe-area-inset-bottom)); }
.al-state { @include page-state-box; }
.al-head { padding: 8px 0 20px; }
.al-title { display: block; font-size: 22px; font-weight: 700; color: $text-primary; line-height: 1.5; margin: 8px 0; }
.al-kicker { color: $primary-color; font-size: 12px; }
.al-card { @include card; }
.al-label { display: block; color: $text-primary; font-size: 15px; font-weight: 600; margin-bottom: 12px; }
.al-note { display: block; color: $text-muted; font-size: 12px; line-height: 1.7; }
.al-choices { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.al-chip { @include hit-target; margin: 0; padding: 8px 12px; border: 1px solid $border-color; border-radius: 10px; background: $card-bg; color: $text-secondary; font-size: 13px; line-height: 26px; }
.al-chip.active { border-color: $primary-color; color: $primary-color; background: $primary-light; }
.al-chip::after, .al-result::after { border: none; }
.al-body { display: block; white-space: pre-wrap; font-size: 16px; line-height: 1.9; color: $text-primary; }
.al-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-top: 12px; }
.al-result { @include hit-target; display: block; width: 100%; padding: 12px; margin-bottom: 8px; text-align: left; background: $elevated; color: $text-primary; font-size: 14px; line-height: 1.6; border: none; }
.al-storage { margin-top: 16px; }
</style>
