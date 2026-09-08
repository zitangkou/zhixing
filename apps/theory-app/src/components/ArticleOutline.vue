<template>
  <scroll-view scroll-x class="article-outline" :show-scrollbar="false">
    <view
      v-for="(item, idx) in items"
      :key="item.id"
      class="outline-item"
      :class="{ active: activeId === item.id, read: isChapterRead(item) }"
      @tap="emit('select', item.id)"
    >
      <text class="idx">
        {{ idx + 1 }}
      </text>
      <text class="label">
        {{ item.title }}
      </text>
    </view>
  </scroll-view>
</template>

<script setup lang="ts">
import type { ArticleSection } from '@/types'

const props = defineProps<{
  items: ArticleSection[]
  activeId?: string
  readIds?: Set<string>
}>()

const emit = defineEmits<{ select: [id: string] }>()

function isChapterRead(chapter: ArticleSection) {
  if (!props.readIds?.size) return false
  const collect = (s: ArticleSection): string[] => {
    const ids: string[] = s.content?.trim() ? [s.id] : []
    s.children?.forEach((c) => ids.push(...collect(c)))
    return ids
  }
  const ids = collect(chapter)
  return ids.length > 0 && ids.every((id) => props.readIds!.has(id))
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.article-outline {
  white-space: nowrap;
  margin-bottom: 12px;
  .outline-item {
    display: inline-flex;
    align-items: flex-start;
    gap: 6px;
    padding: 8px 12px;
    margin-right: 8px;
    background: $page-bg;
    border-radius: 12px;
    border: 1px solid transparent;
    width: 168px;
    height: 52px;
    box-sizing: border-box;
    vertical-align: top;
    &.active {
      background: $primary-light;
      border-color: $primary-strong;
      .idx,
      .label {
        color: $primary-color;
      }
    }
    &.read:not(.active) {
      border-color: rgba(7, 193, 96, 0.35);
      .idx {
        background: rgba(7, 193, 96, 0.15);
        color: var(--zk-success);
      }
    }
    .idx {
      width: 18px;
      height: 18px;
      line-height: 18px;
      text-align: center;
      border-radius: 50%;
      background: $hover-bg;
      font-size: 11px;
      font-weight: 600;
      flex-shrink: 0;
      margin-top: 1px;
    }
    .label {
      flex: 1;
      min-width: 0;
      font-size: 12px;
      line-height: 1.4;
      height: 33.6px;
      overflow: hidden;
      white-space: normal;
      word-break: break-all;
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }
  }
}
</style>

