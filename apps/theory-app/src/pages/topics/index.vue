<template>
  <view class="page">
    <view class="eyebrow">长期学习</view><view class="page-title">重要内容，持续回看</view>
    <view class="section-head"><view class="section-title">长期重点</view><view class="section-meta">持续开放</view></view>
    <view v-if="loading" class="card state-card">正在加载学习入口…</view>
    <view v-else-if="!evergreenEntries.length" class="card state-card">长期重点正在编排中</view>
    <view v-for="entry in evergreenEntries" :key="entry.id" class="card entry-card" @tap="open(entry.articleId)">
      <view class="entry-meta">{{ entry.source }} · {{ entry.questionCount }} 题</view>
      <view class="card-title">{{ entry.title }}</view><view class="card-desc">{{ entry.description }}</view>
      <view class="entry-tags"><text v-for="tag in entry.tags.slice(0, 3)" :key="tag">{{ tag }}</text></view>
    </view>
    <view class="section-head"><view class="section-title">学习方法</view><view class="section-meta">先建框架</view></view>
    <view v-for="item in methods" :key="item.title" class="card row"><view class="step">{{ item.no }}</view><view><view class="card-title">{{ item.title }}</view><view class="card-desc">{{ item.desc }}</view></view></view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { api, type TheoryLearningEntry, type TopicItem } from '@/api'

const entries = ref<TheoryLearningEntry[]>([])
const methods = ref<TopicItem[]>([])
const loading = ref(true)
const evergreenEntries = computed(() => entries.value.filter(entry => entry.isEvergreen))
async function load() {
  loading.value = true
  const [entryResponse, methodResponse] = await Promise.all([api.listLearningEntries(), api.getTopics()])
  if (entryResponse.code === 0 && entryResponse.data) entries.value = entryResponse.data
  if (methodResponse.code === 0 && methodResponse.data) methods.value = methodResponse.data.items
  loading.value = false
}
function open(articleId: string) { Taro.navigateTo({ url: `/pages/learning/article?articleId=${encodeURIComponent(articleId)}` }) }
useDidShow(() => void load())
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.entry-card { margin-bottom: 10px; }
.entry-meta { margin-bottom: 7px; color: $primary-color; font-size: 11px; }
.entry-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.entry-tags text { padding: 3px 8px; border-radius: 5px; background: $primary-light; color: $primary-color; font-size: 11px; }
</style>
