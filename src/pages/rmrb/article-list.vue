<template>
  <view class="page-rmrb-list" :class="themeClass">
    <text class="hint">先读原文，读完后在文末进入时评解析。</text>

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
      <text class="empty-desc">请管理员在后台「时评精拆」发布文章</text>
    </view>
    <view v-else class="list">
      <ArticleCard
        v-for="article in cards"
        :key="article.id"
        :article="article"
        @tap="goDetail"
      />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import ArticleCard from '@/components/ArticleCard.vue'
import { api } from '@/api'
import type { RmrbArticle } from '@/types'
import { rmrbToCard } from '@/utils/rmrbCard'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '时评原文' })

const { themeClass } = useThemeClass()
const loading = ref(false)
const allList = ref<RmrbArticle[]>([])
const activeTag = ref('')

const list = computed(() => {
  if (!activeTag.value) return allList.value
  return allList.value.filter((a) => (a.tags || []).includes(activeTag.value))
})

const cards = computed(() => list.value.map(rmrbToCard))

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
  display: block;
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
}

.list { display: flex; flex-direction: column; }
</style>
