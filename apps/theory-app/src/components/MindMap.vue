<template>
  <view class="mind-map">
    <view v-for="node in nodes" :key="node.id" class="tree-node">
      <view class="node-header" @tap="toggle(node.id)">
        <text class="arrow" :class="{ open: isOpen(node.id) }"> ▶ </text>
        <text class="node-title">
          {{ node.title }}
        </text>
      </view>
      <view v-if="node.content && isOpen(node.id)" class="node-content">
        {{ node.content }}
      </view>
      <view v-if="node.children && isOpen(node.id)" class="children">
        <MindMap :nodes="node.children" />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { MindMapNode } from '@/types'

defineOptions({ name: 'MindMap' })

const props = withDefaults(defineProps<{ nodes: MindMapNode[]; defaultOpen?: boolean }>(), {
  defaultOpen: true,
})

const openSet = ref<Set<string>>(new Set(props.defaultOpen ? props.nodes.map((n) => n.id) : []))

function toggle(id: string) {
  if (openSet.value.has(id)) openSet.value.delete(id)
  else openSet.value.add(id)
}

function isOpen(id: string) {
  return openSet.value.has(id)
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.mind-map {
  .tree-node {
    margin-bottom: 4px;
    .node-header {
      display: flex;
      align-items: center;
      padding: 10px 12px;
      background: $card-bg;
      border-left: 3px solid $primary-color;
      border-radius: 0 6px 6px 0;
      .arrow {
        font-size: 10px;
        margin-right: 8px;
        transition: transform 0.2s;
        color: $primary-color;
        &.open {
          transform: rotate(90deg);
        }
      }
      .node-title {
        font-size: 14px;
        font-weight: 500;
      }
    }
    .node-content {
      padding: 10px 16px 10px 28px;
      font-size: 13px;
      color: $text-secondary;
      line-height: 1.6;
      background: $primary-light;
      border-radius: 0 0 6px 6px;
    }
    .children {
      padding-left: 16px;
      margin-top: 4px;
    }
  }
}
</style>

