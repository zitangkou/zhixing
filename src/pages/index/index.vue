<template>
  <page-meta
    v-if="isWeapp"
    :page-style="pageMeta.pageStyle"
    :background-color="pageMeta.backgroundColor"
    :background-color-top="pageMeta.backgroundColorTop"
    :background-color-bottom="pageMeta.backgroundColorBottom"
    :background-text-style="pageMeta.backgroundTextStyle"
  />
  <view class="page-index page-with-tabbar" :class="themeClass">
    <view class="banner">
      <view class="banner-top">
        <view class="banner-brand">
          <image class="banner-logo" :src="logoSrc" mode="aspectFit" />
          <view class="banner-titles">
            <text class="banner-name">{{ APP_NAME }}</text>
            <text class="banner-tagline">{{ APP_SLOGAN }}</text>
          </view>
        </view>
        <view class="banner-side">
          <text class="banner-sign" @tap="goSignIn">{{ userStore.hasSignedToday ? '已签到' : '签到' }}</text>
          <PointsBadge
            v-if="loggedIn"
            :points="userStore.points"
            show-label
            tone="on-brand"
            @tap="goPoints"
          />
        </view>
      </view>
    </view>

    <view class="quick-actions">
      <view class="action-item" @tap="go('/pages/question/article-pick')">
        <view class="action-icon-wrap">
          <Edit :color="brandColor" size="20" />
        </view>
        <text>时政要点</text>
      </view>
      <view class="action-item" @tap="go('/pages/quotes/index')">
        <view class="action-icon-wrap">
          <CheckChecked :color="brandColor" size="20" />
        </view>
        <text>金句素材</text>
      </view>
      <view v-if="SHOW_KNOWLEDGE" class="action-item" @tap="go('/pages/knowledge/index')">
        <view class="action-icon-wrap">
          <Category :color="brandColor" size="20" />
        </view>
        <text>知识框架</text>
      </view>
    </view>

    <view v-if="loggedIn && dueWrongCount > 0" class="today-wrong" @tap="go('/pages/question/wrong')">
      <text>今日错题</text>
      <text class="today-wrong-n">{{ dueWrongCount }}</text>
    </view>

    <view class="home-block">
      <view class="home-block-title">
        <text>时政要点</text>
        <text class="home-block-meta is-link" @tap="go('/pages/question/article-pick')">全部</text>
      </view>
      <nut-skeleton v-if="loading && !points.length" rows="3" />
      <template v-else-if="points.length">
        <TheoryPointRow v-for="item in points" :key="item.id" :item="item" @tap="goQuizById" />
      </template>
      <view v-else class="empty-rmrb">
        <text class="empty-title">暂无时政要点</text>
        <text class="empty-desc">后台发布后会出现在这里</text>
      </view>
    </view>

    <view class="home-block">
      <view class="home-block-title">
        <text>金句素材</text>
        <text class="home-block-meta is-link" @tap="go('/pages/quotes/index')">全部</text>
      </view>
      <nut-skeleton v-if="loading && !quotes.length" rows="2" />
      <template v-else-if="quotes.length">
        <QuoteRow v-for="item in quotes" :key="item.id" :item="item" @tap="goQuote" />
      </template>
      <view v-else class="empty-rmrb">
        <text class="empty-title">暂无已确认金句</text>
        <text class="empty-desc">后台确认后会出现在这里</text>
      </view>
    </view>

    <AppTabBar active="home" />
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow, usePullDownRefresh } from '@tarojs/taro'
import { Skeleton as NutSkeleton } from '@nutui/nutui-taro'
import { Category, CheckChecked, Edit } from '@nutui/icons-vue-taro'
import AppTabBar from '@/components/AppTabBar.vue'
import QuoteRow from '@/components/QuoteRow.vue'
import TheoryPointRow from '@/components/TheoryPointRow.vue'
import PointsBadge from '@/components/PointsBadge.vue'
import logoSrc from '@/assets/logo/logo.png'
import { api } from '@/api'
import { APP_NAME, APP_SLOGAN } from '@/constants/brand'
import { SHOW_KNOWLEDGE } from '@/constants/featureVisibility'
import { useUserStore } from '@/store/user'
import { useArticleStore } from '@/store/article'
import { useQuestionStore } from '@/store/question'
import { showConfirm, showToast } from '@/utils/platform'
import { bumpAuthView, isLoggedIn, requireLogin } from '@/utils/auth'
import type { DailyQuoteCard, TheoryPointCard } from '@/types'
import { bootstrapApp } from '@/utils/bootstrap'
import { useBrandColor, usePageMeta, useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '杜衡阁' })

