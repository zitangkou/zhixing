<template>
  <view class="app-tab-bar-root">
    <!-- 小程序无全局 body 挂载点，主 Tab 页内嵌反馈层；H5 已挂到 document.body -->
    <AppFeedback v-if="inlineFeedback" />
    <view v-if="showCustomTabs" class="app-tab-bar">
      <view
        v-for="item in tabs"
        :key="item.path"
        class="tab-item"
        :class="{ active: selected === item.key }"
        @tap="onSwitch(item)"
      >
        <view class="tab-icon-wrap" :class="{ active: selected === item.key }">
          <component
            :is="item.icon"
            :color="selected === item.key ? activeColor : mutedColor"
            size="20"
          />
        </view>
        <text class="tab-text">
          {{ item.text }}
        </text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { Clock, Edit, Home, My } from '@nutui/icons-vue-taro'
import AppFeedback from '@/components/AppFeedback.vue'
import { CURRENT_PRODUCT_TABS, type ProductTabKey } from '@/constants/productNavigation'
import { useBrandColor } from '@/utils/brandColor'

const inlineFeedback = process.env.TARO_ENV !== 'h5'
const showCustomTabs = process.env.TARO_ENV === 'h5'

const props = withDefaults(
  defineProps<{
    /** 当前 tab：today | home | quiz | user */
    active?: ProductTabKey
  }>(),
  { active: undefined },
)

const selected = ref<ProductTabKey>(props.active || 'today')
const { brandColor: activeColor, mutedColor } = useBrandColor()

const iconMap = { clock: Clock, home: Home, edit: Edit, user: My }
const tabs = CURRENT_PRODUCT_TABS.map((item) => ({ ...item, icon: iconMap[item.icon] }))

function syncFromRoute() {
  if (props.active) {
    selected.value = props.active
    return
  }
  const path = Taro.getCurrentInstance()?.router?.path || ''
  const hit = tabs.find((t) => path.includes(t.path.replace(/^\//, '')))
  if (hit) selected.value = hit.key
}

function onSwitch(item: (typeof tabs)[number]) {
  if (selected.value === item.key) return
  selected.value = item.key
  Taro.switchTab({ url: item.path })
}

onMounted(syncFromRoute)
useDidShow(syncFromRoute)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.app-tab-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  align-items: flex-start;
  justify-content: space-around;
  padding: 8px 0 calc(8px + env(safe-area-inset-bottom));
  background: var(--zk-tabbar-bg);
  border-top: 1px solid $border-color;
  box-shadow: $shadow-float;
}

.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-height: 48px;
  padding: 4px 0;
  box-sizing: border-box;
}

.tab-icon-wrap {
  width: 44px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  transition: background 0.15s ease;

  &.active {
    background: $primary-light;
  }
}

.tab-text {
  font-size: 11px;
  line-height: 1.2;
  color: $text-muted;
}

.tab-item.active .tab-text {
  color: var(--zk-primary);
  font-weight: 600;
}
</style>
