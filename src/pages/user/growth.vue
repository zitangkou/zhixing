<template>
  <view class="page-growth" :class="themeClass">
    <view v-if="loading && !data" class="empty-tip">加载中…</view>
    <view v-else-if="!data" class="empty-tip">暂无数据</view>
    <template v-else>
      <!-- 数字卡 -->
      <view class="stat-grid">
        <view class="stat-card">
          <text class="stat-num">{{ data.signStreak }}</text>
          <text class="stat-label">连续签到</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ data.weekMinutes }}</text>
          <text class="stat-label">本周分钟</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ quizRate }}%</text>
          <text class="stat-label">本周正确率</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ data.points }}</text>
          <text class="stat-label">积分</text>
        </view>
      </view>

      <view class="sub-row">
        <text>累计签到 {{ data.signDays }} 天</text>
        <text>文章 {{ data.articleReadCount }} · 套卷 {{ data.examFinishedCount }}</text>
        <text>本周刷题 {{ data.weekQuizCorrect }}/{{ data.weekQuizTotal }}</text>
      </view>

      <!-- 领域进度条 -->
      <view class="section">
        <text class="section-title">本周进度</text>
        <view v-for="d in data.domains" :key="d.key" class="domain-row">
          <view class="domain-head">
            <text class="domain-name">{{ d.name }}</text>
            <text class="domain-pct">{{ d.percent }}%</text>
          </view>
          <view class="bar-track">
            <view class="bar-fill" :style="{ width: d.percent + '%' }" />
          </view>
          <text class="domain-detail">{{ d.detail }}</text>
        </view>
      </view>

      <!-- 本周柱状 -->
      <view class="section">
        <text class="section-title">本周投入（分钟）</text>
        <view class="week-chart">
          <view
            v-for="bar in data.weekBars"
            :key="bar.date"
            class="week-col"
            :class="{ today: bar.isToday }"
          >
            <text class="week-val">{{ bar.minutes || '' }}</text>
            <view class="week-bar-wrap">
              <view
                class="week-bar"
                :style="{ height: barHeight(bar.minutes) + '%' }"
              />
            </view>
            <text class="week-label">{{ bar.label }}</text>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useDidShow } from '@tarojs/taro'
import { api } from '@/api'
import type { GrowthOverview } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '知行足迹' })

const { themeClass } = useThemeClass()
const data = ref<GrowthOverview | null>(null)
const loading = ref(false)

const quizRate = computed(() => {
  if (!data.value || data.value.weekQuizTotal <= 0) return 0
  return Math.round((data.value.weekQuizCorrect / data.value.weekQuizTotal) * 100)
})

const maxMinutes = computed(() => {
  if (!data.value?.weekBars?.length) return 1
  return Math.max(1, ...data.value.weekBars.map((b) => b.minutes))
})

function barHeight(minutes: number) {
  if (minutes <= 0) return 0
  return Math.max(8, Math.round((minutes / maxMinutes.value) * 100))
}

async function load() {
  loading.value = true
  try {
    const res = await api.getGrowthOverview()
    if (res.code === 0 && res.data) data.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(load)
useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-growth {
  @include page-padding;
  padding-bottom: 32px;
}

.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 10px;
}

.stat-card {
  @include card;
  padding: 16px 12px;
  margin-bottom: 0;
  text-align: center;
  .stat-num {
    display: block;
    font-size: 24px;
    font-weight: 700;
    color: $primary-color;
    line-height: 1.2;
  }
  .stat-label {
    display: block;
    margin-top: 6px;
    font-size: 12px;
    color: $text-muted;
  }
}

.sub-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: $text-muted;
  margin-bottom: 16px;
  padding: 0 2px;
}

.section {
  @include card;
  padding: 16px;
  margin-bottom: 12px;
}

.section-title {
  display: block;
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 14px;
}

.domain-row {
  & + & { margin-top: 14px; }
}

.domain-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 6px;
}

.domain-name {
  font-size: 13px;
  font-weight: 600;
}

.domain-pct {
  font-size: 12px;
  color: $primary-color;
  font-weight: 600;
}

.bar-track {
  height: 8px;
  border-radius: 4px;
  background: $primary-light;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  background: $primary-color;
  transition: width 0.3s ease;
}

.domain-detail {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: $text-muted;
}

.week-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  height: 140px;
  gap: 4px;
  padding-top: 8px;
}

.week-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  &.today .week-label {
    color: $primary-color;
    font-weight: 700;
  }
  &.today .week-bar {
    background: $primary-color;
  }
}

.week-val {
  font-size: 10px;
  color: $text-muted;
  height: 14px;
  line-height: 14px;
  margin-bottom: 4px;
}

.week-bar-wrap {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  min-height: 0;
}

.week-bar {
  width: 55%;
  max-width: 28px;
  min-height: 0;
  border-radius: 4px 4px 2px 2px;
  background: $primary-bar;
  transition: height 0.3s ease;
}

.week-label {
  margin-top: 6px;
  font-size: 11px;
  color: $text-secondary;
}

.empty-tip {
  text-align: center;
  color: $text-muted;
  padding: 48px 16px;
  font-size: 14px;
}
</style>
