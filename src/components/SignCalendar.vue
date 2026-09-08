<template>
  <view class="sign-calendar">
    <view class="calendar-header">
      <text class="month">
        {{ currentMonth }}
      </text>
      <text class="streak"> 连续签到 {{ streak }} 天 </text>
    </view>
    <view class="weekdays">
      <text v-for="d in weekdays" :key="d" class="weekday">
        {{ d }}
      </text>
    </view>
    <view class="days">
      <view v-for="(day, idx) in calendarDays" :key="idx" class="day-cell">
        <view v-if="day" class="day" :class="{ signed: signStatus[day], today: day === today }">
          {{ day.slice(-2) }}
        </view>
      </view>
    </view>
    <view class="rules">
      <text>签到规则：每日 +5 积分，连续 7 天额外 +10 积分</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatDate } from '@/utils/memoryCurve'
import type { SignStatus } from '@/types'

defineProps<{ signStatus: SignStatus; streak: number }>()

const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const today = formatDate()

const currentMonth = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}年${d.getMonth() + 1}月`
})

const calendarDays = computed(() => {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth()
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (string | null)[] = Array(firstDay).fill(null)
  for (let i = 1; i <= daysInMonth; i++) {
    const m = String(month + 1).padStart(2, '0')
    const d = String(i).padStart(2, '0')
    cells.push(`${year}-${m}-${d}`)
  }
  return cells
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.sign-calendar {
  @include card;
  .calendar-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 16px;
    .month {
      font-size: 16px;
      font-weight: 600;
    }
    .streak {
      color: $primary-color;
      font-size: 13px;
    }
  }
  .weekdays {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    text-align: center;
    margin-bottom: 8px;
    .weekday {
      font-size: 12px;
      color: $text-muted;
    }
  }
  .days {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    .day-cell {
      aspect-ratio: 1;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .day {
      width: 32px;
      height: 32px;
      line-height: 32px;
      text-align: center;
      border-radius: 50%;
      font-size: 13px;
      &.signed {
        background: $primary-color;
        color: #fff;
      }
      &.today {
        border: 2px solid $primary-color;
      }
    }
  }
  .rules {
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid $border-color;
    font-size: 12px;
    color: $text-muted;
  }
}
</style>
