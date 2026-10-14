<template>
  <page-meta
    v-if="isWeapp"
    :page-style="pageMeta.pageStyle"
    :background-color="pageMeta.backgroundColor"
    :background-color-top="pageMeta.backgroundColorTop"
    :background-color-bottom="pageMeta.backgroundColorBottom"
    :background-text-style="pageMeta.backgroundTextStyle"
  />
  <view class="page-pick" :class="themeClass">
    <view v-if="loading" class="state-box">
      <text class="state-title">加载中…</text>
    </view>
    <view v-else-if="loadError" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ loadError }}</text>
      <view class="state-btn" @tap="load">点击重试</view>
    </view>
    <view v-else-if="!items.length" class="state-box">
      <text class="state-title">暂无时政要点</text>
      <text class="state-desc">后台发布后会出现在这里</text>
    </view>
    <template v-else>
      <TheoryPointRow v-for="item in items" :key="item.id" :item="item" @tap="goQuizById" />
    </template>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api } from '@/api'
import TheoryPointRow from '@/components/TheoryPointRow.vue'
import type { TheoryPointCard } from '@/types'
import { requireLogin, isLoggedIn } from '@/utils/auth'
import { showConfirm, showToast } from '@/utils/platform'
import { useThemeClass, usePageMeta } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '时政要点' })

const { themeClass } = useThemeClass()
const pageMeta = usePageMeta()
const isWeapp = process.env.TARO_ENV === 'weapp'
const items = ref<TheoryPointCard[]>([])
const loading = ref(true)
const loadError = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.getTheoryPoints()
    if (res.code === 0 && res.data) items.value = res.data
  } catch {
    loadError.value = '网络异常，请稍后重试'
  } finally {
    loading.value = false
  }
}

function goQuizById(id: string) {
  const item = items.value.find((row) => row.id === id)
    || items.value.flatMap((row) => row.sections || []).find((row) => row.id === id)
  if (item) void goQuiz(item)
}

async function goQuiz(item: TheoryPointCard) {
  if (!item.questionCount) {
    showToast('这套要点还没有题目')
    return
  }
  const url = `/pages/question/taking?theoryPointId=${item.id}`
  if (!isLoggedIn()) {
    const ok = await showConfirm('需要登录', '登录后才能保存练习进度与积分。', { confirmText: '去登录', cancelText: '再看看' })
    if (!ok) return
    requireLogin(url)
    return
  }
  Taro.navigateTo({ url })
}

onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-pick {
  @include page-padding;
  padding-bottom: 40px;
}
.state-box { text-align: center; padding: 48px 0; }
.state-title { display: block; font-size: 16px; color: $text-primary; }
.state-desc { display: block; margin-top: 6px; font-size: 13px; color: $text-muted; }
.state-btn { margin-top: 12px; color: $primary-color; }
</style>
