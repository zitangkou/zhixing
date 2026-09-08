<template>
  <view class="page">
    <view class="eyebrow">申论学习 · 免费开放</view>
    <view class="page-title">读一篇，拆一篇，练一句</view>
    <view class="page-intro">每篇内容均经过教研整理，先看原文，再对照三刀示范，最后完成一道短练习。</view>

    <view class="section-head">
      <view class="section-title">三刀精读</view>
      <view class="section-meta">{{ articles.length }} 篇</view>
    </view>
    <view v-if="loading" class="card state-card">正在加载学习内容…</view>
    <view v-else-if="error" class="card state-card" @tap="load">{{ error }}，点击重试</view>
    <view v-else-if="!articles.length" class="card state-card">已审核的示范正在准备中</view>
    <view
      v-for="article in articles"
      :key="article.id"
      class="card article-card"
      @tap="open(article.id)"
    >
      <view class="article-meta">{{ article.source }} · {{ article.publishDate }} · 免费</view>
      <view class="card-title">{{ article.title }}</view>
      <view class="card-desc">{{ article.summary || '进入文章，完成原文、三刀示范与短练习' }}</view>
      <view class="article-tags">
        <text v-for="tag in article.tags.slice(0, 3)" :key="tag">{{ tag }}</text>
      </view>
    </view>

    <template v-if="loggedIn">
      <view class="section-head">
        <view class="section-title">个人开采</view>
        <view class="section-meta">原版工具 · {{ personalArticles.length }} 篇</view>
      </view>
      <view v-if="personalLoading" class="card state-card">正在加载个人精读库…</view>
      <view
        v-for="article in personalArticles"
        :key="`personal-${article.id}`"
        class="card article-card"
        @tap="openPersonal(article.id)"
      >
        <view class="article-meta">{{ article.source }} · {{ article.publishDate }}</view>
        <view class="card-title">{{ article.title }}</view>
        <view class="card-desc">进入原版页面，可复制、记入语料并创建个人三刀开采。</view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { api, type RmrbArticle, type ShenlunLearningArticle } from '@/api'
import { isLoggedIn } from '@/utils/auth'

const articles = ref<ShenlunLearningArticle[]>([])
const loading = ref(false)
const error = ref('')
const loggedIn = ref(isLoggedIn())
const personalArticles = ref<RmrbArticle[]>([])
const personalLoading = ref(false)

function open(id: string) {
  Taro.navigateTo({ url: `/pages/learning/example?id=${encodeURIComponent(id)}` })
}

function openPersonal(id: string) {
  Taro.navigateTo({ url: `/pages/reading/detail?id=${encodeURIComponent(id)}` })
}

async function load() {
  loggedIn.value = isLoggedIn()
  loading.value = true
  error.value = ''
  const response = await api.listLearningArticles()
  loading.value = false
  if (response.code === 0 && response.data) articles.value = response.data
  else error.value = response.message || '内容加载失败'
  personalArticles.value = []
  if (loggedIn.value) {
    personalLoading.value = true
    const personal = await api.listArticles()
    personalLoading.value = false
    if (personal.code === 0 && personal.data) personalArticles.value = personal.data
  }
}

useDidShow(() => void load())
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-intro {
  margin-top: 10px;
  color: $text-secondary;
  font-size: 13px;
  line-height: 1.7;
}

.state-card { cursor: pointer; }
</style>
