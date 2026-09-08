<template>
  <view v-if="section" class="section-pager">
    <view class="pager-meta">
      <nut-tag type="primary" plain size="small"> 第 {{ index + 1 }}/{{ total }} 节 </nut-tag>
      <text v-if="isRead" class="read-tag"> 已读 ✓ </text>
    </view>
    <text class="pager-title selectable-text" user-select selectable>
      {{ section.title }}
    </text>
    <text class="pager-content selectable-text" user-select selectable>
      {{ section.content }}
    </text>
    <view v-if="section.highlight" class="highlight">
      <text class="highlight-label"> 要点 </text>
      <text class="selectable-text" user-select selectable>
        {{ section.highlight }}
      </text>
    </view>
    <view class="pager-actions">
      <nut-button size="small" plain :disabled="index === 0" @click="emit('prev')">
        上一节
      </nut-button>
      <nut-button size="small" type="primary" plain @click="emit('mark-read')">
        {{ isRead ? '已标记' : '标记已读' }}
      </nut-button>
      <nut-button size="small" plain :disabled="index >= total - 1" @click="emit('next')">
        下一节
      </nut-button>
    </view>
  </view>
  <view v-else class="empty-tip"> 暂无小节内容 </view>
</template>

<script setup lang="ts">
import { Button as NutButton, Tag as NutTag } from '@nutui/nutui-taro'
import type { ArticleSection } from '@/types'

defineProps<{
  section: ArticleSection | null
  index: number
  total: number
  isRead: boolean
}>()

const emit = defineEmits<{
  prev: []
  next: []
  'mark-read': []
}>()
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.section-pager {
  background: $card-bg;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  .pager-meta {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    .read-tag {
      font-size: 12px;
      color: var(--zk-success);
    }
  }
  .pager-title {
    display: block;
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 12px;
    line-height: 1.5;
  }
  .pager-content {
    display: block;
    font-size: 15px;
    line-height: 1.9;
    color: $text-primary;
    white-space: pre-wrap;
    margin-bottom: 12px;
    -webkit-user-select: text;
    user-select: text;
  }
  .selectable-text {
    -webkit-user-select: text;
    user-select: text;
  }
  .highlight {
    padding: 10px 12px;
    background: $primary-light;
    border-left: 3px solid $primary-color;
    border-radius: 0 6px 6px 0;
    font-size: 13px;
    line-height: 1.7;
    margin-bottom: 16px;
    .highlight-label {
      display: block;
      font-size: 11px;
      color: $primary-color;
      font-weight: 600;
      margin-bottom: 4px;
    }
  }
  .pager-actions {
    display: flex;
    justify-content: space-between;
    gap: 8px;
  }
}
</style>
