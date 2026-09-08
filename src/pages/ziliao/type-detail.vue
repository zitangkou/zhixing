<template>
  <view class="zl-page" v-if="item" :class="themeClass">
    <view class="zl-head">
      <text class="zl-chip">{{ item.category }}</text>
      <text class="zl-title">{{ item.name }}</text>
      <text class="zl-desc">{{ item.description }}</text>
    </view>
    <view v-if="item.ability" class="zl-section">
      <text class="zl-block-title">考查能力</text>
      <text class="zl-body">{{ item.ability }}</text>
    </view>
    <view class="zl-section">
      <text class="zl-block-title">难度 · 频率</text>
      <text class="zl-body">难度 {{ item.difficulty }} / 5 · 考试频率 {{ item.examFreq }} / 5</text>
    </view>
    <view class="zl-action-bar">
      <nut-button type="primary" block @click="startDrill">按此题型练习</nut-button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import { api } from '@/api'
import type { ZiliaoQuestionType } from '@/types'
import { showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '题型详情' })

const { themeClass } = useThemeClass()
const router = useRouter()
const item = ref<ZiliaoQuestionType | null>(null)

async function startDrill() {
  if (!item.value) return
  const res = await api.listZiliaoDrillSets(item.value.code)
  const sets = res.data || []
  if (!sets.length) {
    // 弱匹配无结果时回退到全部材料组
    const all = await api.listZiliaoDrillSets()
    const fallback = all.data || []
    if (!fallback.length) {
      showToast('暂无可练材料组')
      return
    }
    const pick = fallback[Math.floor(Math.random() * fallback.length)]
    Taro.navigateTo({
      url: `/pages/ziliao/drill?setId=${encodeURIComponent(pick.setId)}&typeCode=${item.value.code}`,
    })
    return
  }
  const pick = sets[Math.floor(Math.random() * sets.length)]
  Taro.navigateTo({
    url: `/pages/ziliao/drill?setId=${encodeURIComponent(pick.setId)}&typeCode=${item.value.code}`,
  })
}

onMounted(async () => {
  const id = router.params?.id || ''
  const res = await api.getZiliaoType(id)
  if (res.code === 0 && res.data) item.value = res.data
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.zl-page {
  @include page-padding;
  padding-bottom: 80px;
}
.zl-head {
  @include card;
}
.zl-chip {
  @include brand-chip;
}
.zl-title {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: $text-primary;
  margin: 8px 0;
}
.zl-desc {
  display: block;
  font-size: 13px;
  color: $text-secondary;
}
.zl-section {
  @include card;
}
.zl-block-title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: $text-primary;
}
.zl-body {
  display: block;
  font-size: 14px;
  color: $text-secondary;
  line-height: 1.6;
}
.zl-action-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
  background: $card-bg;
  border-top: 1px solid $border-color;
}
</style>
