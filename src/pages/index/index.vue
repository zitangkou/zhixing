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
          :points="userStore.points"
          show-label
          tone="on-brand"
          @tap="goPoints"
        />
      </view>
      <view class="banner-today" @tap="go('/pages/plan/today')">
        <text class="today-label">今日学习</text>
        <text class="today-desc">打开清单 · 按计划推进主线</text>
        <text class="today-arrow">›</text>
      </view>
    </view>

    <view class="quick-actions">
      <view class="action-item" @tap="goSignIn">
        <view class="action-icon-wrap">
          <Date :color="brandColor" size="20" />
        </view>
        <text>{{ userStore.hasSignedToday ? '已签到' : '签到' }}</text>
      </view>
      <view class="action-item" @tap="goQuiz">
        <view class="action-icon-wrap">
          <Edit :color="brandColor" size="20" />
        </view>
        <text>去练习</text>
      </view>
      <view class="action-item" @tap="go('/pages/plan/today')">
        <view class="action-icon-wrap">
          <CheckChecked :color="brandColor" size="20" />
        </view>
        <text>今日清单</text>
      </view>
      <view class="action-item" @tap="goRank">
        <view class="action-icon-wrap">
          <Fabulous :color="brandColor" size="20" />
        </view>
        <text>排行</text>
      </view>
    </view>

    <!-- 公考主线（home-* 类名避免被其它页未 scoped 的 .section 污染） -->
    <view class="home-block">
      <view class="home-block-title">
        <text>公考主线</text>
        <text class="home-block-meta">核心任务</text>
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

    <!-- 能力拓展 -->
    <view class="home-block">
      <view class="home-block-title">
        <text>能力拓展</text>
      </view>
      <view class="domain-grid domain-grid-3">
        <view
          v-for="item in extraDomains"
          :key="item.url"
          class="domain-item"
          @tap="go(item.url)"
        >
          <view class="domain-icon" :class="item.tone">
            <component :is="item.icon" :color="brandColor" size="20" />
          </view>
          <text class="domain-name">{{ item.name }}</text>
          <text class="domain-desc">{{ item.desc }}</text>
        </view>
      </view>
    </view>

    <view class="home-block home-block-review" @tap="go('/pages/review/hub')">
      <view class="home-block-title">
        <text>今日复习中心</text>
        <text v-if="reviewHubLoading && !reviewHub" class="home-block-meta">加载中</text>
        <text v-else-if="reviewHubTotal > 0" class="home-block-meta warn">{{ reviewHubTotal }} 项待办</text>
        <text v-else class="home-block-meta">今日已清</text>
      </view>
      <view class="review-hub-row">
        <view class="review-hub-stat">
          <text class="n">{{ reviewStat('knowledgeDueCount') }}</text>
          <text class="l">知识</text>
        </view>
        <view class="review-hub-stat">
          <text class="n">{{ reviewStat('articleReviewCount') }}</text>
          <text class="l">文章</text>
        </view>
        <view class="review-hub-stat">
          <text class="n">{{ reviewWrongStat }}</text>
          <text class="l">错题</text>
        </view>
        <view class="review-hub-stat">
          <text class="n">{{ reviewStat('corpusInboxCount') }}</text>
          <text class="l">语料</text>
        </view>
        <text class="review-hub-arrow">›</text>
      </view>
    </view>

    <view class="home-block home-block-must-read">
      <view class="home-block-title">
        <text>时政必读</text>
      </view>
      <nut-skeleton v-if="showMustReadSkeleton" rows="3" />
      <FeaturedCarousel
        v-else
        :articles="articleStore.featuredArticles"
        @tap="goArticle"
      />
    </view>

    <view class="home-block home-block-recommended">
      <view class="home-block-title">
        <text>推荐阅读</text>
        <text v-if="articleStore.recommendedTotal" class="home-block-meta">
          共 {{ articleStore.recommendedTotal }} 篇
        </text>
      </view>
      <nut-skeleton v-if="showRecommendedSkeleton" rows="4" />
      <template v-else-if="articleStore.recommendedList.length">
        <ArticleCard
          v-for="article in articleStore.recommendedList"
          :key="article.id"
          :article="article"
          @tap="goArticle"
        />
        <view v-if="articleStore.recommendedLoading" class="list-status">加载中...</view>
        <view v-else-if="articleStore.recommendedHasMore" class="list-status muted">
          上拉加载更多
        </view>
        <view v-else class="list-status muted">已加载全部</view>
      </template>
      <view v-else class="empty-recommended">
        <text class="empty-title">暂无推荐文章</text>
        <text class="empty-desc">下拉刷新试试，或稍后再来</text>
      </view>
    </view>

    <AppTabBar active="home" />
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow, usePullDownRefresh, useReachBottom } from '@tarojs/taro'
import { Skeleton as NutSkeleton } from '@nutui/nutui-taro'
import {
  Category,
  CheckChecked,
  Date,
  Edit,
  Fabulous,
  Order,
} from '@nutui/icons-vue-taro'
import AppTabBar from '@/components/AppTabBar.vue'
import ArticleCard from '@/components/ArticleCard.vue'
import FeaturedCarousel from '@/components/FeaturedCarousel.vue'
import PointsBadge from '@/components/PointsBadge.vue'
import logoSrc from '@/assets/logo/logo.png'
import { api } from '@/api'
import { APP_NAME, APP_SLOGAN } from '@/constants/brand'
import { useUserStore } from '@/store/user'
import { useArticleStore } from '@/store/article'
import { useQuestionStore } from '@/store/question'
import { showToast, tryNotify } from '@/utils/platform'
import { bootstrapApp } from '@/utils/bootstrap'
import { useBrandColor, useThemeClass } from '@/utils/brandColor'
import type { ReviewHub } from '@/types'

