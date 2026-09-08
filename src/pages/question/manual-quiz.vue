<template>
  <view class="page-manual-quiz" :class="themeClass">
    <view v-if="loading" class="state-box">
      <text class="state-title">准备题目中…</text>
    </view>

    <view v-else-if="loadError" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ loadError }}</text>
      <view class="state-btn" @tap="loadSession">点击重试</view>
    </view>

    <view v-else-if="done" class="done-card">
      <text class="done-title">本轮结束</text>
      <text class="done-desc">
        共 {{ cards.length }} 题 · 推进 {{ goodCount }} · 重置 {{ againCount }}
      </text>
      <text v-if="waitingHint" class="done-skip">{{ waitingHint }}</text>
      <view class="done-actions">
        <view class="btn primary" @tap="restart">再刷一轮</view>
        <view class="btn" @tap="goHub">回复习中心</view>
        <view class="btn ghost" @tap="goList">看错题本</view>
      </view>
    </view>

    <view v-else-if="!cards.length" class="state-box">
      <text class="state-title">今日无到期行测错题</text>
      <text class="state-desc">未到期的题今天不用复习，明天按记忆曲线再推</text>
      <view class="state-btn" @tap="goHub">回复习中心</view>
    </view>

    <view v-else class="quiz-card">
      <view class="progress">
        <text>{{ index + 1 }} / {{ cards.length }}</text>
        <text class="meta">第 {{ (current?.reviewStage || 0) + 1 }} 档</text>
      </view>
      <view class="chips">
        <text v-if="current?.subject" class="chip">{{ current.subject }}</text>
        <text v-if="current?.questionType" class="chip soft">{{ current.questionType }}</text>
      </view>
      <text v-if="current?.stem" class="stem">{{ current.stem }}</text>
      <view v-if="current?.images?.length" class="images">
        <image
          v-for="(img, i) in current.images"
          :key="i"
          class="img"
          :src="resolveMediaUrl(img)"
          mode="widthFix"
          @tap="preview(i)"
        />
      </view>
      <text v-if="current?.options" class="options">{{ current.options }}</text>

      <view v-if="!revealed" class="prompt">
        <text class="prompt-tip">先回忆答案与考点，再揭晓对照</text>
        <view class="btn primary" @tap="revealed = true">揭晓</view>
      </view>

      <view v-else class="answer">
        <text v-if="current?.myAnswer" class="line bad">我答：{{ current.myAnswer }}</text>
        <text v-if="current?.correctAnswer" class="line ok">正确：{{ current.correctAnswer }}</text>
        <text v-if="current?.analysis" class="line body">{{ current.analysis }}</text>
        <text v-if="current?.note" class="line muted">{{ current.note }}</text>
        <view class="grade-row">
          <view class="grade again" @tap="onGrade('again')">忘了</view>
          <view class="grade good" @tap="onGrade('good')">记住了</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api } from '@/api'
import { resolveMediaUrl } from '@/utils/media'
import { showToast } from '@/utils/platform'
import type { ManualWrong } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '行测错题复习' })

const { themeClass } = useThemeClass()
const SESSION_CAP = 15
const loading = ref(true)
const loadError = ref('')
const cards = ref<ManualWrong[]>([])
const index = ref(0)
const revealed = ref(false)
const done = ref(false)
const goodCount = ref(0)
const againCount = ref(0)
const submitting = ref(false)
const waitingHint = ref('')

const current = computed(() => cards.value[index.value] || null)

