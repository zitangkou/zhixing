<template>
  <view class="zk-auth-page">
    <view class="zk-auth-brand"><view class="zk-auth-mark">知</view><text>知库 · AI 知识库</text></view>
    <view class="zk-auth-title">微信快捷登录</view>
    <view class="zk-auth-subtitle">登录后浏览公开资料，并管理你的个人文档</view>
    <view class="zk-auth-form">
      <button class="zk-auth-submit" :loading="loading" @tap="submit">{{ loading ? '正在登录…' : '微信一键登录' }}</button>
    </view>
    <view class="zk-auth-footnote">首次登录将自动创建知库账号，仅用于登录和保存你的个人资料。</view>
    <view class="zk-auth-legal">
      <view class="zk-auth-check" @tap="toggleAgreed"><view :class="{ checked: agreed }">{{ agreed ? '✓' : '' }}</view><text>已阅读并同意</text></view>
      <text @tap="openPrivacy">隐私政策</text><text>和</text><text @tap="openTerms">用户服务协议</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro from '@tarojs/taro'
import { authApi } from '@/api'
import { showToast } from '@/utils/feedback'

definePageConfig({ navigationBarTitleText: '知库账号' })

const loading = ref(false)
const agreed = ref(false)

async function submit() {
  if (!agreed.value) { showToast('请先阅读并同意隐私政策和用户服务协议'); return }
  loading.value = true
  try {
    const login = await Taro.login()
    if (!login.code) throw new Error('无法获取微信登录凭证，请重试')
    const result = await authApi.wechatLogin(login.code)
    Taro.setStorageSync('zhiku_token', result.access_token)
    Taro.setStorageSync('zhiku_username', result.user.nickname || result.user.username || '知库用户')
    showToast('微信登录成功', 'success')
    setTimeout(() => { void Taro.navigateBack({ delta: 1 }).catch(() => Taro.switchTab({ url: '/pages/home/index' })) }, 350)
  } catch (error) {
    showToast(error instanceof Error ? error.message : '微信登录失败', 'error')
  } finally { loading.value = false }
}

function openPrivacy() { void Taro.navigateTo({ url: '/pages/legal/privacy' }) }
function openTerms() { void Taro.navigateTo({ url: '/pages/legal/terms' }) }
function toggleAgreed() { agreed.value = !agreed.value }
</script>

<style lang="scss" scoped>
@import '../../styles/tokens.scss';
.zk-auth-page { min-height:100vh; padding:25px 24px; background:$bg; }
.zk-auth-brand { display:flex; align-items:center; gap:10px; color:$ink; font-size:13px; font-weight:700; }
.zk-auth-mark { width:36px; height:36px; display:grid; place-items:center; border-radius:12px; color:#fff; background:$brand; font-size:18px; }
.zk-auth-title { margin-top:48px; font-size:24px; font-weight:750; }
.zk-auth-subtitle { margin-top:8px; color:$muted; font-size:11px; line-height:1.6; }
.zk-auth-form { margin-top:27px; }
.zk-auth-input { height:47px; margin-bottom:12px; padding:0 14px; border:1px solid $border; border-radius:11px; background:$card; font-size:12px; }
.zk-auth-submit { height:45px; margin-top:7px; border:0; border-radius:11px; color:#fff; background:$brand; font-size:12px; font-weight:650; }
.zk-auth-switch { padding:18px; color:$brand; text-align:center; font-size:10px; }
.zk-auth-footnote { margin-top:24px; color:$muted; text-align:center; font-size:9px; line-height:1.7; }
.zk-auth-legal { display:flex; justify-content:center; align-items:center; gap:5px; margin-top:17px; color:$brand; font-size:10px; }
.zk-auth-check { display:flex; align-items:center; gap:5px; color:$body; }
.zk-auth-check view { width:14px; height:14px; border:1px solid $border; border-radius:4px; color:#fff; font-size:10px; line-height:14px; text-align:center; }
.zk-auth-check view.checked { border-color:$brand; background:$brand; }
</style>
