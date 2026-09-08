<template>
  <view class="page-review-hub" :class="themeClass">
    <view v-if="loading && !hub" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在同步今日任务</text>
    </view>

    <view v-else-if="error && !hub" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ error }}</text>
      <view class="state-btn" @tap="load">点击重试</view>
    </view>

    <template v-else-if="hub">
      <view class="summary">
        <text class="summary-num" :class="{ warn: todayRecommended > 0, clear: todayRecommended === 0 }">{{ todayRecommended }}</text>
        <view class="summary-body">
          <text class="summary-title">{{ todayRecommended > 0 ? '项今日推荐' : '今日已清' }}</text>
          <text class="summary-desc">
            {{ todayRecommended > 0 ? `预算 ${todayBudget} 项，先完成推荐队列` : '没有到期任务，去学习或休息都行' }}
          </text>
          <text v-if="backlogCount > 0" class="summary-extra">
            积压 {{ backlogCount }} 项，预计 {{ estimatedClearDays }} 天清完
          </text>
        </view>
      </view>

      <view v-if="reviewPlan.length" class="budget-card">
        <view class="budget-head">
          <text class="budget-title">今日节奏</text>
          <text class="budget-meta">{{ todayRecommended }} / {{ todayBudget }}</text>
        </view>
        <view v-for="item in reviewPlan" :key="item.key" class="budget-row">
          <view class="budget-row-main">
            <text class="budget-label">{{ item.label }}</text>
            <text class="budget-desc">{{ planDesc(item) }}</text>
          </view>
          <view class="budget-bar">
            <view class="budget-fill" :style="{ width: `${barPercent(item)}%` }" />
          </view>
        </view>
      </view>

      <view class="stats-grid">
        <view class="stat" @tap="goQuiz">
          <text class="num" :class="{ warn: hub.knowledgeDueCount > 0 }">{{ hub.knowledgeDueCount }}</text>
          <text class="label">知识</text>
        </view>
        <view class="stat" @tap="goArticleReview">
          <text class="num" :class="{ warn: hub.articleReviewCount > 0 }">{{ hub.articleReviewCount }}</text>
          <text class="label">文章</text>
        </view>
        <view class="stat" @tap="goWrongSession">
          <text class="num" :class="{ warn: hub.wrongReviewCount > 0 }">{{ hub.wrongRecommendCount || hub.wrongReviewCount }}</text>
          <text class="label">错题</text>
        </view>
        <view class="stat" @tap="goCorpus">
          <text class="num" :class="{ warn: hub.corpusInboxCount > 0 }">{{ hub.corpusInboxCount }}</text>
          <text class="label">语料</text>
        </view>
      </view>

      <!-- 今日错题：文案写清优先队列 -->
      <view class="wrong-smart" @tap="goWrongSession">
        <view class="wrong-smart-main">
          <text class="wrong-smart-title">今日错题</text>
          <text v-if="hub.wrongRecommendCount > 0" class="wrong-smart-desc">
            推荐复习 {{ hub.wrongRecommendCount }} 道
            <text v-if="hub.wrongReviewCount > hub.wrongRecommendCount">
              （到期共 {{ hub.wrongReviewCount }}，先刷优先题）
            </text>
          </text>
          <text v-else class="wrong-smart-desc">今日无到期错题</text>
          <text v-if="wrongCtaHint" class="wrong-smart-skip">{{ wrongCtaHint }}</text>
          <text v-if="hub.wrongWaitingCount > 0" class="wrong-smart-skip">
            另有 {{ hub.wrongWaitingCount }} 道未到期，今天不用复习
          </text>
        </view>
        <text v-if="hub.wrongRecommendCount > 0" class="wrong-smart-cta">开始 ›</text>
        <text v-else class="entry-arrow">›</text>
      </view>

      <view class="entries">
        <view class="entry primary" @tap="goQuiz">
          <view class="entry-main">
            <text class="entry-name">知识抽查</text>
            <text class="entry-desc">随机 5 题 · 先回忆再揭晓</text>
          </view>
          <text class="entry-cta">开始 ›</text>
        </view>

        <view class="section-label">复习</view>
        <view class="entry" @tap="goArticleReview">
          <view class="entry-main">
            <text class="entry-name">文章复习</text>
            <text class="entry-desc">
              {{ hub.articleReviewCount ? `${hub.articleReviewCount} 篇待复习` : '暂无到期文章' }}
            </text>
          </view>
          <text class="entry-arrow">›</text>
        </view>

        <view class="section-label">内化</view>
        <view class="entry" @tap="goArticleWrongSession">
          <view class="entry-main">
            <text class="entry-name">文章错题 · 逐题刷</text>
            <text class="entry-desc">
              {{ hub.articleWrongCount ? `${Math.min(hub.articleWrongCount, 15)} 道今日推荐` : '今日无到期文章错题' }}
            </text>
          </view>
          <text class="entry-arrow">›</text>
        </view>
        <view class="entry" @tap="goManualWrongSession">
          <view class="entry-main">
            <text class="entry-name">行测错题 · 逐题刷</text>
            <text class="entry-desc">
              {{ hub.manualWrongCount ? `${Math.min(hub.manualWrongCount, 15)} 道今日推荐` : '今日无到期行测错题' }}
            </text>
          </view>
          <text class="entry-arrow">›</text>
        </view>
        <view class="entry" @tap="goCorpus">
          <view class="entry-main">
            <text class="entry-name">语料内化</text>
            <text class="entry-desc">
              {{ hub.corpusInboxCount ? `${hub.corpusInboxCount} 条待澄清/改写` : '暂无待内化语料' }}
            </text>
          </view>
          <text class="entry-arrow">›</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { api } from '@/api'
