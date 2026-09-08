<template>
  <view class="article-card" :class="{ featured: article.isFeatured }" @tap="onTap">
    <view class="card-meta">
      <text v-if="article.isFeatured" class="chip chip-pin"> 置顶 </text>
      <text
        v-if="article.importance && article.importance >= 4"
        class="chip"
        :class="importanceChipClass"
      >
        {{ article.importanceLabel || '重点' }}
      </text>
      <text class="chip chip-source">
        {{ article.source }}
      </text>
      <text class="meta-date">
        {{ article.publishDate }}
      </text>
    </view>
    <text v-if="article.categoryName" class="category-line">
      {{ article.categoryName }}
    </text>
    <text class="title">
      {{ article.title }}
    </text>
    <text class="summary">
      {{ article.summary }}
    </text>
    <view class="card-footer">
      <view class="tags">
        <text
          v-for="(tag, idx) in article.tags.slice(0, 2)"
          :key="tag"
          class="chip"
          :class="`tone-${idx % 3}`"
        >
          {{ tag }}
        </text>
        <text v-if="article.sections?.length" class="chip tone-muted">
          {{ article.sections.length }} 章
        </text>
      </view>
      <text class="action"> 阅读 › </text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Article } from '@/types'

const props = defineProps<{ article: Article }>()
const emit = defineEmits<{ tap: [id: string] }>()

const importanceChipClass = computed(() => {
  const level = props.article.importance || 3
  if (level >= 5) return 'chip-danger'
  if (level >= 4) return 'chip-warn'
  return 'tone-muted'
})

function onTap() {
  emit('tap', props.article.id)
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.article-card {
  @include card;
  border-radius: $radius-lg;
  border: none;
  position: relative;
  overflow: hidden;

  &.featured {
    background: radial-gradient(120% 80% at 100% 0%, $primary-faint 0%, transparent 50%), $card-bg;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 3px;
      background: linear-gradient(180deg, $primary-color 0%, $primary-soft 100%);
    }
  }

  .card-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 10px;
  }

  .chip {
    flex-shrink: 0;
    max-width: 42%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    @include muted-chip;
  }

  .chip-pin {
    color: #fff;
    background: $primary-color;
  }

  .chip-source {
    @include soft-chip($accent-blue, 0.1);
  }

  .chip-danger {
    @include soft-chip($primary-hex, 0.1);
  }

  .chip-warn {
    @include soft-chip($accent-amber, 0.12);
  }

  .tone-0 {
    @include soft-chip($primary-hex, 0.1);
  }
  .tone-1 {
    @include soft-chip($accent-blue, 0.1);
  }
  .tone-2 {
    @include soft-chip($accent-green, 0.1);
  }
  .tone-muted {
    @include muted-chip;
  }

  .meta-date {
    margin-left: auto;
    flex-shrink: 0;
    font-size: 11px;
    color: $text-muted;
  }

  .category-line {
    display: block;
    font-size: 11px;
    color: $text-muted;
    margin-bottom: 4px;
  }

  .title {
    display: block;
    font-size: 16px;
    font-weight: 600;
    line-height: 1.5;
    color: $text-primary;
    margin-bottom: 8px;
  }

  .summary {
    font-size: 13px;
    color: $text-secondary;
    line-height: 1.6;
    margin-bottom: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;

    .tags {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      min-width: 0;
      flex: 1;
    }

    .action {
      flex-shrink: 0;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      color: $primary-color;
      background: $primary-light;
    }
  }
}
</style>
