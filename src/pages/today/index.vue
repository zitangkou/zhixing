<template>
  <view class="page-today page-with-tabbar" :class="themeClass">
    <view class="today-header">
      <view class="today-greet">
        <text class="today-hi">
          {{ greeting }}
        </text>
        <text class="today-slogan">
          {{ APP_SLOGAN }}
        </text>
      </view>
      <view class="today-date">
        {{ dateLabel }}
      </view>
    </view>

    <ExamCountdownCard ref="countdownCard" />

    <view class="quick-row">
      <view
        class="q-item"
        @tap="goSignIn"
      >
        <view class="q-icon-wrap">
          <DateIcon
            :color="brandColor"
            size="20"
          />
        </view>
        <text>{{ userStore.hasSignedToday ? '已签到' : '签到' }}</text>
      </view>
      <view
        class="q-item"
        @tap="goQuiz"
      >
        <view class="q-icon-wrap">
          <Edit
            :color="brandColor"
            size="20"
          />
        </view>
        <text>去练习</text>
      </view>
      <view
        class="q-item"
        @tap="goHub"
      >
        <view class="q-icon-wrap">
          <CheckChecked
            :color="brandColor"
            size="20"
          />
        </view>
        <text>复习中心</text>
      </view>
      <view
        class="q-item"
        @tap="goGrowth"
      >
        <view class="q-icon-wrap">
          <Fabulous
            :color="brandColor"
            size="20"
          />
        </view>
        <text>足迹</text>
      </view>
    </view>

    <TodayTaskList />
    <DueReviewAlert />
    <YesterdayBar />

    <AppTabBar active="today" />
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { CheckChecked, Date as DateIcon, Edit, Fabulous } from '@nutui/icons-vue-taro'
import AppTabBar from '@/components/AppTabBar.vue'
import ExamCountdownCard from '@/components/today/ExamCountdownCard.vue'
import TodayTaskList from '@/components/today/TodayTaskList.vue'
import DueReviewAlert from '@/components/today/DueReviewAlert.vue'
import YesterdayBar from '@/components/today/YesterdayBar.vue'
import { APP_SLOGAN } from '@/constants/brand'
import { useUserStore } from '@/store/user'
import { useBrandColor, useThemeClass } from '@/utils/brandColor'

const userStore = useUserStore()
const { brandColor } = useBrandColor()
const { themeClass } = useThemeClass()
const countdownCard = ref<{ load: () => void } | null>(null)

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const dateLabel = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} 星期${WEEKDAYS[d.getDay()]}`
})

function goSignIn() {
  Taro.navigateTo({ url: '/pages/user/signin' })
}

function goQuiz() {
  Taro.switchTab({ url: '/pages/question/index' })
}

function goHub() {
  Taro.navigateTo({ url: '/pages/review/hub' })
}

function goGrowth() {
  Taro.navigateTo({ url: '/pages/user/growth' })
}

function refresh() {
  countdownCard.value?.load()
}

onMounted(() => {
  userStore.bootstrap()
})
useDidShow(refresh)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-today {
  @include page-padding;
  padding-bottom: 40px;
}

.today-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 8px 2px 14px;
  .today-greet {
    display: flex;
    flex-direction: column;
    gap: 2px;
    .today-hi { font-size: 22px; font-weight: 700; color: $text-primary; }
    .today-slogan { font-size: 12px; color: $text-muted; }
  }
  .today-date {
    font-size: 12px;
    color: $text-secondary;
    background: $page-bg;
    padding: 4px 10px;
    border-radius: 6px;
  }
}

.quick-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  .q-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 10px 0;
    background: $card-bg;
    border-radius: $radius-md;
    box-shadow: $shadow-card;
    font-size: 12px;
    color: $text-secondary;
    .q-icon-wrap {
      @include icon-tile;
    }
  }
}
</style>