async function loadSession() {
  loading.value = true
  loadError.value = ''
  done.value = false
  index.value = 0
  revealed.value = false
  goodCount.value = 0
  againCount.value = 0
  waitingHint.value = ''
  try {
    const [dueRes, waitingRes] = await Promise.all([
      api.listManualWrongs(undefined, false, 'review'),
      api.listManualWrongs(undefined, false, 'waiting'),
    ])
    if (dueRes.code !== 0) {
      cards.value = []
      loadError.value = dueRes.message || '加载失败'
      return
    }
    const due = [...(dueRes.data || [])].sort(
      (a, b) => (a.reviewStage || 0) - (b.reviewStage || 0) || (b.reviewCount || 0) - (a.reviewCount || 0),
    )
    cards.value = due.slice(0, SESSION_CAP)
    const waiting = waitingRes.code === 0 ? (waitingRes.data?.length || 0) : 0
    if (waiting > 0) {
      waitingHint.value = `另有 ${waiting} 道未到期，今天不用复习`
    }
  } catch {
    cards.value = []
    loadError.value = '网络异常，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function onGrade(result: 'good' | 'again') {
  if (!current.value || submitting.value) return
  submitting.value = true
  try {
    const res = await api.reviewManualWrong(current.value.id, result)
    if (res.code !== 0) {
      showToast(res.message || '提交失败')
      return
    }
    if (result === 'again') {
      againCount.value += 1
      showToast('已重置，明天再来')
    } else {
      goodCount.value += 1
      showToast(res.data?.mastered ? '已掌握' : '已安排下次复习', 'success')
    }
    if (index.value + 1 >= cards.value.length) {
      done.value = true
    } else {
      index.value += 1
      revealed.value = false
    }
  } finally {
    submitting.value = false
  }
}

function preview(i: number) {
  const imgs = current.value?.images || []
  if (!imgs.length) return
  Taro.previewImage({
    urls: imgs.map(resolveMediaUrl),
    current: resolveMediaUrl(imgs[i]),
  })
}

function restart() {
  loadSession()
}

function goHub() {
  Taro.navigateBack({
    fail: () => Taro.redirectTo({ url: '/pages/review/hub' }),
  })
}

function goList() {
  Taro.redirectTo({ url: '/pages/question/manual-list' })
}

onMounted(loadSession)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-manual-quiz {
  @include page-padding;
  padding-bottom: 48px;
}

.state-box { @include page-state-box; }

.empty {
  @include page-state-box;
  .empty-title {
    display: block;
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 8px;
  }
  .empty-desc {
    display: block;
    margin-bottom: 20px;
  }
}

.quiz-card,
.done-card {
  @include card;
  padding: 20px 16px;
}

.progress {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: $text-muted;
  margin-bottom: 12px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  .chip {
    font-size: 11px;
    font-weight: 600;
    color: $primary-color;
    background: $primary-light;
    padding: 2px 8px;
    border-radius: 4px;
    &.soft {
      color: $text-secondary;
      background: $page-bg;
    }
  }
}

.stem {
  display: block;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.55;
  color: $text-primary;
  margin-bottom: 12px;
}

.options {
  display: block;
  font-size: 14px;
  line-height: 1.6;
  color: $text-secondary;
  white-space: pre-wrap;
  margin-bottom: 16px;
}

.images {
  margin-bottom: 12px;
  .img {
    width: 100%;
    border-radius: 8px;
    margin-bottom: 8px;
  }
}

.prompt {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
  .prompt-tip {
    font-size: 13px;
    color: $text-secondary;
  }
}

.answer {
  margin-top: 8px;
  .line {
    display: block;
    font-size: 14px;
    line-height: 1.6;
    margin-bottom: 8px;
    &.bad { color: $accent-amber; }
    &.ok { color: $success; font-weight: 600; }
    &.body { color: $text-primary; white-space: pre-wrap; }
    &.muted { color: $text-muted; font-size: 13px; }
  }
}

.grade-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 16px;
}

.grade {
  @include hit-target(44px);
  text-align: center;
  padding: 0 8px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: $on-primary;
  &.again { background: $text-muted; }
  &.good { background: $success; }
}

.btn {
  text-align: center;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  background: $card-bg;
  color: $text-primary;
  box-shadow: $shadow-card;
  &.primary {
    background: $primary-color;
    color: $on-primary;
    box-shadow: none;
  }
  &.ghost {
    background: transparent;
    box-shadow: none;
    color: $text-muted;
  }
}

.done-card {
  text-align: center;
  .done-title {
    display: block;
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 8px;
  }
  .done-desc {
    display: block;
    font-size: 13px;
    color: $text-muted;
    margin-bottom: 8px;
  }
  .done-skip {
    display: block;
    font-size: 12px;
    color: $text-muted;
    margin-bottom: 20px;
  }
  .done-actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
}
</style>
