<template>
  <view class="page" :class="themeClass">
    <view v-if="loading" class="state">加载中…</view>
    <view v-else-if="!item" class="state">这条金句不存在或尚未确认</view>
    <template v-else>
      <view class="hero">
        <view class="hero-meta">
          <text v-if="item.component" class="pill">{{ item.component }}</text>
          <text v-for="name in item.topics" :key="name" class="pill">{{ name }}</text>
        </view>
        <text class="quote">{{ item.text }}</text>
        <view v-if="item.highlights.length" class="words">
          <text v-for="word in item.highlights" :key="word" class="word">{{ word }}</text>
        </view>
      </view>

      <view v-if="item.formula" class="block">
        <text class="label">句式</text>
        <text class="body">{{ item.formula }}</text>
      </view>
      <view v-if="item.use" class="block">
        <text class="label">用法</text>
        <text class="body">{{ item.use }}</text>
      </view>
      <view v-if="item.why" class="block">
        <text class="label">为什么好</text>
        <text class="body">{{ item.why }}</text>
      </view>
      <view v-if="item.guidance" class="block">
        <text class="label">怎么用</text>
        <text class="body">{{ item.guidance }}</text>
      </view>
      <view v-if="item.pitfall" class="block">
        <text class="label">注意</text>
        <text class="body">{{ item.pitfall }}</text>
      </view>

      <view v-if="item.examples.length" class="block">
        <text class="label">仿写</text>
        <view v-for="ex in item.examples" :key="ex.text" class="example">
          <text class="example-topic">{{ ex.topic }}</text>
          <text class="example-text">{{ ex.text }}</text>
        </view>
      </view>

      <view v-if="item.articleTitle" class="block source">
        <text class="label">来源</text>
        <text class="source-title">{{ item.articleTitle }}</text>
        <text class="source-meta">{{ item.source }}{{ item.articleDate ? ' · ' + item.articleDate : '' }}</text>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro, { useLoad } from '@tarojs/taro'
import { api } from '@/api'
import type { DailyQuoteCard } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '金句详情' })

const { themeClass } = useThemeClass()
const item = ref<DailyQuoteCard | null>(null)
const loading = ref(true)

useLoad(async (params) => {
  const id = params?.id || ''
  try {
    const res = await api.getQuotes()
    if (res.code === 0 && res.data) item.value = res.data.find((row) => row.id === id) || null
  } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page { @include page-padding; padding-bottom: 32px; }
.state { text-align: center; color: $text-muted; padding: 48px 0; }
.hero {
  @include brand-gradient;
  border-radius: $radius-lg;
  padding: 18px 16px 16px;
  color: #fff;
}
.hero-meta { display: flex; flex-wrap: wrap; gap: 6px; }
.pill {
  font-size: 11px;
  line-height: 1;
  padding: 4px 8px;
  border-radius: 99px;
  color: #fff;
  background: rgba(255, 255, 255, 0.18);
}
.quote {
  display: block;
  margin-top: 12px;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.65;
  color: #fff;
}
.words { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.word {
  font-size: 12px;
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  padding: 2px 8px;
  border-radius: 8px;
}
.block {
  @include card;
  margin-top: 10px;
  padding: 14px;
  border-radius: $radius-lg;
}
.label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 700;
  color: $primary-color;
}
.body { display: block; font-size: 14px; line-height: 1.65; color: $text-primary; }
.example { margin-top: 10px; }
.example-topic { display: block; font-size: 12px; color: $text-muted; }
.example-text { display: block; margin-top: 2px; font-size: 14px; line-height: 1.6; color: $text-secondary; }
.source-title { display: block; font-size: 15px; font-weight: 650; line-height: 1.5; color: $text-primary; }
.source-meta { display: block; margin-top: 4px; font-size: 12px; line-height: 1.5; color: $text-muted; }
</style>
