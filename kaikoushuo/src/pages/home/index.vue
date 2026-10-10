<template>
  <view class="page">
    <view class="brand-row"><image class="brand-mark" src="../../assets/logo.svg" mode="aspectFit" /><text class="eyebrow">YANYU · SPEAK WITH EASE</text></view>
    <text class="title">每天开口 10 分钟</text>
    <text class="muted">不用等准备好，现在就从一句话开始。</text>

    <view class="hero card">
      <view class="row"><text class="pill">今日建议 · {{ nextLesson.level }}</text><text class="muted">{{ nextLesson.minutes }} 分钟</text></view>
      <text class="hero-title">{{ nextLesson.title }}</text>
      <text class="muted">{{ nextLesson.goal }}</text>
      <button class="primary start" @tap="open(nextLesson.id)">开始练习 <text>→</text></button>
    </view>

    <view class="row section-head"><text class="section-title">继续你的口语练习</text><text class="link" @tap="goScenes">全部场景 →</text></view>
    <view v-for="lesson in lessons" :key="lesson.id" class="card lesson-card" @tap="open(lesson.id)">
      <view class="row"><text class="lesson-title">{{ lesson.title }}</text><text v-if="done.includes(lesson.id)" class="done">已完成</text></view>
      <text class="muted">{{ lesson.level }} · {{ lesson.minutes }} 分钟</text>
      <text class="lesson-goal">{{ lesson.goal }}</text>
    </view>
    <text class="footnote">先听懂，再模仿；替换表达后，试着脱稿说出来。</text>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { lessons, loadLessons, readProgress } from '@/data'

definePageConfig({ navigationBarTitleText: '言遇英语' })
const done = ref<string[]>([])
const nextLesson = computed(() => lessons.find((lesson) => !done.value.includes(lesson.id)) || lessons[0])
function refresh() { done.value = readProgress(); void loadLessons() }
function open(id: string) { Taro.navigateTo({ url: `/pages/lesson/index?id=${id}` }) }
function goScenes() { Taro.switchTab({ url: '/pages/scenes/index' }) }
onMounted(refresh)
useDidShow(refresh)
</script>

<style lang="scss">
.hero { background: #e7f1ed; padding: 34rpx; }
.brand-row { display:flex; align-items:center; gap:14rpx; }
.brand-mark { width:54rpx; height:54rpx; }
.hero-title { display:block; font-size: 38rpx; font-weight:700; margin: 28rpx 0 12rpx; }
.start { margin: 28rpx 0 0; width: 100%; text-align:left; }
.start text { float:right; }
.section-head { margin-top: 22rpx; }
.section-title { margin: 32rpx 0 8rpx; }
.link { color:#256d73; font-size:24rpx; }
.lesson-card { padding:26rpx 30rpx; }
.lesson-title { font-size:30rpx; font-weight:650; }
.lesson-goal { display:block; margin-top:14rpx; color:#53645f; font-size:25rpx; }
.done { color:#4c8a69; font-size:22rpx; }
.footnote { display:block; text-align:center; margin:36rpx 0; color:#98a19d; font-size:22rpx; }
</style>
