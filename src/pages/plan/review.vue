<template>
  <view class="page-review" :class="themeClass">
    <view class="review-section">
      <text class="section-label">完成度（{{ form.completion }}%）</text>
      <slider :value="form.completion" :min="0" :max="100" :step="5" :activeColor="brandColor" @change="onCompletion" />
    </view>

    <view class="review-section">
      <text class="section-label">实际学习时长（{{ form.totalMinutes }} min）</text>
      <slider :value="form.totalMinutes" :min="0" :max="300" :step="10" :activeColor="brandColor" @change="onMinutes" />
    </view>

    <view class="review-section">
      <text class="section-label">心情</text>
      <view class="mood-row">
        <text
          v-for="m in moods"
          :key="m.value"
          class="mood-chip"
          :class="{ active: form.mood === m.value }"
          @tap="form.mood = m.value"
        >{{ m.label }}</text>
      </view>
    </view>

    <view class="review-section">
      <text class="section-label">今日弱项</text>
      <nut-textarea v-model="form.weakPoint" placeholder="如：资料分析速度不够..." :rows="2" />
    </view>

    <view class="review-section">
      <text class="section-label">明日重点</text>
      <nut-textarea v-model="form.tomorrowFocus" placeholder="如：资料分析速算练习" :rows="2" />
    </view>

    <view class="review-section">
      <text class="section-label">补充笔记</text>
      <nut-textarea v-model="form.note" placeholder="其他想记录的..." :rows="3" />
    </view>

    <nut-button type="primary" block class="primary-btn" :loading="saving" @click="onSave">
      保存复盘
    </nut-button>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { Button as NutButton, Textarea as NutTextarea } from '@nutui/nutui-taro'
import { usePlanStore } from '@/store/plan'
import { useBrandColor, useThemeClass } from '@/utils/brandColor'
import { flushFormBeforeSave } from '@/utils/formFlush'
import { showToast } from '@/utils/platform'

definePageConfig({ navigationBarTitleText: '今日复盘' })

const { themeClass } = useThemeClass()
const planStore = usePlanStore()
const { brandColor } = useBrandColor()
const saving = ref(false)
const loaded = ref(false)

const form = reactive({
  reviewDate: new Date().toISOString().slice(0, 10),
  completion: 0,
  totalMinutes: 0,
  mood: '' as '' | 'good' | 'ok' | 'bad',
  weakPoint: '',
  tomorrowFocus: '',
  note: '',
})

const moods = [
  { value: 'good', label: '不错' },
  { value: 'ok', label: '一般' },
  { value: 'bad', label: '差' },
] as const

function load() {
  if (loaded.value) return
  const r = planStore.today?.review
  if (r) {
    form.completion = r.completion
    form.totalMinutes = r.totalMinutes
    form.mood = r.mood
    form.weakPoint = r.weakPoint
    form.tomorrowFocus = r.tomorrowFocus
    form.note = r.note
  } else if (planStore.today) {
    form.completion = planStore.today.completion
    form.totalMinutes = planStore.today.actualMinutes
  }
  loaded.value = true
}

function onCompletion(e: any) {
  form.completion = e.detail.value
}

function onMinutes(e: any) {
  form.totalMinutes = e.detail.value
}

async function onSave() {
  await flushFormBeforeSave()

  saving.value = true
  try {
    const ok = await planStore.saveReview({ ...form })
    if (ok) {
      showToast('已保存', 'success')
      setTimeout(() => Taro.navigateBack(), 600)
    } else {
      showToast('保存失败', 'error')
    }
  } finally {
    saving.value = false
  }
}

useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-review {
  @include page-padding;
  padding-bottom: 40px;
}

.review-section {
  @include card;
  padding: 14px 16px;
  border-radius: $radius-md;
  .section-label {
    display: block;
    font-size: 13px;
    color: $text-secondary;
    margin-bottom: 10px;
  }
}

.mood-row {
  display: flex;
  gap: 8px;
}

.mood-chip {
  @include filter-tab;
  background: $page-bg;
  color: $text-secondary;
  &.active {
    background: $primary-light;
    color: $primary-color;
    font-weight: 600;
  }
}

.primary-btn {
  margin-top: 12px;
}
</style>
