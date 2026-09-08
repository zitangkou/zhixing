<template>
  <view class="page-rmrb" :class="[themeClass, { 'vertical-home': IS_SHENLUN_PRODUCT }]">
    <template v-if="IS_SHENLUN_PRODUCT">
      <view class="today-head">
        <text class="eyebrow">{{ todayLabel }} · 今日训练</text>
        <text class="today-title">每天吃透一篇，表达自然有根</text>
        <text class="today-subtitle">一次只做一件事，约 {{ dailyTaskStore.estimatedMinutes || 15 }} 分钟</text>
      </view>

      <view v-if="dailyTaskStore.loading && !dailyTask" class="task-card task-loading">
        <text>正在准备今日内容…</text>
      </view>
      <view v-else-if="dailyTask" class="task-card">
        <view class="task-meta">
          <text class="task-source">{{ taskSource }}</text>
          <text class="task-time">{{ dailyTask.estimatedMinutes }} 分钟</text>
        </view>
        <text class="task-title">{{ dailyTask.title }}</text>
        <text class="task-desc">{{ dailyTask.description }}</text>
        <view class="progress-row">
          <view class="progress-track">
            <view class="progress-fill" :style="{ width: `${taskProgress}%` }" />
          </view>
          <text class="progress-text">{{ progressLabel }}</text>
        </view>
        <view class="step-list">
          <view v-for="(step, index) in taskSteps" :key="step.key" class="step-item">
            <text class="step-index">{{ String(index + 1).padStart(2, '0') }}</text>
            <view class="step-copy">
              <text class="step-title">{{ step.title }}</text>
              <text class="step-desc">{{ step.description }}</text>
            </view>
          </view>
        </view>
        <nut-button
          type="primary"
          block
          :loading="starting"
          :disabled="dailyTask.progress.state === 'completed'"
          @click="openDailyTask"
        >
          {{ primaryActionText }}
        </nut-button>
      </view>
      <view v-else class="task-card empty-card">
        <text class="empty-title">今日内容正在准备</text>
        <text class="empty-desc">内容需经过教研审核后才会进入每日训练。</text>
        <text class="text-link" @tap="go('/pages/rmrb/article-list')">先去文章库学习</text>
      </view>

      <view class="section-head">
        <text class="section-title">学习沉淀</text>
        <text class="section-note">不追求多，只看是否真正留下</text>
      </view>
      <view class="insight-card">
        <view class="insight-item">
          <text class="insight-num">{{ stats?.weekMineDays || 0 }}</text>
          <text class="insight-label">本周精练</text>
        </view>
        <view class="insight-item">
          <text class="insight-num">{{ stats?.termCount || 0 }}</text>
          <text class="insight-label">规范表达</text>
        </view>
        <view class="insight-item">
          <text class="insight-num">{{ stats?.weekDrillCount || 0 }}</text>
          <text class="insight-label">迁移训练</text>
        </view>
      </view>
      <view class="quiet-links">
        <view class="quiet-link" @tap="go('/pages/rmrb/mines')">
          <text>开采本</text><text class="quiet-arrow">›</text>
        </view>
        <view class="quiet-link" @tap="go('/pages/rmrb/terms')">
          <text>规范词库</text><text class="quiet-arrow">›</text>
        </view>
        <view class="quiet-link" @tap="go('/pages/rmrb/drill')">
          <text>专项训练</text><text class="quiet-arrow">›</text>
        </view>
      </view>
    </template>

    <template v-else>
      <view v-if="stats" class="hero-card">
        <view class="hero-item">
          <text class="hero-num">{{ stats.weekMineDays }}/{{ stats.weekMineTarget }}</text>
          <text class="hero-label">本周开采</text>
        </view>
        <view class="hero-item">
          <text class="hero-num">{{ stats.termCount }}</text>
          <text class="hero-label">规范词</text>
        </view>
        <view class="hero-item">
          <text class="hero-num">{{ stats.todayMined ? '✓' : '—' }}</text>
          <text class="hero-label">今日</text>
        </view>
      </view>
      <view class="method-tip">三刀解剖（骨架 → 规范词 / 金句 / 动词 / 句式）→ 阶梯训练（造句 · 仿写 · 口述）</view>
      <view class="entry-grid">
        <view class="entry-item" @tap="go('/pages/rmrb/article-list')">
          <text class="entry-name">时评阅读</text><text class="entry-desc">精读 + 三刀解剖</text>
        </view>
        <view class="entry-item" @tap="go('/pages/rmrb/mines')">
          <text class="entry-name">开采本</text><text class="entry-desc">每日一行记录</text>
        </view>
        <view class="entry-item" @tap="go('/pages/rmrb/terms')">
          <text class="entry-name">规范词库</text><text class="entry-desc">{{ stats?.learningTermCount || 0 }} 学习中</text>
        </view>
        <view class="entry-item" @tap="go('/pages/rmrb/drill')">
          <text class="entry-name">阶梯训练</text><text class="entry-desc">本周 {{ stats?.weekDrillCount || 0 }} 次</text>
        </view>
      </view>
    </template>
    <AppTabBar v-if="IS_SHENLUN_PRODUCT" active="today" />
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import AppTabBar from '@/components/AppTabBar.vue'
import { api } from '@/api'
import { IS_SHENLUN_PRODUCT } from '@/constants/product'
import { useDailyTaskStore } from '@/store/dailyTask'
import type { ShenlunStats } from '@/types'
import { useThemeClass } from '@/utils/brandColor'
import { showToast } from '@/utils/platform'

