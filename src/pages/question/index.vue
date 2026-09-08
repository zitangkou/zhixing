<template>
  <view class="page-quiz page-with-tabbar" :class="themeClass">
    <view class="mode-panel">
      <view class="task-card">
        <text class="task-title">今日练习</text>
        <text class="task-desc">已答 {{ questionStore.answeredToday }} 题 · 错题 {{ questionStore.wrongCount }} 道</text>
      </view>

      <view class="hub-section">
        <text class="hub-title">时政刷题</text>
        <text class="hub-sub">随机抽题，或按文章练</text>
        <view class="mode-grid">
          <view
            v-for="item in quizModes"
            :key="item.mode"
            class="mode-item"
            @tap="onSelectMode(item.mode)"
          >
            <view class="mode-icon-wrap">
              <component :is="modeIcons[item.icon]" :color="brandColor" size="22" />
            </view>
            <text class="mode-name">{{ item.title }}</text>
            <text class="mode-desc">{{ item.desc }}</text>
          </view>
        </view>
      </view>

      <view class="hub-section">
        <text class="hub-title">资料分析</text>
        <text class="hub-sub">公式技巧 · 材料组专项练</text>
        <view class="entry-list">
          <view class="entry-row" @tap="goPage('/pages/ziliao/index')">
            <view class="entry-icon"><Category :color="brandColor" size="18" /></view>
            <view class="entry-text">
              <text class="entry-name">资料分析首页</text>
              <text class="entry-desc">学公式 · 练材料组</text>
            </view>
            <text class="entry-arrow">›</text>
          </view>
          <view class="entry-row" @tap="goPage('/pages/question/manual-list?subject=资料')">
            <view class="entry-icon"><Failure :color="brandColor" size="18" /></view>
            <view class="entry-text">
              <text class="entry-name">资料错题本</text>
              <text class="entry-desc">专项错题复习</text>
            </view>
            <text class="entry-arrow">›</text>
          </view>
        </view>
      </view>

      <view class="hub-section">
        <text class="hub-title">套卷与错题</text>
        <text class="hub-sub">整卷演练 · 薄弱回顾</text>
        <view class="entry-list">
          <view class="entry-row" @tap="goPage('/pages/exam/list')">
            <view class="entry-icon"><Order :color="brandColor" size="18" /></view>
            <view class="entry-text">
              <text class="entry-name">真题套卷</text>
              <text class="entry-desc">按套限时作答</text>
            </view>
            <text class="entry-arrow">›</text>
          </view>
          <view class="entry-row" @tap="goPage('/pages/question/wrong')">
            <view class="entry-icon"><Failure :color="brandColor" size="18" /></view>
            <view class="entry-text">
              <text class="entry-name">文章错题本</text>
              <text class="entry-desc">时政题错题重练</text>
            </view>
            <text class="entry-arrow">›</text>
          </view>
          <view class="entry-row" @tap="goPage('/pages/question/manual-list')">
            <view class="entry-icon"><Edit :color="brandColor" size="18" /></view>
            <view class="entry-text">
              <text class="entry-name">行测错题本</text>
              <text class="entry-desc">可关联知识考点</text>
            </view>
            <text class="entry-arrow">›</text>
          </view>
          <view class="entry-row" @tap="goPage('/pages/rmrb/drill')">
            <view class="entry-icon"><Fabulous :color="brandColor" size="18" /></view>
            <view class="entry-text">
              <text class="entry-name">申论阶梯训练</text>
              <text class="entry-desc">造句 · 仿写 · 口述</text>
            </view>
            <text class="entry-arrow">›</text>
          </view>
        </view>
      </view>
    </view>

    <AppTabBar active="quiz" />
  </view>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import {
  Category,
  Edit,
  Fabulous,
  Failure,
  Order,
  Refresh,
} from '@nutui/icons-vue-taro'
import AppTabBar from '@/components/AppTabBar.vue'
import { QUIZ_MODES } from '@/constants/article'
import { useQuestionStore } from '@/store/question'
import type { QuizMode } from '@/types'
import { bootstrapApp } from '@/utils/bootstrap'
import { useBrandColor, useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '练习' })

const { themeClass } = useThemeClass()
const questionStore = useQuestionStore()
const { brandColor } = useBrandColor()
const quizModes = QUIZ_MODES
const modeIcons = { Refresh, Category } as const

async function load() {
  await bootstrapApp()
  await questionStore.loadWrongQuestions()
}

function goPage(url: string) {
  Taro.navigateTo({ url })
}

function onSelectMode(mode: QuizMode) {
  if (mode === 'article') {
    Taro.navigateTo({ url: '/pages/question/article-pick' })
    return
  }
  Taro.navigateTo({ url: `/pages/question/taking?mode=${mode}` })
}

onMounted(load)
useDidShow(() => {
  void questionStore.loadWrongQuestions()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-quiz {
  @include page-padding;
  .mode-panel {
    .task-card {
      @include card;
      padding: 16px;
      margin-bottom: 16px;
      border-radius: $radius-lg;
      background: linear-gradient(135deg, $primary-light, $primary-faint);
      .task-title { display: block; font-size: 16px; font-weight: 600; margin-bottom: 6px; color: $text-primary; }
      .task-desc { font-size: 13px; color: $text-secondary; }
    }
    .hub-section {
      margin-bottom: 20px;
      .hub-title {
        display: block;
        font-size: 16px;
        font-weight: 700;
        color: $text-primary;
        margin-bottom: 4px;
      }
      .hub-sub {
        display: block;
        font-size: 12px;
        color: $text-muted;
        margin-bottom: 12px;
      }
    }
    .mode-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }
    .mode-item {
      @include card;
      margin-bottom: 0;
      padding: 16px 14px;
      border-radius: $radius-lg;
      .mode-icon-wrap {
        @include icon-tile;
        margin-bottom: 10px;
      }
      .mode-name { display: block; font-size: 14px; font-weight: 600; margin-bottom: 4px; color: $text-primary; }
      .mode-desc { font-size: 11px; color: $text-muted; line-height: 1.4; }
    }
    .entry-list {
      @include card;
      margin-bottom: 0;
      padding: 0;
      overflow: hidden;
      .entry-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 14px 14px;
        border-bottom: 1px solid $border-color;
        &:last-child { border-bottom: none; }
        .entry-icon {
          @include icon-tile;
          width: 36px;
          height: 36px;
          border-radius: 10px;
        }
        .entry-text { flex: 1; min-width: 0; }
        .entry-name {
          display: block;
          font-size: 14px;
          font-weight: 600;
          color: $text-primary;
          margin-bottom: 2px;
        }
        .entry-desc { display: block; font-size: 11px; color: $text-muted; }
        .entry-arrow { color: $text-muted; }
      }
    }
  }
}
</style>
