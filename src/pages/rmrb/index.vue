<template>
  <page-meta
    v-if="isWeapp"
    :page-style="pageMeta.pageStyle"
    :background-color="pageMeta.backgroundColor"
    :background-color-top="pageMeta.backgroundColorTop"
    :background-color-bottom="pageMeta.backgroundColorBottom"
    :background-text-style="pageMeta.backgroundTextStyle"
  />
  <view class="page-rmrb" :class="themeClass">
    <view v-if="stats" class="hero-card">
      <view class="hero-item">
        <text class="hero-num">{{ stats.weekMineDays }}/{{ stats.weekMineTarget }}</text>
        <text class="hero-label">本周开采</text>
      </view>
      <view class="hero-item">
        <text class="hero-num">{{ stats.termCount }}</text>
        <text class="hero-label">规范词</text>
      </view>
      <view class="hero-item">
        <text class="hero-num">{{ stats.todayMined ? '✓' : '—' }}</text>
        <text class="hero-label">今日</text>
      </view>
    </view>
    <view class="method-tip">先看教研示范（考题定位 → 原文 → 骨架 → 词句 → 迁移），再跟做开采。</view>
    <view class="exercise-entry" @tap="go('/pages/rmrb/exercise-list')">
      <view><text class="exercise-title">申论题型练习</text><text class="exercise-desc">归纳概括 · 提出对策 · 贯彻执行 · 申发论述</text></view>
      <text class="exercise-arrow">开始练习 ›</text>
    </view>
    <view class="entry-grid">
      <view class="entry-item" @tap="go('/pages/rmrb/article-list')">
        <text class="entry-name">时评阅读</text><text class="entry-desc">精读 + 三刀解剖</text>
      </view>
      <view class="entry-item" @tap="go('/pages/rmrb/mines')">
        <text class="entry-name">开采本</text><text class="entry-desc">每日一行记录</text>
      </view>
      <view class="entry-item" @tap="go('/pages/rmrb/terms')">
        <text class="entry-name">规范词库</text><text class="entry-desc">{{ stats?.learningTermCount || 0 }} 学习中</text>
      </view>
      <view class="entry-item" @tap="go('/pages/rmrb/drill')">
        <text class="entry-name">阶梯训练</text><text class="entry-desc">本周 {{ stats?.weekDrillCount || 0 }} 次</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { api } from '@/api'
import type { ShenlunStats } from '@/types'
import { useThemeClass, usePageMeta } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '申论' })

const { themeClass } = useThemeClass()
const pageMeta = usePageMeta()
const isWeapp = process.env.TARO_ENV === 'weapp'
const stats = ref<ShenlunStats | null>(null)

function go(url: string) {
  Taro.navigateTo({ url })
}

async function load() {
  const res = await api.getRmrbStats()
  if (res.code === 0 && res.data) stats.value = res.data
}

onMounted(load)
useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-rmrb { @include page-padding; padding-bottom: 32px; }
.hero-card {
  @include card;
  display: flex;
  padding: 14px 12px;
  margin-bottom: 12px;
  .hero-item {
    flex: 1;
    text-align: center;
    padding: 0 4px;
    & + .hero-item { border-left: 1px solid $border-color; }
    .hero-num { display: block; font-size: 20px; font-weight: 700; color: $primary-color; }
    .hero-label { font-size: 12px; color: $text-muted; margin-top: 2px; }
  }
}
.method-tip {
  font-size: 12px;
  color: $text-muted;
  line-height: 1.55;
  margin: 0 0 14px;
  padding: 10px 12px;
  background: $elevated;
  border-radius: $radius-md;
  border: 1px solid $border-color;
}
.entry-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.exercise-entry {
  @include card;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  .exercise-title { display: block; font-size: 15px; font-weight: 700; color: $text-primary; }
  .exercise-desc { display: block; margin-top: 5px; font-size: 11px; color: $text-muted; }
  .exercise-arrow { flex: none; color: $primary-color; font-size: 12px; font-weight: 600; }
}
.entry-item {
  @include card;
  padding: 14px 12px;
  margin-bottom: 0;
  .entry-name { display: block; font-size: 15px; font-weight: 700; margin-bottom: 4px; }
  .entry-desc { font-size: 12px; color: $text-muted; line-height: 1.35; }
}
</style>
