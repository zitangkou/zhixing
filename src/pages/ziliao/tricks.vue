<template>
  <view class="zl-page" :class="themeClass">
    <view v-if="loading" class="zl-state-box"><text class="zl-state-title">加载中…</text></view>
    <view v-else class="zl-card-list">
      <view v-for="item in list" :key="item.id" class="zl-card" @tap="go(item.id)">
        <view class="zl-card-head">
          <text class="zl-chip">{{ item.category }}</text>
        </view>
        <text class="zl-title">{{ item.name }}</text>
        <text class="zl-desc">{{ item.principle }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { usePullDownRefresh } from '@tarojs/taro'
import { api } from '@/api'
import type { ZiliaoTrick } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '速算技巧', enablePullDownRefresh: true })

const { themeClass } = useThemeClass()
const list = ref<ZiliaoTrick[]>([])
const loading = ref(true)

function go(id: string) {
  Taro.navigateTo({ url: `/pages/ziliao/trick-detail?id=${id}` })
}

async function load() {
  const res = await api.listZiliaoTricks()
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
  margin-bottom: 6px;
}
.zl-chip {
  @include brand-chip;
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
