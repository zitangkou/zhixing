<template>
  <view class="today-task-list">
    <view class="ttl-head" @tap="goFull">
      <text class="ttl-title"> 今日清单 </text>
      <text v-if="planStore.loading && !planStore.today" class="ttl-meta"> 加载中… </text>
      <text v-else class="ttl-meta">
        {{ plan.doneCount }}/{{ plan.totalCount }} 项 · {{ plan.actualMinutes }}/{{
          plan.expectedMinutes
        }}min ›
      </text>
    </view>

    <view v-if="planStore.loadError && !planStore.today" class="ttl-error">
      <text>{{ planStore.loadError }}</text>
      <text class="ttl-retry" @tap="reload"> 重试 </text>
    </view>

    <view v-else-if="plan.tasks.length" class="ttl-list">
      <view
        v-for="task in plan.tasks.slice(0, 4)"
        :key="task.id"
        class="ttl-task"
        :class="{ done: task.status === 'done' }"
        @tap="onToggle(task)"
      >
        <view class="ttl-check">
          <text v-if="task.status === 'done'" class="ttl-checked"> ✓ </text>
        </view>
        <text class="ttl-content">
          {{ task.content }}
        </text>
        <text v-if="task.timeSlot" class="ttl-time">
          {{ task.timeSlot }}
        </text>
      </view>
      <view v-if="plan.tasks.length > 4" class="ttl-more" @tap="goFull">
        还有 {{ plan.tasks.length - 4 }} 项 · 查看全部 ›
      </view>
    </view>

    <view v-else class="ttl-empty" @tap="goFull">
      <text>今日暂无计划任务，点此添加</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import Taro from '@tarojs/taro'
import { usePlanStore } from '@/store/plan'
import type { PlanTask } from '@/types'

const planStore = usePlanStore()
const plan = computed(
  () =>
    planStore.today || {
      date: '',
      isWeekend: false,
      tasks: [],
      completion: 0,
      doneCount: 0,
      totalCount: 0,
      expectedMinutes: 0,
      actualMinutes: 0,
      review: null,
    },
)

function goFull() {
  Taro.navigateTo({ url: '/pages/plan/today' })
}

function reload() {
  planStore.fetchToday()
}

async function onToggle(task: PlanTask) {
  await planStore.toggleTask(task)
}

onMounted(() => {
  if (!planStore.today) planStore.fetchToday()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.today-task-list {
  @include card;
  border-radius: $radius-lg;
  padding: 14px 16px;
}

.ttl-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
  .ttl-title {
    font-size: 15px;
    font-weight: 600;
  }
  .ttl-meta {
    font-size: 12px;
    color: $text-muted;
  }
}

.ttl-error {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: $text-secondary;
  .ttl-retry {
    color: $primary-color;
    font-weight: 600;
  }
}

.ttl-list {
  .ttl-task {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 0;
    border-bottom: 1px solid $border-color;
    &:last-child {
      border-bottom: none;
    }
    &.done .ttl-content {
      color: $text-muted;
      text-decoration: line-through;
    }
  }
  .ttl-check {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid $border-color;
    display: flex;
    align-items: center;
    justify-content: center;
    .ttl-checked {
      color: $primary-color;
      font-size: 12px;
      font-weight: 700;
    }
  }
  .ttl-content {
    flex: 1;
    font-size: 14px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .ttl-time {
    font-size: 12px;
    color: $text-muted;
  }
  .ttl-more {
    padding-top: 8px;
    text-align: center;
    font-size: 12px;
    color: $primary-color;
  }
}

.ttl-empty {
  padding: 12px 0 6px;
  text-align: center;
  font-size: 13px;
  color: $text-secondary;
}
</style>
