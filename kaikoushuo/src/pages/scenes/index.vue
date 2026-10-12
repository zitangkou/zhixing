<template>
  <view class="page">
    <text class="eyebrow">PRACTICE BY REAL SITUATIONS</text>
    <text class="title">从你会遇到的场景开始</text>
    <text class="muted">每个小课都包含对话、实用句块和开口任务。</text>
    <view v-for="(lesson, i) in lessons" :key="lesson.id" class="card scene" @tap="open(lesson.id)">
      <view class="scene-number">0{{ i + 1 }}</view>
      <view class="scene-content"><view class="row"><text class="scene-title">{{ lesson.title }}</text><text class="pill">{{ lesson.level }}</text></view><text class="muted">{{ lesson.goal }}</text><text class="scene-meta">{{ lesson.minutes }} 分钟 · {{ mediaLabel(lesson) }} · 练表达</text></view>
    </view>
    <view class="note card"><text class="note-title">练习小建议</text><text class="muted">先试着自己说，再看参考表达。卡住时听一遍、跟一句，最后再脱稿说一次。</text></view>
  </view>
</template>
<script setup lang="ts">
import Taro from '@tarojs/taro'
import { lessons, loadLessons, type Lesson } from '@/data'
import { onMounted } from 'vue'
definePageConfig({ navigationBarTitleText: '场景练习' })
function open(id: string) { Taro.navigateTo({ url: `/pages/lesson/index?id=${id}` }) }
function mediaLabel(lesson: Lesson) {
  if (lesson.rightsStatus === 'rejected' || lesson.rightsStatus === 'pending_review') return '台词练习'
  if (lesson.videoUrl) return '视频精听'
  if (lesson.audioUrl) return '音频跟读'
  if (lesson.sourceUrl) return '官方素材外链'
  return '对话跟读'
}
onMounted(() => { void loadLessons() })
</script>
<style lang="scss">
.scene { display:flex; gap:22rpx; align-items:flex-start; padding:28rpx; }
.scene-number { width:58rpx; height:58rpx; flex:none; border-radius:18rpx; background:#e9f1ee; color:#256d73; display:flex; align-items:center; justify-content:center; font-size:25rpx; font-weight:700; }
.scene-content { flex:1; }
.scene-title { font-size:29rpx; font-weight:650; }
.scene-content .muted { display:block; margin-top:12rpx; }
.scene-meta { display:block; color:#9aa39f; font-size:22rpx; margin-top:18rpx; }
.note-title { display:block; font-weight:700; margin-bottom:12rpx; }
</style>
