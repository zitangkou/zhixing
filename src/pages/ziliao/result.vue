<template>
  <view class="zl-page" v-if="result" :class="themeClass">
    <view class="zl-score-card">
      <text class="zl-score">{{ result.correctCount }} / {{ result.totalCount }}</text>
      <text class="zl-label">正确题数</text>
      <text class="zl-accuracy">正确率 {{ accuracy }}%</text>
      <text class="zl-meta">用时 {{ formatSec(result.timeUsedSec) }}</text>
      <text v-if="result.savedWrongCount" class="zl-meta">已记入错题本 {{ result.savedWrongCount }} 道</text>
    </view>

    <view v-if="result.wrongs.length" class="zl-section">
      <text class="zl-block-title">错题解析</text>
      <view v-for="w in result.wrongs" :key="w.questionId" class="zl-wrong-card">
        <text class="zl-stem">{{ w.stem }}</text>
        <text class="zl-ans">我答 {{ displayAns(w.userAnswer) }} · 正确 {{ displayAns(w.correctAnswer) }}</text>
        <text v-if="w.analysis" class="zl-analysis">{{ w.analysis }}</text>
      </view>
    </view>
    <view v-else class="zl-section">
      <text class="zl-ok">全部正确，继续保持！</text>
    </view>

    <view class="zl-actions">
      <nut-button v-if="result.setId" plain type="primary" block @click="goRedo">重做本组</nut-button>
      <nut-button plain type="primary" block @click="goWrong">查看资料错题本</nut-button>
      <nut-button type="primary" block @click="goHub">返回资料分析</nut-button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import type { ZiliaoDrillSubmitResult } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '练习结果' })

const { themeClass } = useThemeClass()
const router = useRouter()
const result = ref<ZiliaoDrillSubmitResult | null>(null)

const accuracy = computed(() => {
  if (!result.value || !result.value.totalCount) return 0
  return Math.round((result.value.correctCount / result.value.totalCount) * 100)
})

function formatSec(s: number) {
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m}分${r}秒`
}

function displayAns(a: string | string[]) {
  return Array.isArray(a) ? a.join(',') : a || '未答'
}

function goWrong() {
  Taro.navigateTo({ url: '/pages/question/manual-list?subject=资料' })
}

function goRedo() {
  if (!result.value?.setId) return
  Taro.redirectTo({
    url: `/pages/ziliao/drill?setId=${encodeURIComponent(result.value.setId)}`,
  })
}

function goHub() {
  Taro.navigateBack({ delta: 1 }).catch(() => {
    Taro.redirectTo({ url: '/pages/ziliao/index' })
  })
}

onMounted(() => {
  try {
    const raw = decodeURIComponent(router.params?.data || '')
    result.value = JSON.parse(raw)
  } catch {
    Taro.showToast({ title: '结果解析失败', icon: 'none' })
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.zl-page {
  @include page-padding;
  padding-bottom: 48px;
}
.zl-score-card {
  @include card;
  padding: 24px 16px;
  text-align: center;
}
.zl-score {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: $primary-color;
}
.zl-label {
  display: block;
  font-size: 13px;
  color: $text-secondary;
  margin-top: 4px;
}
.zl-accuracy {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: $primary-color;
  margin-top: 6px;
}
.zl-meta {
  display: block;
  font-size: 12px;
  color: $text-muted;
  margin-top: 4px;
}
.zl-section {
  @include card;
}
.zl-block-title {
  display: block;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: $text-primary;
}
.zl-wrong-card {
  padding: 10px 0;
  border-bottom: 1px solid $border-color;
}
.zl-wrong-card:last-child {
  border-bottom: none;
}
.zl-stem {
  display: block;
  font-size: 14px;
  color: $text-primary;
  margin-bottom: 4px;
}
.zl-ans {
  display: block;
  font-size: 12px;
  color: $accent-amber;
  margin-bottom: 4px;
}
.zl-analysis {
  display: block;
  font-size: 12px;
  color: $text-secondary;
  line-height: 1.5;
}
.zl-ok {
  font-size: 14px;
  color: $success;
}
.zl-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
