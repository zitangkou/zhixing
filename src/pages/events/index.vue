<template>
  <view class="page-events" :class="themeClass">
    <view class="hero">
      <view class="hero-text">
        <text class="hero-title">时事印象</text>
        <text class="hero-desc">记事件 · 挂框架 · 形成考点联系</text>
      </view>
      <view class="hero-btn" @tap="goEdit()">+ 记一条</view>
    </view>

    <view class="stats-row" v-if="hub">
      <view class="stat" @tap="setMode('timeline')">
        <text class="num">{{ hub.total }}</text>
        <text class="label">全部</text>
      </view>
      <view class="stat-divider" />
      <view class="stat" @tap="setMode('framework')">
        <text class="num" :class="{ warn: hub.linkedCount > 0 }">{{ hub.linkedCount }}</text>
        <text class="label">已挂框架</text>
      </view>
      <view class="stat-divider" />
      <view class="stat" @tap="filterUnlinked">
        <text class="num" :class="{ warn: hub.unlinkedCount > 0 }">{{ hub.unlinkedCount }}</text>
        <text class="label">待归属</text>
      </view>
      <view class="stat-divider" />
      <view class="stat">
        <text class="num">{{ hub.recentCount }}</text>
        <text class="label">近7天</text>
      </view>
    </view>

    <view class="mode-row">
      <text class="mode" :class="{ on: mode === 'timeline' }" @tap="setMode('timeline')">时间线</text>
      <text class="mode" :class="{ on: mode === 'framework' }" @tap="setMode('framework')">按框架</text>
    </view>

    <view v-if="loading" class="empty">加载中...</view>

    <!-- 按框架 -->
    <view v-else-if="mode === 'framework'" class="fw-list">
      <view v-if="!hub?.frameworkGroups?.length" class="empty">
        <text class="empty-title">还没有挂到框架的事件</text>
        <text class="empty-desc">记录时点选知识框架考点，例如「航天常识 / 神舟系列」</text>
        <view class="empty-btn" @tap="goEdit()">记第一条</view>
      </view>
      <view v-for="g in hub?.frameworkGroups || []" :key="g.label" class="fw-group">
        <view class="fw-head" @tap="toggleGroup(g.label)">
          <view class="fw-main">
            <text class="fw-label">{{ g.label }}</text>
            <text class="fw-count">{{ g.count }} 条</text>
          </view>
          <text class="fw-arrow">{{ expanded[g.label] === false ? '▸' : '▾' }}</text>
        </view>
        <view v-if="expanded[g.label] !== false" class="fw-items">
          <view
            v-for="e in g.items"
            :key="e.id"
            class="event-card compact"
            @tap="goEdit(e.id)"
          >
            <view class="card-top">
              <text class="date">{{ e.eventDate || '日期未填' }}</text>
              <text v-if="e.place" class="place">{{ e.place }}</text>
            </view>
            <text class="title">{{ e.title }}</text>
            <text v-if="e.coreContent" class="core">{{ e.coreContent }}</text>
          </view>
          <text
            v-if="g.count > g.items.length"
            class="fw-more"
            @tap="filterPath(g.treeKey, g.path)"
          >查看全部 {{ g.count }} 条 ›</text>
        </view>
      </view>
    </view>

    <!-- 时间线 -->
    <view v-else class="list">
      <view v-if="filterTip" class="filter-tip">
        <text>{{ filterTip }}</text>
        <text class="clear" @tap="clearFilter">清除</text>
      </view>
      <view v-if="!events.length" class="empty">
        <text class="empty-title">{{ emptyTitle }}</text>
        <text class="empty-desc">例：神舟十号发射成功 → 时间/地点/核心内容 → 归属「航天常识 / 神舟系列」</text>
        <view class="empty-btn" @tap="goEdit()">记第一条</view>
      </view>
      <view
        v-for="e in events"
        :key="e.id"
        class="event-card"
        @tap="goEdit(e.id)"
      >
        <view class="card-top">
          <text class="date">{{ e.eventDate || '日期未填' }}</text>
          <text v-if="e.place" class="place">{{ e.place }}</text>
        </view>
        <text class="title">{{ e.title }}</text>
        <text v-if="e.coreContent" class="core">{{ e.coreContent }}</text>
        <view v-if="e.knowledgePath || e.knowledgeTreeKey" class="kb">
          <text class="kb-label">框架</text>
          <text class="kb-path">{{ formatKb(e) }}</text>
        </view>
        <view v-else class="kb muted">
          <text class="kb-path">未归属框架 · 点开补挂</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { api } from '@/api'
import { formatKnowledgeLabel } from '@/utils/knowledge'
import type { EventHub, EventImpression } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '时事印象' })

const { themeClass } = useThemeClass()
const loading = ref(false)
const mode = ref<'timeline' | 'framework'>('timeline')
const hub = ref<EventHub | null>(null)
const events = ref<EventImpression[]>([])
const expanded = reactive<Record<string, boolean>>({})
const filter = ref<{ treeKey?: string; path?: string; unlinked?: boolean }>({})

const filterTip = computed(() => {
  if (filter.value.unlinked) return '筛选：待归属框架'
  if (filter.value.path || filter.value.treeKey) {
    const label = filter.value.path
      ? formatKnowledgeLabel(filter.value.path)
      : filter.value.treeKey
    return `筛选：${filter.value.treeKey || ''}${filter.value.path ? ' / ' + label : ''}`
  }
  return ''
})

