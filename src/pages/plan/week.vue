<template>
  <view class="page-week" :class="themeClass">
    <view v-if="planStore.weekLoading && !week.length" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在同步本周计划</text>
    </view>
    <view v-else-if="planStore.weekError && !week.length" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ planStore.weekError }}</text>
      <view class="state-btn" @tap="reload">点击重试</view>
    </view>
    <template v-else>
      <view class="week-summary">
        <view class="summary-item">
          <text class="sum-num">{{ weekDone }}</text>
          <text class="sum-label">本周完成</text>
        </view>
        <view class="summary-item">
          <text class="sum-num">{{ weekMinutes }}</text>
          <text class="sum-label">用时(min)</text>
        </view>
        <view class="summary-item">
          <text class="sum-num">{{ avgCompletion }}%</text>
          <text class="sum-label">平均完成</text>
        </view>
      </view>

      <view v-if="!week.length" class="state-box soft">
        <text class="state-title">本周暂无计划</text>
        <text class="state-desc">去今日清单添加任务后会出现在这里</text>
      </view>

      <view v-for="d in week" :key="d.date" class="day-card" @tap="goDay(d.date)">
        <view class="day-header">
          <view class="day-main">
            <text class="day-date">{{ formatDay(d.date) }}</text>
            <text class="day-tag" :class="{ weekend: d.isWeekend }">{{ d.isWeekend ? '周末' : '工作日' }}</text>
          </view>
          <text class="day-compl">{{ d.completion }}%</text>
        </view>
        <view class="day-bar">
          <view class="day-fill" :style="{ width: d.completion + '%' }" />
        </view>
        <view class="day-meta">
          <text>{{ d.doneCount }}/{{ d.totalCount }} 任务</text>
          <text>{{ d.actualMinutes }}/{{ d.expectedMinutes }} min</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { usePlanStore } from '@/store/plan'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '本周计划' })

const { themeClass } = useThemeClass()
const planStore = usePlanStore()
const week = computed(() => planStore.week)

const weekDone = computed(() => planStore.week.reduce((s, d) => s + d.doneCount, 0))
const weekMinutes = computed(() => planStore.week.reduce((s, d) => s + d.actualMinutes, 0))
const avgCompletion = computed(() => {
  const days = planStore.week.filter((d) => d.totalCount > 0)
  if (!days.length) return 0
  return Math.round(days.reduce((s, d) => s + d.completion, 0) / days.length)
})

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

function formatDay(date: string) {
  const d = new Date(date)
  return `${d.getMonth() + 1}/${d.getDate()} 周${WEEKDAYS[d.getDay()]}`
}

function goDay(date: string) {
  Taro.navigateTo({ url: `/pages/plan/day?date=${date}` })
}

function reload() {
  planStore.fetchWeek()
}

useDidShow(reload)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-week {
  @include page-padding;
  padding-bottom: 40px;
}

.state-box {
  @include page-state-box;
  &.soft { margin-bottom: 12px; }
}

.week-summary {
  display: flex;
  background: $card-bg;
  border-radius: $radius-lg;
  padding: 18px 12px;
  margin-bottom: 12px;
  box-shadow: $shadow-card;
  .summary-item {
    flex: 1;
    text-align: center;
    .sum-num {
      display: block;
      font-size: 22px;
      font-weight: 700;
      color: $primary-color;
    }
    .sum-label {
      display: block;
      margin-top: 4px;
      font-size: 12px;
      color: $text-muted;
    }
  }
}

.day-card {
  @include card;
  padding: 14px 16px;
  border-radius: $radius-md;
  margin-bottom: 10px;
  &:active { opacity: 0.85; }
  .day-header {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    .day-main { flex: 1; display: flex; gap: 8px; align-items: baseline; }
    .day-date { font-size: 15px; font-weight: 600; }
    .day-tag {
      font-size: 11px;
      color: $text-muted;
      padding: 1px 6px;
      border-radius: 3px;
      background: $page-bg;
      &.weekend { color: $accent-amber; background: rgba($accent-amber, 0.12); }
    }
    .day-compl {
      font-size: 14px;
      font-weight: 600;
      color: $primary-color;
    }
  }
  .day-bar {
    height: 4px;
    background: $page-bg;
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 6px;
    .day-fill {
      height: 100%;
      background: linear-gradient(90deg, $primary-color, $primary-mid);
      border-radius: 2px;
    }
  }
  .day-meta {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: $text-muted;
  }
}
</style>