import type { ReviewHub } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '复习中心' })

const { themeClass } = useThemeClass()
const hub = ref<ReviewHub | null>(null)
const loading = ref(false)
const error = ref('')

const hubTotal = computed(() => {
  const h = hub.value
  if (!h) return 0
  return (
    (h.knowledgeDueCount || 0) +
    (h.articleReviewCount || 0) +
    (h.wrongRecommendCount || h.wrongReviewCount || 0) +
    (h.corpusInboxCount || 0)
  )
})
const todayBudget = computed(() => hub.value?.todayBudget || 30)
const todayRecommended = computed(() => hub.value?.todayRecommended ?? hubTotal.value)
const backlogCount = computed(() => hub.value?.backlogCount || 0)
const estimatedClearDays = computed(() => hub.value?.estimatedClearDays || 0)
const reviewPlan = computed(() => (hub.value?.reviewPlan || []).filter((x) => x.due > 0 || x.recommended > 0))

const wrongCtaHint = computed(() => {
  const h = hub.value
  if (!h || h.wrongRecommendCount <= 0) return ''
  if (h.articleWrongCount > 0) return '将优先进入：文章错题'
  if (h.manualWrongCount > 0) return '将优先进入：行测错题'
  return ''
})

function go(url: string) {
  Taro.navigateTo({ url })
}

function goQuiz() {
  go('/pages/review/quiz')
}

function goArticleReview() {
  go('/pages/question/review')
}

function goArticleWrongSession() {
  go('/pages/question/taking?wrongSession=1')
}

function goManualWrongSession() {
  go('/pages/question/manual-quiz')
}

/** 优先文章错题，否则行测（文案已提示） */
function goWrongSession() {
  const h = hub.value
  if (!h) {
    goArticleWrongSession()
    return
  }
  if (h.articleWrongCount > 0) {
    goArticleWrongSession()
  } else if (h.manualWrongCount > 0) {
    goManualWrongSession()
  } else {
    goArticleWrongSession()
  }
}

