<template>
  <view class="page-pick" :class="themeClass">
    <text class="tip">置顶文章在前。先读原文，读完后再练习。</text>
    <view v-if="loading && !articleStore.recommendedList.length" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在获取时政文章</text>
    </view>
    <view v-else-if="loadError" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ loadError }}</text>
      <view class="state-btn" @tap="load">点击重试</view>
    </view>
    <view v-else-if="!articleStore.recommendedList.length" class="state-box">
      <text class="state-title">暂无时政文章</text>
      <text class="state-desc">请管理员在后台发布时政文章</text>
    </view>
    <template v-else>
      <ArticleCard
        v-for="article in articleStore.recommendedList"
        :key="article.id"
        :article="article"
        @tap="goDetail"
      />
      <view v-if="articleStore.recommendedLoading" class="list-status">加载中...</view>
      <view v-else-if="articleStore.recommendedHasMore" class="list-status muted">上拉加载更多</view>
      <view v-else class="list-status muted">已加载全部</view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { useReachBottom } from '@tarojs/taro'
import ArticleCard from '@/components/ArticleCard.vue'
import { useArticleStore } from '@/store/article'
import { bootstrapApp } from '@/utils/bootstrap'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '时政阅读' })

const { themeClass } = useThemeClass()
const articleStore = useArticleStore()
const loading = ref(true)
const loadError = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    await bootstrapApp()
    await articleStore.fetchRecommendedArticles(true)
  } catch {
    loadError.value = '网络异常，请稍后重试'
  } finally {
    loading.value = false
  }
}

function goDetail(articleId: string) {
  Taro.navigateTo({ url: `/pages/article/detail?id=${articleId}` })
}

onMounted(load)
useReachBottom(() => {
  articleStore.fetchRecommendedArticles(false)
})
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
    line-height: 1.5;
  }
  .state-box { @include page-state-box; margin-bottom: 12px; }
  .list-status {
    text-align: center;
    padding: 12px 0 4px;
    font-size: 13px;
    color: $primary-color;
    &.muted { color: $text-muted; }
  }
}
</style>
