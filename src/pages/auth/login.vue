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
      <view v-if="allowRegister" class="link-row">
        <text class="link" @tap="goRegister">没有账号？去注册</text>
      </view>
      <view v-else class="link-row">
        <text class="hint">暂未开放自助注册，请联系管理员开通</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { Button as NutButton, Input as NutInput } from '@nutui/nutui-taro'
import BrandLogo from '@/components/BrandLogo.vue'
import { api } from '@/api'
import { PRODUCT_HOME_ROUTE } from '@/constants/productNavigation'
import { useUserStore } from '@/store/user'
import { bootstrapApp } from '@/utils/bootstrap'
import { showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '登录' })

const { themeClass } = useThemeClass()
const userStore = useUserStore()
const username = ref('')
const password = ref('')
const loading = ref(false)
const allowRegister = ref(false)

onMounted(async () => {
  try {
    const res = await api.getPublicConfig()
    if (res.code === 0 && res.data) {
      allowRegister.value = !!res.data.allowRegister
    }
  } catch {
    allowRegister.value = false
  }
})

async function onLogin() {
  if (!username.value.trim() || !password.value) {
    showToast('请输入用户名和密码', 'error')
    return
  }
  loading.value = true
  try {
    await userStore.login(username.value.trim(), password.value)
    await bootstrapApp(true)
    Taro.switchTab({ url: PRODUCT_HOME_ROUTE })
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
      .hint { font-size: 12px; color: $text-muted; }
    }
  }
}
</style>
