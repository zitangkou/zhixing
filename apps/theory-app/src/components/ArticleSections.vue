<template>
  <view class="article-sections">
    <view
      v-for="section in sections"
      :id="`sec-${section.id}`"
      :key="section.id"
      class="section-block"
      :class="[`level-${section.level}`, { 'is-read': isRead(section.id) }]"
    >
      <view class="section-header" @tap="onHeaderTap(section)">
        <view class="title-row">
          <text v-if="section.level === 1" class="chapter-badge">
            第{{ chapterIndex(section.id) }}章
          </text>
          <text class="section-title">
            {{ section.title }}
          </text>
          <text v-if="isReadable(section) && isRead(section.id)" class="read-badge"> 已读 </text>
        </view>
        <text v-if="hasBody(section)" class="toggle-icon">
          {{ isOpen(section.id) ? '▼' : '▶' }}
        </text>
      </view>

      <view v-if="isOpen(section.id)" class="section-body">
        <text v-if="section.content" class="section-content selectable-text" user-select selectable>
          {{ section.content }}
        </text>
        <view v-if="section.highlight" class="highlight">
          <text class="highlight-label"> 要点 </text>
          <text class="selectable-text" user-select selectable>
            {{ section.highlight }}
          </text>
        </view>
        <view
          v-if="isReadable(section) && !isRead(section.id)"
          class="mark-read-btn"
          @tap.stop="emit('read', section.id)"
        >
          标记本节已读
        </view>
        <ArticleSections
          v-if="section.children?.length"
          :sections="section.children"
          :open-ids="openIds"
          :read-ids="readIds"
          @toggle="(id: string) => emit('toggle', id)"
          @read="(id: string) => emit('read', id)"
        />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import type { ArticleSection } from '@/types'

defineOptions({ name: 'ArticleSections' })

const props = defineProps<{
  sections: ArticleSection[]
  openIds: Set<string>
  readIds: Set<string>
}>()

const emit = defineEmits<{ toggle: [id: string]; read: [id: string] }>()

function isOpen(id: string) {
  return props.openIds.has(id)
}

function isRead(id: string) {
  return props.readIds.has(id)
}

function isReadable(section: ArticleSection) {
  return !!section.content?.trim()
}

function hasBody(section: ArticleSection) {
  return !!(section.content || section.children?.length || section.highlight)
}

function onHeaderTap(section: ArticleSection) {
  if (!hasBody(section)) return
  const willOpen = !isOpen(section.id)
  emit('toggle', section.id)
  if (isReadable(section) && willOpen) {
    emit('read', section.id)
  }
}

function chapterIndex(id: string) {
  const num = props.sections.findIndex((s) => s.id === id)
  const cn = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
  return cn[num] ?? String(num + 1)
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.article-sections {
  .section-block {
    margin-bottom: 12px;
    &.level-1 {
      background: $card-bg;
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
      .section-header {
        min-height: 56px;
        box-sizing: border-box;
      }
      .section-title {
        height: 43.5px;
      }
    }
    &.is-read.level-2,
    &.is-read.level-3 {
      .section-header {
        opacity: 0.92;
      }
    }
    &.level-2 {
      padding-left: 12px;
      margin-top: 8px;
    }
    &.level-3 {
      padding-left: 8px;
      margin-top: 6px;
    }
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px;
    .level-2 & {
      padding: 10px 12px;
      background: $page-bg;
      border-radius: 8px;
    }
    .level-3 & {
      padding: 8px 10px;
    }
  }

  .title-row {
    flex: 1;
    display: flex;
    align-items: flex-start;
    gap: 8px;
    min-width: 0;
  }

  .chapter-badge {
    font-size: 11px;
    color: $primary-color;
    background: $primary-light;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
    flex-shrink: 0;
    line-height: 1.4;
    margin-top: 1px;
  }

  .read-badge {
    font-size: 10px;
    color: var(--zk-success);
    background: rgba(7, 193, 96, 0.1);
    padding: 1px 6px;
    border-radius: 4px;
  }

  .section-title {
    flex: 1;
    min-width: 0;
    font-size: 15px;
    font-weight: 600;
    line-height: 1.45;
    overflow: hidden;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    word-break: break-all;
    .level-2 & {
      font-size: 14px;
      font-weight: 500;
      -webkit-line-clamp: 2;
    }
    .level-3 & {
      font-size: 13px;
      color: $text-secondary;
      -webkit-line-clamp: 2;
    }
  }

  .toggle-icon {
    font-size: 10px;
    color: $text-muted;
    margin-left: 8px;
  }

  .section-body {
    padding: 0 16px 14px;
    .level-2 & {
      padding: 0 0 8px 0;
    }
  }

  .section-content {
    display: block;
    font-size: 15px;
    line-height: 1.9;
    color: $text-primary;
    white-space: pre-wrap;
    margin-bottom: 10px;
    -webkit-user-select: text;
    user-select: text;
  }

  .selectable-text {
    -webkit-user-select: text;
    user-select: text;
  }

  .mark-read-btn {
    display: inline-block;
    font-size: 12px;
    color: $primary-color;
    padding: 6px 0;
    margin-bottom: 8px;
  }

  .highlight {
    padding: 10px 12px;
    background: $primary-light;
    border-left: 3px solid $primary-color;
    border-radius: 0 6px 6px 0;
    font-size: 13px;
    line-height: 1.7;
    color: $text-secondary;
    margin-bottom: 8px;
    .highlight-label {
      display: block;
      font-size: 11px;
      color: $primary-color;
      font-weight: 600;
      margin-bottom: 4px;
    }
  }
}
</style>

