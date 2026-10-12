<template>
  <view class="page">
    <view class="intro"><text class="eyebrow">LEARN FROM PHOTOGRAPHS</text><text class="title">先看懂，再试着拍。</text><text class="copy">每个案例都聚焦一个练习点。摄影参数只展示来源可确认的信息。</text></view>
    <scroll-view scroll-x class="filters"><text v-for="item in categories" :key="item" class="filter" :class="{ selected: category === item }" @tap="category = item">{{ item }}</text></scroll-view>
    <view v-if="!filtered.length" class="empty">还没有发布的作品案例。<text>案例上线后会出现在这里。</text></view>
    <view v-for="item in filtered" :key="item.id" class="case-card" @tap="open(item.id)"><image class="cover" :src="item.imageUrl" mode="aspectFill"/><view class="case-main"><text class="tag">{{ item.category }} · {{ item.level }}</text><text class="case-title">{{ item.title }}</text><text class="case-author">{{ item.author }} · {{ item.durationMin }} 分钟练习</text><text class="case-goal">练习：{{ item.practiceTitle }}</text></view></view>
  </view>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { photoCases, loadCatalog } from '@/data/catalog'
definePageConfig({ navigationBarTitleText: '作品拆解' })
const category = ref('全部')
const categories = computed(() => ['全部', ...new Set(photoCases.value.map((item) => item.category))])
const filtered = computed(() => category.value === '全部' ? photoCases.value : photoCases.value.filter((item) => item.category === category.value))
function open(id: string) { void Taro.navigateTo({ url: `/pages/case-detail/index?id=${id}` }) }
useDidShow(() => { void loadCatalog(true) })
</script>
<style lang="scss">
@import '../../styles/tokens.scss';
.page{padding:16px 20px 32px}.intro{padding:19px;border-radius:17px;background:linear-gradient(140deg,$dark,#58766c);color:#fff}.eyebrow{display:block;color:#c2d0c3;font-size:8px;letter-spacing:1.5px}.title{display:block;margin-top:9px;font-size:19px;font-weight:750}.copy{display:block;margin-top:7px;color:rgba(255,255,255,.76);font-size:10px;line-height:1.6}.filters{margin:15px 0 8px;white-space:nowrap}.filter{display:inline-block;margin-right:7px;padding:8px 13px;border:1px solid $line;border-radius:20px;background:$card;color:$body;font-size:10px}.filter.selected{border-color:$green;background:$green-soft;color:$green;font-weight:700}.case-card{display:flex;gap:12px;margin-top:11px;padding:10px;border-radius:15px;background:$card}.cover{width:92px;height:102px;flex:none;border-radius:10px;background:#e9e5dc}.case-main{flex:1;min-width:0}.tag{display:inline-block;padding:4px 7px;border-radius:6px;background:$green-soft;color:$green;font-size:9px}.case-title{display:block;margin-top:8px;font-size:13px;font-weight:750}.case-author,.case-goal{display:block;margin-top:6px;color:$muted;font-size:9px;line-height:1.5}.case-goal{color:$body}.empty{padding:35px 16px;text-align:center;border-radius:14px;background:$card;color:$body;font-size:12px}.empty text{display:block;margin-top:8px;color:$muted;font-size:10px}
</style>
