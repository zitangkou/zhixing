<template>
  <view class="page-exam-detail" :class="themeClass">
    <view v-if="loading" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在获取试卷详情</text>
    </view>
    <view v-else-if="loadError" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ loadError }}</text>
      <view class="state-btn" @tap="load">点击重试</view>
    </view>
    <view v-else-if="!paper" class="state-box">
      <text class="state-title">试卷不存在</text>
      <text class="state-desc">该试卷可能已下架或链接无效</text>
    </view>
    <view v-else>
      <view class="paper-header">
        <text class="title">{{ paper.title }}</text>
        <view class="meta-row">
          <text v-if="paper.year" class="chip chip-soft">{{ paper.year }}</text>
          <text v-if="paper.region" class="chip chip-soft">{{ paper.region }}</text>
          <text class="chip" :class="examTypeClass(paper.examType)">{{ examTypeLabel(paper.examType) }}</text>
        </view>
        <view class="stats-row">
          <view class="stat-item">
            <text class="stat-num">{{ paper.totalCount }}</text>
            <text class="stat-label">题目</text>
          </view>
          <view class="stat-item">
            <text class="stat-num">{{ paper.timeLimitMin }}</text>
            <text class="stat-label">分钟</text>
          </view>
          <view class="stat-item">
            <text class="stat-num">{{ sectionCount }}</text>
            <text class="stat-label">模块</text>
          </view>
        </view>
        <text v-if="paper.description" class="desc">{{ paper.description }}</text>
      </view>

      <view class="sections">
        <text class="block-title">试卷结构</text>
        <view v-for="s in paper.sections" :key="s.section" class="section-row">
          <text class="section-name">{{ s.section }}</text>
          <text class="section-count">{{ s.questions.length }} 题</text>
        </view>
      </view>

      <view v-if="attempts.length" class="history">
        <text class="block-title">我的作答</text>
        <view v-for="a in attempts" :key="a.id" class="attempt-row" @tap="goResult(a.id)">
          <view class="attempt-main">
            <text class="attempt-score">{{ a.score }} 分</text>
            <text class="attempt-time">{{ formatTime(a.finishedAt) }}</text>
          </view>
          <text class="attempt-acc">{{ a.correctCount }}/{{ a.totalCount }} 正确</text>
          <text class="arrow">›</text>
        </view>
      </view>

      <view class="footer-bar">
        <nut-button type="primary" block class="primary-btn" @click="onStart">
          {{ hasUnfinished ? '继续作答' : '开始作答' }}
        </nut-button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import { api } from '@/api'
import type { ExamPaperDetail, ExamAttempt } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '试卷详情' })

const { themeClass } = useThemeClass()
const router = useRouter()
const paperId = ref(router.params?.id || '')
const loading = ref(true)
const loadError = ref('')
const paper = ref<ExamPaperDetail | null>(null)
const attempts = ref<ExamAttempt[]>([])

const sectionCount = computed(() => paper.value?.sections.length || 0)
const hasUnfinished = computed(() => attempts.value.some((a) => !a.isFinished))

function examTypeLabel(t: string) {
  return { real: '真题', custom: '自定义', mock: '模拟' }[t] || t
}
function examTypeClass(t: string) {
  return { real: 'chip-red', custom: 'chip-blue', mock: 'chip-green' }[t] || 'chip-soft'
}

function formatTime(iso: string | null) {
  if (!iso) return '未交卷'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [r1, r2] = await Promise.all([
      api.getExamPaperDetail(paperId.value),
      api.listExamAttempts(paperId.value),
    ])
    if (r1.code === 0 && r1.data) {
      paper.value = r1.data
    } else if (r1.code === 404 || r1.message?.includes('不存在')) {
      paper.value = null
    } else {
      loadError.value = r1.message || '加载试卷失败'
      paper.value = null
    }
    if (r2.code === 0 && r2.data) attempts.value = r2.data
  } catch {
    loadError.value = '网络异常，请稍后重试'
    paper.value = null
  } finally {
    loading.value = false
  }
}

async function onStart() {
  Taro.navigateTo({ url: `/pages/exam/taking?paperId=${paperId.value}` })
}

function goResult(attemptId: string) {
  Taro.navigateTo({ url: `/pages/exam/result?attemptId=${attemptId}` })
}

onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-exam-detail {
  @include page-padding;
  padding-bottom: 100px;
}

.state-box { @include page-state-box; }

.empty {
  @include page-state-box;
}

.paper-header {
  @include card;
  padding: 18px 16px;
  border-radius: $radius-lg;
  margin-bottom: 12px;
  .title { display: block; font-size: 18px; font-weight: 700; line-height: 1.4; margin-bottom: 10px; }
  .meta-row { display: flex; gap: 6px; margin-bottom: 14px; flex-wrap: wrap; .chip { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; &.chip-red { color: $primary-color; background: $primary-light; } &.chip-blue { color: $accent-blue; background: rgba($accent-blue, 0.1); } &.chip-green { color: $accent-green; background: rgba($accent-green, 0.1); } &.chip-soft { color: $text-secondary; background: $chip-bg; } } }
  .stats-row { display: flex; margin-bottom: 12px; .stat-item { flex: 1; text-align: center; .stat-num { display: block; font-size: 22px; font-weight: 700; color: $primary-color; } .stat-label { display: block; font-size: 11px; color: $text-muted; margin-top: 2px; } } }
  .desc { display: block; font-size: 13px; color: $text-secondary; line-height: 1.6; }
}

.sections, .history {
  @include card;
  padding: 14px 16px;
  border-radius: $radius-lg;
  margin-bottom: 12px;
  .block-title { display: block; font-size: 14px; font-weight: 600; margin-bottom: 10px; }
}

.section-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 13px;
  border-bottom: 1px solid $border-color;
  &:last-child { border-bottom: none; }
  .section-name { color: $text-primary; }
  .section-count { color: $text-muted; }
}

.attempt-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid $border-color;
  &:last-child { border-bottom: none; }
  &:active { opacity: 0.7; }
  .attempt-main { flex: 1; .attempt-score { display: block; font-size: 14px; font-weight: 600; color: $primary-color; } .attempt-time { display: block; font-size: 11px; color: $text-muted; } }
  .attempt-acc { font-size: 12px; color: $text-secondary; }
  .arrow { color: $text-muted; }
}

.footer-bar {
  position: fixed;
  left: 16px;
  right: 16px;
  bottom: 16px;
}
</style>
