<template>
  <view class="zl-page" :class="themeClass">
    <view v-if="loading" class="zl-state-box"><text class="zl-state-title">加载中…</text></view>
    <view v-else-if="!list.length" class="zl-state-box"><text class="zl-state-title">暂无公式</text></view>
    <template v-else>
      <scroll-view scroll-x class="zl-filter-bar">
        <view
          v-for="cat in categories"
          :key="cat"
          class="zl-filter-chip"
          :class="{ 'zl-filter-chip-active': activeCat === cat }"
          @tap="activeCat = cat"
        >{{ cat }}</view>
      </scroll-view>
      <view class="zl-card-list">
        <view v-for="item in filteredList" :key="item.id" class="zl-card" @tap="go(item.id)">
          <view class="zl-card-head">
            <text class="zl-chip">{{ item.category || '公式' }}</text>
            <text class="zl-freq">★{{ item.examFreq }}</text>
          </view>
          <text class="zl-title">{{ item.name }}</text>
          <LatexBlock
            :latex="item.latex"
            :plain="item.formulaPlain"
            size="sm"
            :show-plain="false"
            :display-mode="false"
          />
        </view>
        <view v-if="!filteredList.length" class="zl-state-box">
          <text class="zl-state-title">该分类下暂无公式</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { usePullDownRefresh } from '@tarojs/taro'
import { api } from '@/api'
import LatexBlock from '@/components/LatexBlock.vue'
import type { ZiliaoFormula } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '公式库', enablePullDownRefresh: true })

const { themeClass } = useThemeClass()
const list = ref<ZiliaoFormula[]>([])
const loading = ref(true)
const activeCat = ref('全部')

const categories = computed(() => {
  const cats = new Set(list.value.map((f) => f.category || '公式'))
  return ['全部', ...Array.from(cats)]
})

const filteredList = computed(() => {
  if (activeCat.value === '全部') return list.value
  return list.value.filter((f) => (f.category || '公式') === activeCat.value)
})

function go(id: string) {
  Taro.navigateTo({ url: `/pages/ziliao/formula-detail?id=${id}` })
}

async function load() {
  const res = await api.listZiliaoFormulas()
  list.value = res.data || []
  loading.value = false
}

onMounted(load)

usePullDownRefresh(async () => {
  try {
    await load()
  } finally {
    Taro.stopPullDownRefresh()
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.zl-page {
  @include page-padding;
}
.zl-filter-bar {
  white-space: nowrap;
  margin-bottom: 12px;
}
.zl-filter-chip {
  display: inline-block;
  padding: 6px 14px;
  margin-right: 8px;
  border-radius: 20px;
  font-size: 13px;
  color: $text-secondary;
  background: $card-bg;
  border: 1px solid $border-color;
  transition: all 0.15s ease;
}
.zl-filter-chip-active {
  color: $primary-color;
  background: $primary-light;
  border-color: $primary-color;
  font-weight: 600;
}
.zl-card-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.zl-card {
  @include card;
  margin-bottom: 0;
}
.zl-card-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}
.zl-chip {
  @include brand-chip;
}
.zl-freq {
  font-size: 12px;
  color: $accent-amber;
}
.zl-title {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 8px;
}
.zl-state-box {
  @include page-state-box;
}
.zl-state-title {
  font-size: 14px;
  color: $text-muted;
}
</style>
