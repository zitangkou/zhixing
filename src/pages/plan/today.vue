<template>
  <view class="page-plan" :class="themeClass">
    <view v-if="planStore.loading && !planStore.today" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在同步今日清单</text>
    </view>
    <view v-else-if="planStore.loadError && !planStore.today" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ planStore.loadError }}</text>
      <view class="state-btn" @tap="load">点击重试</view>
    </view>
    <template v-else-if="plan">
      <view class="plan-header">
        <view class="header-main">
          <text class="date">{{ plan.date }}</text>
          <text class="weekday">{{ plan.isWeekend ? '周末' : '工作日' }}</text>
        </view>
        <view class="header-progress">
          <view class="progress-bar">
            <view class="progress-fill" :style="{ width: plan.completion + '%' }" />
          </view>
          <text class="progress-text">{{ plan.doneCount }}/{{ plan.totalCount }} · {{ plan.actualMinutes }}/{{ plan.expectedMinutes }}min</text>
        </view>
      </view>

      <view v-if="!plan.tasks.length" class="state-box soft">
        <text class="state-title">今日暂无任务</text>
        <text class="state-desc">在下方添加一条，或去「本周计划」查看节奏</text>
      </view>

      <view class="task-list">
        <view
          v-for="task in plan.tasks"
          :key="task.id"
          class="task-item"
          :class="{ done: task.status === 'done', skipped: task.status === 'skipped' }"
        >
          <view class="task-check" @tap="onToggle(task)">
            <text v-if="task.status === 'done'" class="check-icon">✓</text>
          </view>
          <view class="task-body" @tap="onToggle(task)">
            <view class="task-line1">
              <text class="task-time" v-if="task.timeSlot">{{ task.timeSlot }}</text>
              <text class="task-subject" :class="subjectClass(task.subject)">{{ task.subject || '其他' }}</text>
              <text class="task-priority" :class="priorityClass(task.priority)">P{{ task.priority || 3 }}</text>
              <text v-if="task.expectedMinutes" class="task-min">{{ task.expectedMinutes }}min</text>
            </view>
            <text class="task-content">{{ task.content }}</text>
            <text v-if="task.note" class="task-note">{{ task.note }}</text>
          </view>
          <view class="task-actions">
            <text class="action-btn" @tap.stop="onNote(task)">备注</text>
            <text class="action-btn danger" @tap.stop="onRemove(task)">删除</text>
          </view>
        </view>
      </view>

      <view class="add-row">
        <nut-input v-model="newContent" placeholder="添加临时任务..." clearable class="add-input" />
        <nut-button size="small" type="primary" @click="onAdd">添加</nut-button>
      </view>

      <view class="review-card">
        <view class="review-title">今日复盘</view>
        <view v-if="plan.review" class="review-body">
          <view class="review-row">
            <text class="review-label">完成度</text>
            <text class="review-value">{{ plan.review.completion }}%</text>
          </view>
          <view class="review-row">
            <text class="review-label">弱项</text>
            <text class="review-value">{{ plan.review.weakPoint || '—' }}</text>
          </view>
          <view class="review-row">
            <text class="review-label">明日重点</text>
            <text class="review-value">{{ plan.review.tomorrowFocus || '—' }}</text>
          </view>
          <view class="review-row">
            <text class="review-label">心情</text>
            <text class="review-value">{{ moodLabel(plan.review.mood) }}</text>
          </view>
          <text v-if="plan.review.note" class="review-note">{{ plan.review.note }}</text>
          <nut-button size="small" plain type="primary" @click="editReview">编辑复盘</nut-button>
        </view>
        <view v-else>
          <text class="review-empty">还没填写今日复盘</text>
          <nut-button size="small" type="primary" @click="editReview">开始复盘</nut-button>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { Button as NutButton, Input as NutInput } from '@nutui/nutui-taro'
import { usePlanStore } from '@/store/plan'
import { promptText, showConfirm, showToast } from '@/utils/platform'
import type { PlanTask } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '今日清单' })

const { themeClass } = useThemeClass()
const planStore = usePlanStore()
const newContent = ref('')

const plan = computed(() => planStore.today)

const SUBJECT_CLASS: Record<string, string> = {
  行测: 'subj-red',
  申论: 'subj-amber',
  时政: 'subj-blue',
  资料: 'subj-blue',
  健身: 'subj-green',
  阅读: 'subj-muted',
  休息: 'subj-muted',
  复盘: 'subj-purple',
}

function subjectClass(s: string) {
  return SUBJECT_CLASS[s] || 'subj-muted'
}

function priorityClass(p: number) {
  if (p >= 5) return 'prio-high'
  if (p >= 4) return 'prio-mid'
  if (p >= 3) return 'prio-normal'
  return 'prio-low'
}

function moodLabel(m: string) {
  return { good: '不错', ok: '一般', bad: '差' }[m] || '—'
}

async function load() {
  await planStore.fetchToday()
}

onMounted(load)
useDidShow(load)

