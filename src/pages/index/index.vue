<template>
  <page-meta
    v-if="isWeapp"
    :page-style="pageMeta.pageStyle"
    :background-color="pageMeta.backgroundColor"
    :background-color-top="pageMeta.backgroundColorTop"
    :background-color-bottom="pageMeta.backgroundColorBottom"
    :background-text-style="pageMeta.backgroundTextStyle"
  />
  <view class="study-tab-shell" :class="themeClass">
    <StudyHomePanel
      v-if="isWeapp"
      ref="homePanel"
      :active="activeTab === 'home'"
      :activation-key="activationKey"
    />
    <StudyUserPanel
      v-if="isWeapp"
      ref="userPanel"
      :active="activeTab === 'user'"
      :activation-key="activationKey"
    />
    <StudyHomePanel v-else :active="true" :activation-key="activationKey" />
    <AppTabBar :active="activeTab" :in-page-shell="isWeapp" @select="selectTab" />
  </view>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Taro, { useDidShow, useLoad, usePullDownRefresh } from '@tarojs/taro'
import AppTabBar from '@/components/AppTabBar.vue'
import StudyHomePanel from '@/components/StudyHomePanel.vue'
import StudyUserPanel from '@/components/StudyUserPanel.vue'
import { usePageMeta, useThemeClass } from '@/utils/brandColor'
import type { ProductTabKey } from '@/constants/productNavigation'

const { themeClass } = useThemeClass()
const pageMeta = usePageMeta()
const isWeapp = process.env.TARO_ENV === 'weapp'
const activeTab = ref<ProductTabKey>('home')
const activationKey = ref(0)
const homePanel = ref<{ refresh: () => Promise<void> } | null>(null)
const userPanel = ref<{ refresh: () => void } | null>(null)

definePageConfig({ navigationBarTitleText: '杜衡阁', enablePullDownRefresh: true })

useLoad((params) => {
  activeTab.value = params?.tab === 'user' ? 'user' : 'home'
})

watch(
  activeTab,
  (tab) => {
    if (isWeapp) void Taro.setNavigationBarTitle({ title: tab === 'user' ? '我的' : '杜衡阁' })
  },
  { immediate: true },
)

useDidShow(() => {
  activationKey.value += 1
})

usePullDownRefresh(async () => {
  try {
    if (activeTab.value === 'home') await homePanel.value?.refresh()
    else userPanel.value?.refresh()
  } finally {
    Taro.stopPullDownRefresh()
  }
})

function selectTab(tab: ProductTabKey) {
  if (tab === 'home' || tab === 'user') activeTab.value = tab
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.study-tab-shell {
  min-height: 100vh;
  background: $page-bg;
}
</style>
