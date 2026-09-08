<template>
  <view class="page practice-page">
    <view class="eyebrow">时政复习</view>
    <view class="page-title">每道题都回到原文</view>

    <view v-if="loggedIn" class="task-card">
      <view>
        <text class="task-title">今日练习</text>
        <text class="task-desc">已答 {{ questionStore.answeredToday }} 题 · 当前错题 {{ questionStore.wrongCount }} 道</text>
      </view>
      <text class="task-mark">题</text>
    </view>

    <view class="section-head">
      <view>
        <view class="section-title">练习方式</view>
        <view class="section-meta">保留原版随机练与按文章练</view>
      </view>
    </view>

    <view class="mode-grid" :class="{ single: !loggedIn }">
      <view v-if="loggedIn" class="mode-card" @tap="startRandom">
        <text class="mode-icon">随</text>
        <text class="mode-title">随机练习</text>
        <text class="mode-desc">从已审核题库抽取 10 题</text>
      </view>
      <view class="mode-card" @tap="pickArticle">
        <text class="mode-icon">文</text>
        <text class="mode-title">按文章学习</text>
        <text class="mode-desc">免费读全文或重点，可选五题分辑或全文合集</text>
      </view>
    </view>

    <view v-if="loggedIn" class="section-head">
      <view class="section-title">复习入口</view>
    </view>
    <view v-if="loggedIn" class="card row" @tap="openWrong">
      <view>
        <view class="card-title">文章错题本</view>
        <view class="card-desc">按间隔计划回收错误表述</view>
      </view>
      <view class="tag">进入 ›</view>
    </view>
    <view v-if="loggedIn" class="card row" @tap="openReview">
      <view>
        <view class="card-title">到期文章复习</view>
        <view class="card-desc">按 1、2、4、7、15、30 天回看原文并重做题组</view>
      </view>
      <view class="tag">{{ questionStore.reviewTasks.length }} 项 ›</view>
    </view>
    <view v-if="!loggedIn" class="card guest-card">
      <text class="mode-title">免费学习无需登录</text>
      <text class="mode-desc">作答记录保存在当前设备。账号复习与跨设备同步将在登录后使用。</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { useQuestionStore } from '@/store/question'
import { isLoggedIn } from '@/utils/auth'

const questionStore = useQuestionStore()
const loggedIn = ref(isLoggedIn())

function startRandom() {
  Taro.navigateTo({ url: '/pages/question/taking?mode=random' })
}

function pickArticle() {
  Taro.navigateTo({ url: '/pages/question/article-pick' })
}

function openWrong() {
  Taro.navigateTo({ url: '/pages/question/wrong' })
}

function openReview() {
  Taro.navigateTo({ url: '/pages/question/review' })
}

async function load() {
  loggedIn.value = isLoggedIn()
  if (!loggedIn.value) return
  await Promise.all([
    questionStore.loadWrongQuestions('all'),
    questionStore.fetchReviewTasks(),
  ])
}

onMounted(load)
useDidShow(() => void load())
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.practice-page { padding-bottom: 32px; }
.task-card {
  @include card;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 18px;
  background: linear-gradient(135deg, $primary-light, $primary-faint);
  .task-title { display: block; font-size: 16px; font-weight: 700; }
  .task-desc { display: block; margin-top: 5px; font-size: 12px; color: $text-secondary; }
  .task-mark {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: $primary-color;
    color: $on-primary;
    text-align: center;
    line-height: 38px;
    font-weight: 700;
  }
}
.mode-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.mode-grid.single { grid-template-columns: 1fr; }
.mode-card {
  @include card;
  margin: 0;
  .mode-icon {
    display: block;
    width: 34px;
    height: 34px;
    line-height: 34px;
    text-align: center;
    border-radius: 10px;
    background: $primary-light;
    color: $primary-color;
    font-weight: 700;
    margin-bottom: 12px;
  }
  .mode-title { display: block; font-size: 15px; font-weight: 700; }
  .mode-desc { display: block; margin-top: 5px; color: $text-muted; font-size: 11px; line-height: 1.45; }
}
.guest-card { margin-top: 12px; }
</style>
