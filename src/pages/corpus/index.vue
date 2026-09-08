<template>
  <view class="page-corpus" :class="themeClass">
    <view class="hero">
      <view class="hero-text">
        <text class="hero-title">语料本</text>
        <text class="hero-desc">专名/成语/诗典/金句 · 快记 → 澄清 → 改写</text>
      </view>
      <view class="hero-btn" @tap="goEdit()">+ 快记</view>
    </view>

    <view class="stats-row">
      <view class="stat" @tap="setTab('inbox')">
        <text class="num" :class="{ warn: (stats?.inboxCount || 0) > 0 }">{{ stats?.inboxCount ?? 0 }}</text>
        <text class="label">待内化</text>
      </view>
      <view class="stat-divider" />
      <view class="stat" @tap="setTab('owned')">
        <text class="num">{{ (stats?.ownedCount ?? 0) + (stats?.usedCount ?? 0) }}</text>
        <text class="label">已占有</text>
      </view>
      <view class="stat-divider" />
      <view class="stat" @tap="setTab('all')">
        <text class="num">{{ stats?.total ?? 0 }}</text>
        <text class="label">全部</text>
      </view>
    </view>

    <scroll-view scroll-x class="filter-scroll">
      <view class="filter-row">
        <text
          v-for="t in tabs"
          :key="t.value"
          class="filter"
          :class="{ on: tab === t.value }"
          @tap="setTab(t.value)"
        >{{ t.label }}</text>
      </view>
    </scroll-view>

    <view v-if="loading" class="empty">加载中...</view>
    <view v-else-if="!items.length" class="empty">
      <text class="empty-title">{{ emptyTitle }}</text>
      <text class="empty-desc">{{ emptyDesc }}</text>
      <view class="empty-btn" @tap="goEdit()">记第一条</view>
    </view>
    <view v-else class="list">
      <view v-for="item in items" :key="item.id" class="item" @tap="goEdit(item.id)">
        <view class="item-meta">
          <text class="status" :class="item.status">{{ statusLabel(item.status) }}</text>
          <text class="meta-dot">·</text>
          <text class="meta-kind">{{ item.kind }}</text>
          <text class="meta-dot">·</text>
          <text class="meta-src">{{ item.sourceType }}</text>
        </view>
        <text class="original">{{ item.original }}</text>
        <text v-if="item.knowledgePath" class="kb-path">{{ formatKb(item) }}</text>
        <text v-if="item.plainNote" class="plain-note">{{ item.plainNote }}</text>
        <text v-else-if="item.rewrite" class="rewrite">{{ item.rewrite }}</text>
        <view v-if="item.tags.length" class="tags">
          <text v-for="tag in item.tags" :key="tag" class="tag">{{ tag }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import { api } from '@/api'
import { corpusStatusLabel } from '@/utils/corpus'
import { formatKnowledgeLabel } from '@/utils/knowledge'
import type { CorpusItem, CorpusStats } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '语料本' })

const { themeClass } = useThemeClass()
const tabs = [
  { value: 'inbox', label: '待内化' },
  { value: 'clarified', label: '已澄清' },
  { value: 'owned', label: '已占有' },
  { value: 'used', label: '已运用' },
  { value: 'all', label: '全部' },
]

const router = useRouter()
const tabFromQuery = router.params?.tab
const tab = ref(
  tabFromQuery && tabs.some((t) => t.value === tabFromQuery) ? tabFromQuery : 'inbox',
)
const loading = ref(false)
const items = ref<CorpusItem[]>([])
const stats = ref<CorpusStats | null>(null)

const emptyTitle = computed(() =>
  tab.value === 'inbox' ? 'Inbox 已清空' : '这里还没有语料',
)
const emptyDesc = computed(() =>
  tab.value === 'inbox'
    ? '去「已占有」看看，或再快记一条'
    : '报纸、视频里好的词句，先丢进来',
)

function statusLabel(s: string) {
  return corpusStatusLabel(s)
}

function formatKb(item: CorpusItem) {
  return formatKnowledgeLabel(item.knowledgePath || '', item.knowledgeTreeKey || undefined)
}

function setTab(v: string) {
  tab.value = v
  loadList()
}