async function onToggle(task: PlanTask) {
  await planStore.toggleTask(task)
}

async function onNote(task: PlanTask) {
  const content = await promptText('添加备注', {
    placeholder: '记录完成情况/笔记...',
    defaultValue: task.note || '',
  })
  if (content === null) return
  await planStore.setTaskNote(task, content)
  showToast('已保存', 'success')
}

async function onRemove(task: PlanTask) {
  const ok = await showConfirm('删除任务', `确定删除「${task.content}」？`)
  if (!ok) return
  await planStore.removeTask(task.id)
}

async function onAdd() {
  if (!newContent.value.trim()) return
  await planStore.addTask(newContent.value.trim())
  newContent.value = ''
  showToast('已添加', 'success')
}

function editReview() {
  Taro.navigateTo({ url: '/pages/plan/review' })
}

</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-plan {
  @include page-padding;
  padding-bottom: 40px;
}

.state-box {
  @include page-state-box;
  &.soft { margin-bottom: 12px; }
}

.plan-header {
  @include card;
  padding: 16px;
  border-radius: $radius-lg;
  margin-bottom: 12px;
  .header-main {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 12px;
    .date { font-size: 18px; font-weight: 700; }
    .weekday {
      font-size: 12px;
      color: $text-muted;
      padding: 2px 8px;
      border-radius: 4px;
      background: $page-bg;
    }
  }
  .header-progress {
    .progress-bar {
      height: 6px;
      background: $page-bg;
      border-radius: 3px;
      overflow: hidden;
      .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, $primary-color, $primary-mid);
        border-radius: 3px;
        transition: width 0.3s;
      }
    }
    .progress-text {
      display: block;
      margin-top: 8px;
      font-size: 12px;
      color: $text-secondary;
    }
  }
}

.task-list {
  margin-bottom: 12px;
}

.task-item {
  @include card;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: $radius-md;
  &:active { opacity: 0.85; }
  &.done {
    .task-content {
      color: $text-muted;
      text-decoration: line-through;
    }
  }
}

.task-check {
  flex-shrink: 0;
  @include hit-target(44px);
  width: 44px;
  height: 44px;
  margin: -4px 0 0 -8px;
  border-radius: 50%;
  position: relative;
  &::after {
    content: '';
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: 2px solid $border-color;
    box-sizing: border-box;
  }
  .check-icon {
    position: absolute;
    color: $primary-color;
    font-weight: 700;
    font-size: 14px;
  }
  .done & {
    &::after {
      background: $primary-light;
      border-color: $primary-color;
    }
  }
}

.task-body {
  flex: 1;
  min-width: 0;
}

.task-line1 {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.task-time {
  font-size: 12px;
  color: $text-muted;
}

.task-subject {
  font-size: 12px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
  &.subj-red { color: $primary-color; background: $primary-light; }
  &.subj-amber { color: $accent-amber; background: rgba($accent-amber, 0.12); }
  &.subj-blue { color: $accent-blue; background: rgba($accent-blue, 0.1); }
  &.subj-green { color: $accent-green; background: rgba($accent-green, 0.1); }
  &.subj-purple { color: $accent-amber; background: rgba($accent-amber, 0.12); }
  &.subj-muted { color: $text-secondary; background: $chip-bg; }
}

.task-min {
  font-size: 12px;
  color: $text-muted;
}

.task-priority {
  font-size: 12px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  &.prio-high { color: $on-primary; background: $primary-color; }
  &.prio-mid { color: $primary-color; background: $primary-soft; }
  &.prio-normal { color: $text-secondary; background: $chip-bg; }
  &.prio-low { color: $text-muted; background: transparent; }
}

.task-content {
  font-size: 14px;
  line-height: 1.5;
  color: $text-primary;
}

.task-note {
  display: block;
  margin-top: 6px;
  padding: 6px 8px;
  background: $page-bg;
  border-radius: 6px;
  font-size: 12px;
  color: $text-secondary;
  line-height: 1.5;
}

.task-actions {
  display: flex;
  flex-direction: column;
  gap: 0;
  align-items: flex-end;
  .action-btn {
    @include list-act;
    font-size: 13px;
    color: $text-muted;
    &.danger { color: $primary-color; }
  }
}

.add-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  align-items: center;
  .add-input { flex: 1; }
}

.review-card {
  @include card;
  padding: 16px;
  border-radius: $radius-lg;
  .review-title {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 12px;
  }
  .review-body {
    .review-row {
      display: flex;
      padding: 6px 0;
      font-size: 13px;
      .review-label {
        width: 70px;
        color: $text-muted;
      }
      .review-value {
        flex: 1;
        color: $text-primary;
      }
    }
    .review-note {
      display: block;
      margin: 10px 0;
      padding: 8px 10px;
      background: $page-bg;
      border-radius: 6px;
      font-size: 12px;
      color: $text-secondary;
      line-height: 1.5;
    }
  }
  .review-empty {
    display: block;
    color: $text-muted;
    font-size: 13px;
    margin-bottom: 12px;
  }
}
</style>
