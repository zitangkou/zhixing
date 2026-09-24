<template>
  <view class="page-xingce-modules" :class="themeClass" />
</template>

<script setup lang="ts">
import Taro, { useRouter } from '@tarojs/taro'
import { onMounted } from 'vue'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '套卷题型' })

const { themeClass } = useThemeClass()
const router = useRouter()

onMounted(() => {
  const year = router.params?.year || ''
  const paperType = router.params?.paperType || ''
  const qs = new URLSearchParams()
  if (year) qs.set('year', String(year))
  if (paperType) qs.set('paperType', paperType)
  const suffix = qs.toString() ? `?${qs.toString()}` : ''
  Taro.redirectTo({ url: `/pages/question/xingce-hub${suffix}` })
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-xingce-modules {
  min-height: 120px;
}
</style>
