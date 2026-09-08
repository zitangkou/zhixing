<template>
  <view class="page-rmrb-list" :class="themeClass">
    <view class="hint">只收录评论/人民时评。按主题归类，读完后可「三刀解剖」写入开采本。</view>

    <scroll-view v-if="tagOptions.length" class="tag-scroll" scroll-x :show-scrollbar="false">
      <view class="tag-row">
        <text
          class="tag-chip"
          :class="{ on: !activeTag }"
          @tap="setTag('')"
        >全部</text>
        <text
          v-for="t in tagOptions"
          :key="t"
          class="tag-chip"
          :class="{ on: activeTag === t }"
          @tap="setTag(t)"
        >{{ t }}</text>
      </view>
    </scroll-view>

    <view v-if="loading" class="empty">加载中...</view>
    <view v-else-if="!list.length" class="empty">
      <text class="empty-title">{{ activeTag ? `暂无「${activeTag}」时评` : '暂无时评' }}</text>
      <text class="empty-desc">请管理员在后台「人民日报」中发布并打上主题标签</text>
      <nut-button size="small" type="primary" class="mt" @click="goPaste">粘贴开采</nut-button>
    </view>
    <view v-else class="list">
      <view v-for="a in list" :key="a.id" class="card" @tap="goDetail(a.id)">
        <view class="row">
          <text class="source">{{ a.source || '人民时评' }}</text>
          <text class="date">{{ a.publishDate }}</text>
        </view>
        <text class="title">{{ a.title }}</text>
        <view v-if="a.tags?.length" class="tags">
          <text v-for="t in a.tags" :key="t" class="tag">{{ t }}</text>
        </view>
        <text v-if="a.summary" class="summary">{{ a.summary }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import { api } from '@/api'
import type { RmrbArticle } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '时评阅读' })

const { themeClass } = useThemeClass()
const loading = ref(false)
const allList = ref<RmrbArticle[]>([])
const activeTag = ref('')

const list = computed(() => {
  if (!activeTag.value) return allList.value
  return allList.value.filter((a) => (a.tags || []).includes(activeTag.value))
})

const tagOptions = computed(() => {
  const set = new Set<string>()
  for (const a of allList.value) {
    for (const t of a.tags || []) set.add(t)
  }
  return Array.from(set)
})

async function load() {
  loading.value = true
  try {
    const res = await api.listRmrbArticles()
    if (res.code === 0 && res.data) {
      allList.value = res.data.map((a) => ({ ...a, tags: a.tags || [] }))
    }
  } finally {
    loading.value = false
  }
}

function setTag(t: string) {
  activeTag.value = t
}

function goDetail(id: string) {
  Taro.navigateTo({ url: `/pages/rmrb/article-detail?id=${id}` })
}

function goPaste() {
  Taro.navigateTo({ url: '/pages/rmrb/mine-edit' })
}

onMounted(load)
useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-rmrb-list {
  @include page-padding;
  padding-bottom: 40px;
}

.hint {
  font-size: 12px;
  color: $text-muted;
  margin-bottom: 12px;
  line-height: 1.5;
}

.tag-scroll {
  margin-bottom: 12px;
  white-space: nowrap;
}

.tag-row {
  display: inline-flex;
  gap: 8px;
  padding-bottom: 2px;
}

.tag-chip {
  display: inline-block;
  padding: 6px 12px;
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

.empty {
  text-align: center;
  padding: 48px 16px;
  color: $text-muted;
  .empty-title { display: block; font-size: 15px; color: $text-primary; margin-bottom: 6px; }
  .empty-desc { font-size: 13px; line-height: 1.5; display: block; }
  .mt { margin-top: 16px; }
}

.list { display: flex; flex-direction: column; gap: 10px; }

.card {
  @include card;
  padding: 14px;
  .row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
    .source { font-size: 12px; color: $primary-color; }
    .date { font-size: 12px; color: $text-muted; }
  }
  .title { display: block; font-size: 16px; font-weight: 700; line-height: 1.4; margin-bottom: 6px; }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 6px;
    .tag {
      font-size: 11px;
      color: $primary-color;
      background: $primary-light;
      padding: 2px 8px;
      border-radius: 4px;
    }
  }
  .summary { font-size: 13px; color: $text-secondary; line-height: 1.45; display: block; }
}
</style>
