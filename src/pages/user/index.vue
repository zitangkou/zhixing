<template>
  <page-meta
    v-if="isWeapp"
    :page-style="pageMeta.pageStyle"
    :background-color="pageMeta.backgroundColor"
    :background-color-top="pageMeta.backgroundColorTop"
    :background-color-bottom="pageMeta.backgroundColorBottom"
    :background-text-style="pageMeta.backgroundTextStyle"
  />
  <view v-if="isWeapp" class="redirect-page" />
  <view v-else class="standalone-user-page">
    <StudyUserPanel :active="true" :activation-key="activationKey" />
    <AppTabBar active="user" />
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro, { useDidShow, useLoad } from '@tarojs/taro'
import AppTabBar from '@/components/AppTabBar.vue'
import StudyUserPanel from '@/components/StudyUserPanel.vue'
import { usePageMeta } from '@/utils/brandColor'

const isWeapp = process.env.TARO_ENV === 'weapp'
const pageMeta = usePageMeta()
const activationKey = ref(0)

definePageConfig({ navigationBarTitleText: '我的' })

useLoad(() => {
  if (isWeapp) void Taro.reLaunch({ url: '/pages/index/index?tab=user' })
})
useDidShow(() => {
  activationKey.value += 1
})
</script>

<style lang="scss" scoped>
.standalone-user-page {
  min-height: 100vh;
}
</style>
