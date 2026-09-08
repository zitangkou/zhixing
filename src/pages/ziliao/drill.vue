<template>
  <view class="zl-page" v-if="detail" :class="themeClass">
    <view class="zl-top-bar">
      <text class="zl-progress">{{ currentIndex + 1 }} / {{ detail.questions.length }}</text>
      <text class="zl-timer">{{ formatSec(elapsed) }}</text>
    </view>

    <view class="zl-dots">
      <view
        v-for="(q, i) in detail.questions"
        :key="q.id"
        class="zl-dot"
        :class="{ 'zl-dot-active': i === currentIndex, 'zl-dot-done': answers[q.id] }"
        @tap="currentIndex = i"
      />
    </view>

    <view v-if="detail.material" class="zl-material">
      <view class="zl-material-head" @tap="materialExpanded = !materialExpanded">
        <text class="zl-material-label">材料</text>
        <text class="zl-material-toggle">{{ materialExpanded ? '收起 ▲' : '展开 ▼' }}</text>
      </view>
      <text v-if="materialExpanded" class="zl-material-text">{{ detail.material }}</text>
      <text v-else class="zl-material-text zl-material-clamp">{{ detail.material }}</text>
    </view>

    <view class="zl-stem-block" v-if="currentQ">
      <text class="zl-stem-tag">第 {{ currentIndex + 1 }} 题</text>
      <text class="zl-stem">{{ currentQ.stem }}</text>
    </view>

    <view class="zl-options" v-if="currentQ">
      <view
        v-for="(opt, i) in currentQ.options"
        :key="i"
        class="zl-option"
        :class="{ 'zl-option-selected': answers[currentQ.id] === letter(i) }"
        @tap="onSelect(letter(i))"
      >
        <text class="zl-option-letter">{{ letter(i) }}</text>
        <text class="zl-option-text">{{ opt }}</text>
      </view>
    </view>

    <view class="zl-nav-buttons">
      <nut-button plain type="primary" :disabled="currentIndex === 0" @click="goPrev">上一题</nut-button>
      <nut-button
        v-if="currentIndex < detail.questions.length - 1"
        type="primary"
        @click="goNext"
      >下一题</nut-button>
      <nut-button v-else type="primary" :loading="submitting" @click="onSubmit">交卷</nut-button>
    </view>
  </view>
  <view v-else class="zl-loading" :class="themeClass">加载中...</view>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import { api } from '@/api'
import type { ZiliaoDrillSetDetail } from '@/types'
import { showConfirm, showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '专项练习' })

const { themeClass } = useThemeClass()
const router = useRouter()
const setId = decodeURIComponent(router.params?.setId || '')
const typeCode = router.params?.typeCode || ''
const detail = ref<ZiliaoDrillSetDetail | null>(null)
const currentIndex = ref(0)
const answers = ref<Record<string, string>>({})
const elapsed = ref(0)
const submitting = ref(false)
const materialExpanded = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const currentQ = computed(() => detail.value?.questions[currentIndex.value] || null)

function letter(i: number) {
  return String.fromCharCode(65 + i)
}

function formatSec(s: number) {
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m}:${String(r).padStart(2, '0')}`
}

function onSelect(l: string) {
  if (!currentQ.value) return
  answers.value = { ...answers.value, [currentQ.value.id]: l }
}

function goPrev() {
  if (currentIndex.value > 0) currentIndex.value -= 1
}

function goNext() {
  if (detail.value && currentIndex.value < detail.value.questions.length - 1) {
    currentIndex.value += 1
  }
}

async function onSubmit() {
  if (!detail.value) return
  const unanswered = detail.value.questions.filter((q) => !answers.value[q.id]).length
  if (unanswered > 0) {
    const ok = await showConfirm('确认交卷', `还有 ${unanswered} 题未作答，确认交卷？`)
    if (!ok) return
  }
  submitting.value = true
  try {
    const res = await api.submitZiliaoDrill({
      setId,
      answers: detail.value.questions.map((q) => ({
        questionId: q.id,
        userAnswer: answers.value[q.id] || '',
      })),
      timeUsedSec: elapsed.value,
      typeCode,
      saveWrongs: true,
    })
    if (res.code !== 0 || !res.data) {
      showToast(res.message || '提交失败')
      return
    }
    const payload = encodeURIComponent(JSON.stringify(res.data))
    Taro.redirectTo({ url: `/pages/ziliao/result?data=${payload}` })
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const res = await api.getZiliaoDrillSet(setId)
  if (res.code !== 0 || !res.data) {
    showToast('练习组不存在')
    return
  }
  detail.value = res.data
  timer = setInterval(() => {
    elapsed.value += 1
  }, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.zl-page {
  @include page-padding;
  padding-bottom: 80px;
}
.zl-top-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}
.zl-progress,
.zl-timer {
  font-size: 13px;
  color: $text-secondary;
}
.zl-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 12px;
}
.zl-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: $border-color;
  transition: all 0.15s ease;
}
.zl-dot-done {
  background: rgba($primary-color, 0.35);
}
.zl-dot-active {
  background: $primary-color;
  transform: scale(1.3);
}
.zl-material {
  background: var(--zk-warn-soft);
  border-radius: $radius-md;
  padding: 12px;
  margin-bottom: 12px;
}
.zl-material-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.zl-material-toggle {
  font-size: 12px;
  color: $accent-amber;
}
.zl-material-label {
  display: block;
  font-size: 12px;
  color: $accent-amber;
  margin-bottom: 4px;
}
.zl-material-text {
  display: block;
  font-size: 13px;
  color: $text-secondary;
  line-height: 1.6;
}
.zl-material-clamp {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.zl-stem-block {
  @include card;
  border-radius: $radius-md;
}
.zl-stem-tag {
  display: block;
  font-size: 12px;
  color: $text-muted;
  margin-bottom: 6px;
}
.zl-stem {
  display: block;
  font-size: 14px;
  color: $text-primary;
  line-height: 1.5;
}
.zl-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.zl-option {
  display: flex;
  gap: 8px;
  background: $card-bg;
  border-radius: $radius-md;
  padding: 12px;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}
.zl-option-selected {
  border-color: $primary-color;
  background: $primary-light;
}
.zl-option-letter {
  font-weight: 700;
  color: $primary-color;
  width: 20px;
}
.zl-option-text {
  flex: 1;
  font-size: 14px;
  color: $text-primary;
}
.zl-nav-buttons {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  gap: 8px;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
  background: $card-bg;
  border-top: 1px solid $border-color;
}
.zl-loading {
  padding: 40px;
  text-align: center;
  color: $text-muted;
}
</style>
