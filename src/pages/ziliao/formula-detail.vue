<template>
  <view class="zl-page" v-if="item" :class="themeClass">
    <view class="zl-head">
      <text class="zl-chip">{{ item.category }}</text>
      <text class="zl-title">{{ item.name }}</text>
      <view class="zl-formula-box">
        <LatexBlock
          :latex="item.latex"
          :plain="item.formulaPlain"
          size="lg"
          :show-plain="true"
        />
      </view>
    </view>
    <view v-if="item.definition" class="zl-section">
      <text class="zl-block-title">定义</text>
      <text class="zl-body">{{ item.definition }}</text>
    </view>
    <view v-if="item.scenarios" class="zl-section">
      <text class="zl-block-title">适用场景</text>
      <text class="zl-body">{{ item.scenarios }}</text>
    </view>
    <view v-if="item.pitfalls" class="zl-section">
      <text class="zl-block-title">易错点</text>
      <text class="zl-body zl-body-warn">{{ item.pitfalls }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { api } from '@/api'
import LatexBlock from '@/components/LatexBlock.vue'
import type { ZiliaoFormula } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '公式详情' })

const { themeClass } = useThemeClass()
const router = useRouter()
const item = ref<ZiliaoFormula | null>(null)

onMounted(async () => {
  const id = router.params?.id || ''
  const res = await api.getZiliaoFormula(id)
  if (res.code === 0 && res.data) item.value = res.data
  else Taro.showToast({ title: '未找到', icon: 'none' })
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.zl-page {
  @include page-padding;
}
.zl-head {
  @include card;
  padding: 16px;
}
.zl-chip {
  @include brand-chip;
}
.zl-title {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: $text-primary;
  margin: 8px 0 12px;
}
.zl-formula-box {
  background: $elevated;
  border-radius: $radius-md;
  padding: 12px;
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
