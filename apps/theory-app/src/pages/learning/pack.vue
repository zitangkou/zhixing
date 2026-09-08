<template>
  <view class="page-pack">
    <view v-if="loading" class="state-card">正在恢复学习包…</view>
    <view v-else-if="!task || !pretestQuestions.length" class="state-card">
      <text class="state-title">学习包内容不完整</text>
      <text class="state-desc">请返回今日页，等待教研审核完成。</text>
    </view>
    <template v-else>
      <view class="step-head">
        <text class="step-kicker">第 1 步 · 读前定向</text>
        <text class="step-title">先暴露直觉，再带着问题读</text>
        <text class="step-desc">这里只记录你的第一判断，不揭答案、不计入错题。</text>
      </view>

      <view v-for="(question, qIndex) in pretestQuestions" :key="question.id" class="question-card">
        <view class="question-meta">
          <text>定向 {{ qIndex + 1 }}</text>
          <text>{{ typeLabel(question.type) }}</text>
        </view>
        <text class="question-stem">{{ question.stem }}</text>
        <view class="options">
          <view
            v-for="(option, index) in question.options || []"
            :key="option"
            class="option"
            :class="{ selected: selected(question.id, option) }"
            @tap="select(question, option)"
          >
            <text class="option-key">{{ String.fromCharCode(65 + index) }}</text>
            <text class="option-copy">{{ option }}</text>
          </view>
        </view>
      </view>

      <view class="reading-focus">
        <text class="focus-title">等会儿重点看</text>
        <view v-for="item in readingFocuses" :key="item" class="focus-item">
          <text class="focus-dot">·</text><text>{{ item }}</text>
        </view>
      </view>
      <nut-button type="primary" block :loading="saving" @click="startReading">
        带着问题读原文
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
import type { Question } from '@/api'
import { showToast } from '@/utils/platform'

definePageConfig({ navigationBarTitleText: '读前定向' })

const router = useRouter()
const dailyTaskStore = useDailyTaskStore()
const taskId = (router.params?.taskId || '').trim()
const loading = ref(true)
const saving = ref(false)
const questions = ref<Question[]>([])
const answers = ref<Record<string, string[]>>({})
const task = computed(() => dailyTaskStore.tasks.find((item) => item.id === taskId) || null)
const pretestQuestions = computed(() => questions.value.slice(0, 2))
const readingFocuses = computed(() => {
  const focuses = task.value?.metadata?.focuses
  const items = Array.isArray(focuses) ? focuses.map(String).filter(Boolean) : []
  return [
    items.length ? `主题边界：${items.join('、')}` : '主题对应的主体和适用范围',
    '原文中的行动、目标与程度限定',
    '哪些相近表述容易被偷换或扩大',
  ]
})

function typeLabel(type: Question['type']) {
  return { single: '单选', multiple: '多选', judge: '判断' }[type]
}

function selected(questionId: string, option: string) {
  return answers.value[questionId]?.includes(option) || false
}

function select(question: Question, option: string) {
  const current = answers.value[question.id] || []
  answers.value = {
    ...answers.value,
    [question.id]:
      question.type === 'multiple'
        ? current.includes(option)
          ? current.filter((item) => item !== option)
          : [...current, option]
        : [option],
  }
}

async function startReading() {
  if (!task.value) return
  const missing = pretestQuestions.value.some((question) => !answers.value[question.id]?.length)
  if (missing) {
    showToast('请先完成两道第一判断')
    return
  }
  saving.value = true
  try {
    await dailyTaskStore.saveDraft(
      task.value.id,
      {
        ...task.value.progress.draft,
        pretestAnswers: answers.value,
        pretestCompleted: true,
      },
      1,
      task.value.totalSteps,
    )
    const query = `id=${encodeURIComponent(task.value.contentId)}&taskId=${encodeURIComponent(task.value.id)}`
    Taro.redirectTo({ url: `/pages/article/detail?${query}` })
  } catch (error) {
    showToast(error instanceof Error ? error.message : '读前判断保存失败', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (!task.value) await dailyTaskStore.load()
  if (task.value) {
    const saved = task.value.progress.draft?.pretestAnswers
    if (saved && typeof saved === 'object') answers.value = saved as Record<string, string[]>
    const result = await api.getQuestions(task.value.contentId)
    if (result.code === 0 && result.data) questions.value = result.data
  }
  loading.value = false
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-pack { @include page-padding; padding-bottom: 36px; }
.state-card { @include card; text-align: center; color: $text-muted; margin-top: 24px; padding: 36px 20px; }
.state-title, .state-desc, .step-kicker, .step-title, .step-desc, .question-stem,
.focus-title { display: block; }
.state-title { color: $text-primary; font-size: 17px; font-weight: 700; }
.state-desc { margin-top: 8px; font-size: 13px; }
.step-head { padding: 14px 2px 20px; }
.step-kicker { color: $primary-color; font-size: 12px; font-weight: 600; margin-bottom: 8px; }
.step-title { color: $text-primary; font-size: 23px; font-weight: 700; line-height: 1.4; }
.step-desc { color: $text-muted; font-size: 13px; line-height: 1.6; margin-top: 8px; }
.question-card { @include card; padding: 18px; }
.question-meta { display: flex; justify-content: space-between; color: $primary-color; font-size: 11px; font-weight: 600; margin-bottom: 10px; }
.question-stem { color: $text-primary; font-size: 15px; line-height: 1.7; font-weight: 600; }
.options { margin-top: 14px; }
.option { display: flex; align-items: flex-start; gap: 9px; background: $elevated; border: 1px solid $border-color; border-radius: 9px; padding: 11px 12px; margin-top: 8px; }
.option.selected { border-color: $primary-color; background: $primary-light; }
.option-key { color: $primary-color; font-size: 12px; font-weight: 700; line-height: 21px; }
.option-copy { flex: 1; color: $text-secondary; font-size: 13px; line-height: 1.6; }
.reading-focus { @include card; padding: 18px; }
.focus-title { color: $text-primary; font-size: 14px; font-weight: 700; margin-bottom: 8px; }
.focus-item { display: flex; gap: 8px; color: $text-secondary; font-size: 13px; line-height: 1.65; padding: 3px 0; }
.focus-dot { color: $primary-color; font-weight: 700; }
</style>
