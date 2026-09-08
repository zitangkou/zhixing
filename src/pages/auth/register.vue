<template>
  <view class="page-auth" :class="themeClass">
    <view class="auth-header">
      <BrandLogo size="md" tagline="知行合一 · 开启学习" />
      <text class="subtitle">用户名 3-32 位，支持字母、数字、下划线</text>
    </view>

    <view class="form-card">
      <nut-input v-model="username" placeholder="用户名" clearable />
      <nut-input v-model="password" type="password" placeholder="密码（至少 6 位）" clearable />
      <nut-input v-model="passwordConfirm" type="password" placeholder="确认密码" clearable />
      <nut-button type="primary" block class="primary-btn" :loading="loading" @click="onRegister">
        注册并登录
      </nut-button>
      <view class="link-row">
        <text class="link" @tap="goLogin">已有账号？去登录</text>
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
import { enterAfterAuth } from '@/utils/auth'
import { showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '注册' })

const { themeClass } = useThemeClass()
const userStore = useUserStore()
const username = ref('')
const password = ref('')
const passwordConfirm = ref('')
const loading = ref(false)

async function onRegister() {
  if (!username.value.trim() || !password.value || !passwordConfirm.value) {
    showToast('请填写完整信息', 'error')
    return
  }
  loading.value = true
  try {
    await userStore.register(username.value.trim(), password.value, passwordConfirm.value)
    await bootstrapApp(true)
    enterAfterAuth()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '注册失败', 'error')
  } finally {
    loading.value = false
  }
}

function goLogin() {
  Taro.redirectTo({ url: '/pages/auth/login' })
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-auth {
  min-height: 100vh;
  padding: 48px 24px 24px;
  background: linear-gradient(180deg, $primary-light 0%, $page-bg 42%);
  .auth-header {
    margin-bottom: 32px;
    .subtitle {
      display: block;
      margin-top: 16px;
      font-size: 13px;
      color: $text-secondary;
      line-height: 1.5;
    }
  }
  .form-card {
    @include card;
    padding: 22px 16px;
    border-radius: $radius-lg;
    box-shadow: $shadow-float;
    :deep(.nut-input) { margin-bottom: 14px; }
    .primary-btn { margin-top: 8px; }
    .link-row { text-align: center; margin-top: 18px; }
    .link { color: $primary-color; font-size: 14px; }
  }
}
</style>
