<template>
  <view class="due-review-alert" @tap="goHub">
    <view v-if="loading && !hub" class="dra-loading"> 复习加载中… </view>
    <view v-else-if="hub && total > 0" class="dra-body warn">
      <view class="dra-main">
        <text class="dra-title"> 今日有 {{ total }} 项复习/内化待完成 </text>
        <text class="dra-desc">
          {{ summary }}
        </text>
      </view>
      <text class="dra-cta"> 去处理 › </text>
    </view>
    <view v-else class="dra-body ok">
      <view class="dra-main">
        <text class="dra-title"> 今日复习已清 </text>
        <text class="dra-desc"> 保持节奏，按计划推进 </text>
      </view>
      <text class="dra-cta"> 查看 › </text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api } from '@/api'
import type { ReviewHub } from '@/types'

const hub = ref<ReviewHub | null>(null)
const loading = ref(true)

const total = computed(() => hub.value?.totalCount || 0)

const summary = computed(() => {
  const h = hub.value
  if (!h) return ''
  const parts: string[] = []
  if (h.knowledgeDueCount > 0) parts.push(`知识 ${h.knowledgeDueCount}`)
  if (h.articleReviewCount > 0) parts.push(`文章 ${h.articleReviewCount}`)
  const w = h.wrongRecommendCount || h.wrongReviewCount || 0
  if (w > 0) parts.push(`错题 ${w}`)
  if (h.corpusInboxCount > 0) parts.push(`语料 ${h.corpusInboxCount}`)
  return parts.length ? parts.join(' · ') : '查看明细'
})

function goHub() {
  Taro.navigateTo({ url: '/pages/review/hub' })
}

async function load() {
  loading.value = true
  try {
    const res = await api.getReviewHub()
    if (res.code === 0) hub.value = res.data
  } catch {
    /* 忽略 */
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.due-review-alert {
  @include card;
  border-radius: $radius-lg;
  padding: 14px 16px;
}

.dra-loading {
  font-size: 13px;
  color: $text-muted;
}

.dra-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  &.warn {
    background: rgba($accent-amber, 0.12);
    border-radius: 10px;
    padding: 12px;
    .dra-title {
      color: $accent-amber;
    }
  }
  .dra-main {
    flex: 1;
    min-width: 0;
  }
  .dra-title {
    display: block;
    font-size: 14px;
    font-weight: 600;
  }
  .dra-desc {
    display: block;
    margin-top: 3px;
    font-size: 12px;
    color: $text-secondary;
  }
  .dra-cta {
    font-size: 13px;
    color: $primary-color;
    font-weight: 600;
    flex-shrink: 0;
  }
}
</style>
