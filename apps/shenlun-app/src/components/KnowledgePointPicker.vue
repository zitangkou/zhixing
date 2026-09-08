<template>
  <view class="kb-picker">
    <view class="picker-trigger" @tap="open">
      <text v-if="displayLabel" class="picked">
        {{ displayLabel }}
      </text>
      <text v-else class="placeholder"> 点选知识框架考点（可选） </text>
      <text v-if="modelValue.path" class="clear" @tap.stop="clear"> 清除 </text>
      <text v-else class="arrow"> › </text>
    </view>

    <view v-if="visible" class="sheet-mask" @tap="close">
      <view class="sheet" @tap.stop>
        <view class="sheet-hd">
          <text class="sheet-title"> 选择考点 </text>
          <text class="sheet-close" @tap="close"> 关闭 </text>
        </view>

        <scroll-view scroll-x class="tree-tabs">
          <text
            v-for="t in trees"
            :key="t.treeKey"
            class="tab"
            :class="{ active: currentKey === t.treeKey }"
            @tap="selectTree(t.treeKey)"
          >
            {{ t.title }}
          </text>
        </scroll-view>

        <view v-if="loading" class="sheet-empty"> 加载中... </view>
        <scroll-view v-else scroll-y class="node-list">
          <view v-if="!flatNodes.length" class="sheet-empty">
            该知识树暂无节点，请先同步知识库
          </view>
          <view
            v-for="n in flatNodes"
            :key="n.id"
            class="node-row"
            :class="{ active: modelValue.nodeId === n.id }"
            :style="{ paddingLeft: 12 + n.depth * 12 + 'px' }"
            @tap="pick(n)"
          >
            <text class="node-mark">
              {{ n.hasChildren ? '▸' : '·' }}
            </text>
            <text class="node-title">
              {{ n.title }}
            </text>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '@/api'
import {
  flattenKnowledgeNodes,
  formatKnowledgeLabel,
  pickTreeForSubject,
  type FlatKnowledgeNode,
  type KnowledgePickValue,
} from '@/utils/knowledge'
import type { KnowledgeTree } from '@/types'

const props = defineProps<{
  modelValue: KnowledgePickValue
  subject?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [KnowledgePickValue]
}>()

const visible = ref(false)
const loading = ref(false)
const trees = ref<KnowledgeTree[]>([])
const currentKey = ref('')
const currentTree = ref<KnowledgeTree | null>(null)

const flatNodes = computed(() =>
  currentTree.value ? flattenKnowledgeNodes(currentTree.value) : [],
)

const displayLabel = computed(() => {
  if (!props.modelValue.path) return ''
  const t = trees.value.find((x) => x.treeKey === props.modelValue.treeKey)
  return formatKnowledgeLabel(props.modelValue.path, t?.title || props.modelValue.treeKey)
})

async function open() {
  visible.value = true
  loading.value = true
  try {
    const res = await api.getKnowledgeTrees()
    trees.value = res.code === 0 && res.data ? res.data : []
    const preferred = pickTreeForSubject(trees.value, props.subject || '')
    const key = preferred?.treeKey || trees.value[0]?.treeKey || ''
    if (key) await selectTree(key)
  } finally {
    loading.value = false
  }
}

async function selectTree(key: string) {
  currentKey.value = key
  loading.value = true
  try {
    const res = await api.getKnowledgeTree(key)
    currentTree.value = res.code === 0 && res.data ? res.data : null
  } finally {
    loading.value = false
  }
}

function pick(n: FlatKnowledgeNode) {
  emit('update:modelValue', {
    nodeId: n.id,
    treeKey: n.treeKey,
    path: n.path,
  })
  visible.value = false
}

function clear() {
  emit('update:modelValue', { nodeId: '', treeKey: '', path: '' })
}

function close() {
  visible.value = false
}

watch(
  () => props.subject,
  async (s) => {
    if (!visible.value || !trees.value.length) return
    const preferred = pickTreeForSubject(trees.value, s || '')
    if (preferred && preferred.treeKey !== currentKey.value) {
      await selectTree(preferred.treeKey)
    }
  },
)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.kb-picker {
  .picker-trigger {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    background: $elevated;
    border-radius: 8px;
    border: 1px solid $border-color;
    .picked {
      flex: 1;
      font-size: 13px;
      color: $primary-color;
      font-weight: 600;
      line-height: 1.4;
    }
    .placeholder {
      flex: 1;
      font-size: 13px;
      color: $text-muted;
    }
    .clear,
    .arrow {
      font-size: 12px;
      color: $text-muted;
      flex-shrink: 0;
    }
    .clear {
      color: $primary-color;
    }
  }
}

.sheet-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-end;
}

.sheet {
  width: 100%;
  max-height: 72vh;
  background: $card-bg;
  border-radius: 16px 16px 0 0;
  display: flex;
  flex-direction: column;
  padding-bottom: env(safe-area-inset-bottom);
}

.sheet-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 8px;
  .sheet-title {
    font-size: 16px;
    font-weight: 700;
    color: $text-primary;
  }
  .sheet-close {
    font-size: 13px;
    color: $text-muted;
  }
}

.tree-tabs {
  white-space: nowrap;
  padding: 4px 12px 8px;
  .tab {
    display: inline-block;
    margin-right: 8px;
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 12px;
    background: $elevated;
    color: $text-secondary;
    &.active {
      background: $primary-light;
      color: $primary-color;
      font-weight: 700;
    }
  }
}

.node-list {
  flex: 1;
  max-height: 52vh;
  padding-bottom: 12px;
}

.node-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-bottom: 1px solid $border-color;
  &.active {
    background: $primary-light;
    .node-title {
      color: $primary-color;
      font-weight: 700;
    }
  }
  .node-mark {
    color: $text-muted;
    font-size: 12px;
    width: 12px;
  }
  .node-title {
    font-size: 13px;
    color: $text-primary;
    line-height: 1.35;
  }
}

.sheet-empty {
  padding: 28px 16px;
  text-align: center;
  color: $text-muted;
  font-size: 13px;
}
</style>

