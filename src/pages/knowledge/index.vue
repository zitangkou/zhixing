<template>
  <view class="page-knowledge" :class="themeClass">
    <!-- 科目列表 -->
    <view v-if="!currentKey" class="map-list">
      <view v-if="loading" class="empty">加载中...</view>
      <view v-else-if="!maps.length" class="empty">暂无已发布的知识导图</view>
      <view
        v-for="m in maps"
        :key="m.treeKey"
        class="map-card"
        @tap="onSelect(m.treeKey)"
      >
        <image
          v-if="m.cover?.url"
          class="map-cover"
          :src="resolveMediaUrl(m.cover.url)"
          mode="aspectFill"
        />
        <view class="map-meta">
          <text class="map-title">{{ m.title }}</text>
          <text class="map-sub">{{ m.nodeCount }} 个节点 · v{{ m.version }}</text>
        </view>
      </view>
    </view>

    <!-- 科目详情 -->
    <view v-else>
      <view class="kb-header">
        <view class="kb-header-row">
          <text class="kb-back" @tap="backToList">← 科目</text>
          <text class="kb-tip">{{ currentTitle }}</text>
          <text class="kb-quiz" @tap="goQuiz">抽查</text>
        </view>
        <view v-if="current" class="kb-stats">
          <text class="kb-stat known">已掌握 {{ progress.known }}</text>
          <text class="kb-stat fuzzy">待复习 {{ progress.fuzzy }}</text>
          <text class="kb-stat fresh">未学 {{ progress.fresh }}</text>
        </view>
      </view>

      <view class="seg-tabs">
        <text class="seg-tab" :class="{ active: viewMode === 'outline' }" @tap="viewMode = 'outline'">
          大纲
        </text>
        <text class="seg-tab" :class="{ active: viewMode === 'map' }" @tap="viewMode = 'map'">
          导图
        </text>
      </view>

      <view v-if="viewMode === 'outline'">
        <view class="kb-toolbar">
          <input
            class="kb-search"
            type="text"
            placeholder="搜索知识点…"
            :value="searchQuery"
            confirm-type="search"
            @input="onSearchInput"
          />
          <text class="kb-expand-btn" @tap="toggleExpandAll">
            {{ allExpanded ? '折叠全部' : '展开全部' }}
          </text>
        </view>

        <view v-if="loading" class="empty">加载中...</view>
        <view v-else-if="current" class="tree-body">
          <KnowledgeTree
            :nodes="displayNodes"
            :expand-all="effectiveExpandAll"
            @node-tap="onNodeTap"
          />
        </view>
        <view v-else class="empty">暂无大纲数据</view>
      </view>

      <view v-else class="map-pane">
        <MarkmapView v-if="isH5 && mapDetail?.tree" :tree="mapDetail.tree" />
        <view v-if="isH5" class="map-pic-label">图片版（可双指缩放）</view>
        <MapSegmentList :manifest="mapDetail?.manifest" />
      </view>
    </view>

    <nut-popup v-model:visible="popupVisible" position="bottom" round :closeable="true">
      <view v-if="activeNode" class="node-popup">
        <text class="np-title">{{ activeNode.title }}</text>
        <text class="np-path">{{ formatPath(activeNode.path) }}</text>

        <view v-if="activeNode.content" class="np-content">
          <text class="np-content-text">{{ activeNode.content }}</text>
        </view>
        <view v-else class="np-content np-empty">
          <text class="np-content-text">暂无知识要点，可添加备注</text>
        </view>

        <view v-if="activeNode.myNote" class="np-note">
          <text class="np-note-label">我的备注</text>
          <text class="np-note-text">{{ activeNode.myNote }}</text>
        </view>

        <text class="np-edit-note" @tap="editNote">编辑备注</text>

        <view class="np-actions">
          <nut-button plain type="warning" :loading="answering" @click="onAnswer('again')">
            模糊
          </nut-button>
          <nut-button type="primary" :loading="answering" @click="onAnswer('good')">
            记住了
          </nut-button>
        </view>
      </view>
    </nut-popup>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton, Popup as NutPopup } from '@nutui/nutui-taro'
