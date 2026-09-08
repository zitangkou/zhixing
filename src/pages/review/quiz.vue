<template>
  <view class="page-review-quiz" :class="themeClass">
    <view v-if="loading" class="state-box">
      <text class="state-title">抽题中…</text>
    </view>

    <view v-else-if="loadError" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ loadError }}</text>
      <view class="state-btn" @tap="loadSession">点击重试</view>
    </view>

    <view v-else-if="done" class="done-card">
      <text class="done-title">本轮结束</text>
      <text class="done-desc">共 {{ cards.length }} 题 · again {{ againCount }} · 其余已推进</text>
      <view class="done-actions">
        <view class="btn primary" @tap="restart">再来一轮</view>
        <view class="btn" @tap="goHub">回复习中心</view>
      </view>
    </view>

    <view v-else-if="!cards.length" class="state-box">
      <text class="state-title">暂无可抽查节点</text>
      <text class="state-desc">在知识框架里给节点补正文或备注后再来</text>
      <view class="state-btn" @tap="goKnowledge">去知识框架</view>
    </view>

    <view v-else class="quiz-card">
      <view class="progress">
        <text>{{ index + 1 }} / {{ cards.length }}</text>
        <text class="mastery">{{ current?.masteryLevel || 'new' }}</text>
      </view>
      <text class="path">{{ current?.path }}</text>
      <text class="title">{{ current?.title }}</text>

      <view v-if="!revealed" class="prompt">
        <text class="prompt-tip">先回忆要点，再揭晓对照</text>
        <view class="btn primary" @tap="revealed = true">揭晓</view>
        <view class="btn ghost" @tap="revealed = true">想不起来</view>
      </view>

      <view v-else class="answer">
        <text class="answer-label">参考</text>
        <text class="answer-body">{{ displayAnswer }}</text>
        <view class="grade-row">
          <view
            v-for="g in grades"
            :key="g.value"
            class="grade"
            :class="g.value"
            @tap="onGrade(g.value)"
          >{{ g.label }}</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api } from '@/api'
import { showToast } from '@/utils/platform'
import type { KnowledgeReviewCard, KnowledgeReviewResult } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '知识抽查' })

const { themeClass } = useThemeClass()
const loading = ref(true)
const loadError = ref('')
const cards = ref<KnowledgeReviewCard[]>([])
const index = ref(0)
const revealed = ref(false)
const done = ref(false)
const againCount = ref(0)
const submitting = ref(false)

const grades: { value: KnowledgeReviewResult; label: string }[] = [
  { value: 'again', label: '重来' },
  { value: 'hard', label: '困难' },
  { value: 'good', label: '良好' },
  { value: 'easy', label: '简单' },
]

const current = computed(() => cards.value[index.value] || null)
const displayAnswer = computed(() => {
  const c = current.value
  if (!c) return ''
  return (c.content || c.myNote || '（无正文）').trim()
})

async function loadSession() {
  loading.value = true
  loadError.value = ''
  done.value = false
  index.value = 0
  revealed.value = false
  againCount.value = 0
  try {
    const res = await api.createKnowledgeReviewSession(5)
    if (res.code === 0 && res.data) {
      cards.value = res.data.cards || []
    } else {
      cards.value = []
      loadError.value = res.message || '抽题失败'
    }
  } catch {
    cards.value = []
    loadError.value = '网络异常，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function onGrade(result: KnowledgeReviewResult) {
  if (!current.value || submitting.value) return
  submitting.value = true
  try {
    const res = await api.answerKnowledgeReview(current.value.id, result)
    if (res.code !== 0) {
      showToast(res.message || '提交失败')
      return
    }
    if (result === 'again') againCount.value += 1
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

function restart() {
  loadSession()
}

function goHub() {
  Taro.navigateBack({
    fail: () => Taro.redirectTo({ url: '/pages/review/hub' }),
  })
}

function goKnowledge() {
  Taro.navigateTo({ url: '/pages/knowledge/index' })
}

onMounted(loadSession)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-review-quiz {
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
  .mastery {
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
}

.path {
  display: block;
  font-size: 12px;
  color: $text-muted;
  margin-bottom: 8px;
  word-break: break-all;
}

.title {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: $text-primary;
  line-height: 1.35;
  margin-bottom: 24px;
}

.prompt {
  display: flex;
  flex-direction: column;
  gap: 10px;
  .prompt-tip {
    font-size: 13px;
    color: $text-secondary;
    margin-bottom: 4px;
  }
}

.answer {
  .answer-label {
    display: block;
    font-size: 12px;
    color: $text-muted;
    margin-bottom: 8px;
  }
  .answer-body {
    display: block;
    font-size: 15px;
    line-height: 1.7;
    color: $text-primary;
    white-space: pre-wrap;
    margin-bottom: 20px;
    max-height: 280px;
    overflow-y: auto;
  }
}

.grade-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.grade {
  @include hit-target(44px);
  text-align: center;
  padding: 0 4px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: $on-primary;
  &.again { background: $text-muted; }
  &.hard { background: $accent-amber; }
  &.good { background: $accent-blue; }
  &.easy { background: $success; }
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
    margin-bottom: 24px;
  }
  .done-actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
}
</style>
