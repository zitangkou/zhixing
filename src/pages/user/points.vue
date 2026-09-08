<template>
  <view class="page-points" :class="themeClass">
    <view class="summary">
      <text class="label">当前积分</text>
      <text class="value">{{ userStore.points }}</text>
    </view>

    <view class="filter">
      <nut-tag :type="filter === 'all' ? 'primary' : 'default'" @click="filter = 'all'">全部</nut-tag>
      <nut-tag :type="filter === 'income' ? 'primary' : 'default'" @click="filter = 'income'">收入</nut-tag>
      <nut-tag :type="filter === 'expense' ? 'primary' : 'default'" @click="filter = 'expense'">支出</nut-tag>
    </view>

    <view v-if="filteredLogs.length === 0" class="empty-tip">暂无积分记录</view>

    <view v-for="log in filteredLogs" :key="log.id" class="log-item">
      <view class="log-info">
        <text class="desc">{{ log.description }}</text>
        <text class="time">{{ formatTime(log.createdAt) }}</text>
      </view>
      <text class="amount" :class="log.type">{{ log.type === 'income' ? '+' : '-' }}{{ log.amount }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Tag as NutTag } from '@nutui/nutui-taro'
import { useUserStore } from '@/store/user'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '积分明细' })

const { themeClass } = useThemeClass()
const userStore = useUserStore()
const filter = ref<'all' | 'income' | 'expense'>('all')

const filteredLogs = computed(() => {
  if (filter.value === 'all') return userStore.pointsLogs
  return userStore.pointsLogs.filter((l) => l.type === filter.value)
})

onMounted(() => userStore.fetchPointsLog())

function formatTime(iso: string) {
  return iso.slice(0, 16).replace('T', ' ')
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-points {
  @include page-padding;
  .summary {
    text-align: center;
    padding: 24px;
    @include brand-gradient;
    border-radius: 12px;
    color: #fff;
    margin-bottom: 16px;
    .label { display: block; font-size: 13px; opacity: 0.85; }
    .value { display: block; font-size: 36px; font-weight: 700; margin-top: 8px; }
  }
  .filter { display: flex; gap: 8px; margin-bottom: 16px; }
  .log-item {
    @include card;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    .log-info {
      .desc { display: block; font-size: 14px; margin-bottom: 4px; }
      .time { font-size: 12px; color: $text-muted; }
    }
    .amount {
      font-size: 16px;
      font-weight: 600;
      &.income { color: $primary-color; }
      &.expense { color: $text-secondary; }
    }
  }
}
</style>