import KnowledgeTree from '@/components/KnowledgeTree.vue'
import MapSegmentList from '@/components/knowledge/MapSegmentList.vue'
import MarkmapView from '@/components/knowledge/MarkmapView'
import { useKnowledgeStore } from '@/store/knowledge'
import { promptText, showToast } from '@/utils/platform'
import { resolveMediaUrl } from '@/utils/media'
import type { KnowledgeNode, KnowledgeReviewResult } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '知识框架' })

const { themeClass } = useThemeClass()
const router = useRouter()
const kbStore = useKnowledgeStore()
const currentKey = ref('')
const searchQuery = ref('')
const allExpanded = ref(false)
const viewMode = ref<'outline' | 'map'>('outline')
const isH5 = process.env.TARO_ENV === 'h5'

const popupVisible = ref(false)
const activeNode = ref<KnowledgeNode | null>(null)
const answering = ref(false)

const maps = computed(() => kbStore.maps)
const mapDetail = computed(() => kbStore.mapDetail)
const current = computed(() => kbStore.current)
const loading = computed(() => kbStore.loading)
const currentTitle = computed(
  () => maps.value.find((m) => m.treeKey === currentKey.value)?.title || currentKey.value,
)

const effectiveExpandAll = computed<boolean>(() => {
  if (searchQuery.value.trim()) return true
  return allExpanded.value
})

const displayNodes = computed(() => {
  if (!current.value) return []
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return current.value.nodes
  return filterTree(current.value.nodes, q)
})

function filterTree(nodes: KnowledgeNode[], q: string): KnowledgeNode[] {
  const result: KnowledgeNode[] = []
  for (const node of nodes) {
    const selfMatch = node.title.toLowerCase().includes(q)
    const kids = node.children || []
    const filteredKids = filterTree(kids, q)
    if (selfMatch || filteredKids.length) {
      result.push({ ...node, children: selfMatch ? node.children : filteredKids })
    }
  }
  return result
}

const progress = computed(() => {
  if (!current.value) return { known: 0, fuzzy: 0, fresh: 0 }
  let known = 0
  let fuzzy = 0
  let fresh = 0
  const walk = (nodes: KnowledgeNode[]) => {
    for (const n of nodes) {
      if (!n.lastReviewedAt) fresh++
      else if (n.masteryLevel === 'again') fuzzy++
      else known++
      if (n.children) walk(n.children)
    }
  }
  walk(current.value.nodes)
  return { known, fuzzy, fresh }
})

function formatPath(path: string): string {
  if (!path) return ''
  return path.replace(/\//g, ' / ')
}

async function load() {
  await kbStore.fetchMaps()
  const fromQuery = router.params?.treeKey ? decodeURIComponent(router.params.treeKey) : ''
  if (fromQuery) {
    await onSelect(fromQuery)
  }
}

async function onSelect(key: string) {
  currentKey.value = key
  searchQuery.value = ''
  allExpanded.value = false
  viewMode.value = 'outline'
  await Promise.all([kbStore.fetchTree(key), kbStore.fetchMap(key)])
}

function backToList() {
  currentKey.value = ''
  kbStore.mapDetail = null
  kbStore.current = null
}

function onSearchInput(e: { detail: { value: string } }) {
  searchQuery.value = e.detail.value
}

function toggleExpandAll() {
  allExpanded.value = !allExpanded.value
}

function onNodeTap(node: KnowledgeNode) {
  activeNode.value = node
  popupVisible.value = true
}

async function onAnswer(result: KnowledgeReviewResult) {
  if (!activeNode.value || answering.value) return
  answering.value = true
  try {
    const r = await kbStore.answerNode(activeNode.value.id, result)
    if (r.code === 0) {
      showToast(result === 'good' ? '已标记掌握' : '已加入复习', 'success')
      popupVisible.value = false
      activeNode.value = null
    } else {
      showToast(r.message || '提交失败', 'error')
    }
  } finally {
    answering.value = false
  }
}

async function editNote() {
  if (!activeNode.value) return
  const content = await promptText('节点备注', {
    placeholder: '给这个知识点加一句自己的笔记...',
    defaultValue: activeNode.value.myNote || '',
  })
  if (content === null) return
  const r = await kbStore.updateNode(activeNode.value.id, { myNote: content })
  if (r.code === 0) {
    showToast('已保存', 'success')
    if (activeNode.value) activeNode.value.myNote = content
  } else {
    showToast(r.message || '保存失败', 'error')
  }
}

function goQuiz() {
  Taro.navigateTo({ url: '/pages/review/quiz' })
}

onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-knowledge {
  @include page-padding;
  padding-bottom: 40px;
}

.map-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.map-card {
  @include card;
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: $radius-lg;
}
.map-cover {
  width: 88px;
  height: 66px;
  border-radius: 8px;
  background: $page-bg;
  flex-shrink: 0;
}
.map-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}
.map-title {
  font-size: 16px;
  font-weight: 700;
  color: $text-primary;
}
.map-sub {
  font-size: 12px;
  color: $text-muted;
}