function goEdit(id?: string) {
  Taro.navigateTo({
    url: id ? `/pages/corpus/edit?id=${id}` : '/pages/corpus/edit',
  })
}

async function loadStats() {
  const res = await api.getCorpusStats()
  if (res.code === 0) stats.value = res.data
}

async function loadList() {
  loading.value = true
  try {
    const status = tab.value === 'all' ? undefined : tab.value
    const res = await api.listCorpusItems(status)
    if (res.code === 0) items.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function refresh() {
  await Promise.all([loadStats(), loadList()])
}

onMounted(refresh)
useDidShow(refresh)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-corpus {
  padding: 20px 16px 48px;
  min-height: 100vh;
  box-sizing: border-box;
}

.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  .hero-text {
    flex: 1;
    min-width: 0;
  }
  .hero-title {
    display: block;
    font-size: 24px;
    font-weight: 700;
    color: $text-primary;
    letter-spacing: 0.02em;
    line-height: 1.2;
  }
  .hero-desc {
    display: block;
    margin-top: 8px;
    font-size: 13px;
    color: $text-muted;
    line-height: 1.4;
  }
  .hero-btn {
    flex-shrink: 0;
    padding: 10px 16px;
    border-radius: 8px;
    background: $primary-color;
    color: $on-primary;
    font-size: 14px;
    font-weight: 600;
  }
}

.stats-row {
  display: flex;
  align-items: stretch;
  margin-bottom: 20px;
  padding: 16px 0;
  border-top: 1px solid $border-color;
  border-bottom: 1px solid $border-color;
  .stat {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    .num {
      font-size: 22px;
      font-weight: 700;
      color: $text-primary;
      line-height: 1;
      &.warn { color: $primary-color; }
    }
    .label {
      font-size: 12px;
      color: $text-muted;
    }
  }
  .stat-divider {
    width: 1px;
    background: $border-color;
    margin: 4px 0;
  }
}

.filter-scroll {
  white-space: nowrap;
  margin-bottom: 16px;
}
.filter-row {
  display: inline-flex;
  gap: 4px;
}
.filter {
  display: inline-block;
  font-size: 14px;
  padding: 8px 14px;
  color: $text-muted;
  position: relative;
  &.on {
    color: $text-primary;
    font-weight: 600;
    &::after {
      content: '';
      position: absolute;
      left: 14px;
      right: 14px;
      bottom: 2px;
      height: 2px;
      background: $primary-color;
      border-radius: 1px;
    }
  }
}

.empty {
  padding: 56px 20px;
  text-align: center;
  .empty-title {
    display: block;
    font-size: 16px;
    font-weight: 600;
    color: $text-secondary;
    margin-bottom: 8px;
  }
  .empty-desc {
    display: block;
    font-size: 13px;
    color: $text-muted;
    line-height: 1.5;
    margin-bottom: 20px;
  }
  .empty-btn {
    display: inline-block;
    padding: 10px 20px;
    border-radius: 8px;
    border: 1px solid $primary-color;
    color: $primary-color;
    font-size: 14px;
    font-weight: 600;
  }
}

.list {
  display: flex;
  flex-direction: column;
}

.item {
  padding: 18px 0;
  border-bottom: 1px solid $border-color;
  &:last-child { border-bottom: none; }

  .item-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 10px;
    .status {
      font-size: 12px;
      font-weight: 600;
      color: $text-secondary;
      &.inbox { color: $primary-color; }
      &.owned, &.used { color: $accent-green; }
    }
    .meta-dot { color: $text-muted; font-size: 12px; }
    .meta-kind, .meta-src {
      font-size: 12px;
      color: $text-muted;
    }
  }

  .original {
    display: block;
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
    line-height: 1.55;
  }

  .kb-path {
    display: block;
    margin-top: 6px;
    font-size: 12px;
    color: $primary-color;
    line-height: 1.4;
  }
  .plain-note,
  .rewrite {
    display: block;
    margin-top: 10px;
    font-size: 14px;
    color: $text-secondary;
    line-height: 1.5;
  }
  .plain-note {
    color: $text-muted;
  }

  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
    .tag {
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 6px;
      background: $elevated;
      color: $text-muted;
    }
  }
}
</style>
