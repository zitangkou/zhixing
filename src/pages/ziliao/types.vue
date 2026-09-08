<template>
  <view class="zl-page" :class="themeClass">
    <view v-if="loading" class="zl-state-box"><text class="zl-state-title">加载中…</text></view>
    <view v-else class="zl-card-list">
      <view v-for="item in list" :key="item.id" class="zl-card" @tap="go(item.id)">
        <view class="zl-card-head">
          <text class="zl-chip">{{ item.category }}</text>
          <text class="zl-meta">难度 {{ item.difficulty }}</text>
        </view>
        <text class="zl-title">{{ item.name }}</text>
        <text class="zl-desc">{{ item.description }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { usePullDownRefresh } from '@tarojs/taro'
import { api } from '@/api'
import type { ZiliaoQuestionType } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '题型模型', enablePullDownRefresh: true })

const { themeClass } = useThemeClass()
const list = ref<ZiliaoQuestionType[]>([])
const loading = ref(true)

function go(id: string) {
  Taro.navigateTo({ url: `/pages/ziliao/type-detail?id=${id}` })
}

async function load() {
  const res = await api.listZiliaoTypes()
  list.value = res.data || []
  loading.value = false
}

onMounted(load)

usePullDownRefresh(async () => {
  try {
    await load()
  } finally {
    Taro.stopPullDownRefresh()
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.zl-page {
  @include page-padding;
}
.zl-card-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.zl-card {
  @include card;
  margin-bottom: 0;
}
.zl-card-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}
.zl-chip {
  @include brand-chip;
}
.zl-meta {
  font-size: 12px;
  color: $text-muted;
}
.zl-title {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 4px;
}
.zl-desc {
  display: block;
  font-size: 12px;
  color: $text-muted;
}
.zl-state-box {
  @include page-state-box;
}
.zl-state-title {
  color: $text-muted;
}
</style>