const emptyTitle = computed(() =>
  filter.value.unlinked ? '没有待归属事件' : filterTip.value ? '该框架下暂无事件' : '还没有事件印象',
)

function formatKb(e: EventImpression) {
  if (e.knowledgeTreeKey && e.knowledgePath) {
    return `${e.knowledgeTreeKey} / ${formatKnowledgeLabel(e.knowledgePath)}`
  }
  return e.knowledgePath
    ? formatKnowledgeLabel(e.knowledgePath)
    : e.knowledgeTreeKey || ''
}

function setMode(m: 'timeline' | 'framework') {
  mode.value = m
  if (m === 'timeline' && (filter.value.path || filter.value.unlinked)) {
    // keep filter
  } else if (m === 'timeline') {
    filter.value = {}
  }
  load()
}

function filterUnlinked() {
  mode.value = 'timeline'
  filter.value = { unlinked: true }
  load()
}

function filterPath(treeKey: string, path: string) {
  mode.value = 'timeline'
  filter.value = { treeKey, path }
  load()
}

function clearFilter() {
  filter.value = {}
  load()
}

function toggleGroup(label: string) {
  const open = expanded[label] !== false
  expanded[label] = !open
}

async function load() {
  loading.value = true
  try {
    const hubRes = await api.getEventHub()
    if (hubRes.code === 0) hub.value = hubRes.data

    if (mode.value === 'timeline') {
      const res = await api.listEvents(filter.value)
      if (res.code === 0 && res.data) events.value = res.data
    }
  } finally {
    loading.value = false
  }
}

function goEdit(id?: string) {
  Taro.navigateTo({
    url: id ? `/pages/events/edit?id=${id}` : '/pages/events/edit',
  })
}

onMounted(load)
useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-events {
  @include page-padding;
  padding-bottom: 48px;
}

.hero {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  .hero-text { flex: 1; min-width: 0; }
  .hero-title {
    display: block;
    font-size: 22px;
    font-weight: 700;
    color: $text-primary;
  }
  .hero-desc {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: $text-muted;
  }
  .hero-btn {
    flex-shrink: 0;
    padding: 8px 14px;
    border-radius: 8px;
    background: $primary-color;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
  }
}

.stats-row {
  @include card;
  display: flex;
  padding: 12px 4px;
  margin-bottom: 12px;
  .stat {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    .num {
      font-size: 17px;
      font-weight: 700;
      color: $text-primary;
      &.warn { color: $primary-color; }
    }
    .label { font-size: 10px; color: $text-muted; }
  }
  .stat-divider {
    width: 1px;
    background: rgba(0, 0, 0, 0.06);
    margin: 4px 0;
  }
}

.mode-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  .mode {
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 13px;
    background: $card-bg;
    color: $text-secondary;
    box-shadow: $shadow-card;
    &.on {
      background: $primary-color;
      color: #fff;
      font-weight: 600;
    }
  }
}

.filter-tip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: $text-secondary;
  background: $primary-light;
  padding: 8px 12px;
  border-radius: 8px;
  margin-bottom: 10px;
  .clear { color: $primary-color; font-weight: 600; }
}

.empty {
  text-align: center;
  padding: 40px 16px;
  color: $text-muted;
  .empty-title {
    display: block;
    font-size: 15px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 8px;
  }
  .empty-desc {
    display: block;
    font-size: 12px;
    line-height: 1.55;
    margin-bottom: 16px;
  }
  .empty-btn {
    display: inline-block;
    padding: 8px 16px;
    border-radius: 8px;
    background: $primary-color;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
  }
}

.list, .fw-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.event-card {
  @include card;
  padding: 14px;
  &.compact { padding: 12px; }
  .card-top {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;
  }
  .date {
    font-size: 12px;
    font-weight: 600;
    color: $primary-color;
  }
  .place {
    font-size: 12px;
    color: $text-muted;
  }
  .title {
    display: block;
    font-size: 16px;
    font-weight: 700;
    line-height: 1.4;
    margin-bottom: 6px;
    color: $text-primary;
  }
  .core {
    display: block;
    font-size: 13px;
    line-height: 1.55;
    color: $text-secondary;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .kb {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px dashed $border-color;
    &.muted .kb-path { color: $text-muted; }
  }
  .kb-label {
    flex-shrink: 0;
    font-size: 11px;
    font-weight: 700;
    color: $primary-color;
    background: $primary-light;
    padding: 2px 6px;
    border-radius: 4px;
  }
  .kb-path {
    flex: 1;
    font-size: 12px;
    color: $text-secondary;
    line-height: 1.45;
    word-break: break-all;
  }
}

.fw-group {
  @include card;
  padding: 0;
  overflow: hidden;
}

.fw-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px;
  .fw-main { flex: 1; min-width: 0; }
  .fw-label {
    display: block;
    font-size: 14px;
    font-weight: 700;
    color: $text-primary;
    word-break: break-all;
  }
  .fw-count {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: $text-muted;
  }
  .fw-arrow {
    color: $text-muted;
    font-size: 14px;
  }
}

.fw-items {
  padding: 0 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: $page-bg;
}

.fw-more {
  display: block;
  text-align: center;
  font-size: 12px;
  color: $primary-color;
  font-weight: 600;
  padding: 6px 0 2px;
}
</style>