definePageConfig({ navigationBarTitleText: '知行' })

const { themeClass } = useThemeClass()
const userStore = useUserStore()
const articleStore = useArticleStore()
const questionStore = useQuestionStore()
const { brandColor } = useBrandColor()

const pageReady = ref(false)
const reviewHub = ref<ReviewHub | null>(null)
const reviewHubLoading = ref(false)
const reviewHubTotal = computed(() => reviewHub.value?.totalCount ?? 0)

function reviewStat(key: keyof ReviewHub) {
  if (!reviewHub.value) return '—'
  const v = reviewHub.value[key]
  return typeof v === 'number' ? v : 0
}

const reviewWrongStat = computed(() => {
  if (!reviewHub.value) return '—'
  return reviewHub.value.wrongRecommendCount ?? reviewHub.value.wrongReviewCount ?? 0
})

const showMustReadSkeleton = computed(
  () => articleStore.dailyLoading && articleStore.featuredArticles.length === 0,
)

const showRecommendedSkeleton = computed(
  () => articleStore.recommendedLoading && articleStore.recommendedList.length === 0,
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
  { name: '时政阅读', desc: '继续上次', url: '', icon: Order, tone: 'tone-red', special: 'featured' },
  { name: '时事印象', desc: '事件挂框架', url: '/pages/events/index', icon: Date, tone: 'tone-amber' },
  { name: '人民日报', desc: '开采与训练', url: '/pages/rmrb/index', icon: Edit, tone: 'tone-amber' },
  { name: '语料本', desc: '专名成语金句', url: '/pages/corpus/index', icon: Edit, tone: 'tone-blue' },
]

const extraDomains: DomainItem[] = [
  { name: '知识框架', desc: '考点导图', url: '/pages/knowledge/index', icon: Order, tone: 'tone-blue' },
  { name: '资料分析', desc: '公式刷题', url: '/pages/ziliao/index', icon: Category, tone: 'tone-green' },
  { name: '错题本', desc: '行测错题', url: '/pages/question/wrong', icon: Edit, tone: 'tone-red' },
  { name: '本周计划', desc: '节奏安排', url: '/pages/plan/week', icon: Date, tone: 'tone-amber' },
]

async function fetchReviewHub() {
  reviewHubLoading.value = true
  try {
    const res = await api.getReviewHub()
    if (res.code === 0 && res.data) {
      reviewHub.value = {
        ...res.data,
        wrongWaitingCount: res.data.wrongWaitingCount ?? 0,
        wrongRecommendCount: res.data.wrongRecommendCount ?? res.data.wrongReviewCount ?? 0,
      }
    }
  } finally {
    reviewHubLoading.value = false
  }
}

function notifyReviews() {
  const total = reviewHubTotal.value
  if (total > 0) {
    tryNotify(APP_NAME, `您有 ${total} 项复习/内化待完成`)
  }
}

async function fetchPageData() {
  await Promise.all([
    articleStore.fetchDailyArticles(),
    articleStore.fetchRecommendedArticles(true),
    questionStore.fetchReviewTasks(),
    questionStore.loadWrongQuestions(),
    fetchReviewHub(),
  ])
}

async function loadInitial() {
  await bootstrapApp(true)
  await fetchPageData()
  notifyReviews()
}

async function refreshOnShow() {
  await Promise.all([
    articleStore.fetchDailyArticles(),
    articleStore.fetchRecommendedArticles(true),
    articleStore.syncStudyData(),
    questionStore.fetchReviewTasks(),
    questionStore.loadWrongQuestions(),
    fetchReviewHub(),
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

useReachBottom(() => {
  articleStore.fetchRecommendedArticles(false)
})

function go(url: string) {
  if (url.startsWith('/pages/index') || url.startsWith('/pages/question/index') || url.startsWith('/pages/user/index')) {
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

function goQuiz() {
  Taro.switchTab({ url: '/pages/question/index' })
}

function goRank() {
  Taro.navigateTo({ url: '/pages/user/rank' })
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
    else showToast('暂无时政文章，可先看下方推荐')
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
