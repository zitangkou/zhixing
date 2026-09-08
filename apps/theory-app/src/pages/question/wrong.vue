<template>
  <view class="page-wrong">
    <view class="srs-tip">间隔：1 → 2 → 4 → 7 → 15 → 30 天；今日只刷到期题</view>

    <view
      v-if="status === 'review' && questionStore.wrongQuestions.length > 0"
      class="start-cta"
      @tap="startSession"
    >
      <view class="start-main">
        <text class="start-title">开始今日复习</text>
        <text class="start-desc">推荐 {{ recommendCount }} 道 · 逐题刷，不罗列</text>
      </view>
      <text class="start-arrow">›</text>
    </view>

    <view class="filter-row">
      <text
        v-for="t in tabs"
        :key="t.value"
        class="filter"
        :class="{ on: status === t.value }"
        @tap="setStatus(t.value)"
      >{{ t.label }}</text>
    </view>

    <view v-if="status === 'waiting'" class="skip-tip">
      这些题尚未到期，今天不用复习
    </view>

    <view v-if="questionStore.wrongLoading && questionStore.wrongQuestions.length === 0" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在同步错题本</text>
    </view>
    <view v-else-if="loadError && questionStore.wrongQuestions.length === 0" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ loadError }}</text>
      <view class="state-btn" @tap="reloadWrongList">点击重试</view>
    </view>
    <view v-else-if="groupedArticles.length === 0" class="state-box">
      <text class="state-title">
        {{ status === 'review' ? '今日无到期错题' : status === 'waiting' ? '没有安排中的错题' : '暂无错题' }}
      </text>
      <text v-if="status === 'all'" class="state-desc">继续保持！</text>
    </view>

    <view v-else class="article-groups">
      <view
        v-for="group in groupedArticles"
        :key="group.articleId"
        class="article-group"
      >
        <view class="article-header" @tap="toggleArticle(group.articleId)">
          <view class="article-main">
            <text class="article-title">{{ group.articleTitle }}</text>
            <text class="article-meta">{{ group.items.length }} 道</text>
          </view>
          <text class="expand-icon">{{ isExpanded(group.articleId) ? '▾' : '▸' }}</text>
        </view>

        <view v-if="isExpanded(group.articleId)" class="question-list">
          <view
            v-for="item in group.items"
            :key="item.question.id"
            class="question-item"
          >
            <view class="question-content" @tap="redoQuestion(item.question.id)">
              <view class="stem-row">
                <text class="type-tag">{{ typeShort(item.question.type) }}</text>
                <text class="stem">{{ item.question.stem }}</text>
              </view>
              <text class="question-meta">
                错 {{ item.wrongCount }} 次 · 第 {{ (item.reviewStage || 0) + 1 }} 档
                · {{ formatSchedule(item) }}
              </text>
            </view>
            <text class="remove-btn" @tap.stop="confirmRemove(item.question.id)">移除</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Taro, { useDidShow, usePullDownRefresh, useRouter } from '@tarojs/taro'
import { useQuestionStore } from '@/store/question'
import { showConfirm, showToast } from '@/utils/platform'
import type { WrongQuestionRecord } from '@/types'

definePageConfig({ navigationBarTitleText: '错题本' })

type WrongStatus = 'review' | 'waiting' | 'all'

const SESSION_CAP = 15
const router = useRouter()
const fromReview = router.params?.from === 'review'
const redirected = ref(false)

const tabs: { value: WrongStatus; label: string }[] = [
  { value: 'review', label: '待复习' },
  { value: 'waiting', label: '已安排' },
  { value: 'all', label: '全部' },
]

interface WrongArticleGroup {
  articleId: string
  articleTitle: string
  items: WrongQuestionRecord[]
  latestWrongAt: number
}

const questionStore = useQuestionStore()
const expandedMap = ref<Record<string, boolean>>({})
const status = ref<WrongStatus>('review')
const loadError = ref('')

const recommendCount = computed(() =>
  Math.min(questionStore.wrongQuestions.length, SESSION_CAP),
)

const groupedArticles = computed<WrongArticleGroup[]>(() => {
  const map = new Map<string, WrongArticleGroup>()
  for (const item of questionStore.wrongQuestions) {
    const articleId = item.question.articleId
    let group = map.get(articleId)
    if (!group) {
      group = {
        articleId,
        articleTitle: item.articleTitle,
        items: [],
        latestWrongAt: 0,
      }
      map.set(articleId, group)
    }
    group.items.push(item)
    const ts = new Date(item.lastWrongAt).getTime()
    if (ts > group.latestWrongAt) group.latestWrongAt = ts
  }
  return Array.from(map.values())
    .map((group) => ({
      ...group,
      items: [...group.items].sort(
        (a, b) => new Date(b.lastWrongAt).getTime() - new Date(a.lastWrongAt).getTime(),
      ),
    }))
    .sort((a, b) => b.latestWrongAt - a.latestWrongAt)
})

watch(
  groupedArticles,
  (groups) => {
    if (groups.length === 1 && expandedMap.value[groups[0].articleId] === undefined) {
      expandedMap.value = { [groups[0].articleId]: true }
    }
  },
  { immediate: true },
)

function isExpanded(articleId: string) {
  return !!expandedMap.value[articleId]
}

