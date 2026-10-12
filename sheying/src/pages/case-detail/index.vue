<template>
  <view v-if="item" class="page">
    <image class="hero-image" :src="item.imageUrl" mode="widthFix"/>
    <view class="credit">作品：{{ item.author }} · {{ item.licenseNote }}</view>
    <view class="heading"><text class="tag">{{ item.category }} · {{ item.level }}</text><text class="title">{{ item.title }}</text></view>
    <view class="section"><text class="label">先观察画面</text><view v-for="(text, index) in item.observations" :key="index" class="point"><text class="point-no">0{{ index + 1 }}</text><text class="body">{{ text }}</text></view></view>
    <view class="section"><text class="label">拍摄信息</text><view v-if="Object.keys(item.exif).length"><view v-for="(value, key) in item.exif" :key="key" class="meta-row"><text>{{ key }}</text><text>{{ value }}</text></view></view><text v-else class="body muted">原图没有可核验的 EXIF 参数，无法仅凭成片确认具体设置。</text></view>
    <view v-if="item.inferences.length" class="section"><text class="label">可能的拍摄思路</text><view v-for="(guess, index) in item.inferences" :key="index" class="inference"><text class="inference-title">推断 · {{ guess.statement }}（{{ guess.confidence }}置信）</text><text class="body">依据：{{ guess.evidence }}</text><text class="disclaimer">这是根据画面作出的推断，不代表已确认的拍摄过程。</text></view></view>
    <view class="task"><text class="label">今天练一个点 · {{ item.durationMin }} 分钟</text><text class="task-title">{{ item.practiceTitle }}</text><text class="body">{{ item.practiceGoal }}</text><view v-for="(step, index) in item.practiceSteps" :key="index" class="step"><text class="point-no">0{{ index + 1 }}</text><text class="body">{{ step }}</text></view><text class="task-tip">本次只重点改变：{{ item.practiceVariable }}</text></view>
    <view class="section"><text class="label">拍完检查</text><view v-for="(criterion, index) in item.criteria" :key="index" class="check"><text>□</text><text class="body">{{ criterion }}</text></view></view>
    <view class="source" @tap="openSource">复制作品来源链接 ›</view>
    <view class="bottom"><view class="primary" @tap="startPractice">开始这项练习 <text>→</text></view></view>
  </view>
  <view v-else class="empty">案例暂不可用，请返回案例列表刷新。</view>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { photoCases, loadCatalog } from '@/data/catalog'
definePageConfig({ navigationBarTitleText: '作品拆解' })
const caseId = Taro.getCurrentInstance().router?.params?.id || ''
const item = computed(() => photoCases.value.find((row) => row.id === caseId))
function startPractice() { if (item.value) void Taro.navigateTo({ url: `/pages/practice/index?caseId=${item.value.id}` }) }
function openSource() { if (item.value?.sourceUrl) void Taro.setClipboardData({ data: item.value.sourceUrl }) }
useDidShow(() => { void loadCatalog(true) })
</script>
<style lang="scss">
@import '../../styles/tokens.scss';
.page{padding:0 20px 90px}.hero-image{display:block;width:100%;max-height:380px;border-radius:0 0 16px 16px;background:#e9e5dc}.credit{padding:8px 2px;color:$muted;font-size:9px;line-height:1.5}.heading{padding:13px 0 4px}.tag{padding:5px 8px;border-radius:6px;background:$green-soft;color:$green;font-size:9px}.title{display:block;margin-top:10px;font-size:20px;font-weight:750;line-height:1.4}.section,.task{margin-top:13px;padding:15px;border-radius:14px;background:$card}.label{display:block;margin-bottom:10px;color:$green;font-size:11px;font-weight:750}.body{display:block;color:$body;font-size:10px;line-height:1.7}.point,.step,.check{display:flex;gap:9px;margin-top:8px}.point-no{color:$gold;font-size:10px;font-weight:750;flex:none}.meta-row{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid $line;color:$body;font-size:10px}.meta-row:last-child{border:0}.muted{color:$muted}.inference{margin-top:10px;padding:11px;border-radius:10px;background:#f2eee5}.inference-title{display:block;margin-bottom:6px;color:$body;font-size:10px;font-weight:700}.disclaimer{display:block;margin-top:6px;color:$muted;font-size:9px}.task{background:#efe8d8}.task .label{color:#526b5e}.task-title{display:block;margin-bottom:7px;font-size:13px;font-weight:750}.task-tip{display:block;margin-top:10px;color:#735e36;font-size:10px;font-weight:700}.source{padding:16px 0;color:$muted;text-align:center;font-size:10px}.bottom{position:fixed;left:0;right:0;bottom:0;padding:10px 20px calc(10px + env(safe-area-inset-bottom));background:rgba(244,241,235,.96)}.primary{height:45px;display:flex;align-items:center;justify-content:center;gap:12px;border-radius:12px;background:$green;color:#fff;font-size:12px;font-weight:700}.empty{padding:45px 20px;color:$muted;text-align:center;font-size:12px}
</style>
