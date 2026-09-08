<template>
  <view class="page-auth" :class="themeClass">
    <view class="auth-header">
      <BrandLogo size="lg" tagline="读得进，练得出" />
      <text class="subtitle">账号登录</text>
    </view>

    <view class="form-card">
      <nut-input v-model="username" placeholder="用户名" clearable />
      <nut-input v-model="password" type="password" placeholder="密码" clearable />
      <nut-button type="primary" block class="primary-btn" :loading="loading" @click="onLogin">
        登录
      </nut-button>
      <view class="link-row">
        <text class="link" @tap="goRegister">没有账号？去注册</text>
      </view>
      <view class="link-row">
        <text class="link muted" @tap="skipAuth">先逛逛，稍后再登录</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro from '@tarojs/taro'
import { Button as NutButton, Input as NutInput } from '@nutui/nutui-taro'
import BrandLogo from '@/components/BrandLogo.vue'
import { useUserStore } from '@/store/user'
import { bootstrapApp } from '@/utils/bootstrap'
import { enterAfterAuth, skipAuth } from '@/utils/auth'
import { showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '登录' })

const { themeClass } = useThemeClass()
const userStore = useUserStore()
const username = ref('')
const password = ref('')
const loading = ref(false)

async function onLogin() {
  if (!username.value.trim() || !password.value) {
    showToast('请输入用户名和密码', 'error')
    return
  }
  loading.value = true
  try {
    await userStore.login(username.value.trim(), password.value)
    await bootstrapApp(true)
    enterAfterAuth()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '登录失败', 'error')
  } finally {
    loading.value = false
  }
}

function goRegister() {
  Taro.navigateTo({ url: '/pages/auth/register' })
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-auth {
  min-height: 100vh;
  padding: 56px 24px 24px;
  background: linear-gradient(180deg, $primary-light 0%, $page-bg 42%);
  .auth-header {
    margin-bottom: 36px;
    .subtitle {
      display: block;
      margin-top: 20px;
      font-size: 15px;
      color: $text-secondary;
    }
  }
  .form-card {
    @include card;
    padding: 22px 16px;
    border-radius: $radius-lg;
    box-shadow: $shadow-float;
    :deep(.nut-input) { margin-bottom: 14px; }
    .primary-btn { margin-top: 8px; }
    .link-row {
      margin-top: 18px;
      text-align: center;
      .link { font-size: 14px; color: $primary-color; }
      .link.muted { color: $text-secondary; font-size: 13px; }
    }
  }
}
</style>
