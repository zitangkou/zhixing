<template>
  <view class="seg-list">
    <view v-if="!items.length" class="seg-empty">
      <text>导图生成中，可先看大纲</text>
    </view>
    <view
      v-for="(it, idx) in items"
      :key="it.key || idx"
      class="seg-card"
      @tap="onPreview(idx)"
    >
      <image class="seg-img" :src="it.thumb" mode="widthFix" lazy-load />
      <text class="seg-title">{{ it.title }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Taro from '@tarojs/taro'
import type { KnowledgeMapManifest } from '@/types'
import { resolveMediaUrl } from '@/utils/media'

const props = defineProps<{
  manifest: KnowledgeMapManifest | null | undefined
}>()

type Item = { key: string; title: string; thumb: string; full: string }

const items = computed<Item[]>(() => {
  const m = props.manifest
  if (!m) return []
  const out: Item[] = []
  if (m.overview?.url || m.overview?.thumbUrl) {
    out.push({
      key: 'overview',
      title: '概览',
      thumb: resolveMediaUrl(m.overview.thumbUrl || m.overview.url),
      full: resolveMediaUrl(m.overview.url),
    })
  }
  for (const s of m.segments || []) {
    if (!s.url && !s.thumbUrl) continue
    out.push({
      key: s.key,
      title: s.title,
      thumb: resolveMediaUrl(s.thumbUrl || s.url),
      full: resolveMediaUrl(s.url),
    })
  }
  return out
})

function onPreview(idx: number) {
  const urls = items.value.map((i) => i.full)
  if (!urls.length) return
  Taro.previewImage({
    urls,
    current: urls[idx],
  })
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.seg-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.seg-empty {
  text-align: center;
  color: $text-muted;
  font-size: 13px;
  padding: 32px 0;
}
.seg-card {
  @include card;
  padding: 10px;
  border-radius: $radius-md;
}
.seg-img {
  width: 100%;
  border-radius: 6px;
  background: $page-bg;
  display: block;
}
.seg-title {
  display: block;
  margin-top: 8px;
  font-size: 13px;
  color: $text-secondary;
}
</style>
