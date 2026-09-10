<template>
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
        <PointsBadge
          v-if="loggedIn"
          :points="userStore.points"
          show-label
          tone="on-brand"
          @tap="goPoints"
        />
      </view>
    </view>

    <view class="quick-actions">
      <view class="action-item" @tap="goSignIn">
        <view class="action-icon-wrap">
          <Date :color="brandColor" size="20" />
        </view>
        <text>{{ userStore.hasSignedToday ? '已签到' : '今日签到' }}</text>
      </view>
      <view class="action-item" @tap="go('/pages/question/article-pick')">
        <view class="action-icon-wrap">
          <Edit :color="brandColor" size="20" />
        </view>
        <text>时政练习</text>
      </view>
      <view class="action-item" @tap="go('/pages/rmrb/article-list')">
        <view class="action-icon-wrap">
          <CheckChecked :color="brandColor" size="20" />
        </view>
        <text>时评精拆</text>
      </view>
    </view>

    <view v-if="SHOW_HOME_DOMAINS" class="home-block">
      <view class="home-block-title">
        <text>学习入口</text>
        <text class="home-block-meta">时政 / 申论</text>
      </view>
      <view class="domain-grid">
        <view
          v-for="item in examDomains"
          :key="item.name"
          class="domain-item"
          @tap="onExamDomain(item)"
        >
          <view class="domain-icon" :class="item.tone">
            <component :is="item.icon" :color="brandColor" size="22" />
          </view>
          <text class="domain-name">{{ item.name }}</text>
          <text class="domain-desc">{{ item.desc }}</text>
        </view>
      </view>
    </view>

    <view class="home-block">
      <view class="home-block-title">
        <text>{{ usingDailyPicks ? '今日文章' : '最近文章' }}</text>
      </view>
      <text v-if="usingFallbackFeed" class="home-block-note">今日精选暂未排期，先看最近发布</text>
      <nut-skeleton v-if="todayLoading && !todayArticles.length" rows="3" />
      <template v-else-if="todayArticles.length">
        <ArticleCard
          v-for="item in todayArticles"
          :key="`${item.kind}-${item.article.id}`"
          :article="item.article"
          :type-label="item.kind === 'rmrb' ? '时评' : '时政'"
          @tap="onTodayTap"
        />
      </template>
      <view v-else class="empty-rmrb">
        <text class="empty-title">暂无已发布文章</text>
        <text class="empty-desc">发布后会出现在这里；也可从上方进入时政练习或时评精拆</text>
      </view>
    </view>

    <AppTabBar active="home" />
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow, usePullDownRefresh } from '@tarojs/taro'
import { Skeleton as NutSkeleton } from '@nutui/nutui-taro'
import {
  CheckChecked,
  Date,
  Edit,
  Order,
} from '@nutui/icons-vue-taro'
import AppTabBar from '@/components/AppTabBar.vue'
import ArticleCard from '@/components/ArticleCard.vue'
import PointsBadge from '@/components/PointsBadge.vue'
import { api } from '@/api'
import logoSrc from '@/assets/logo/logo.png'
import { APP_NAME, APP_SLOGAN } from '@/constants/brand'
import { SHOW_CORPUS_MENU, SHOW_EVENTS, SHOW_HOME_DOMAINS } from '@/constants/featureVisibility'
import { useUserStore } from '@/store/user'
import { useArticleStore } from '@/store/article'
import type { Article, RmrbArticle } from '@/types'
import { rmrbToCard } from '@/utils/rmrbCard'
import { showToast } from '@/utils/platform'
import { isLoggedIn } from '@/utils/auth'
import { bootstrapApp } from '@/utils/bootstrap'
import { useBrandColor, useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '知行' })

const { themeClass } = useThemeClass()
const userStore = useUserStore()
const articleStore = useArticleStore()
const { brandColor } = useBrandColor()
const loggedIn = computed(() => isLoggedIn() && !!userStore.userInfo?.id)

const pageReady = ref(false)
const todayRmrbLoading = ref(false)
const todayRmrbList = ref<RmrbArticle[]>([])

type TodayKind = 'rmrb' | 'theory'
type TodayItem = { kind: TodayKind; article: Article }

const todayLoading = computed(() => todayRmrbLoading.value || articleStore.dailyLoading)
const todayArticles = computed(() => {
  const items: TodayItem[] = [
    ...todayRmrbList.value.map((row) => ({ kind: 'rmrb' as const, article: rmrbToCard(row) })),
    ...articleStore.dailyArticles.map((row) => ({ kind: 'theory' as const, article: row })),
  ]
  items.sort((a, b) => {
    const date = (b.article.publishDate || '').localeCompare(a.article.publishDate || '')
    if (date) return date
    return (b.article.createdAt || '').localeCompare(a.article.createdAt || '')
  })
  return items
})

