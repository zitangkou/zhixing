<template>
  <view class="page">
    <view class="head"><text class="eyebrow">{{ lesson.category }} · {{ lesson.level }} · {{ lesson.time }}</text><text class="title">{{ lesson.title }}</text><text class="subtitle">{{ lesson.subtitle }}</text></view>
    <view class="section"><text class="label">先理解一个原理</text><text class="body">{{ lesson.principle }}</text></view>
    <view class="section"><text class="label">跟着做，三步就够</text><view v-for="(step, i) in lesson.steps" :key="step" class="step"><text class="num">0{{ i + 1 }}</text><text class="body">{{ step }}</text></view></view>
    <view class="task"><text class="label">今日拍摄任务</text><text class="body">{{ lesson.task }}</text></view>
    <view class="section"><text class="label">拍完这样复盘</text><text class="body">{{ lesson.review }}</text></view>
    <view class="bottom"><view class="primary" @tap="startPractice">我去拍一张 <text>↗</text></view></view>
  </view>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { lessons, loadCatalog } from '@/data/catalog'
definePageConfig({ navigationBarTitleText: '技巧练习' })
const lessonId = Taro.getCurrentInstance().router?.params?.id || lessons.value[0].id
const lesson = computed(() => lessons.value.find((item) => item.id === lessonId) || lessons.value[0])
function startPractice() { void Taro.navigateTo({ url: `/pages/practice/index?lessonId=${lesson.value.id}` }) }
useDidShow(() => { void loadCatalog(true) })
</script>
<style lang="scss">
@import '../../styles/tokens.scss';
.page{padding:18px 20px 100px}.head{padding:19px;border-radius:18px;color:#f9f5ea;background:linear-gradient(145deg,$dark,#58776c)}.eyebrow{font-size:9px;color:#bfd1c3;letter-spacing:1px}.title{display:block;margin-top:10px;font-size:22px;font-weight:750;line-height:1.35}.subtitle{display:block;margin-top:8px;color:rgba(255,255,255,.72);font-size:11px;line-height:1.5}.section,.task{margin-top:14px;padding:16px;border-radius:15px;background:$card}.label{display:block;margin-bottom:9px;color:$green;font-size:11px;font-weight:750}.body{display:block;color:$body;font-size:11px;line-height:1.75}.step{display:flex;gap:10px;padding:10px 0;border-top:1px solid $line}.step:first-of-type{border:0}.num{color:$gold;font-size:10px;font-weight:750}.task{background:#efe8d8}.task .body{color:#514a3e}.bottom{position:fixed;left:0;right:0;bottom:0;padding:10px 20px calc(10px + env(safe-area-inset-bottom));background:rgba(244,241,235,.95)}.primary{height:45px;display:flex;align-items:center;justify-content:center;gap:16px;border-radius:12px;background:$green;color:#fff;font-size:12px;font-weight:700}
</style>
