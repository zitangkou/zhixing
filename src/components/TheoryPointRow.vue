<template>
  <view class="row" @tap="emit('tap', item.id)">
    <view class="line">
      <text v-if="item.isKey" class="chip key">重点</text>
      <text class="title">{{ item.title }}</text>
      <text class="go">{{ statusText }}</text>
    </view>
    <text v-if="item.summary" class="summary">{{ item.summary }}</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TheoryPointCard } from '@/types'

const props = defineProps<{ item: TheoryPointCard }>()
const emit = defineEmits<{ tap: [id: string] }>()

const statusText = computed(() => {
  const total = props.item.questionCount || 0
  const answered = props.item.answered || 0
  const wrong = props.item.wrongLeft || 0
  if (!total) return '暂无题'
  if (!answered) return `${total} 题`
  if (answered < total) return `${answered}/${total}`
  if (wrong > 0) return `错 ${wrong}`
  return '已完成'
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.row {
  @include card;
  margin-bottom: 8px;
  padding: 10px 12px;
}
.line {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.chip {
  flex-shrink: 0;
  font-size: 11px;
  line-height: 1;
  color: $primary-color;
  background: $primary-light;
  padding: 3px 6px;
  border-radius: 4px;
  &.key {
    color: #fff;
    background: $primary-color;
  }
}
.title {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  font-weight: 650;
  color: $text-primary;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.go {
  flex-shrink: 0;
  font-size: 12px;
  color: $primary-color;
}
.summary {
  display: -webkit-box;
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.45;
  color: $text-secondary;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>
