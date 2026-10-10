<template>
  <view class="page">
    <text class="eyebrow">YOUR PRACTICE</text>
    <text class="title">稳稳地说出来</text>
    <view class="profile card"><view class="avatar">言</view><view><text class="profile-name">我的口语练习</text><text class="muted">每一次开口都算进步</text></view></view>
    <view class="stats"><view class="stat card"><text class="stat-number">{{ done.length }}</text><text class="muted">完成单元</text></view><view class="stat card"><text class="stat-number">{{ lessons.length - done.length }}</text><text class="muted">待练单元</text></view><view class="stat card"><text class="stat-number">10</text><text class="muted">每日目标(分)</text></view></view>
    <text class="section-title">练习中的好习惯</text>
    <view class="card tip"><text>01 · 先说出来</text><text class="muted">遇到不会的词，先用简单表达绕过去。</text></view>
    <view class="card tip"><text>02 · 重说一遍</text><text class="muted">听完反馈后马上再说一次，让表达更顺。</text></view>
    <view class="privacy card"><text class="privacy-title">录音隐私</text><text class="muted">本版录音仅保存在当前设备，不会上传。卸载小程序或清理缓存可能导致录音和本地进度丢失。</text></view>
  </view>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { lessons, loadLessons, readProgress } from '@/data'
definePageConfig({ navigationBarTitleText: '我的学习' })
const done = ref<string[]>([])
function refresh() { done.value = readProgress() }
onMounted(() => { refresh(); void loadLessons() })
useDidShow(refresh)
</script>
<style lang="scss">
.profile { display:flex; gap:20rpx; align-items:center; }
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
