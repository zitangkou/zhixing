<template>
  <page-meta v-if="isWeapp" :page-style="pageMeta.pageStyle" :background-color="pageMeta.backgroundColor" :background-color-top="pageMeta.backgroundColorTop" :background-color-bottom="pageMeta.backgroundColorBottom" :background-text-style="pageMeta.backgroundTextStyle" />
  <view class="se-list-page" :class="themeClass">
    <view class="se-intro"><text class="se-title">申论题型练习</text><text class="se-subtitle">读材料、按设问作答，提交后对照依据和参考答案。</text></view>
    <scroll-view class="se-filters" scroll-x :show-scrollbar="false"><view class="se-filter-row"><view v-for="item in filters" :key="item.value" class="se-chip" :class="{active:activeType===item.value}" @tap="selectType(item.value)">{{ item.label }}</view></view></scroll-view>
    <view v-if="loading" class="se-state">正在加载练习…</view>
    <view v-else-if="!items.length" class="se-state"><text class="se-state-title">暂时没有已发布练习</text><text class="se-state-desc">练习经教研审核后会在这里开放。</text></view>
    <view v-else class="se-cards"><view v-for="item in items" :key="item.id" class="se-card" @tap="open(item.id)"><view class="se-card-top"><text class="se-kind">{{ typeName(item.question_type) }}</text><text v-if="item.is_featured" class="se-featured">今日推荐</text><text class="se-time">约 {{ item.estimated_minutes }} 分钟</text></view><text class="se-card-title">{{ item.title }}</text><text class="se-source">{{ item.source_title }}<text v-if="item.source_date"> · {{ item.source_date }}</text></text><view class="se-card-bottom"><text>{{ item.difficulty }} · {{ item.max_chars ? `${item.max_chars} 字以内` : '不限字数' }}</text><text class="se-arrow">开始练习 ›</text></view></view></view>
  </view>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { usePullDownRefresh } from '@tarojs/taro'
import { api } from '@/api'
import type { ShenlunExerciseCard } from '@/api/domains/rmrb'
import { useThemeClass, usePageMeta } from '@/utils/brandColor'
import { showToast } from '@/utils/platform'
definePageConfig({ navigationBarTitleText: '申论题型练习', enablePullDownRefresh: true })
const {themeClass}=useThemeClass(),pageMeta=usePageMeta(),isWeapp=process.env.TARO_ENV==='weapp'
const filters=[{label:'全部',value:''},{label:'归纳概括',value:'summary'},{label:'提出对策',value:'countermeasure'},{label:'贯彻执行',value:'implementation'},{label:'申发论述',value:'essay'}]
const activeType=ref(''),items=ref<ShenlunExerciseCard[]>([]),loading=ref(false)
function typeName(v:string){return filters.find(x=>x.value===v)?.label||'申论练习'}
async function load(){loading.value=true;try{const r=await api.listShenlunExercises(activeType.value||undefined);if(r.code===0)items.value=r.data||[];else showToast(r.message||'练习加载失败','error')}catch{showToast('练习加载失败','error')}finally{loading.value=false}}
function selectType(value:string){activeType.value=value;load()}
function open(id:string){Taro.navigateTo({url:`/pages/rmrb/exercise?id=${encodeURIComponent(id)}`})}
onMounted(load)
usePullDownRefresh(async()=>{try{await load()}finally{Taro.stopPullDownRefresh()}})
</script>
<style lang="scss" scoped>
@import '@/styles/variables.scss';
.se-list-page{@include page-padding;padding-bottom:32px}.se-intro{@include card;margin-bottom:12px}.se-title{display:block;font-size:22px;font-weight:700;color:$text-primary}.se-subtitle{display:block;margin-top:6px;font-size:13px;line-height:1.55;color:$text-secondary}.se-filters{margin:0 -16px 12px;padding:0 16px;white-space:nowrap}.se-filter-row{display:flex;gap:8px}.se-chip{@include filter-tab;white-space:nowrap}.se-chip.active{@include brand-chip}.se-cards{display:flex;flex-direction:column;gap:10px}.se-card{@include card;margin:0;padding:16px}.se-card-top{display:flex;align-items:center;gap:8px;margin-bottom:10px}.se-kind{@include brand-chip}.se-featured{@include soft-chip($accent-amber)}.se-time{margin-left:auto;color:$text-muted;font-size:12px}.se-card-title{display:block;font-size:16px;font-weight:700;line-height:1.45;color:$text-primary}.se-source{display:block;margin-top:8px;color:$text-secondary;font-size:12px;line-height:1.45}.se-card-bottom{display:flex;justify-content:space-between;align-items:center;margin-top:14px;padding-top:11px;border-top:1px solid $border-color;color:$text-muted;font-size:12px}.se-arrow{color:$primary-color;font-weight:600}.se-state{@include page-state-box;margin-top:24px}.se-state-title{display:block;font-size:15px;font-weight:600;color:$text-primary}.se-state-desc{display:block;margin-top:6px;font-size:13px;color:$text-muted}
</style>