definePageConfig({ navigationBarTitleText: '知行申论' })

interface TaskStep {
  key: string
  title: string
  description: string
}

const fallbackSteps: TaskStep[] = [
  { key: 'read', title: '精读定位', description: '读懂主题、对象与核心问题' },
  { key: 'analyze', title: '三刀拆解', description: '拆骨架、抓规范表达、学句式' },
  { key: 'answer', title: '小题作答', description: '围绕材料完成一次短作答' },
  { key: 'deposit', title: '表达沉淀', description: '留下一个可迁移表达' },
]

const { themeClass } = useThemeClass()
const dailyTaskStore = useDailyTaskStore()
const stats = ref<ShenlunStats | null>(null)
const starting = ref(false)
const dailyTask = computed(() => dailyTaskStore.activeTask || dailyTaskStore.tasks[0] || null)
const todayLabel = computed(() => {
  const date = new Date()
  return `${date.getMonth() + 1}月${date.getDate()}日`
})
const taskSource = computed(() => String(dailyTask.value?.metadata?.source || '人民时评'))
const taskSteps = computed<TaskStep[]>(() => {
  const raw = dailyTask.value?.metadata?.steps
  return Array.isArray(raw) && raw.length ? (raw as TaskStep[]) : fallbackSteps
})
const taskProgress = computed(() => {
  const progress = dailyTask.value?.progress
  if (!progress) return 0
  if (progress.state === 'completed') return 100
  return Math.round((progress.currentStep * 100) / Math.max(progress.totalSteps, 1))
})
const progressLabel = computed(() => {
  const state = dailyTask.value?.progress.state
  if (state === 'completed') return '今日完成'
  if (state === 'reviewed') return '反馈已生成'
  if (state === 'submitted') return '等待反馈'
  if (state === 'in_progress') {
    return `已到第 ${Math.max(dailyTask.value?.progress.currentStep || 1, 1)} 步`
  }
  return '尚未开始'
})
const primaryActionText = computed(() => {
  const state = dailyTask.value?.progress.state
  if (state === 'completed') return '今日训练已完成'
  if (state === 'not_started') return '开始今日训练'
  return '继续今日训练'
})

function go(url: string) {
  Taro.navigateTo({ url })
}

async function openDailyTask() {
  const task = dailyTask.value
  if (!task || task.progress.state === 'completed') return
  starting.value = true
  try {
    if (task.progress.state === 'not_started') await dailyTaskStore.start(task.id)
    const query = `id=${encodeURIComponent(task.contentId)}&taskId=${encodeURIComponent(task.id)}`
    Taro.navigateTo({ url: `/pages/rmrb/article-detail?${query}` })
  } catch (error) {
    showToast(error instanceof Error ? error.message : '训练启动失败', 'error')
  } finally {
    starting.value = false
  }
}

async function load() {
  const requests: Promise<unknown>[] = [
    api.getRmrbStats().then((res) => {
      if (res.code === 0 && res.data) stats.value = res.data
    }),
  ]
  if (IS_SHENLUN_PRODUCT) requests.push(dailyTaskStore.load())
  await Promise.all(requests)
}