function goCorpus() {
  go('/pages/corpus/index?tab=inbox')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.getReviewHub()
    if (res.code === 0 && res.data) {
      hub.value = {
        ...res.data,
        wrongWaitingCount: res.data.wrongWaitingCount ?? 0,
        wrongRecommendCount: res.data.wrongRecommendCount ?? res.data.wrongReviewCount ?? 0,
        todayBudget: res.data.todayBudget ?? 30,
        todayRecommended: res.data.todayRecommended ?? res.data.totalCount ?? 0,
        backlogCount: res.data.backlogCount ?? 0,
        estimatedClearDays: res.data.estimatedClearDays ?? 0,
        reviewPlan: res.data.reviewPlan ?? [],
      }
    } else {
      error.value = res.message || '获取复习任务失败'
    }
  } catch {
    error.value = '网络异常，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(load)
useDidShow(load)

function barPercent(item: { due: number; recommended: number }) {
  if (!item.due) return 0
  return Math.max(4, Math.min(100, Math.round((item.recommended / item.due) * 100)))
}

function planDesc(item: { due: number; recommended: number; backlog: number }) {
  const base = `推荐 ${item.recommended} / 到期 ${item.due}`
  return item.backlog > 0 ? `${base} · 延后 ${item.backlog}` : base
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-review-hub {
  padding: 16px 16px 48px;
  min-height: 100vh;
  box-sizing: border-box;
}

.summary {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
  padding: 4px 2px 2px;
  .summary-num {
    flex-shrink: 0;
    min-width: 48px;
    font-size: 36px;
    font-weight: 700;
    line-height: 1;
    color: $text-primary;
    letter-spacing: -0.02em;
    &.warn { color: $primary-color; }
    &.clear { color: $accent-green; }
  }
  .summary-body {
    flex: 1;
    min-width: 0;
  }
  .summary-title {
    display: block;
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
  }
  .summary-desc {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: $text-muted;
    line-height: 1.4;
  }
}

.state-box {
  @include card;
  text-align: center;
  padding: 32px 16px;
  .state-title {
    display: block;
    font-size: 15px;
    font-weight: 600;
    color: $text-secondary;
    margin-bottom: 6px;
  }
  .state-desc {
    display: block;
    font-size: 13px;
    color: $text-muted;
    margin-bottom: 16px;
  }
  .state-btn {
    @include hit-target;
    display: inline-flex;
    padding: 0 20px;
    border-radius: 10px;
    background: $primary-light;
    color: $primary-color;
    font-size: 14px;
    font-weight: 600;
  }
}

.stats-grid {
  @include card;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px 0;
  padding: 8px 4px;
  margin-bottom: 12px;
  .stat {
    @include hit-target(56px);
    flex-direction: column;
    gap: 4px;
    min-width: 0;
    padding: 8px 4px;
    .num {
      font-size: 18px;
      font-weight: 700;
      color: $text-primary;
      &.warn { color: $primary-color; }
    }
    .label {
      font-size: 12px;
      color: $text-muted;
    }
  }
}

.wrong-smart {
  @include card;
  padding: 16px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(135deg, $primary-light, $primary-faint);
  border: 1px solid $primary-soft;
  .wrong-smart-main {
    flex: 1;
    min-width: 0;
  }
  .wrong-smart-title {
    display: block;
    font-size: 16px;
    font-weight: 700;
    color: $text-primary;
  }
  .wrong-smart-desc {
    display: block;
    margin-top: 6px;
    font-size: 13px;
    color: $text-secondary;
    line-height: 1.5;
  }
  .wrong-smart-skip {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: $text-muted;
  }
  .wrong-smart-cta {
    font-size: 14px;
    font-weight: 600;
    color: $primary-color;
    @include hit-target;
  }
  .entry-arrow {
    font-size: 18px;
    color: $text-muted;
  }
}

.section-label {
  display: block;
  margin: 8px 2px 4px;
  font-size: 12px;
  font-weight: 600;
  color: $text-muted;
  letter-spacing: 0.04em;
}

.entries {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.entry {
  @include card;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  &.primary {
    background: linear-gradient(135deg, $primary-light, $primary-faint);
    border: 1px solid $primary-soft;
  }
  .entry-main {
    flex: 1;
    min-width: 0;
  }
  .entry-name {
    display: block;
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
  }
  .entry-desc {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: $text-muted;
  }
  .entry-cta {
    font-size: 14px;
    font-weight: 600;
    color: $primary-color;
  }
  .entry-arrow {
    font-size: 18px;
    color: $text-muted;
  }
}
</style>