const { themeClass } = useThemeClass()
const pageMeta = usePageMeta()
const isWeapp = process.env.TARO_ENV === 'weapp'
const userStore = useUserStore()
const articleStore = useArticleStore()
const questionStore = useQuestionStore()
const { brandColor } = useBrandColor()
const loggedIn = computed(() => isLoggedIn() && !!userStore.userInfo?.id)
const dueWrongCount = computed(() => (loggedIn.value ? questionStore.wrongCount : 0))

const pageReady = ref(false)
const loading = ref(false)
const points = ref<TheoryPointCard[]>([])
const quotes = ref<DailyQuoteCard[]>([])

async function fetchPageData() {
  loading.value = true
  try {
    const [pointRes, quoteRes] = await Promise.all([api.getTheoryPoints(), api.getQuotes()])
    if (pointRes.code === 0 && pointRes.data) points.value = pointRes.data.slice(0, 5)
    if (quoteRes.code === 0 && quoteRes.data) quotes.value = quoteRes.data.slice(0, 5)
  } finally {
    loading.value = false
  }
}

async function loadInitial() {
  await bootstrapApp(true)
  await fetchPageData()
}

async function refreshOnShow() {
  const authed = isLoggedIn()
  await Promise.all([
    fetchPageData(),
    authed ? articleStore.syncStudyData() : Promise.resolve(),
    authed ? questionStore.loadWrongQuestions('review') : Promise.resolve(),
  ])
}

onMounted(async () => {
  await loadInitial()
  pageReady.value = true
})

useDidShow(async () => {
  bumpAuthView()
  if (!pageReady.value) return
  if (isLoggedIn() && !userStore.userInfo?.id) {
    await userStore.bootstrap()
  }
  await refreshOnShow()
})

usePullDownRefresh(async () => {
  try {
    await refreshOnShow()
  } finally {
    Taro.stopPullDownRefresh()
  }
})

function go(url: string) {
  if (url.startsWith('/pages/index') || url.startsWith('/pages/user/index')) {
    Taro.switchTab({ url })
    return
  }
  Taro.navigateTo({ url })
}

function goSignIn() {
  Taro.navigateTo({ url: '/pages/user/signin' })
}

function goQuote(id: string) {
  Taro.navigateTo({ url: `/pages/quotes/detail?id=${id}` })
}

function goQuizById(id: string) {
  const item = points.value.find((row) => row.id === id)
    || points.value.flatMap((row) => row.sections || []).find((row) => row.id === id)
  if (item) void goQuiz(item)
}

function goPoints() {
  Taro.navigateTo({ url: '/pages/user/points' })
}

