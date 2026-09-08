<template>
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
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '知行申论' })

const { themeClass } = useThemeClass()
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
.entry-item {
  @include card;
  padding: 14px 12px;
  margin-bottom: 0;
  .entry-name { display: block; font-size: 15px; font-weight: 700; margin-bottom: 4px; }
  .entry-desc { font-size: 12px; color: $text-muted; line-height: 1.35; }
}
</style>
