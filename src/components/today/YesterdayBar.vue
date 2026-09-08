<template>
  <view class="yesterday-bar" @tap="goGrowth">
    <view v-if="loading && !overview" class="yb-loading"> 足迹加载中… </view>
    <view v-else class="yb-stats">
      <view class="yb-stat">
        <text class="yb-num">
          {{ yesterdayMinutes }}
        </text>
        <text class="yb-label"> 昨日学习(分) </text>
      </view>
      <view class="yb-stat">
        <text class="yb-num">
          {{ overview?.signStreak || 0 }}
        </text>
        <text class="yb-label"> 连续签到(天) </text>
      </view>
      <view class="yb-stat">
        <text class="yb-num">
          {{ overview?.weekMinutes || 0 }}
        </text>
        <text class="yb-label"> 本周累计(分) </text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api } from '@/api'
import type { GrowthOverview } from '@/types'

const overview = ref<GrowthOverview | null>(null)
const loading = ref(true)

const yesterdayMinutes = computed(() => {
  const bars = overview.value?.weekBars || []
  if (!bars.length) return 0
  const yesterday = bars[bars.length - 2]
  return yesterday ? yesterday.minutes : 0
})

function goGrowth() {
  Taro.navigateTo({ url: '/pages/user/growth' })
}

async function load() {
  loading.value = true
  try {
    const res = await api.getGrowthOverview()
    if (res.code === 0) overview.value = res.data
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

.yesterday-bar {
  @include card;
  border-radius: $radius-lg;
  padding: 14px 16px;
}

.yb-loading {
  font-size: 13px;
  color: $text-muted;
}

.yb-stats {
  display: flex;
  align-items: center;
  justify-content: space-around;
}

.yb-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  .yb-num {
    font-size: 20px;
    font-weight: 700;
    color: $primary-color;
  }
  .yb-label {
    font-size: 11px;
    color: $text-muted;
  }
}
</style>
