<template>
  <view class="page-theory page-with-tabbar" :class="themeClass">
    <view class="today-head">
      <text class="eyebrow">{{ todayLabel }} · 今日学习包</text>
      <text class="today-title">每天弄懂一个理论主题</text>
      <text class="today-subtitle">不是追新闻，而是理解规范表述、辨清选项边界</text>
    </view>

    <view v-if="dailyTaskStore.loading && !dailyTask" class="pack-card loading-card">
      正在准备今日学习包…
    </view>
    <view v-else-if="dailyTask" class="pack-card">
      <view class="pack-meta">
        <text class="source-badge">{{ taskSource }}</text>
        <text class="time-text">{{ dailyTask.estimatedMinutes }} 分钟</text>
      </view>
      <text class="pack-title">{{ dailyTask.title }}</text>
      <text class="pack-desc">{{ dailyTask.description }}</text>

      <view v-if="focuses.length" class="focus-row">
        <text v-for="focus in focuses" :key="focus" class="focus-chip">{{ focus }}</text>
      </view>

      <view class="fact-row">
        <view class="fact-item">
          <text class="fact-num">{{ questionCount }}</text>
          <text class="fact-label">审核题目</text>
        </view>
        <view class="fact-item">
          <text class="fact-num">{{ evidenceCount }}</text>
          <text class="fact-label">原文依据</text>
        </view>
        <view class="fact-item">
          <text class="fact-num">{{ dailyTask.totalSteps }}</text>
          <text class="fact-label">学习步骤</text>
        </view>
      </view>

      <view class="step-list">
        <view v-for="(step, index) in taskSteps" :key="step.key" class="step-item">
          <text class="step-index">{{ index + 1 }}</text>
          <view class="step-copy">
            <text class="step-title">{{ step.title }}</text>
            <text class="step-desc">{{ step.description }}</text>
          </view>
        </view>
      </view>

      <view class="evidence-note">
        <text class="evidence-dot">●</text>
        <text>进入学习包的题目均已审核，并关联原文依据</text>
      </view>
      <nut-button
        type="primary"
        block
        :loading="starting"
        :disabled="dailyTask.progress.state === 'completed'"
        @click="openPack"
      >
        {{ primaryActionText }}
      </nut-button>
    </view>
    <view v-else class="pack-card empty-card">
      <text class="empty-title">今日学习包正在审核</text>
      <text class="empty-desc">至少 3 道题全部具备原文依据后才会发布，不用未审核内容凑数。</text>
      <text class="text-link" @tap="switchTo('home')">先去专题学习</text>
    </view>

    <view class="section-head">
      <text class="section-title">学习入口</text>
      <text class="section-note">主任务之外，只保留必要去处</text>
    </view>
    <view class="quiet-links">
      <view class="quiet-link" @tap="go('/pages/review/hub')">
        <view>
          <text class="quiet-title">到期复习</text>
          <text class="quiet-desc">回收错题和易混表述</text>
        </view>
        <text class="quiet-arrow">›</text>
      </view>
      <view class="quiet-link" @tap="switchTo('home')">
        <view>
          <text class="quiet-title">理论专题</text>
          <text class="quiet-desc">按体系理解，不按热搜浏览</text>
        </view>
        <text class="quiet-arrow">›</text>
      </view>
      <view class="quiet-link" @tap="switchTo('quiz')">
        <view>
          <text class="quiet-title">证据刷题</text>
          <text class="quiet-desc">从原文依据辨析干扰项</text>
        </view>
        <text class="quiet-arrow">›</text>
      </view>
    </view>

    <AppTabBar active="today" />
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import AppTabBar from '@/components/AppTabBar.vue'
import { CURRENT_PRODUCT_TABS, type ProductTabKey } from '@/constants/productNavigation'
import { useDailyTaskStore } from '@/store/dailyTask'
import { useThemeClass } from '@/utils/brandColor'
import { showToast } from '@/utils/platform'

definePageConfig({ navigationBarTitleText: '知行政治理论' })

interface PackStep {
  key: string
  title: string
  description: string
}

const fallbackSteps: PackStep[] = [
  { key: 'orient', title: '读前定向', description: '先看主体、行动与限定条件' },
  { key: 'read', title: '原文精读', description: '理解规范表述和知识位置' },
  { key: 'quiz', title: '证据刷题', description: '每道题都回到原文依据' },
  { key: 'review', title: '错因回收', description: '辨清偷换、扩大与程度变化' },
]

const { themeClass } = useThemeClass()
const dailyTaskStore = useDailyTaskStore()
const starting = ref(false)
const dailyTask = computed(() => dailyTaskStore.activeTask || dailyTaskStore.tasks[0] || null)
const todayLabel = computed(() => {
  const date = new Date()
  return `${date.getMonth() + 1}月${date.getDate()}日`
})
const taskSource = computed(() => String(dailyTask.value?.metadata?.source || '权威来源'))
const focuses = computed(() => {
  const raw = dailyTask.value?.metadata?.focuses
  return Array.isArray(raw) ? raw.map(String).filter(Boolean).slice(0, 3) : []
})
const questionCount = computed(() => Number(dailyTask.value?.metadata?.questionCount || 0))
const evidenceCount = computed(() => Number(dailyTask.value?.metadata?.evidenceCount || 0))
const taskSteps = computed<PackStep[]>(() => {
  const raw = dailyTask.value?.metadata?.steps
  return Array.isArray(raw) && raw.length ? (raw as PackStep[]) : fallbackSteps
})
const primaryActionText = computed(() => {
  const state = dailyTask.value?.progress.state
  if (state === 'completed') return '今日学习已完成'
  if (state === 'not_started') return '开始今日学习'
  return '继续今日学习'
})