onMounted(load)
useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-rmrb { @include page-padding; padding-bottom: 32px; }
.page-rmrb.vertical-home { padding-bottom: 104px; }
.today-head { padding: 12px 2px 20px; }
.eyebrow, .today-title, .today-subtitle, .task-source, .task-time, .task-title,
.task-desc, .step-title, .step-desc, .empty-title, .empty-desc, .section-title,
.section-note, .insight-num, .insight-label { display: block; }
.eyebrow { color: $primary-color; font-size: 12px; font-weight: 600; margin-bottom: 8px; }
.today-title { color: $text-primary; font-size: 23px; font-weight: 700; line-height: 1.4; }
.today-subtitle { color: $text-muted; font-size: 13px; margin-top: 7px; }
.task-card { @include card; border-radius: $radius-lg; padding: 20px; }
.task-loading { color: $text-muted; min-height: 160px; display: flex; align-items: center; justify-content: center; }
.task-meta { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.task-source { color: $primary-color; font-size: 12px; font-weight: 600; }
.task-time { color: $text-muted; font-size: 12px; }
.task-title { color: $text-primary; font-size: 20px; font-weight: 700; line-height: 1.5; }
.task-desc { color: $text-secondary; font-size: 13px; line-height: 1.65; margin-top: 8px; }
.progress-row { display: flex; align-items: center; gap: 10px; margin: 18px 0; }
.progress-track { flex: 1; height: 4px; background: $elevated; border-radius: 4px; overflow: hidden; }
.progress-fill { height: 100%; background: $primary-color; border-radius: 4px; transition: width 200ms ease; }
.progress-text { color: $text-muted; font-size: 11px; white-space: nowrap; }
.step-list { border-top: 1px solid $border-color; padding: 10px 0 16px; }
.step-item { display: flex; gap: 12px; padding: 9px 0; }
.step-index { color: $primary-color; font-size: 11px; font-weight: 700; line-height: 20px; }
.step-copy { flex: 1; min-width: 0; }
.step-title { color: $text-primary; font-size: 14px; font-weight: 600; }
.step-desc { color: $text-muted; font-size: 12px; line-height: 1.5; margin-top: 2px; }
.empty-card { padding: 26px 20px; }
.empty-title { color: $text-primary; font-size: 17px; font-weight: 700; }
.empty-desc { color: $text-muted; font-size: 13px; line-height: 1.6; margin: 8px 0 16px; }
.text-link { color: $primary-color; font-size: 13px; font-weight: 600; }
.section-head { display: flex; justify-content: space-between; align-items: flex-end; padding: 18px 2px 10px; }
.section-title { color: $text-primary; font-size: 16px; font-weight: 700; }
.section-note { color: $text-muted; font-size: 11px; }
.insight-card { @include card; display: flex; padding: 16px 8px; }
.insight-item { flex: 1; text-align: center; }
.insight-item + .insight-item { border-left: 1px solid $border-color; }
.insight-num { color: $text-primary; font-size: 19px; font-weight: 700; }
.insight-label { color: $text-muted; font-size: 11px; margin-top: 4px; }
.quiet-links { @include card; padding: 2px 16px; }
.quiet-link { @include hit-target; width: 100%; justify-content: space-between; color: $text-secondary; font-size: 14px; border-bottom: 1px solid $border-color; }
.quiet-link:last-child { border-bottom: 0; }
.quiet-arrow { color: $text-muted; font-size: 22px; font-weight: 300; }
.hero-card {
  @include card;
  display: flex;
  padding: 14px 12px;
  margin-bottom: 12px;
  .hero-item {
    flex: 1;
    text-align: center;
    padding: 0 4px;
    & + .hero-item { border-left: 1px solid $border-color; }
    .hero-num { display: block; font-size: 20px; font-weight: 700; color: $primary-color; }
    .hero-label { font-size: 12px; color: $text-muted; margin-top: 2px; }
  }
}
.method-tip {
  font-size: 12px;
  color: $text-muted;
  line-height: 1.55;
  margin: 0 0 14px;
  padding: 10px 12px;
  background: $elevated;
  border-radius: $radius-md;
  border: 1px solid $border-color;
}
.entry-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.entry-item {
  @include card;
  padding: 14px 12px;
  margin-bottom: 0;
  .entry-name { display: block; font-size: 15px; font-weight: 700; margin-bottom: 4px; }
  .entry-desc { font-size: 12px; color: $text-muted; line-height: 1.35; }
}
</style>
