<template>
  <view class="knowledge-page" :class="themeClass">
    <view class="hero">
      <text class="hero-kicker">杜衡阁 · 知识框架</text>
      <text class="hero-title">{{ currentKey ? currentTitle : '看清知识结构' }}</text>
      <text class="hero-desc">
        {{
          root?.description || '按分类逐层浏览，找到知识点所在的位置。'
        }}
      </text>
      <view v-if="root" class="hero-stats">
        <text>{{ root.children?.length || 0 }} 个一级分类</text>
        <text>{{ mapDetail?.version ? `已发布 v${mapDetail.version}` : '' }}</text>
      </view>
    </view>

    <view v-if="!currentKey" class="body">
      <view v-if="loading && !maps.length" class="state">加载中…</view>
      <view v-else-if="loadError" class="state" @tap="refresh">{{ loadError }}，点击重试</view>
      <view v-else-if="!maps.length" class="state">暂无已发布的知识框架</view>
      <view v-for="item in maps" :key="item.treeKey" class="row" @tap="selectTree(item.treeKey)">
        <view class="row-main">
          <text class="row-title">{{ item.title }}</text>
          <text class="row-meta">{{ item.nodeCount }} 个知识节点</text>
        </view>
        <text class="arrow">›</text>
      </view>
    </view>

    <view v-else class="body">
      <view class="crumbs">
        <text class="crumb-link" @tap="backToTrees">科目</text>
        <text class="crumb-sep">›</text>
        <text
          v-for="(item, index) in breadcrumbs"
          :key="item.id"
          class="crumb-link"
          @tap="index === 0 ? goHome() : enterNode(item)"
        >
          {{ item.title
          }}<text v-if="index < breadcrumbs.length - 1" class="crumb-sep"> › </text>
        </text>
      </view>

      <view v-if="loading && !root" class="state">加载中…</view>
      <view v-else-if="!root" class="state" @tap="selectTree(currentKey)">
        {{ loadError || '暂无知识结构' }}，点击重试
      </view>
      <template v-else>
        <view class="mode-tabs">
          <text :class="{ active: mode === 'directory' }" @tap="mode = 'directory'">逐层浏览</text>
          <text :class="{ active: mode === 'overview' }" @tap="mode = 'overview'">结构总览</text>
        </view>

        <template v-if="mode === 'directory'">
          <view class="search-box">
            <text class="search-symbol">⌕</text>
            <input :value="query" placeholder="搜索当前科目的知识节点" @input="onSearch" />
          </view>
          <template v-if="query.trim()">
            <text class="section-title">搜索结果 · {{ searchResults.length }}</text>
            <view v-if="!searchResults.length" class="state">没有找到相关知识点</view>
            <view v-for="node in searchResults" :key="node.id" class="row" @tap="enterNode(node)">
              <view class="row-main">
                <text class="row-title">{{ node.title }}</text>
                <text class="row-meta">{{ node.path.replace(/\//g, ' / ') }}</text>
              </view>
              <text class="arrow">›</text>
            </view>
          </template>
          <template v-else-if="isHome">
            <view class="notice">先看分类之间的关系，再进入具体知识点。</view>
            <view v-for="group in rootGroups" :key="group.title" class="group">
              <text v-if="rootGroups.length > 1" class="section-title">{{ group.title }}</text>
              <view v-for="node in group.nodes" :key="node.id" class="row" @tap="enterNode(node)">
                <view class="row-main">
                  <text class="row-title">{{ node.title }}</text>
                  <text class="row-meta">
                    {{ descendantCount(node) }} 个下级节点 · {{ childPreview(node) }}
                  </text>
                </view>
                <text class="arrow">›</text>
              </view>
            </view>
          </template>
          <template v-else>
            <text class="branch-title">{{ selected?.title }}</text>
            <text class="branch-meta">
              {{ selected?.children?.length || 0 }} 个直接分支 ·
              {{ selected ? descendantCount(selected) : 0 }} 个下级节点
            </text>
            <view
              v-if="selected && hasDetails(selected)"
              class="detail-link"
              @tap="openDetails(selected)"
            >
              查看这个知识点的内容 ›
            </view>
            <view
              v-for="(node, index) in selected?.children || []"
              :key="node.id"
              class="row"
              @tap="enterNode(node)"
            >
              <text class="index">{{ String(index + 1).padStart(2, '0') }}</text>
              <view class="row-main">
                <text class="row-title">{{ node.title }}</text>
                <text class="row-meta">
                  {{
                    node.children?.length
                      ? `${node.children.length} 个直接分支 · ${descendantCount(node)} 个下级节点`
                      : '查看知识节点'
                  }}
                </text>
              </view>
              <text class="arrow">›</text>
            </view>
          </template>
        </template>

        <template v-else>
          <text class="section-title">{{ currentTitle }}结构总览</text>
          <text class="overview-tip">只展示前两层。点击分类可继续逐层浏览。</text>
          <view v-for="node in root.children || []" :key="node.id" class="overview-card">
            <view class="overview-title" @tap="enterNode(node)">
              <text>{{ node.title }}</text><text class="overview-count">{{ descendantCount(node) }} 个下级节点 ›</text>
            </view>
            <view class="chips">
              <text
                v-for="child in node.children || []"
                :key="child.id"
                class="chip"
                @tap="enterNode(child)"
              >
                {{ child.title }}
              </text>
            </view>
          </view>
        </template>
      </template>
    </view>

    <nut-popup v-model:visible="detailsVisible" position="bottom" round :closeable="true">
      <view class="detail-sheet">
        <text class="detail-kicker">知识节点</text>
        <text class="detail-title">{{ detailNode?.title }}</text>
        <text class="detail-path">{{ detailNode?.path.replace(/\//g, ' / ') }}</text>
        <template v-if="detailBlocks.length">
          <view v-for="(block, index) in detailBlocks" :key="index" class="content-block">
            <text v-if="block.type === 'text'" class="block-text">{{ block.text }}</text>
            <view v-else-if="block.type === 'formula'" class="formula-box">
              <LatexBlock :latex="block.latex" :plain="block.plain" :show-plain="true" />
            </view>
            <view v-else-if="block.type === 'image'" @tap="previewImage(block.url)">
              <image class="block-image" :src="resolveMediaUrl(block.url)" mode="widthFix" />
              <text v-if="block.alt" class="block-caption">{{ block.alt }}</text>
            </view>
            <view v-else-if="block.type === 'example'">
              <text class="block-label">例题</text><text class="block-text">{{ block.question }}</text>
              <text v-if="block.answer" class="block-label answer-label">解析</text><text v-if="block.answer" class="block-text">{{ block.answer }}</text>
            </view>
          </view>
        </template>
        <text v-else class="empty-detail">当前只有知识结构，讲解和例题待补充。</text>
      </view>
    </nut-popup>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow, usePullDownRefresh, useRouter } from '@tarojs/taro'
import { Popup as NutPopup } from '@nutui/nutui-taro'
import LatexBlock from '@/components/LatexBlock.vue'
import { useKnowledgeStore } from '@/store/knowledge'
import { resolveMediaUrl } from '@/utils/media'
import { showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'
import type { KnowledgeContentBlock, KnowledgeMapNode } from '@/types'

definePageConfig({ navigationBarTitleText: '知识框架', enablePullDownRefresh: true })

const { themeClass } = useThemeClass()
const router = useRouter()
const store = useKnowledgeStore()
const maps = computed(() => store.maps)
const mapDetail = computed(() => store.mapDetail)
const root = computed(() => mapDetail.value?.tree || null)
const loading = computed(() => store.loading)
const currentKey = ref('')
const nodeId = ref('')
const mode = ref<'directory' | 'overview'>('directory')
const query = ref('')
const detailsVisible = ref(false)
const detailNode = ref<KnowledgeMapNode | null>(null)
const pageReady = ref(false)
const loadError = ref('')
const currentTitle = computed(
  () =>
    maps.value.find((m) => m.treeKey === currentKey.value)?.title ||
    mapDetail.value?.title ||
    currentKey.value,
)

const nodeMap = computed(() => {
  const found = new Map<string, KnowledgeMapNode>()
  const walk = (node: KnowledgeMapNode) => {
    found.set(node.id, node)
    ;(node.children || []).forEach(walk)
  }
  if (root.value) walk(root.value)
  return found
})
const selected = computed(() => nodeMap.value.get(nodeId.value) || root.value)
const isHome = computed(() => !root.value || selected.value?.id === root.value.id)
const breadcrumbs = computed(() => {
  if (!root.value) return []
  const parts = [root.value]
  if (!isHome.value && selected.value) {
    const find = (node: KnowledgeMapNode, trail: KnowledgeMapNode[]): KnowledgeMapNode[] | null => {
      if (node.id === selected.value?.id) return trail
      for (const child of node.children || []) {
        const found = find(child, [...trail, child])
        if (found) return found
      }
      return null
    }
    parts.push(...(find(root.value, []) || []))
  }
  return parts
})
const allNodes = computed(() => [...nodeMap.value.values()].filter((n) => n.id !== root.value?.id))
const searchResults = computed(() =>
  allNodes.value
    .filter((n) => n.title.toLowerCase().includes(query.value.trim().toLowerCase()))
    .slice(0, 80),
)
const rootGroups = computed(() => {
  const children = root.value?.children || []
  const groups = root.value?.groups || []
  if (!groups.length) return [{ title: '全部分类', nodes: children }]
  const used = new Set<string>()
  const out = groups
    .map((group) => ({
      title: group.title,
      nodes: group.nodeIds
        .map((id) => children.find((n) => n.id === id))
        .filter((n): n is KnowledgeMapNode => !!n)
        .filter((n) => {
          used.add(n.id)
          return true
        }),
    }))
    .filter((group) => group.nodes.length)
  const rest = children.filter((n) => !used.has(n.id))
  if (rest.length) out.push({ title: '其他分类', nodes: rest })
  return out
})
const detailBlocks = computed<KnowledgeContentBlock[]>(() => {
  if (!detailNode.value) return []
  if (detailNode.value.blocks?.length) return detailNode.value.blocks
  return detailNode.value.content?.trim() ? [{ type: 'text', text: detailNode.value.content }] : []
})

function descendantCount(node: KnowledgeMapNode): number {
  return (node.children || []).reduce((sum, child) => 1 + sum + descendantCount(child), 0)
}
function childPreview(node: KnowledgeMapNode): string {
  return (
    (node.children || [])
      .slice(0, 3)
      .map((n) => n.title)
      .join(' / ') || '查看知识节点'
  )
}
function hasDetails(node: KnowledgeMapNode): boolean {
  return !!node.blocks?.length || !!node.content?.trim()
}
function onSearch(event: { detail: { value: string } }) {
  query.value = event.detail.value
}
function goHome() {
  nodeId.value = root.value?.id || ''
  mode.value = 'directory'
  query.value = ''
}
function backToTrees() {
  currentKey.value = ''
  nodeId.value = ''
  query.value = ''
  store.mapDetail = null
}
function enterNode(node: KnowledgeMapNode) {
  if (node.children?.length) {
    nodeId.value = node.id
    mode.value = 'directory'
    query.value = ''
  } else openDetails(node)
}
function openDetails(node: KnowledgeMapNode) {
  detailNode.value = node
  detailsVisible.value = true
}
function previewImage(url: string) {
  const resolved = resolveMediaUrl(url)
  Taro.previewImage({ urls: [resolved], current: resolved })
}
async function selectTree(key: string) {
  loadError.value = ''
  store.mapDetail = null
  currentKey.value = key
  query.value = ''
  mode.value = 'directory'
  nodeId.value = ''
  try {
    await store.fetchMap(key)
    nodeId.value = store.mapDetail?.tree.id || ''
  } catch {
    loadError.value = '知识框架加载失败'
    showToast(loadError.value, 'error')
  }
}
async function refresh() {
  loadError.value = ''
  try {
    await store.fetchMaps()
    if (currentKey.value) {
      if (!store.maps.some((m) => m.treeKey === currentKey.value)) {
        backToTrees()
        return
      }
      const priorId = selected.value?.id
      await store.fetchMap(currentKey.value)
      const same = priorId ? nodeMap.value.get(priorId) : null
      nodeId.value = same?.id || root.value?.id || ''
    }
  } catch {
    loadError.value = '知识框架加载失败'
    showToast(loadError.value, 'error')
  }
}
onMounted(async () => {
  await refresh()
  pageReady.value = true
  const key = router.params?.treeKey
  if (key && maps.value.some((m) => m.treeKey === key)) await selectTree(key)
})
useDidShow(() => {
  if (pageReady.value) void refresh()
})
usePullDownRefresh(async () => {
  try {
    await refresh()
  } finally {
    Taro.stopPullDownRefresh()
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
.knowledge-page {
  min-height: 100vh;
  background: $page-bg;
  color: $text-primary;
  padding-bottom: 28px;
}
.hero {
  display: flex;
  flex-direction: column;
  gap: 9px;
  background: linear-gradient(155deg, $primary-color, $primary-dark);
  color: var(--zk-on-primary);
  padding: 26px 20px 24px;
  border-radius: 0 0 22px 22px;
}
.hero-kicker {
  font-size: 12px;
  opacity: 0.85;
}
.hero-title {
  font-size: 25px;
  font-weight: 750;
}
.hero-desc {
  font-size: 13px;
  line-height: 1.6;
  opacity: 0.92;
}
.hero-stats {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  font-size: 12px;
  opacity: 0.9;
}
.body {
  padding: 18px 16px;
}
.state {
  padding: 34px 12px;
  text-align: center;
  color: $text-muted;
  font-size: 13px;
}
.row {
  display: flex;
  align-items: center;
  gap: 12px;
  background: $card-bg;
  border: 1px solid $border-color;
  border-radius: 14px;
  padding: 15px 13px;
  margin-bottom: 9px;
  box-shadow: $shadow-card;
}
.row-main {
  flex: 1;
  min-width: 0;
}
.row-title {
  display: block;
  font-size: 15px;
  font-weight: 650;
  line-height: 1.4;
  word-break: break-word;
}
.row-meta {
  display: block;
  color: $text-muted;
  font-size: 12px;
  line-height: 1.5;
  margin-top: 5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.arrow {
  color: $text-muted;
  font-size: 21px;
}
.crumbs {
  display: flex;
  align-items: center;
  gap: 5px;
  overflow-x: auto;
  white-space: nowrap;
  margin: 0 0 14px;
  font-size: 12px;
}
.crumb-link {
  color: $primary-color;
}
.crumb-sep {
  color: $text-muted;
  margin: 0 3px;
}
.mode-tabs {
  display: flex;
  background: $card-bg;
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 16px;
}
.mode-tabs text {
  flex: 1;
  text-align: center;
  color: $text-muted;
  padding: 9px 0;
  font-size: 13px;
}
.mode-tabs .active {
  color: $primary-color;
  background: $primary-light;
  border-radius: 9px;
  font-weight: 700;
}
.search-box {
  height: 43px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: $card-bg;
  border: 1px solid $border-color;
  border-radius: 11px;
  padding: 0 12px;
  margin-bottom: 16px;
}
.search-box input {
  flex: 1;
  font-size: 13px;
  color: $text-primary;
}
.search-symbol {
  font-size: 19px;
  color: $text-muted;
}
.notice {
  padding: 12px;
  border-left: 3px solid $primary-color;
  background: $card-bg;
  color: $text-secondary;
  font-size: 12px;
  line-height: 1.6;
  border-radius: 10px;
  margin-bottom: 18px;
}
.section-title {
  display: block;
  font-size: 16px;
  font-weight: 700;
  margin: 18px 2px 11px;
}
.group:first-child .section-title {
  margin-top: 0;
}
.branch-title {
  display: block;
  font-size: 22px;
  font-weight: 750;
  line-height: 1.4;
}
.branch-meta {
  display: block;
  color: $text-secondary;
  font-size: 13px;
  margin: 7px 0 18px;
}
.detail-link {
  color: $primary-color;
  background: $primary-light;
  padding: 12px;
  border-radius: 10px;
  font-size: 13px;
  margin-bottom: 13px;
}
.index {
  background: $elevated;
  color: $text-secondary;
  font-size: 12px;
  border-radius: 7px;
  padding: 5px;
}
.overview-tip {
  display: block;
  color: $text-secondary;
  font-size: 12px;
  line-height: 1.6;
  margin-bottom: 15px;
}
.overview-card {
  background: $card-bg;
  border: 1px solid $border-color;
  border-radius: 14px;
  padding: 14px;
  margin-bottom: 11px;
}
.overview-title {
  display: flex;
  justify-content: space-between;
  gap: 9px;
  font-size: 14px;
  font-weight: 700;
}
.overview-count {
  font-size: 11px;
  color: $text-muted;
  font-weight: 400;
  white-space: nowrap;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 12px;
}
.chip {
  background: $elevated;
  color: $text-secondary;
  font-size: 12px;
  line-height: 1.4;
  padding: 7px 9px;
  border-radius: 7px;
}
.detail-sheet {
  padding: 24px 20px 34px;
  max-height: 76vh;
  overflow-y: auto;
}
.detail-kicker {
  display: block;
  color: $primary-color;
  font-size: 12px;
}
.detail-title {
  display: block;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.4;
  margin: 9px 0;
}
.detail-path {
  display: block;
  color: $text-muted;
  font-size: 12px;
  line-height: 1.5;
}
.content-block {
  padding: 13px 0;
  border-bottom: 1px solid $border-color;
}
.block-text {
  display: block;
  color: $text-primary;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
}
.formula-box {
  background: $elevated;
  border-radius: 10px;
  padding: 12px;
}
.block-image {
  display: block;
  width: 100%;
  border-radius: 8px;
}
.block-caption {
  display: block;
  margin-top: 6px;
  color: $text-muted;
  font-size: 12px;
}
.block-label {
  display: block;
  color: $primary-color;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 7px;
}
.answer-label {
  margin-top: 14px;
}
.empty-detail {
  display: block;
  color: $text-muted;
  font-size: 13px;
  margin-top: 22px;
  line-height: 1.6;
}
</style>
