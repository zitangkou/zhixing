<template>
  <view class="page-review">
    <view class="header-tip">
      <text>根据艾宾浩斯记忆曲线，在最佳时间点复习可巩固记忆</text>
    </view>

    <view v-if="loading" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在同步复习任务</text>
    </view>
    <view v-else-if="loadError" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ loadError }}</text>
      <view class="state-btn" @tap="load">点击重试</view>
    </view>
    <view v-else-if="questionStore.reviewTasks.length === 0" class="state-box">
      <text class="state-title">暂无复习任务</text>
      <text class="state-desc">继续学习新文章吧</text>
    </view>

    <template v-else>
      <view
        v-for="task in questionStore.reviewTasks"
        :key="task.id"
        class="review-card"
        @tap="startReview(task.articleId)"
      >
        <view class="urgency" :class="urgencyClass(task.urgency)">
          紧急度 {{ task.urgency }}
        </view>
        <text class="title">{{ task.articleTitle }}</text>
        <view class="meta">
          <nut-tag size="small">第 {{ task.reviewIndex + 1 }} 次复习</nut-tag>
          <text class="due">应复习日：{{ task.dueDate }}</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { Tag as NutTag } from '@nutui/nutui-taro'
import { useQuestionStore } from '@/store/question'

definePageConfig({ navigationBarTitleText: '记忆曲线复习' })

const questionStore = useQuestionStore()
const loading = ref(false)
const loadError = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const ok = await questionStore.fetchReviewTasks()
    if (!ok) loadError.value = questionStore.reviewLoadError || '加载复习任务失败'
  } catch {
    loadError.value = '网络异常，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function urgencyClass(urgency: number) {
  if (urgency >= 10) return 'high'
  if (urgency >= 5) return 'medium'
  return 'low'
}

async function startReview(articleId: string) {
  const ok = await questionStore.completeReviewTask(articleId)
  if (!ok) return
  Taro.navigateTo({ url: `/pages/question/taking?articleId=${articleId}` })
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-review {
  @include page-padding;
  .header-tip {
    padding: 12px 14px;
    background: $primary-light;
    border-radius: 8px;
    font-size: 13px;
    color: $text-secondary;
    margin-bottom: 16px;
    line-height: 1.6;
  }
  .state-box { @include page-state-box; margin-bottom: 12px; }
  .review-card {
    @include card;
    .urgency {
      display: inline-block;
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 4px;
      margin-bottom: 8px;
      &.high { background: $primary-light; color: $primary-color; }
      &.medium { background: $primary-faint; color: $accent-amber; }
      &.low { background: $elevated; color: $text-muted; }
    }
    .title { display: block; font-size: 15px; font-weight: 500; margin-bottom: 10px; }
    .meta { display: flex; align-items: center; gap: 10px; .due { font-size: 12px; color: $text-muted; } }
  }
}
</style>
