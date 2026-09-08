<template>
  <view class="page-exam-list" :class="themeClass">
    <view class="filter-bar">
      <text
        v-for="t in tabs"
        :key="t.value"
        class="tab"
        :class="{ active: activeTab === t.value }"
        @tap="activeTab = t.value; load()"
      >{{ t.label }}</text>
    </view>

    <view v-if="loading" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在获取试卷列表</text>
    </view>
    <view v-else-if="loadError" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ loadError }}</text>
      <view class="state-btn" @tap="load">点击重试</view>
    </view>
    <view v-else-if="!papers.length" class="state-box">
      <text class="state-title">暂无试卷</text>
      <text class="state-desc">真题套卷上线后会出现在这里</text>
    </view>

    <view v-else class="paper-list">
      <view v-for="p in papers" :key="p.id" class="paper-card" @tap="goDetail(p.id)">
        <view class="paper-meta">
          <text class="chip" :class="examTypeClass(p.examType)">{{ examTypeLabel(p.examType) }}</text>
          <text v-if="p.year" class="chip chip-soft">{{ p.year }}</text>
          <text v-if="p.region" class="chip chip-soft">{{ p.region }}</text>
          <text class="paper-count">{{ p.totalCount }} 题</text>
        </view>
        <text class="paper-title">{{ p.title }}</text>
        <text v-if="p.description" class="paper-desc">{{ p.description }}</text>
        <view class="paper-footer">
          <text class="paper-time">{{ p.timeLimitMin }} 分钟</text>
          <text class="paper-cta">开始 ›</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { api } from '@/api'
import type { ExamPaper } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '真题套卷' })

const { themeClass } = useThemeClass()
const loading = ref(false)
const loadError = ref('')
const papers = ref<ExamPaper[]>([])
const activeTab = ref('')

const tabs = [
  { value: '', label: '全部' },
  { value: 'real', label: '真题' },
  { value: 'custom', label: '自定义' },
  { value: 'mock', label: '模拟' },
]

function examTypeLabel(t: string) {
  return { real: '真题', custom: '自定义', mock: '模拟' }[t] || t
}

function examTypeClass(t: string) {
  return { real: 'chip-red', custom: 'chip-blue', mock: 'chip-green' }[t] || 'chip-soft'
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.listExamPapers(activeTab.value ? { examType: activeTab.value } : undefined)
    if (res.code === 0 && res.data) {
      papers.value = res.data
    } else {
      loadError.value = res.message || '加载试卷失败'
    }
  } catch {
    loadError.value = '网络异常，请稍后重试'
  } finally {
    loading.value = false
  }
}

function goDetail(id: string) {
  Taro.navigateTo({ url: `/pages/exam/detail?id=${id}` })
}

onMounted(load)
useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-exam-list {
  @include page-padding;
  padding-bottom: 40px;
}

.filter-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
  .tab {
    @include filter-tab;
    font-size: 12px;
    background: $card-bg;
    color: $text-secondary;
    &.active {
      background: $primary-color;
      color: $on-primary;
      font-weight: 600;
    }
  }
}

.state-box { @include page-state-box; }

.empty {
  @include page-state-box;
  .empty-title { display: block; font-size: 15px; color: $text-secondary; margin-bottom: 8px; }
  .empty-desc { display: block; font-size: 12px; color: $text-muted; line-height: 1.6; }
}

.paper-card {
  @include card;
  padding: 14px 16px;
  border-radius: $radius-lg;
  margin-bottom: 12px;
  &:active { opacity: 0.85; }
}

.paper-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
  .chip {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
  }
  .chip-red { color: $primary-color; background: $primary-light; }
  .chip-blue { color: $accent-blue; background: rgba($accent-blue, 0.1); }
  .chip-green { color: $accent-green; background: rgba($accent-green, 0.1); }
  .chip-soft { color: $text-secondary; background: $chip-bg; }
  .paper-count {
    margin-left: auto;
    font-size: 11px;
    color: $text-muted;
  }
}

.paper-title {
  display: block;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
  margin-bottom: 4px;
}

.paper-desc {
  display: block;
  font-size: 12px;
  color: $text-secondary;
  line-height: 1.5;
  margin-bottom: 10px;
}

.paper-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid $border-color;
  padding-top: 8px;
  .paper-time { font-size: 12px; color: $text-muted; }
  .paper-cta { font-size: 13px; color: $primary-color; font-weight: 600; }
}
</style>
