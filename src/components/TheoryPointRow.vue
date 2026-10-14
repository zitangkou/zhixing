<template>
  <view>
    <view class="row" @tap="onTap">
      <view class="line">
        <text v-if="item.isKey" class="chip key">重点</text>
        <text class="title">{{ item.title }}</text>
        <text class="go">{{ statusText }}</text>
      </view>
      <text v-if="item.summary" class="summary">{{ item.summary }}</text>
    </view>
    <view v-if="open && item.sections?.length" class="sections">
      <view v-for="child in item.sections" :key="child.id" class="row child" @tap="emit('tap', child.id)">
        <view class="line">
          <text v-if="child.isKey" class="chip key">重点</text>
          <text class="title">{{ child.title }}</text>
          <text class="go">{{ childStatus(child) }}</text>
        </view>
        <text v-if="child.summary" class="summary">{{ child.summary }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { TheoryPointCard } from '@/types'

const props = defineProps<{ item: TheoryPointCard }>()
const emit = defineEmits<{ tap: [id: string] }>()
const open = ref(false)

function statusOf(item: TheoryPointCard) {
  const total = item.questionCount || 0
  const answered = item.answered || 0
  const wrong = item.wrongLeft || 0
  if (!total) return '暂无题'
  if (!answered) return `${total} 题`
  if (answered < total) return `${answered}/${total}`
  if (wrong > 0) return `错 ${wrong}`
  return '已完成'
}

const statusText = computed(() => {
  const count = props.item.sections?.length || 0
  if (count) return open.value ? '收起' : `${count} 节`
  return statusOf(props.item)
})

function childStatus(item: TheoryPointCard) {
  return statusOf(item)
}

function onTap() {
  if (props.item.sections?.length) {
    open.value = !open.value
    return
  }
  emit('tap', props.item.id)
}
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
.sections {
  margin: -4px 0 8px 12px;
}
.child {
  background: $page-bg;
}
</style>
