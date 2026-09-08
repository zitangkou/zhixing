<template>
  <view class="page-result" :class="themeClass">
    <view v-if="loading" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在获取成绩单</text>
    </view>
    <view v-else-if="loadError" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ loadError }}</text>
      <view class="state-btn" @tap="load">点击重试</view>
    </view>
    <view v-else-if="!detail" class="state-box">
      <text class="state-title">记录不存在</text>
      <text class="state-desc">该作答记录可能已失效</text>
    </view>
    <view v-else>
      <view class="score-card">
        <text class="score-num">{{ detail.score }}</text>
        <text class="score-label">总分</text>
        <view class="score-meta">
          <text>正确 {{ detail.correctCount }} / {{ detail.totalCount }}</text>
          <text>答题 {{ detail.answeredCount }} 题</text>
          <text>用时 {{ formatDuration(detail.timeUsedSec) }}</text>
        </view>
      </view>

      <view class="section-stats">
        <text class="block-title">各模块正确率</text>
        <view v-for="s in detail.sectionStats" :key="s.section" class="section-stat">
          <view class="stat-head">
            <text class="stat-name">{{ s.section }}</text>
            <text class="stat-acc">{{ s.accuracy }}%</text>
          </view>
          <view class="stat-bar">
            <view class="stat-fill" :style="{ width: s.accuracy + '%' }" />
          </view>
          <text class="stat-meta">{{ s.correct }}/{{ s.total }} · 已答 {{ s.answered }}</text>
        </view>
      </view>

      <view class="answers">
        <text class="block-title">答题明细</text>
        <view class="filter-row">
          <text class="filter-chip" :class="{ active: filter === '' }" @tap="filter = ''">全部</text>
          <text class="filter-chip" :class="{ active: filter === 'wrong' }" @tap="filter = 'wrong'">仅错题</text>
          <text class="filter-chip" :class="{ active: filter === 'unanswered' }" @tap="filter = 'unanswered'">未答</text>
        </view>
        <view
          v-for="a in filteredAnswers"
          :key="a.questionId"
          class="answer-item"
          :class="{ correct: a.isCorrect, wrong: a.answered && !a.isCorrect, skipped: !a.answered }"
        >
          <view class="answer-head">
            <text class="answer-num">{{ a.section }} #{{ a.sortOrder }}</text>
            <text class="answer-status">
              {{ a.isCorrect ? '✓ 正确' : a.answered ? '✗ 错误' : '— 未答' }}
            </text>
          </view>
          <text class="answer-stem">{{ a.stem }}</text>
          <view v-if="a.userAnswer" class="answer-row">
            <text class="row-label">你答：</text>
            <text class="row-value bad">{{ formatAnswer(a.userAnswer) }}</text>
          </view>
          <view class="answer-row">
            <text class="row-label">正确：</text>
            <text class="row-value good">{{ formatAnswer(a.correctAnswer) }}</text>
          </view>
          <text v-if="a.analysis" class="answer-analysis">{{ a.analysis }}</text>
        </view>
      </view>

      <view class="footer-bar">
        <nut-button plain type="primary" @click="goBack">返回试卷</nut-button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import { api } from '@/api'
import type { ExamAttemptDetail } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '成绩单' })

const { themeClass } = useThemeClass()
const router = useRouter()
const attemptId = ref(router.params?.attemptId || '')
const loading = ref(true)
const loadError = ref('')
const detail = ref<ExamAttemptDetail | null>(null)
const filter = ref('')

const filteredAnswers = computed(() => {
  if (!detail.value) return []
  if (filter.value === 'wrong') return detail.value.answers.filter((a) => a.answered && !a.isCorrect)
  if (filter.value === 'unanswered') return detail.value.answers.filter((a) => !a.answered)
  return detail.value.answers
})

function formatDuration(sec: number) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}分${s}秒`
}

function formatAnswer(a: string | string[]) {
  if (Array.isArray(a)) return a.join('、')
  return a || '—'
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.getExamAttemptDetail(attemptId.value)
    if (res.code === 0 && res.data) {
      detail.value = res.data
    } else if (res.code === 404 || res.message?.includes('不存在')) {
      detail.value = null
    } else {
      loadError.value = res.message || '加载失败'
      detail.value = null
    }
  } catch {
    loadError.value = '网络异常，请稍后重试'
    detail.value = null
  } finally {
    loading.value = false
  }
}

function goBack() {
  Taro.navigateBack()
}

onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-result {
  @include page-padding;
  padding-bottom: 100px;
}

.state-box { @include page-state-box; }

.empty {
  @include page-state-box;
}

.score-card {
  background: linear-gradient(135deg, $primary-color, $primary-dark);
  color: #fff;
  border-radius: $radius-lg;
  padding: 24px 16px;
  text-align: center;
  margin-bottom: 14px;
  .score-num { display: block; font-size: 48px; font-weight: 700; line-height: 1; }
  .score-label { display: block; font-size: 13px; opacity: 0.85; margin-top: 6px; }
  .score-meta { display: flex; justify-content: space-around; margin-top: 14px; font-size: 12px; opacity: 0.9; }
}

.section-stats, .answers {
  @include card;
  padding: 14px 16px;
  border-radius: $radius-lg;
  margin-bottom: 12px;
  .block-title { display: block; font-size: 14px; font-weight: 600; margin-bottom: 10px; }
}

.section-stat {
  margin-bottom: 12px;
  &:last-child { margin-bottom: 0; }
  .stat-head { display: flex; justify-content: space-between; margin-bottom: 4px; .stat-name { font-size: 13px; color: $text-primary; } .stat-acc { font-size: 13px; font-weight: 600; color: $primary-color; } }
  .stat-bar { height: 4px; background: $page-bg; border-radius: 2px; overflow: hidden; margin-bottom: 4px; .stat-fill { height: 100%; background: linear-gradient(90deg, $primary-color, $primary-mid); border-radius: 2px; } }
  .stat-meta { font-size: 11px; color: $text-muted; }
}

.filter-row {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
  .filter-chip {
    @include filter-tab;
    font-size: 11px;
    background: $page-bg;
    color: $text-secondary;
    &.active { background: $primary-color; color: $on-primary; font-weight: 600; }
  }
}

.answer-item {
  padding: 12px 0;
  border-bottom: 1px solid $border-color;
  &:last-child { border-bottom: none; }
  &.correct .answer-status { color: $accent-green; }
  &.wrong .answer-status { color: $primary-color; }
  &.skipped .answer-status { color: $text-muted; }
  .answer-head { display: flex; justify-content: space-between; margin-bottom: 6px; .answer-num { font-size: 11px; color: $text-muted; } .answer-status { font-size: 12px; font-weight: 600; } }
  .answer-stem { display: block; font-size: 14px; line-height: 1.5; color: $text-primary; margin-bottom: 8px; }
  .answer-row { display: flex; gap: 4px; font-size: 12px; margin-bottom: 4px; .row-label { color: $text-muted; } .row-value.good { color: $accent-green; } .row-value.bad { color: $primary-color; } }
  .answer-analysis { display: block; margin-top: 6px; padding: 8px 10px; background: $page-bg; border-radius: 6px; font-size: 12px; color: $text-secondary; line-height: 1.6; }
}

.footer-bar {
  position: fixed;
  left: 16px;
  right: 16px;
  bottom: 16px;
  .nut-button { width: 100%; }
}
</style>
