<template>
  <view class="page-mindmap" v-if="article" :class="themeClass">
    <text class="title">{{ article.mindMap.title }}</text>
    <scroll-view scroll-x scroll-y class="canvas-area" :scale-area="true">
      <view class="tree-wrapper" :style="{ transform: `scale(${scale})` }">
        <MindMap :nodes="article.mindMap.children || []" :default-open="true" />
      </view>
    </scroll-view>
    <view class="zoom-controls">
      <nut-button size="small" @click="zoomOut">－</nut-button>
      <text>{{ Math.round(scale * 100) }}%</text>
      <nut-button size="small" @click="zoomIn">＋</nut-button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Taro from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import MindMap from '@/components/MindMap.vue'
import { useArticleStore } from '@/store/article'
import type { Article } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '知识框架' })

const { themeClass } = useThemeClass()
const articleStore = useArticleStore()
const article = ref<Article | null>(null)
const scale = ref(1)

onMounted(async () => {
  const { id } = Taro.getCurrentInstance().router?.params || {}
  if (id) {
    article.value = (await articleStore.getArticleDetail(id)) || null
  }
})

function zoomIn() {
  scale.value = Math.min(scale.value + 0.1, 2)
}

function zoomOut() {
  scale.value = Math.max(scale.value - 0.1, 0.5)
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-mindmap {
  height: 100vh;
  display: flex;
  flex-direction: column;
  .title {
    padding: 16px;
    font-size: 17px;
    font-weight: 600;
    text-align: center;
    @include brand-gradient;
    color: #fff;
  }
  .canvas-area {
    flex: 1;
    padding: 16px;
    .tree-wrapper {
      min-width: 300px;
      transform-origin: top left;
      transition: transform 0.2s;
    }
  }
  .zoom-controls {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 16px;
    padding: 12px;
    background: $card-bg;
    border-top: 1px solid $border-color;
  }
}
</style>
