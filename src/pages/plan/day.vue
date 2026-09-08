<template>
  <view class="page-day" :class="themeClass">
    <view v-if="loading && !plan" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在获取当日清单</text>
    </view>
    <view v-else-if="error && !plan" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ error }}</text>
      <view class="state-btn" @tap="load">点击重试</view>
    </view>
    <template v-else-if="plan">
      <view class="day-header">
        <text class="date">{{ plan.date }}</text>
        <text class="weekday">{{ plan.isWeekend ? '周末' : '工作日' }}</text>
      </view>
      <view class="day-progress">
        <view class="bar"><view class="fill" :style="{ width: plan.completion + '%' }" /></view>
        <text class="progress-text">{{ plan.doneCount }}/{{ plan.totalCount }} · {{ plan.actualMinutes }}min</text>
      </view>

      <view v-if="!plan.tasks.length" class="state-box soft">
        <text class="state-title">当日暂无任务</text>
      </view>

      <view v-for="task in plan.tasks" :key="task.id" class="task-item" :class="{ done: task.status === 'done' }">
        <view class="task-check"><text v-if="task.status === 'done'" class="check-icon">✓</text></view>
        <view class="task-body">
          <view class="task-line1">
            <text v-if="task.timeSlot" class="task-time">{{ task.timeSlot }}</text>
            <text class="task-subject">{{ task.subject }}</text>
            <text class="task-priority">P{{ task.priority || 3 }}</text>
          </view>
          <text class="task-content">{{ task.content }}</text>
        </view>
      </view>

      <view v-if="plan.review" class="review-block">
        <text class="block-title">复盘</text>
        <text class="block-line">完成度：{{ plan.review.completion }}%</text>
        <text class="block-line">弱项：{{ plan.review.weakPoint || '—' }}</text>
        <text class="block-line">明日重点：{{ plan.review.tomorrowFocus || '—' }}</text>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDidShow, useRouter } from '@tarojs/taro'
import { api } from '@/api'
import type { DayPlan } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '日清单详情' })

const { themeClass } = useThemeClass()
const router = useRouter()
const date = ref(router.params?.date || new Date().toISOString().slice(0, 10))
const dayPlan = ref<DayPlan | null>(null)
const loading = ref(false)
const error = ref('')

const plan = computed(() => dayPlan.value)

async function load() {
  date.value = router.params?.date || new Date().toISOString().slice(0, 10)
  loading.value = true
  error.value = ''
  try {
    const res = await api.getDayPlan(date.value)
    if (res.code === 0 && res.data) dayPlan.value = res.data
    else error.value = res.message || '获取日清单失败'
  } catch {
    error.value = '网络异常，请稍后重试'
  } finally {
    loading.value = false
  }
}

useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-day {
  @include page-padding;
  padding-bottom: 40px;
}

.state-box {
  @include page-state-box;
  &.soft { margin-bottom: 12px; }
}

.day-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 12px;
  .date { font-size: 18px; font-weight: 700; }
  .weekday { font-size: 12px; color: $text-muted; padding: 2px 8px; background: $page-bg; border-radius: 4px; }
}

.day-progress {
  margin-bottom: 16px;
  .bar { height: 6px; background: $page-bg; border-radius: 3px; overflow: hidden; .fill { height: 100%; background: $primary-color; } }
  .progress-text { display: block; margin-top: 6px; font-size: 12px; color: $text-secondary; }
}

.task-item {
  @include card;
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  border-radius: $radius-md;
  &.done .task-content { color: $text-muted; text-decoration: line-through; }
  .task-check {
    @include hit-target(44px);
    width: 44px; height: 44px; margin: -8px 0 0 -10px;
    border-radius: 50%; color: $primary-color; flex-shrink: 0;
    position: relative;
    &::after {
      content: ''; width: 22px; height: 22px; border-radius: 50%;
      border: 2px solid $border-color; box-sizing: border-box;
    }
    .check-icon { position: absolute; font-size: 12px; }
  }
  .done .task-check::after { background: $primary-light; border-color: $primary-color; }
  .task-line1 { display: flex; gap: 8px; margin-bottom: 4px; .task-time { font-size: 12px; color: $text-muted; } .task-subject { font-size: 12px; color: $primary-color; } .task-priority { font-size: 12px; color: $text-secondary; font-weight: 700; } }
  .task-content { font-size: 14px; line-height: 1.5; }
}

.review-block {
  @include card;
  padding: 14px 16px;
  border-radius: $radius-md;
  .block-title { display: block; font-weight: 600; margin-bottom: 8px; }
  .block-line { display: block; font-size: 13px; color: $text-secondary; padding: 4px 0; }
}
</style>
