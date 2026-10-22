<template>
  <view class="page">
    <text class="eyebrow">YOUR PRACTICE</text>
    <text class="title">稳稳地说出来</text>
    <view class="profile card">
      <view class="avatar">{{ avatarText }}</view>
      <view class="profile-copy">
        <text class="profile-name">{{ profileName }}</text>
        <text class="muted">{{ profileStatus }}</text>
      </view>
      <button v-if="isWechatMiniProgram" class="login-button" :disabled="loginState === 'loading'" @tap="handleWechatLogin">
        {{ loginButtonText }}
      </button>
    </view>
    <view class="stats"><view class="stat card"><text class="stat-number">{{ done.length }}</text><text class="muted">完成单元</text></view><view class="stat card"><text class="stat-number">{{ lessons.length - done.length }}</text><text class="muted">待练单元</text></view><view class="stat card"><text class="stat-number">10</text><text class="muted">每日目标(分)</text></view></view>
    <text class="section-title">练习中的好习惯</text>
    <view class="card tip"><text>01 · 先说出来</text><text class="muted">遇到不会的词，先用简单表达绕过去。</text></view>
    <view class="card tip"><text>02 · 重说一遍</text><text class="muted">听完反馈后马上再说一次，让表达更顺。</text></view>
    <view class="privacy card"><text class="privacy-title">录音隐私</text><text class="muted">本版录音仅保存在当前设备，不会上传。卸载小程序或清理缓存可能导致录音和本地进度丢失。</text></view>
  </view>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { lessons, loadLessons, readProgress, syncProgressAfterLogin } from '@/data'
import { ensureWechatLogin, getAccessToken, getWechatUser } from '@/auth'
definePageConfig({ navigationBarTitleText: '我的学习' })
const done = ref<string[]>([])
const isWechatMiniProgram = Taro.getEnv() === Taro.ENV_TYPE.WEAPP
const account = ref<{ nickname?: string } | null>(getWechatUser() as { nickname?: string } | null)
const loginState = ref<'loading' | 'logged-in' | 'failed' | 'web'>('loading')
const loginError = ref('')
const profileName = computed(() => account.value?.nickname || '我的口语练习')
const profileStatus = computed(() => {
  if (loginState.value === 'logged-in') return '微信已登录，学习进度将同步保存'
  if (loginState.value === 'loading') return '正在连接微信账号…'
  if (loginState.value === 'failed') return loginError.value || '微信登录未完成，请点击重试'
  return '每一次开口都算进步'
})
const avatarText = computed(() => profileName.value.trim().slice(0, 1) || '言')
const loginButtonText = computed(() => loginState.value === 'logged-in' ? '已登录' : loginState.value === 'loading' ? '登录中' : '微信登录')

function refresh() { done.value = readProgress() }
async function refreshLogin() {
  if (!isWechatMiniProgram) { loginState.value = 'web'; return }
  account.value = getWechatUser() as { nickname?: string } | null
  if (getAccessToken()) { loginState.value = 'logged-in'; return }
  loginState.value = 'loading'
  loginError.value = ''
  try {
    await ensureWechatLogin()
    account.value = getWechatUser() as { nickname?: string } | null
    loginState.value = getAccessToken() ? 'logged-in' : 'failed'
    if (loginState.value === 'logged-in') await syncProgressAfterLogin()
  } catch (error) {
    loginState.value = 'failed'
    loginError.value = error instanceof Error ? error.message : '微信登录失败，请重试'
  }
}
async function handleWechatLogin() {
  if (loginState.value === 'loading') return
  loginState.value = 'loading'
  loginError.value = ''
  try {
    await ensureWechatLogin(true)
    account.value = getWechatUser() as { nickname?: string } | null
    loginState.value = getAccessToken() ? 'logged-in' : 'failed'
    if (loginState.value === 'logged-in') await syncProgressAfterLogin()
  } catch (error) {
    loginState.value = 'failed'
    loginError.value = error instanceof Error ? error.message : '微信登录失败，请重试'
  }
}
onMounted(() => { refresh(); void loadLessons(); void refreshLogin() })
useDidShow(() => { refresh(); void refreshLogin() })
</script>
<style lang="scss">
.profile { display:flex; gap:20rpx; align-items:center; }
.profile-copy { flex:1; min-width:0; }
.login-button { flex-shrink:0; margin:0; padding:10rpx 18rpx; color:#256d73; background:#e8f2ef; border:0; border-radius:999rpx; font-size:22rpx; line-height:1.5; }
.login-button::after { border:0; }
.avatar { width:82rpx; height:82rpx; border-radius:26rpx; display:flex; align-items:center; justify-content:center; color:#fff; background:#256d73; font-size:36rpx; font-weight:700; }
.profile-name { display:block; font-size:29rpx; font-weight:650; margin-bottom:8rpx; }
.stats { display:flex; gap:14rpx; }
.stat { flex:1; padding:24rpx 10rpx; text-align:center; }
.stat-number { display:block; color:#256d73; font-size:38rpx; font-weight:700; margin-bottom:6rpx; }
.stat .muted { font-size:21rpx; }
.tip { padding:24rpx 28rpx; }
.tip > text:first-child { display:block; font-weight:650; margin-bottom:8rpx; }
.privacy { background:#eef1ed; }
.privacy-title { display:block; font-weight:650; margin-bottom:8rpx; }
</style>
