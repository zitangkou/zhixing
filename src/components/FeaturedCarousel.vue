<template>
  <swiper
    v-if="articles.length"
    class="featured-swiper"
    :indicator-dots="articles.length > 1"
    :indicator-color="indicatorMuted"
    :indicator-active-color="brandColor"
    :autoplay="articles.length > 1"
    :circular="articles.length > 1"
    :interval="4500"
    :duration="400"
  >
    <swiper-item v-for="article in articles" :key="article.id">
      <view class="featured-slide" @tap="onTap(article.id)">
        <view class="slide-accent" />
        <view class="slide-body">
          <view class="slide-meta">
            <text class="chip chip-pin"> 置顶 </text>
            <text class="chip chip-source">
              {{ article.source }}
            </text>
            <text class="meta-date">
              {{ article.publishDate }}
            </text>
          </view>
          <text class="slide-title">
            {{ article.title }}
          </text>
          <text class="slide-summary">
            {{ article.summary }}
          </text>
          <view class="slide-footer">
            <text class="chip chip-hint"> 重点必读 </text>
            <text class="slide-action"> 立即阅读 › </text>
          </view>
        </view>
      </view>
    </swiper-item>
  </swiper>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Article } from '@/types'
import { useBrandColor, withAlpha } from '@/utils/brandColor'

defineProps<{ articles: Article[] }>()
const emit = defineEmits<{ tap: [id: string] }>()
const { brandColor, darkMode } = useBrandColor()
const indicatorMuted = computed(() => withAlpha(brandColor.value, darkMode.value ? 0.28 : 0.18))

function onTap(id: string) {
  emit('tap', id)
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.featured-swiper {
  height: 172px;
  border-radius: $radius-lg;
  overflow: hidden;
}

.featured-slide {
  position: relative;
  height: 100%;
  box-sizing: border-box;
  display: flex;
  background: $card-bg;
  border-radius: $radius-lg;
  box-shadow: $shadow-card;
  overflow: hidden;

  /* 左侧品牌强调，替代整块红底 */
  .slide-accent {
    width: 4px;
    flex-shrink: 0;
    background: linear-gradient(180deg, $primary-color 0%, $primary-soft 100%);
  }

  .slide-body {
    flex: 1;
    min-width: 0;
    padding: 14px 14px 14px 12px;
    display: flex;
    flex-direction: column;
    /* 右上角极淡暖色，与灰底形成层次，但不抢内容 */
    background: radial-gradient(120% 80% at 100% 0%, $primary-faint 0%, transparent 55%), $card-bg;
  }

  .slide-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 10px;
  }

  .chip {
    flex-shrink: 0;
    max-width: 46%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chip-pin {
    @include soft-chip($primary-hex, 1);
    color: #fff;
    background: $primary-color;
  }

  .chip-source {
    @include soft-chip($accent-blue, 0.1);
  }

  .chip-hint {
    @include soft-chip($accent-amber, 0.12);
  }

  .meta-date {
    margin-left: auto;
    flex-shrink: 0;
    font-size: 11px;
    color: $text-muted;
  }

  .slide-title {
    font-size: 16px;
    font-weight: 700;
    line-height: 1.45;
    color: $text-primary;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .slide-summary {
    flex: 1;
    margin-top: 6px;
    font-size: 12px;
    line-height: 1.5;
    color: $text-secondary;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .slide-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
    gap: 8px;
  }

  .slide-action {
    flex-shrink: 0;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    color: $primary-color;
    background: $primary-light;
  }
}
</style>
