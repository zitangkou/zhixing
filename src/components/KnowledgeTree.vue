<template>
  <view class="kn-tree">
    <view v-for="node in nodes" :key="node.id" class="kn-node">
      <view
        class="kn-row"
        :class="{
          expanded: expandedMap[node.id],
          'has-children': hasChildren(node),
          starred: node.isStarred,
          'has-note': !!node.myNote,
        }"
        :style="{ paddingLeft: node.depth * 14 + 'px' }"
        @tap="onTap(node)"
        @longpress="onLongPress(node)"
      >
        <text v-if="hasChildren(node)" class="kn-arrow">
          {{ expandedMap[node.id] ? '▾' : '▸' }}
        </text>
        <text v-else class="kn-leaf-dot"> · </text>
        <view class="kn-status" :class="statusClass(node)" />
        <text v-if="node.isStarred" class="kn-star"> ★ </text>
        <text class="kn-title">
          {{ node.title }}
        </text>
        <text v-if="node.myNote" class="kn-note-icon"> ✎ </text>
      </view>
      <view v-if="hasChildren(node) && expandedMap[node.id]" class="kn-children">
        <KnowledgeTree
          :nodes="node.children || []"
          :expand-all="expandAll"
          @node-tap="onChildNodeTap"
        />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Taro from '@tarojs/taro'
import { useKnowledgeStore } from '@/store/knowledge'
import { promptText, showToast } from '@/utils/platform'
import type { KnowledgeNode } from '@/types'

const props = defineProps<{
  nodes: KnowledgeNode[]
  expandAll?: boolean
}>()

const emit = defineEmits<{
  (e: 'node-tap', node: KnowledgeNode): void
}>()

const kbStore = useKnowledgeStore()

// 共享展开状态（递归组件间）
const expandedMap = ref<Record<string, boolean>>({})

watch(
  () => props.nodes,
  (n) => {
    // 默认展开第一层
    for (const node of n) {
      if (node.depth === 0 && expandedMap.value[node.id] === undefined) {
        expandedMap.value[node.id] = true
      }
    }
  },
  { immediate: true },
)

// 外部控制全部展开/折叠
watch(
  () => props.expandAll,
  (val) => {
    if (val === undefined) return
    const next: Record<string, boolean> = {}
    for (const node of props.nodes) {
      if (hasChildren(node)) next[node.id] = val
    }
    expandedMap.value = next
  },
)

function hasChildren(node: KnowledgeNode) {
  return !!(node.children && node.children.length)
}

function statusClass(node: KnowledgeNode): string {
  if (!node.lastReviewedAt) return 'dot-new'
  if (node.masteryLevel === 'again') return 'dot-fuzzy'
  return 'dot-known'
}

function onTap(node: KnowledgeNode) {
  if (hasChildren(node)) {
    toggle(node.id)
  } else {
    emit('node-tap', node)
  }
}

function onChildNodeTap(node: KnowledgeNode) {
  emit('node-tap', node)
}

function toggle(id: string) {
  expandedMap.value = { ...expandedMap.value, [id]: !expandedMap.value[id] }
}

async function onLongPress(node: KnowledgeNode) {
  const actions = ['编辑备注', node.isStarred ? '取消重点' : '标重点']
  try {
    const { tapIndex } = await Taro.showActionSheet({ itemList: actions })
    if (tapIndex === 0) {
      const content = await promptText('节点备注', {
        placeholder: '给这个知识点加一句自己的笔记...',
        defaultValue: node.myNote || '',
      })
      if (content !== null) {
        const r = await kbStore.updateNode(node.id, { myNote: content })
        if (r.code === 0) showToast('已保存', 'success')
        else showToast(r.message || '保存失败', 'error')
      }
    } else if (tapIndex === 1) {
      const r = await kbStore.updateNode(node.id, { isStarred: !node.isStarred })
      if (r.code === 0) showToast(node.isStarred ? '已取消重点' : '已标重点', 'success')
    }
  } catch {
    // 用户取消
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.kn-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 0;
  font-size: 14px;
  line-height: 1.5;
  &:active {
    background: $page-bg;
  }
  &.starred .kn-title {
    color: $primary-color;
    font-weight: 600;
  }
}

.kn-arrow {
  flex-shrink: 0;
  width: 14px;
  color: $text-muted;
  text-align: center;
}

.kn-leaf-dot {
  flex-shrink: 0;
  width: 14px;
  color: $text-muted;
  text-align: center;
}

.kn-status {
  flex-shrink: 0;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  &.dot-new {
    background: #d1d5db;
  }
  &.dot-known {
    background: #22c55e;
  }
  &.dot-fuzzy {
    background: #f59e0b;
  }
}

.kn-star {
  flex-shrink: 0;
  color: $primary-color;
  font-size: 13px;
}

.kn-title {
  flex: 1;
  color: $text-primary;
}

.kn-note-icon {
  flex-shrink: 0;
  color: $accent-blue;
  font-size: 12px;
}

.kn-children {
  /* 递归渲染 */
}
</style>
