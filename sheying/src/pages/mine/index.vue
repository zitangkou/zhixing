<template>
  <view class="page">
    <view class="hero"><view class="avatar">光</view><text class="title">{{ user?.nickname || '慢慢拍，慢慢看' }}</text><text class="copy">{{ user ? '微信已登录 · 练习档案已关联' : '登录后关联你的摄影练习档案' }}</text><button class="login" :disabled="loggingIn" @tap="handleLogin">{{ user ? '重新登录' : '微信登录' }}</button></view>
    <view class="stats"><view><text class="number">{{ notes.length }}</text><text class="caption">练习记录</text></view><view><text class="number">{{ practicedLessons.length }}</text><text class="caption">练过的技巧</text></view><view><text class="number">{{ roadmap.length }}</text><text class="caption">知识阶段</text></view></view>
    <view class="card" @tap="goPractice"><text class="card-title">拍摄练习本</text><text class="card-copy">回看你的观察与下一次尝试</text><text class="arrow">›</text></view>
    <view class="card" @tap="goCourses"><text class="card-title">摄影技巧课</text><text class="card-copy">光线、构图、曝光与对焦</text><text class="arrow">›</text></view>
    <view class="card" @tap="goMap"><text class="card-title">摄影知识地图</text><text class="card-copy">从看见光，到形成作品</text><text class="arrow">›</text></view>
    <view v-if="latestNote" class="latest"><text class="latest-label">最近一次练习</text><text class="latest-title">{{ latestNote.subject || latestNote.lessonTitle }}</text><text class="latest-copy">{{ latestNote.date }} · {{ latestNote.lessonTitle }}</text></view>
    <view class="foot">光线练习簿 · 学一点，拍一组</view>
  </view>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { roadmap, loadCatalog } from '@/data/catalog'
import { readPracticeNotes, type PracticeNote } from '@/utils/practiceStorage'
import { loginPhotographyWithWechat, readPhotographyUser } from '@/api/photography'
definePageConfig({ navigationBarTitleText: '我的练习' })
const notes = ref<PracticeNote[]>([])
const user = ref(readPhotographyUser())
const loggingIn = ref(false)
const practicedLessons = computed(() => [...new Set(notes.value.map((note) => note.lessonId).filter(Boolean))])
const latestNote = computed(() => notes.value[0])
async function loadNotes() { await loadCatalog(); notes.value = readPracticeNotes() }
async function handleLogin() {
  if (loggingIn.value) return
  loggingIn.value = true
  try {
    user.value = await loginPhotographyWithWechat()
    Taro.showToast({ title: '登录成功', icon: 'success' })
  } catch (error) {
    Taro.showToast({ title: error instanceof Error ? error.message : '微信登录失败', icon: 'none' })
  } finally { loggingIn.value = false }
}
function goPractice() { void Taro.navigateTo({ url: '/pages/practice/index' }) }
function goCourses() { void Taro.navigateTo({ url: '/pages/courses/index' }) }
function goMap() { void Taro.navigateTo({ url: '/pages/practice/index?tab=map' }) }
useDidShow(() => { user.value = readPhotographyUser(); void loadNotes() })
</script>
<style lang="scss">
@import '../../styles/tokens.scss';
.page{padding:18px 20px 32px}.hero{padding:22px 18px;border-radius:17px;background:linear-gradient(140deg,$dark,#56776b);color:#fff}.avatar{width:42px;height:42px;display:grid;place-items:center;border-radius:50%;background:#e4d5b1;color:$dark;font-size:17px;font-weight:750}.title{display:block;margin-top:13px;font-size:18px;font-weight:750}.copy{display:block;margin-top:5px;color:rgba(255,255,255,.7);font-size:10px}.login{margin:15px 0 0;padding:0 16px;height:34px;line-height:34px;border:1px solid rgba(255,255,255,.4);border-radius:18px;background:rgba(255,255,255,.12);color:#fff;font-size:11px}.login::after{border:0}.stats{display:flex;justify-content:space-around;margin:14px 0;padding:17px 5px;border-radius:14px;background:$card}.stats view{text-align:center}.number,.caption{display:block}.number{color:$green;font-size:18px;font-weight:750}.caption{margin-top:5px;color:$muted;font-size:9px}.card{position:relative;margin-top:10px;padding:16px;border-radius:14px;background:$card}.card-title{display:block;font-size:12px;font-weight:750}.card-copy{display:block;margin-top:6px;color:$muted;font-size:10px}.arrow{position:absolute;right:16px;top:22px;color:$muted;font-size:18px}.latest{margin-top:18px;padding:14px;border-radius:13px;background:$green-soft}.latest-label,.latest-title,.latest-copy{display:block}.latest-label{color:$green;font-size:9px}.latest-title{margin-top:7px;font-size:12px;font-weight:700}.latest-copy{margin-top:5px;color:$body;font-size:9px}.foot{margin-top:27px;color:#aaa69c;font-size:9px;text-align:center}
</style>
