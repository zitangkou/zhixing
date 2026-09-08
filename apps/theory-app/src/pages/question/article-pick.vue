<template>
  <view class="page-pick">
    <text class="tip">只展示已经教研审核并完成分辑编排的学习内容</text>
    <view v-if="loading" class="state-box"><text class="state-title">加载中…</text><text class="state-desc">正在获取学习入口</text></view>
    <view v-else-if="loadError" class="state-box"><text class="state-title">加载失败</text><text class="state-desc">{{ loadError }}</text><view class="state-btn" @tap="load">点击重试</view></view>
    <view v-else-if="!entries.length" class="state-box"><text class="state-title">内容准备中</text><text class="state-desc">已审核入口发布后会显示在这里</text></view>
    <template v-else>
      <view v-if="dailyEntries.length" class="section-title">今日学习</view>
      <view v-for="entry in dailyEntries" :key="`daily-${entry.id}`" class="item" @tap="start(entry.articleId)">
        <view class="text"><view class="badges"><text class="badge">今日</text><text v-if="entry.collectionEnabled" class="badge light">可练合集</text></view><text class="title">{{ entry.title }}</text><text class="desc">{{ entry.description }}</text><text class="date">{{ entry.source }} · {{ entry.publishDate }} · {{ entry.questionCount }} 题</text></view><text class="arrow">›</text>
      </view>
      <view v-if="evergreenEntries.length" class="section-title">长期重点</view>
      <view v-for="entry in evergreenEntries" :key="`evergreen-${entry.id}`" class="item" @tap="start(entry.articleId)">
        <view class="text"><view class="badges"><text class="badge evergreen">长期重点</text></view><text class="title">{{ entry.title }}</text><text class="desc">{{ entry.description }}</text><text class="date">{{ entry.source }} · {{ entry.questionCount }} 题</text></view><text class="arrow">›</text>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api, type TheoryLearningEntry } from '@/api'

definePageConfig({ navigationBarTitleText: '选择学习内容' })
const entries = ref<TheoryLearningEntry[]>([])
const loading = ref(true)
const loadError = ref('')
const dailyEntries = computed(() => entries.value.filter(entry => entry.isDaily))
const evergreenEntries = computed(() => entries.value.filter(entry => entry.isEvergreen))
async function load() {
  loading.value = true
  loadError.value = ''
  const response = await api.listLearningEntries()
  if (response.code === 0 && response.data) entries.value = response.data
  else loadError.value = response.message || '网络异常，请稍后重试'
  loading.value = false
}
function start(articleId: string) { Taro.navigateTo({ url: `/pages/learning/article?articleId=${encodeURIComponent(articleId)}` }) }
onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-pick { @include page-padding; padding-bottom: 40px; }
.tip { display: block; margin-bottom: 16px; color: $text-muted; font-size: 12px; line-height: 1.6; }
.state-box { @include page-state-box; margin-bottom: 12px; }
.section-title { margin: 20px 2px 10px; color: $text-primary; font-size: 17px; font-weight: 700; }
.item { @include card; display: flex; align-items: center; gap: 10px; padding: 15px 16px; margin-bottom: 10px; }
.text { flex: 1; min-width: 0; }
.badges { display: flex; gap: 6px; margin-bottom: 7px; }
.badge { padding: 3px 7px; border-radius: 5px; background: $primary-color; color: $on-primary; font-size: 10px; }
.badge.light, .badge.evergreen { background: $primary-light; color: $primary-color; }
.title { display: block; color: $text-primary; font-size: 15px; font-weight: 650; line-height: 1.5; }
.desc { display: block; margin-top: 5px; color: $text-secondary; font-size: 12px; line-height: 1.6; }
.date { display: block; margin-top: 7px; color: $text-muted; font-size: 11px; }
.arrow { color: $text-muted; font-size: 18px; }
</style>