function go(url: string) {
  Taro.navigateTo({ url })
}

function switchTo(key: ProductTabKey) {
  const tab = CURRENT_PRODUCT_TABS.find((item) => item.key === key)
  if (tab) Taro.switchTab({ url: tab.path })
}

async function openPack() {
  const task = dailyTask.value
  if (!task || task.progress.state === 'completed') return
  starting.value = true
  try {
    if (task.progress.state === 'not_started') await dailyTaskStore.start(task.id)
    const query = `id=${encodeURIComponent(task.contentId)}&taskId=${encodeURIComponent(task.id)}`
    Taro.navigateTo({ url: `/pages/theory/pack?${query}` })
  } catch (error) {
    showToast(error instanceof Error ? error.message : '学习包启动失败', 'error')
  } finally {
    starting.value = false
  }
}

function load() {
  return dailyTaskStore.load()
}

onMounted(load)
useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-theory { @include page-padding; padding-bottom: 108px; }
.today-head { padding: 12px 2px 20px; }
.eyebrow, .today-title, .today-subtitle, .pack-title, .pack-desc, .fact-num,
.fact-label, .step-title, .step-desc, .empty-title, .empty-desc, .section-title,
.section-note, .quiet-title, .quiet-desc { display: block; }
.eyebrow { color: $primary-color; font-size: 12px; font-weight: 600; margin-bottom: 8px; }
.today-title { color: $text-primary; font-size: 23px; font-weight: 700; line-height: 1.4; }
.today-subtitle { color: $text-muted; font-size: 13px; line-height: 1.6; margin-top: 7px; }
.pack-card { @include card; border-radius: $radius-lg; padding: 20px; }
.loading-card { min-height: 180px; display: flex; align-items: center; justify-content: center; color: $text-muted; }
.pack-meta { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.source-badge { color: $primary-color; background: $primary-light; border-radius: 5px; padding: 4px 8px; font-size: 11px; font-weight: 600; }
.time-text { color: $text-muted; font-size: 12px; }
.pack-title { color: $text-primary; font-size: 20px; font-weight: 700; line-height: 1.5; }
.pack-desc { color: $text-secondary; font-size: 13px; line-height: 1.65; margin-top: 8px; }
.focus-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.focus-chip { color: $text-secondary; background: $elevated; border-radius: 4px; padding: 3px 8px; font-size: 11px; }
.fact-row { display: flex; padding: 17px 0; margin-top: 16px; border-top: 1px solid $border-color; border-bottom: 1px solid $border-color; }
.fact-item { flex: 1; text-align: center; }
.fact-item + .fact-item { border-left: 1px solid $border-color; }
.fact-num { color: $text-primary; font-size: 18px; font-weight: 700; }
.fact-label { color: $text-muted; font-size: 11px; margin-top: 3px; }
.step-list { padding: 10px 0; }
.step-item { display: flex; gap: 11px; padding: 8px 0; }
.step-index { width: 20px; height: 20px; color: $primary-color; background: $primary-light; border-radius: 50%; text-align: center; line-height: 20px; font-size: 10px; font-weight: 700; }
.step-copy { flex: 1; min-width: 0; }
.step-title { color: $text-primary; font-size: 13px; font-weight: 600; }
.step-desc { color: $text-muted; font-size: 11px; margin-top: 2px; }
.evidence-note { display: flex; align-items: center; gap: 6px; color: $text-muted; font-size: 11px; background: $elevated; border-radius: 7px; padding: 9px 10px; margin-bottom: 14px; }
.evidence-dot { color: $success; font-size: 8px; }
.empty-card { padding: 26px 20px; }
.empty-title { color: $text-primary; font-size: 17px; font-weight: 700; }
.empty-desc { color: $text-muted; font-size: 13px; line-height: 1.65; margin: 8px 0 16px; }
.text-link { color: $primary-color; font-size: 13px; font-weight: 600; }
.section-head { display: flex; justify-content: space-between; align-items: flex-end; padding: 18px 2px 10px; }
.section-title { color: $text-primary; font-size: 16px; font-weight: 700; }
.section-note { color: $text-muted; font-size: 11px; }
.quiet-links { @include card; padding: 2px 16px; }
.quiet-link { @include hit-target; width: 100%; justify-content: space-between; border-bottom: 1px solid $border-color; }
.quiet-link:last-child { border-bottom: 0; }
.quiet-title { color: $text-primary; font-size: 14px; font-weight: 600; }
.quiet-desc { color: $text-muted; font-size: 11px; margin-top: 3px; }
.quiet-arrow { color: $text-muted; font-size: 22px; font-weight: 300; }
</style>