async function goQuiz(item: TheoryPointCard) {
  if (!item.questionCount) {
    showToast('这套要点还没有题目')
    return
  }
  const url = `/pages/question/taking?theoryPointId=${item.id}`
  if (!isLoggedIn()) {
    const ok = await showConfirm('需要登录', '登录后才能保存练习进度与积分。', { confirmText: '去登录', cancelText: '再看看' })
    if (!ok) return
    requireLogin(url)
    return
  }
  Taro.navigateTo({ url })
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-index {
  min-height: 100vh;
  background: $page-bg;
  padding-bottom: 20px;
  .banner {
    /* 略抬角度、加中间色阶，对比更柔和（结构不变） */
    background: linear-gradient(168deg, $primary-color 0%, $primary-mid 48%, $primary-dark 100%);
    padding: 24px 16px 22px;
    color: #fff;
    .banner-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .banner-brand {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
      flex: 1;
    }
    .banner-logo {
      width: 40px;
      height: 40px;
      flex-shrink: 0;
      border-radius: 10px;
    }
    .banner-titles {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }
    .banner-name {
      font-size: 21px;
      font-weight: 700;
      line-height: 1.2;
      color: #fff;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .banner-tagline {
      font-size: 12px;
      opacity: 0.78;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .banner-side {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 8px;
      flex-shrink: 0;
    }
    .banner-sign {
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      line-height: 1.4;
      color: #fff;
      background: rgba(255, 255, 255, 0.18);
    }
    .banner-today {
      margin-top: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 44px;
      padding: 12px;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.12);
      .today-label {
        font-size: 13px;
        font-weight: 700;
      }
      .today-desc {
        flex: 1;
        font-size: 12px;
        opacity: 0.88;
      }
      .today-arrow {
        opacity: 0.8;
      }
    }
  }
  .today-wrong {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 0 16px 14px;
    padding: 12px 14px;
    background: $card-bg;
    border: 1px solid $border-color;
    border-radius: $radius-lg;
    font-size: 14px;
    color: $text-primary;
  }
  .today-wrong-n {
    font-weight: 700;
    color: $primary-color;
  }
  .quick-actions {
    display: flex;
    background: $card-bg;
    margin: -12px 16px 14px;
    border-radius: $radius-lg;
    padding: 14px 4px;
    /* 比全局 $shadow-float 更轻 */
    box-shadow:
      0 1px 4px rgba(16, 24, 40, 0.04),
      0 2px 8px rgba(16, 24, 40, 0.04);
    border: 1px solid $border-color;
    position: relative;
    z-index: 1;
    .action-item {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: $text-secondary;
      .action-icon-wrap {
        @include icon-tile;
      }
      .action-sub {
        font-size: 10px;
        color: $text-muted;
        line-height: 1;
      }
    }
  }
  /* 不用通用 .section：部分子页会注入未 scoped 的 .section{card}，
     switchTab 回首页时样式仍留在文档里，刷新才消失 */
  .home-block {
    padding: 0 16px;
    margin-bottom: 18px;
    background: transparent;
    box-shadow: none;
    border: none;
    border-radius: 0;
    .home-block-title {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      padding-left: 0;
      border-left: none;
      font-size: 16px;
      font-weight: 600;
      color: $text-primary;
      .home-block-meta {
        margin-left: auto;
        font-size: 12px;
        font-weight: 400;
        color: $text-muted;
        &.warn {
          color: $primary-color;
          font-weight: 600;
        }
        &.is-link {
          color: $primary-color;
        }
      }
    }
    .home-block-note {
      display: block;
      font-size: 12px;
      color: $text-muted;
      margin: -6px 0 12px;
      line-height: 1.5;
    }
    .empty-rmrb {
      @include card;
      padding: 20px 16px;
      text-align: center;
      .empty-title {
        display: block;
        font-size: 14px;
        color: $text-secondary;
        margin-bottom: 6px;
      }
      .empty-desc {
        display: block;
        font-size: 12px;
        color: $text-muted;
        line-height: 1.5;
      }
    }
  }
  .review-hub-row {
    @include card;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px 4px;
    padding: 14px 12px 12px;
    position: relative;
    .review-hub-stat {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
      min-height: 44px;
      justify-content: center;
      .n {
        font-size: 17px;
        font-weight: 700;
        color: $text-primary;
      }
      .l {
        font-size: 12px;
        color: $text-muted;
      }
    }
    .review-hub-arrow {
      position: absolute;
      right: 10px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 18px;
      color: $text-muted;
      pointer-events: none;
    }
  }
  .domain-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    &.domain-grid-3 {
      grid-template-columns: 1fr 1fr 1fr;
      gap: 10px;
    }
    .domain-item {
      @include card;
      margin-bottom: 0;
      padding: 16px 14px;
      .domain-icon {
        @include icon-tile;
        margin-bottom: 8px;
        &.tone-amber {
          background: rgba($accent-amber, 0.12);
        }
        &.tone-blue {
          background: rgba($accent-blue, 0.1);
        }
        &.tone-green {
          background: rgba($accent-green, 0.1);
        }
        &.tone-red {
          background: $primary-light;
        }
      }
      .domain-name {
        display: block;
        font-size: 15px;
        font-weight: 700;
        color: $text-primary;
        margin-bottom: 3px;
      }
      .domain-desc {
        display: block;
        font-size: 12px;
        line-height: 1.35;
        color: $text-muted;
      }
    }
  }
  .review-item {
    @include card;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    border-radius: $radius-lg;
    .review-chip {
      @include soft-chip($accent-amber, 0.12);
      flex-shrink: 0;
    }
    .review-title {
      flex: 1;
      font-size: 14px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: $text-primary;
    }
    .review-arrow {
      color: $text-muted;
    }
  }
  .home-block-rmrb {
    .empty-rmrb {
      @include card;
      padding: 20px 16px;
      text-align: center;
      .empty-title {
        display: block;
        font-size: 14px;
        color: $text-secondary;
        margin-bottom: 6px;
      }
      .empty-desc {
        display: block;
        font-size: 12px;
        color: $text-muted;
        line-height: 1.5;
      }
    }
  }
  .home-block-recommended {
    .list-status {
      text-align: center;
      padding: 12px 0 4px;
      font-size: 13px;
      color: $primary-color;
      &.muted {
        color: $text-muted;
      }
    }
    .empty-recommended {
      @include card;
      padding: 24px 16px;
      text-align: center;
      .empty-title {
        display: block;
        font-size: 14px;
        color: $text-secondary;
        margin-bottom: 8px;
      }
      .empty-desc {
        display: block;
        font-size: 12px;
        color: $text-muted;
        line-height: 1.6;
      }
    }
  }
}
</style>
