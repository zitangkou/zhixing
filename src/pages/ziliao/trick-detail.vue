<template>
  <view class="zl-page" v-if="item" :class="themeClass">
    <view class="zl-head">
      <text class="zl-chip">{{ item.category }}</text>
      <text class="zl-title">{{ item.name }}</text>
    </view>
    <view v-if="item.principle" class="zl-section">
      <text class="zl-block-title">原理</text>
      <text class="zl-body">{{ item.principle }}</text>
    </view>
    <view v-if="item.whenToUse" class="zl-section">
      <text class="zl-block-title">什么时候用</text>
      <text class="zl-body">{{ item.whenToUse }}</text>
    </view>
    <view v-if="item.whenNot" class="zl-section">
      <text class="zl-block-title">什么时候不用</text>
      <text class="zl-body zl-body-warn">{{ item.whenNot }}</text>
    </view>
    <view v-if="item.errorNote" class="zl-section">
      <text class="zl-block-title">误差说明</text>
      <text class="zl-body">{{ item.errorNote }}</text>
    </view>
    <view v-if="item.example" class="zl-section">
      <text class="zl-block-title">示例</text>
      <text class="zl-body">{{ item.example }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from '@tarojs/taro'
import { api } from '@/api'
import type { ZiliaoTrick } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '技巧详情' })

const { themeClass } = useThemeClass()
const router = useRouter()
const item = ref<ZiliaoTrick | null>(null)

onMounted(async () => {
  const id = router.params?.id || ''
  const res = await api.getZiliaoTrick(id)
  if (res.code === 0 && res.data) item.value = res.data
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.zl-page {
  @include page-padding;
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
  margin-top: 8px;
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
.zl-body-warn {
  color: $accent-amber;
}
</style>
