<template>
  <page-meta
    v-if="isWeapp"
    :page-style="pageMeta.pageStyle"
    :background-color="pageMeta.backgroundColor"
    :background-color-top="pageMeta.backgroundColorTop"
    :background-color-bottom="pageMeta.backgroundColorBottom"
    :background-text-style="pageMeta.backgroundTextStyle"
  />
  <view class="page" :class="themeClass">
    <view v-if="loading" class="state">加载中…</view>
    <view v-else-if="!items.length" class="state">今天还没有已确认的金句</view>
    <QuoteRow v-for="item in items" :key="item.id" :item="item" @tap="open" />
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api } from '@/api'
import QuoteRow from '@/components/QuoteRow.vue'
import type { DailyQuoteCard } from '@/types'
import { useThemeClass, usePageMeta } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '金句素材' })

const { themeClass } = useThemeClass()
const pageMeta = usePageMeta()
const isWeapp = process.env.TARO_ENV === 'weapp'
const items = ref<DailyQuoteCard[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.getQuotes()
    if (res.code === 0 && res.data) items.value = res.data
  } finally {
    loading.value = false
  }
})

function open(id: string) {
  Taro.navigateTo({ url: `/pages/quotes/detail?id=${id}` })
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
.page { @include page-padding; padding-bottom: 32px; }
.state { text-align: center; color: $text-muted; padding: 40px 0; }
</style>
