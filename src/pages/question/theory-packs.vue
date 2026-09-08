<template>
  <view class="page-packs" :class="themeClass">
    <text class="hint">纲要专项模拟套题。可练整卷 20 题，或按五题分辑作答。</text>
    <view v-if="loading" class="empty">加载中...</view>
    <view v-else-if="!packs.length" class="empty">暂无已发布的纲要专项卷，请管理员导入 T0c JSON</view>
    <view v-else>
      <view v-for="pack in packs" :key="pack.articleId" class="pack">
        <text class="title">{{ pack.title }}</text>
        <text class="desc">{{ pack.description }}</text>
        <view class="row" @tap="startFull(pack.articleId)">
          <text>整卷 {{ pack.questionCount }} 题</text>
          <text class="arrow">›</text>
        </view>
        <view
          v-for="part in pack.parts"
          :key="part.number"
          class="row"
          @tap="startPart(pack.articleId, part.number)"
        >
          <text>{{ part.title }} · {{ part.questionIds.length }} 题</text>
          <text class="arrow">›</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api } from '@/api'
import { useThemeClass } from '@/utils/brandColor'
import { showToast } from '@/utils/platform'

definePageConfig({ navigationBarTitleText: '纲要专项' })

interface PackPart {
  number: number
  title: string
  questionIds: string[]
}
interface TheoryPack {
  articleId: string
  title: string
  description: string
  questionCount: number
  parts: PackPart[]
}

const { themeClass } = useThemeClass()
const loading = ref(true)
const packs = ref<TheoryPack[]>([])

async function load() {
  loading.value = true
  try {
    const res = await api.getTheoryPacks()
    if (res.code === 0 && res.data) packs.value = res.data
    else showToast(res.message || '加载失败', 'error')
  } finally {
    loading.value = false
  }
}

function startFull(articleId: string) {
  Taro.navigateTo({ url: `/pages/question/taking?articleId=${articleId}` })
}

function startPart(articleId: string, part: number) {
  Taro.navigateTo({ url: `/pages/question/taking?articleId=${articleId}&part=${part}` })
}

onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-packs { @include page-padding; }
.hint { display: block; font-size: 12px; color: $text-muted; margin-bottom: 12px; line-height: 1.5; }
.empty { text-align: center; color: $text-muted; padding: 40px 12px; }
.pack {
  @include card;
  padding: 14px;
  margin-bottom: 12px;
  .title { display: block; font-size: 16px; font-weight: 700; margin-bottom: 6px; }
  .desc { display: block; font-size: 12px; color: $text-muted; margin-bottom: 10px; line-height: 1.5; }
  .row {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-top: 1px solid $border-color;
    font-size: 14px;
  }
  .arrow { color: $text-muted; }
}
</style>
