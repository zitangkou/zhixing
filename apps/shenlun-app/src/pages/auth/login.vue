<template>
  <view class="auth-page">
    <view class="auth-mark">知行策论</view><view class="auth-title">读得深，写得出</view><view class="auth-desc">登录后同步今日精读、三刀拆解和训练沉淀</view>
    <view class="auth-card">
      <view class="auth-field"><view class="auth-label">账号</view><input v-model="username" class="auth-input" placeholder-class="auth-placeholder" placeholder="请输入用户名" confirm-type="next" /></view>
      <view class="auth-field"><view class="auth-label">密码</view><input v-model="password" class="auth-input" placeholder-class="auth-placeholder" password placeholder="请输入密码" confirm-type="done" @confirm="submit" /></view>
      <view class="auth-agree" @tap="agreed = !agreed">
        <text class="auth-agree-box" :class="{ 'auth-agree-box-on': agreed }">{{ agreed ? '✓' : '' }}</text>
        <view class="auth-agree-text">我已阅读并同意<text class="auth-agree-link" @tap.stop="openLegal('agreement')">《用户协议》</text>与<text class="auth-agree-link" @tap.stop="openLegal('privacy')">《隐私政策》</text></view>
      </view>
      <button class="auth-button" :disabled="loading" @tap="submit">{{ loading ? '登录中…' : '登录' }}</button>
      <view class="auth-hint">使用统一知行账号登录</view><view class="auth-link" @tap="copyRecoveryMail">忘记密码？点此复制邮箱人工重置</view><view class="auth-link" @tap="goRegister">没有账号？立即注册</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro from '@tarojs/taro'
import { api } from '@/api'
import { LEGAL_CONTACT } from '@/constants/legal'
import { setToken } from '@/utils/auth'
import { showToast } from '@/utils/platform'

const username = ref('')
const password = ref('')
const loading = ref(false)
const agreed = ref(false)
function goRegister() { Taro.navigateTo({ url: '/pages/auth/register' }) }
function openLegal(doc: string) { Taro.navigateTo({ url: `/pages/legal/index?doc=${doc}` }) }
function copyRecoveryMail() { Taro.setClipboardData({ data: LEGAL_CONTACT.email, success: () => showToast('邮箱已复制，请在邮件中附上你的用户名') }) }
async function submit() {
  if (!username.value.trim() || !password.value) return showToast('请输入用户名和密码')
  if (!agreed.value) return showToast('请先阅读并同意用户协议与隐私政策')
  loading.value = true
  const response = await api.login(username.value.trim(), password.value)
  loading.value = false
  if (response.code !== 0 || !response.data?.access_token) return showToast(response.message || '登录失败')
  setToken(response.data.access_token)
  Taro.switchTab({ url: '/pages/today/index' })
}
</script>
