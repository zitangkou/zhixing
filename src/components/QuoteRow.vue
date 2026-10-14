<template>
  <view class="row" @tap="emit('tap', item.id)">
    <text v-if="topic" class="topic">{{ topic }}</text>
    <text class="text">{{ item.text }}</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DailyQuoteCard } from '@/types'

const props = defineProps<{ item: DailyQuoteCard }>()
const emit = defineEmits<{ tap: [id: string] }>()

const topic = computed(() => props.item.topics?.[0] || props.item.component || '')
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.row {
  @include card;
  margin-bottom: 8px;
  padding: 10px 12px;
}
.topic {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  line-height: 1.3;
  color: $primary-color;
}
.text {
  display: -webkit-box;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.45;
  color: $text-primary;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>
