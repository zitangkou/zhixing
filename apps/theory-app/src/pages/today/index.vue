<template>
  <view class="page">
    <view class="card today-entry">
      <view class="eyebrow">知行日知</view>
      <view class="card-title">时政学习 · 免费阅读与练习</view>
      <view class="card-desc">每次五题，也可练习全文合集；先读全文或重点，由你选择。</view>
      <view class="today-entry-action" @tap="openArticles">选择文章开始学习</view>
    </view>
    <template v-if="loggedIn">
      <view class="eyebrow">{{ todayLabel }} · 今日一课</view><view class="page-title">理解一个主题，辨清一组表述</view>
      <view v-if="store.loading && !store.task" class="card state-card">正在准备个人学习记录…</view>
      <view v-else-if="store.task" class="hero">
        <view class="hero-kicker">
          {{ sourceLabel }} · 约 {{ store.task.estimatedMinutes }} 分钟
        </view><view class="hero-title">{{ store.task.title }}</view>
        <view class="hero-desc">{{ store.task.description }}</view><view class="progress-track">
          <view class="progress-fill" :style="{ width: `${store.progressPercent}%` }" />
        </view>
        <view class="hero-action" @tap="startTask">{{ actionText }}</view>
      </view>
      <view v-else class="hero">
        <view class="hero-kicker">权威内容 · 仿真练习</view><view class="hero-title">从一个高频主题开始</view><view class="hero-desc">
          {{
            store.message || '学习内容需经过教研审核并带原文依据，先去专题建立知识框架。'
          }}
        </view><view class="hero-action" @tap="openTopics">进入专题</view>
      </view>
      <view class="section-head">
        <view class="section-title">今日路径</view><view class="section-meta">{{ progressLabel }}</view>
      </view>
      <view v-for="(stepItem, index) in steps" :key="stepItem.key" class="card row">
        <view class="step">{{ index + 1 }}</view><view>
          <view class="card-title">{{ stepItem.title }}</view><view class="card-desc">{{ stepItem.description }}</view>
        </view><view v-if="index < currentStep" class="tag">已完成</view><view v-else-if="index === currentStep && store.task" class="tag">当前</view>
      </view>
      <view class="section-head">
        <view class="section-title">内容门槛</view><view class="section-meta">可信 · 可考 · 可溯源</view>
      </view>
      <view class="card">
        <view class="card-title">每道题都能回到原文依据</view><view class="card-desc">
          学习包只使用已审核文章和证据完整的仿真练习，不用碎片化记忆替代理解。
        </view>
      </view>
    </template>
    <view v-else class="card guest-note">
      <view class="card-title">无需登录即可开始</view>
      <view class="card-desc">
        阅读和作答会保存在当前设备；主动登录后可同步到同一账号的其他设备，不影响免费体验。
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { useDailyTaskStore } from '@/store/dailyTask'
import { showToast } from '@/utils/platform'
import { isLoggedIn } from '@/utils/auth'

interface TaskStep {
  key: string
  title: string
  description: string
}
const fallbackSteps: TaskStep[] = [
  { key: 'orient', title: '读前定向', description: '先看主体、行动与限定条件' },
  { key: 'read', title: '原文精读', description: '理解规范表述和知识位置' },
  { key: 'quiz', title: '证据练习', description: '每道题都回到原文依据' },
  { key: 'review', title: '错因回收', description: '辨清偷换、扩大与程度变化' },
]
const store = useDailyTaskStore()
const loggedIn = ref(isLoggedIn())
const todayLabel = computed(() => `${new Date().getMonth() + 1}月${new Date().getDate()}日`)
const sourceLabel = computed(() => String(store.task?.metadata?.source || '今日学习包'))
const steps = computed(() => {
  const value = store.task?.metadata?.steps
  return Array.isArray(value) && value.length ? (value as TaskStep[]) : fallbackSteps
})
const currentStep = computed(() => store.task?.progress.currentStep || 0)
const progressLabel = computed(() => (store.task ? `${store.progressPercent}%` : '从第一步开始'))
const actionText = computed(() => {
  if (store.starting) return '正在开始…'
  if (store.task?.progress.state === 'completed') return '今日学习已完成'
  return store.task?.progress.state === 'not_started' ? '开始今日学习' : '继续今日学习'
})
function openTopics() {
  Taro.switchTab({ url: '/pages/topics/index' })
}
function openArticles() {
  Taro.navigateTo({ url: '/pages/question/article-pick' })
}
async function startTask() {
  if (store.starting || store.task?.progress.state === 'completed') return
  if (await store.start())
    Taro.navigateTo({
      url: `/pages/learning/pack?taskId=${encodeURIComponent(store.task?.id || '')}`,
    })
  else showToast(store.message || '暂时无法开始')
}
function load() {
  loggedIn.value = isLoggedIn()
  if (!loggedIn.value) return
  void store.load()
}
onMounted(load)
useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.today-entry {
  padding: 20px;
  .card-title {
    margin-top: 8px;
    font-size: 20px;
    line-height: 1.5;
  }
  .card-desc {
    margin-top: 8px;
    line-height: 1.7;
  }
}
.today-entry-action {
  @include hit-target;
  width: 100%;
  margin-top: 18px;
  border-radius: 12px;
  background: $primary-color;
  color: $on-primary;
  font-size: 15px;
  font-weight: 600;
}
.guest-note {
  margin-top: 4px;
}
</style>