.kb-header {
  margin-bottom: 12px;
  .kb-header-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .kb-back {
    flex-shrink: 0;
    font-size: 13px;
    color: $accent-blue;
  }
  .kb-tip {
    flex: 1;
    font-size: 15px;
    font-weight: 600;
    color: $text-primary;
  }
  .kb-quiz {
    flex-shrink: 0;
    font-size: 13px;
    font-weight: 600;
    color: $primary-color;
    padding: 4px 10px;
    border-radius: 8px;
    background: $primary-light;
  }
}

.kb-stats {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  .kb-stat {
    font-size: 12px;
    font-weight: 500;
    &.known {
      color: $success;
    }
    &.fuzzy {
      color: $accent-amber;
    }
    &.fresh {
      color: $text-muted;
    }
  }
}

.seg-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.seg-tab {
  padding: 6px 16px;
  border-radius: 8px;
  font-size: 13px;
  background: $card-bg;
  color: $text-secondary;
  box-shadow: $shadow-card;
  &.active {
    background: $primary-color;
    color: #fff;
    font-weight: 600;
  }
}

.kb-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.kb-search {
  flex: 1;
  height: 34px;
  padding: 0 12px;
  font-size: 13px;
  background: $card-bg;
  border-radius: $radius-md;
  box-shadow: $shadow-card;
}

.kb-expand-btn {
  flex-shrink: 0;
  font-size: 12px;
  color: $accent-blue;
  padding: 4px 0;
}

.tree-body {
  @include card;
  padding: 14px 16px;
  border-radius: $radius-lg;
}

.map-pane {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.map-pic-label {
  font-size: 12px;
  color: $text-muted;
  margin-top: 4px;
}

.empty {
  text-align: center;
  color: $text-muted;
  padding: 40px 0;
  font-size: 14px;
}

.node-popup {
  padding: 20px 20px calc(20px + env(safe-area-inset-bottom));
  max-height: 70vh;
  overflow-y: auto;
}

.np-title {
  display: block;
  font-size: 17px;
  font-weight: 700;
  color: $text-primary;
  line-height: 1.4;
}

.np-path {
  display: block;
  font-size: 12px;
  color: $text-muted;
  margin-top: 4px;
  margin-bottom: 14px;
}

.np-content {
  background: $page-bg;
  border-radius: $radius-md;
  padding: 12px 14px;
  margin-bottom: 12px;
}

.np-content-text {
  font-size: 14px;
  color: $text-primary;
  line-height: 1.7;
  white-space: pre-wrap;
}

.np-empty .np-content-text {
  color: $text-muted;
  font-size: 13px;
}

.np-note {
  background: rgba($accent-blue, 0.06);
  border-radius: $radius-md;
  padding: 10px 14px;
  margin-bottom: 8px;
}

.np-note-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: $accent-blue;
  margin-bottom: 4px;
}

.np-note-text {
  font-size: 13px;
  color: $text-secondary;
  line-height: 1.6;
  white-space: pre-wrap;
}

.np-edit-note {
  display: inline-block;
  font-size: 12px;
  color: $accent-blue;
  margin-bottom: 16px;
}

.np-actions {
  display: flex;
  gap: 12px;
  :deep(.nut-button) {
    flex: 1;
  }
}
</style>
