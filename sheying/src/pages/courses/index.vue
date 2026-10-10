<template>
  <view class="page">
    <view class="intro"><text class="eyebrow">PHOTO LESSONS</text><text class="title">挑一个问题，开始练习。</text><text class="copy">每节只学一个概念，并配一项可以马上完成的拍摄任务。</text></view>
    <scroll-view scroll-x class="filters"><view v-for="category in categories" :key="category" class="filter" :class="{ selected: activeCategory === category }" @tap="activeCategory = category">{{ category }}</view></scroll-view>
    <view class="count">{{ filteredLessons.length }} 节技巧课</view>
    <view v-for="lesson in filteredLessons" :key="lesson.id" class="lesson-card" @tap="openLesson(lesson.id)">
      <view class="lesson-head"><text class="tag">{{ lesson.category }} · {{ lesson.level }}</text><text class="time">{{ lesson.time }}</text></view>
      <text class="lesson-title">{{ lesson.title }}</text><text class="lesson-desc">{{ lesson.subtitle }}</text>
      <view class="lesson-foot"><text>原理 + 拍摄任务 + 复盘</text><text class="arrow">开始学习 ›</text></view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { lessons, loadCatalog } from '@/data/catalog'
definePageConfig({ navigationBarTitleText: '摄影技巧' })
const activeCategory = ref('全部')
const categories = computed(() => ['全部', ...new Set(lessons.value.map((lesson) => lesson.category))])
const filteredLessons = computed(() => activeCategory.value === '全部' ? lessons.value : lessons.value.filter((lesson) => lesson.category === activeCategory.value))
function openLesson(id: string) { void Taro.navigateTo({ url: `/pages/lesson/index?id=${id}` }) }
useDidShow(() => { void loadCatalog(true) })
</script>
<style lang="scss">
@import '../../styles/tokens.scss';
.page{padding:16px 20px 32px}.intro{padding:19px;border-radius:17px;background:linear-gradient(140deg,$dark,#58766c);color:#fff}.eyebrow{display:block;color:#c2d0c3;font-size:8px;letter-spacing:1.5px}.title{display:block;margin-top:9px;font-size:19px;font-weight:750}.copy{display:block;margin-top:7px;color:rgba(255,255,255,.76);font-size:10px;line-height:1.6}.filters{margin:15px 0 10px;white-space:nowrap}.filter{display:inline-block;margin-right:7px;padding:8px 13px;border:1px solid $line;border-radius:20px;background:$card;color:$body;font-size:10px}.filter.selected{border-color:$green;background:$green-soft;color:$green;font-weight:700}.count{margin:13px 1px 9px;color:$muted;font-size:9px}.lesson-card{margin-top:10px;padding:15px;border:1px solid $line;border-radius:15px;background:$card}.lesson-head,.lesson-foot{display:flex;align-items:center;justify-content:space-between}.tag{padding:5px 8px;border-radius:6px;background:$green-soft;color:$green;font-size:9px}.time{color:$muted;font-size:9px}.lesson-title{display:block;margin-top:12px;font-size:14px;font-weight:750}.lesson-desc{display:block;margin-top:5px;color:$body;font-size:10px}.lesson-foot{margin-top:13px;padding-top:10px;border-top:1px solid $line;color:$muted;font-size:9px}.arrow{color:$green;font-weight:700}
</style>
