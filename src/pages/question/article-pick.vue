<template>
  <view class="page-pick" :class="themeClass">
    <text class="tip">选一篇文章，按该文题目练习</text>
    <view v-if="loading" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在获取可练文章</text>
    </view>
    <view v-else-if="loadError" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ loadError }}</text>
      <view class="state-btn" @tap="load">点击重试</view>
    </view>
    <view v-else-if="!articles.length" class="state-box">
      <text class="state-title">暂无可练文章</text>
      <text class="state-desc">先去阅读几篇英文文章吧</text>
    </view>
    <template v-else>
      <view
        v-for="article in articles"
        :key="article.id"
        class="item"
        @tap="start(article.id)"
      >
        <view class="text">
          <text class="title">{{ article.title }}</text>
          <text v-if="article.publishDate" class="date">{{ article.publishDate }}</text>
        </view>
        <text class="arrow">›</text>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { useArticleStore } from '@/store/article'
import { bootstrapApp } from '@/utils/bootstrap'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '按文章练' })

const { themeClass } = useThemeClass()
const articleStore = useArticleStore()
const loading = ref(true)
const loadError = ref('')

const articles = computed(() => {
  const map = new Map<string, (typeof articleStore.dailyArticles)[0]>()
  for (const a of [...articleStore.dailyArticles, ...articleStore.recommendedList]) {
    if (!map.has(a.id)) map.set(a.id, a)
  }
  return [...map.values()].sort((a, b) => (b.publishDate || '').localeCompare(a.publishDate || ''))
})

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    await bootstrapApp()
    await Promise.all([
      articleStore.fetchDailyArticles(),
      articleStore.fetchRecommendedArticles(true),
    ])
  } catch {
    loadError.value = '网络异常，请稍后重试'
  } finally {
    loading.value = false
  }
}

function start(articleId: string) {
  Taro.navigateTo({ url: `/pages/question/taking?articleId=${articleId}` })
}

onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-pick {
  @include page-padding;
  padding-bottom: 40px;
  .tip {
    display: block;
    font-size: 12px;
    color: $text-muted;
    margin-bottom: 12px;
  }
  .state-box { @include page-state-box; margin-bottom: 12px; }
  .item {
    @include card;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    .text { flex: 1; min-width: 0; }
    .title {
      display: block;
      font-size: 14px;
      font-weight: 600;
      color: $text-primary;
      line-height: 1.4;
    }
    .date {
      display: block;
      margin-top: 4px;
      font-size: 11px;
      color: $text-muted;
    }
    .arrow { color: $text-muted; font-size: 16px; }
  }
}
</style>
