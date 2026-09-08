<template>
  <view class="page-today page-with-tabbar" :class="themeClass">
    <view class="today-header">
      <view class="today-greet">
        <text class="today-hi">
          {{ greeting }}
        </text>
        <text class="today-slogan">
          {{ APP_SLOGAN }}
        </text>
      </view>
      <view class="today-date">
        {{ dateLabel }}
      </view>
    </view>

    <view class="track-list">
      <view class="track-card" @tap="goTheory">
        <text class="track-kicker">今日时政</text>
        <text class="track-title">按文章练</text>
        <text class="track-desc">选一篇文章，刷该文配套题目</text>
      </view>
      <view class="track-card" @tap="goRmrb">
        <text class="track-kicker">今日申论</text>
        <text class="track-title">时评精拆 · 三刀法</text>
        <text class="track-desc">时评阅读、开采本、规范词、阶梯训练</text>
      </view>
    </view>

    <view class="quick-row">
      <view
        class="q-item"
        @tap="goSignIn"
      >
        <view class="q-icon-wrap">
          <DateIcon
            :color="brandColor"
            size="20"
          />
        </view>
        <text>{{ userStore.hasSignedToday ? '已签到' : '签到' }}</text>
      </view>
      <view
        class="q-item"
        @tap="goQuiz"
      >
        <view class="q-icon-wrap">
          <Edit
            :color="brandColor"
            size="20"
          />
        </view>
        <text>去练习</text>
      </view>
    </view>

    <AppTabBar active="today" />
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { Date as DateIcon, Edit } from '@nutui/icons-vue-taro'
import AppTabBar from '@/components/AppTabBar.vue'
import { APP_SLOGAN } from '@/constants/brand'
import { useArticleStore } from '@/store/article'
import { useUserStore } from '@/store/user'
import { useBrandColor, useThemeClass } from '@/utils/brandColor'

const userStore = useUserStore()
const articleStore = useArticleStore()
const { brandColor } = useBrandColor()
const { themeClass } = useThemeClass()

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const dateLabel = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} 星期${WEEKDAYS[d.getDay()]}`
})

function goSignIn() {
  Taro.navigateTo({ url: '/pages/user/signin' })
}

function goQuiz() {
  Taro.navigateTo({ url: '/pages/question/article-pick' })
}

function goRmrb() {
  Taro.navigateTo({ url: '/pages/rmrb/index' })
}

function goTheory() {
  Taro.navigateTo({ url: '/pages/question/article-pick' })
}

async function refresh() {
  await Promise.all([
    articleStore.fetchDailyArticles(),
    articleStore.fetchRecommendedArticles(true),
  ])
}

onMounted(() => {
  userStore.bootstrap()
  void refresh()
})
useDidShow(() => {
  void refresh()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-today {
  @include page-padding;
  padding-top: 0;
  padding-left: 0;
  padding-right: 0;
  padding-bottom: 40px;
}

.today-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  padding: 28px 16px 22px;
  background: linear-gradient(168deg, $primary-color 0%, $primary-mid 48%, $primary-dark 100%);
  color: $on-primary;
  .today-greet {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
    .today-hi { font-size: 22px; font-weight: 700; color: $on-primary; }
    .today-slogan { font-size: 12px; color: $on-primary; opacity: 0.78; }
  }
  .today-date {
    flex-shrink: 0;
    font-size: 12px;
    color: $on-primary;
    background: rgba(255, 255, 255, 0.16);
    padding: 4px 10px;
    border-radius: 6px;
  }
}

.track-list,
.quick-row {
  margin-left: 16px;
  margin-right: 16px;
}

.track-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
}

.track-card {
  @include card;
  padding: 16px 16px 14px;
  .track-kicker {
    display: block;
    font-size: 12px;
    color: $primary-color;
    font-weight: 600;
    margin-bottom: 4px;
  }
  .track-title {
    display: block;
    font-size: 17px;
    font-weight: 700;
    color: $text-primary;
    margin-bottom: 4px;
  }
  .track-desc {
    display: block;
    font-size: 12px;
    color: $text-muted;
    line-height: 1.45;
  }
}

.quick-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  .q-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 10px 0;
    background: $card-bg;
    border-radius: $radius-md;
    box-shadow: $shadow-card;
    font-size: 12px;
    color: $text-secondary;
    .q-icon-wrap {
      @include icon-tile;
    }
  }
}
</style>