function toggleArticle(articleId: string) {
  expandedMap.value = {
    ...expandedMap.value,
    [articleId]: !expandedMap.value[articleId],
  }
}

function formatSchedule(item: WrongQuestionRecord) {
  if (item.due || status.value === 'review') return '今日到期'
  if (!item.nextReviewAt) return '待安排'
  const d = new Date(item.nextReviewAt)
  if (Number.isNaN(d.getTime())) return '待安排'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `下次 ${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function typeShort(type?: string) {
  const map: Record<string, string> = {
    single: '单选',
    multiple: '多选',
    judge: '判断',
  }
  return map[type || ''] || '题目'
}

function startSession() {
  questionStore.completeDailyWrongReview()
  Taro.navigateTo({ url: '/pages/question/taking?wrongSession=1' })
}

function redoQuestion(questionId: string) {
  Taro.navigateTo({ url: `/pages/question/taking?wrongId=${questionId}` })
}

async function confirmRemove(questionId: string) {
  const ok = await showConfirm('移除错题', '确定已掌握该题，从错题本移除？')
  if (!ok) return
  const success = await questionStore.removeWrongQuestion(questionId)
  if (success) {
    showToast('已移除', 'success')
  }
}

async function setStatus(v: WrongStatus) {
  status.value = v
  await reloadWrongList()
}

async function reloadWrongList() {
  loadError.value = ''
  const ok = await questionStore.loadWrongQuestions(status.value)
  if (!ok && questionStore.wrongQuestions.length === 0) {
    loadError.value = '加载错题失败，请稍后重试'
    return
  }
  // 从复习中心进来：有到期题则直接进逐题模式
  if (
    fromReview
    && !redirected.value
    && status.value === 'review'
    && questionStore.wrongQuestions.length > 0
  ) {
    redirected.value = true
    Taro.redirectTo({ url: '/pages/question/taking?wrongSession=1' })
  }
}

onMounted(() => {
  reloadWrongList()
})

useDidShow(() => {
  if (!redirected.value) reloadWrongList()
})

usePullDownRefresh(async () => {
  try {
    await reloadWrongList()
  } finally {
    Taro.stopPullDownRefresh()
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-wrong {
  @include page-padding;
  .srs-tip {
    font-size: 12px;
    color: $text-muted;
    margin-bottom: 10px;
  }
  .start-cta {
    @include card;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px;
    margin-bottom: 12px;
    background: linear-gradient(135deg, var(--zk-primary-light), var(--zk-primary-faint));
    border: 1px solid var(--zk-primary-soft);
    .start-main { flex: 1; min-width: 0; }
    .start-title {
      display: block;
      font-size: 16px;
      font-weight: 700;
      color: $text-primary;
    }
    .start-desc {
      display: block;
      margin-top: 4px;
      font-size: 12px;
      color: $text-muted;
    }
    .start-arrow {
      font-size: 18px;
      color: $primary-color;
      font-weight: 600;
    }
  }
  .skip-tip {
    font-size: 12px;
    color: $text-muted;
    margin-bottom: 10px;
  }
  .filter-row {
    display: flex;
    gap: 8px;
    margin-bottom: 14px;
    .filter {
      @include filter-tab;
      background: $card-bg;
      color: $text-secondary;
      box-shadow: $shadow-card;
      &.on {
        background: $primary-color;
        color: $on-primary;
        font-weight: 600;
      }
    }
  }
  .state-box { @include page-state-box; }
  .article-groups {
    .article-group {
      @include card;
      padding: 0;
      overflow: hidden;
      margin-bottom: 12px;
    }
    .article-header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      .article-main {
        flex: 1;
        min-width: 0;
      }
      .article-title {
        display: block;
        font-size: 15px;
        font-weight: 600;
        line-height: 1.5;
        margin-bottom: 4px;
      }
      .article-meta {
        display: block;
        font-size: 12px;
        color: $text-muted;
      }
      .expand-icon {
        flex-shrink: 0;
        font-size: 16px;
        color: $text-muted;
        width: 20px;
        text-align: center;
      }
    }
    .question-list {
      border-top: 1px solid $border-color;
      background: $page-bg;
      .question-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        border-bottom: 1px solid $border-color;
        &:last-child { border-bottom: none; }
        .question-content {
          flex: 1;
          min-width: 0;
          &:active { opacity: 0.6; }
        }
        .stem-row {
          display: flex;
          align-items: flex-start;
          gap: 6px;
          margin-bottom: 6px;
        }
        .type-tag {
          flex-shrink: 0;
          font-size: 11px;
          font-weight: 600;
          color: $primary-color;
          background: $primary-light;
          padding: 1px 5px;
          border-radius: 4px;
          margin-top: 2px;
        }
        .stem {
          flex: 1;
          font-size: 14px;
          line-height: 1.6;
          color: $text-primary;
          overflow: hidden;
          text-overflow: ellipsis;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
        }
        .question-meta {
          display: block;
          font-size: 12px;
          color: $text-secondary;
        }
        .remove-btn {
          @include list-act;
          flex-shrink: 0;
          font-size: 12px;
          color: $text-muted;
          border: 1px solid $border-color;
          border-radius: 6px;
          &.danger { color: $text-muted; }
          &:active { color: $primary-color; border-color: $primary-color; }
        }
      }
    }
  }
}
</style>
