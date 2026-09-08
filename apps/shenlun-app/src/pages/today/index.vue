<template>
  <view class="page">
    <view class="eyebrow">{{ todayLabel }} · 今日学习</view><view class="page-title">每天吃透一篇，表达自然有根</view>
    <view v-if="!loggedIn" class="hero">
      <view class="hero-kicker">申论学习 · 免费开放</view><view class="hero-title">先读原文，再看三刀，最后练一句</view>
      <view class="hero-desc">无需登录即可完成一篇教研示范和短练习，进度保存在当前设备。</view><view class="hero-action" @tap="openReading">开始今日学习</view>
    </view>
    <view v-else-if="store.loading && !store.task" class="card state-card">正在准备今日内容…</view>
    <view v-else-if="store.task" class="hero">
      <view class="hero-kicker">{{ sourceLabel }} · 约 {{ store.task.estimatedMinutes }} 分钟</view>
      <view class="hero-title">{{ store.task.title }}</view><view class="hero-desc">{{ store.task.description }}</view>
      <view class="progress-track"><view class="progress-fill" :style="{ width: `${store.progressPercent}%` }" /></view>
      <view class="hero-action" @tap="startTask">{{ actionText }}</view>
    </view>
    <view v-else class="hero">
      <view class="hero-kicker">人民日报精读 · 约 18 分钟</view><view class="hero-title">从一篇好文章开始今日申论</view>
      <view class="hero-desc">{{ store.message || '内容通过教研审核后进入每日训练，先去精读库学习。' }}</view><view class="hero-action" @tap="openReading">进入精读库</view>
    </view>
    <view class="section-head"><view class="section-title">今日路径</view><view class="section-meta">{{ progressLabel }}</view></view>
    <view v-for="(stepItem, index) in steps" :key="stepItem.key" class="card row">
      <view class="step">{{ index + 1 }}</view><view><view class="card-title">{{ stepItem.title }}</view><view class="card-desc">{{ stepItem.description }}</view></view>
      <view v-if="index < currentStep" class="tag">已完成</view><view v-else-if="index === currentStep && store.task" class="tag">当前</view>
    </view>
    <template v-if="loggedIn">
      <view class="section-head"><view class="section-title">学习沉淀</view><view class="section-meta">本周</view></view>
      <view class="card insight-row"><view><view class="insight-num">{{ store.stats?.weekMineDays || 0 }}</view><view class="card-desc">精练天数</view></view><view><view class="insight-num">{{ store.stats?.termCount || 0 }}</view><view class="card-desc">规范表达</view></view><view><view class="insight-num">{{ store.stats?.weekDrillCount || 0 }}</view><view class="card-desc">迁移训练</view></view></view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { useDailyTaskStore } from '@/store/dailyTask'
import { showToast } from '@/utils/platform'
import { isLoggedIn } from '@/utils/auth'

interface TaskStep { key: string; title: string; description: string }
const fallbackSteps: TaskStep[] = [
  { key: 'read', title: '精读定位', description: '读懂主题、对象与核心问题' },
  { key: 'analyze', title: '三刀拆解', description: '拆骨架、抓规范表达、学句式' },
  { key: 'answer', title: '小题作答', description: '围绕材料完成一次短作答' },
  { key: 'deposit', title: '表达沉淀', description: '留下一个可迁移表达' },
]
const guestSteps: TaskStep[] = [
  { key: 'read', title: '读原文', description: '独立判断中心观点和行文结构' },
  { key: 'example', title: '看三刀', description: '对照论证骨架、规范表达和万能句式' },
  { key: 'practice', title: '练一句', description: '完成短作答，再与教研参考对照' },
]
const store = useDailyTaskStore()
const loggedIn = ref(isLoggedIn())
const todayLabel = computed(() => `${new Date().getMonth() + 1}月${new Date().getDate()}日`)
const sourceLabel = computed(() => String(store.task?.metadata?.source || '人民时评'))
const steps = computed(() => {
  if (!loggedIn.value) return guestSteps
  const value = store.task?.metadata?.steps
  return Array.isArray(value) && value.length ? (value as TaskStep[]) : fallbackSteps
})
const currentStep = computed(() => store.task?.progress.currentStep || 0)
const progressLabel = computed(() => loggedIn.value && store.task ? `${store.progressPercent}%` : '3 步闭环')
const actionText = computed(() => {
  if (store.starting) return '正在开始…'
  if (store.task?.progress.state === 'completed') return '今日训练已完成'
  return store.task?.progress.state === 'not_started' ? '开始今日学习' : '继续今日学习'
})
function openReading() { Taro.switchTab({ url: '/pages/reading/index' }) }
async function startTask() {
  if (store.starting || store.task?.progress.state === 'completed') return
  if (await store.start()) {
    const id = store.task?.contentId
    if (id) Taro.navigateTo({ url: `/pages/reading/detail?id=${encodeURIComponent(id)}&taskId=${encodeURIComponent(store.task?.id || '')}` })
    else openReading()
  }
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