const usingDailyPicks = computed(() => todayArticles.value.some((item) => item.article.isDaily))
const usingFallbackFeed = computed(
  () => todayArticles.value.length > 0 && !usingDailyPicks.value,
)

type DomainItem = {
  name: string
  desc: string
  url: string
  icon: typeof Order
  tone: string
  special?: 'featured'
}

const examDomains: DomainItem[] = [
      { name: '时政阅读', desc: '读完再练', url: '/pages/question/article-pick', icon: Order, tone: 'tone-red' },
  ...(SHOW_EVENTS
    ? [{ name: '时事印象', desc: '事件挂框架', url: '/pages/events/index', icon: Date, tone: 'tone-amber' } as DomainItem]
    : []),
  { name: '时评精拆', desc: '先读原文', url: '/pages/rmrb/article-list', icon: Edit, tone: 'tone-amber' },
  ...(SHOW_CORPUS_MENU
    ? [{ name: '语料本', desc: '专名成语金句', url: '/pages/corpus/index', icon: Edit, tone: 'tone-blue' } as DomainItem]
    : []),
]

async function fetchTodayRmrb() {
  todayRmrbLoading.value = true
  try {
    const res = await api.listRmrbToday()
    if (res.code === 0 && res.data) todayRmrbList.value = res.data
  } finally {
    todayRmrbLoading.value = false
  }
}

async function fetchPageData() {
  await Promise.all([
    articleStore.fetchDailyArticles(),
    fetchTodayRmrb(),
  ])
}

async function loadInitial() {
  await bootstrapApp(true)
  await fetchPageData()
}

async function refreshOnShow() {
  const authed = isLoggedIn()
  await Promise.all([
    articleStore.fetchDailyArticles(),
    fetchTodayRmrb(),
    authed ? articleStore.syncStudyData() : Promise.resolve(),
  ])
}

onMounted(async () => {
  await loadInitial()
  pageReady.value = true
})

useDidShow(async () => {
  if (!pageReady.value) return
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

function goArticle(id: string) {
  Taro.navigateTo({ url: `/pages/article/detail?id=${id}` })
}

function goSignIn() {
  Taro.navigateTo({ url: '/pages/user/signin' })
}

function goRmrbArticle(id: string) {
  Taro.navigateTo({ url: `/pages/rmrb/article-detail?id=${id}` })
}

function onTodayTap(id: string) {
  const hit = todayArticles.value.find((item) => item.article.id === id)
  if (hit?.kind === 'rmrb') goRmrbArticle(id)
  else goArticle(id)
}

function goPoints() {
  Taro.navigateTo({ url: '/pages/user/points' })
}

function onExamDomain(item: DomainItem) {
  if (item.special === 'featured') {
    const recentId = articleStore.lastStudyingArticleId
    const fallback = articleStore.featuredArticles[0] || articleStore.recommendedList[0]
    const targetId = recentId || fallback?.id
    if (targetId) goArticle(targetId)
    else showToast('暂无时政文章')
    return
  }
  go(item.url)
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-index {
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
    }
    .banner-tagline {
      font-size: 12px;
      opacity: 0.78;
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
  .quick-actions {
    display: flex;
    background: $card-bg;
    margin: -12px 16px 14px;
    border-radius: $radius-lg;
    padding: 14px 4px;
    /* 比全局 $shadow-float 更轻 */
    box-shadow: 0 1px 4px rgba(16, 24, 40, 0.04), 0 2px 8px rgba(16, 24, 40, 0.04);
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
        &.warn { color: $primary-color; font-weight: 600; }
        &.is-link { color: $primary-color; }
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
      .empty-title { display: block; font-size: 14px; color: $text-secondary; margin-bottom: 6px; }
      .empty-desc { display: block; font-size: 12px; color: $text-muted; line-height: 1.5; }
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
        &.tone-amber { background: rgba($accent-amber, 0.12); }
        &.tone-blue { background: rgba($accent-blue, 0.1); }
        &.tone-green { background: rgba($accent-green, 0.1); }
        &.tone-red { background: $primary-light; }
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
    .review-arrow { color: $text-muted; }
  }
  .home-block-rmrb {
    .empty-rmrb {
      @include card;
      padding: 20px 16px;
      text-align: center;
      .empty-title { display: block; font-size: 14px; color: $text-secondary; margin-bottom: 6px; }
      .empty-desc { display: block; font-size: 12px; color: $text-muted; line-height: 1.5; }
    }
  }
  .home-block-recommended {
    .list-status {
      text-align: center;
      padding: 12px 0 4px;
      font-size: 13px;
      color: $primary-color;
      &.muted { color: $text-muted; }
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
