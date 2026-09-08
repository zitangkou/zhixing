<template>
  <view class="page-signin" :class="themeClass">
    <SignCalendar :sign-status="userStore.signStatus" :streak="userStore.signStreak" />
    <nut-button
      type="primary"
      block
      size="large"
      class="primary-btn sign-btn"
      :disabled="userStore.hasSignedToday"
      @click="handleSignIn"
    >
      {{ userStore.hasSignedToday ? '今日已签到' : '立即签到' }}
    </nut-button>
    <view class="points-info">
      <text>当前积分：{{ userStore.points }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { Button as NutButton } from '@nutui/nutui-taro'
import SignCalendar from '@/components/SignCalendar.vue'
import { useUserStore } from '@/store/user'
import { showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '每日签到' })

const { themeClass } = useThemeClass()
const userStore = useUserStore()

async function handleSignIn() {
  const res = await userStore.signIn()
  if (res.code === 0) {
    showToast(`签到成功 +${res.data.points}积分，连续${res.data.streak}天`, 'success')
  } else {
    showToast(res.message, 'error')
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-signin {
  @include page-padding;
  .sign-btn { margin-top: 20px; }
  .points-info {
    text-align: center;
    margin-top: 16px;
    color: $text-secondary;
    font-size: 14px;
  }
}
</style>
