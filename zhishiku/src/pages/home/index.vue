<template>
  <view class="zk-page">
    <view class="zk-topbar">
      <view class="zk-brand"><view class="zk-brand-mark">知</view><view><text class="zk-brand-title">知库</text><text class="zk-brand-subtitle">AI 知识库</text></view></view>
      <button class="zk-avatar" @tap="openMine">林</button>
    </view>

    <view class="zk-hero">
      <view class="zk-eyebrow">KNOWLEDGE, IN YOUR HAND</view>
      <view class="zk-hero-title">把知识，<text>读得更深</text></view>
      <view class="zk-hero-desc">文档搜索 · 分类阅读 · 个人资料</view>
      <view class="zk-hero-mark">✳</view>
    </view>

    <view class="zk-search">
      <text class="zk-search-icon">⌕</text>
      <input :value="query" placeholder="搜索知识、主题或关键词" confirm-type="search" @input="onQueryInput" @confirm="loadCatalog" />
      <text v-if="query" class="zk-clear" @tap="clearQuery">×</text>
    </view>

    <view class="zk-section-head">
      <view><text class="zk-eyebrow">KNOWLEDGE CATALOG</text><text class="zk-section-title">知识目录</text></view>
      <text class="zk-section-link" @tap="loadCatalog">{{ docs.length }} 篇 ›</text>
    </view>
    <view v-if="featured" class="zk-feature-card" @tap="openDocument(featured)">
      <view class="zk-feature-tag">文档速览</view>
      <view class="zk-feature-kind">{{ featured.format.toUpperCase() }} · {{ featured.category }}</view>
      <view class="zk-feature-title">{{ featured.title }}</view>
      <view class="zk-feature-desc">{{ featured.description || '打开文档，开始一段深度阅读。' }}</view>
      <view class="zk-feature-footer">知库精选 <text>·</text> {{ formatSize(featured.fileSize) }}</view>
      <view class="zk-feature-index">01</view>
    </view>
    <view v-else class="zk-feature-card zk-feature-empty">
      <view class="zk-feature-tag">知库 · AI 知识库</view>
      <view class="zk-feature-title">让好知识，<text class="zk-feature-title-line">随时可以找到</text></view>
      <view class="zk-feature-desc">登录后浏览精选文档，或上传自己的资料。</view>
      <button class="zk-feature-cta" @tap="openAuth">登录后开始阅读 ›</button>
      <view class="zk-feature-index">知</view>
    </view>

    <view class="zk-stats"><view><text>{{ docs.length }}</text><text class="zk-stat-label">精选知识</text></view><view class="zk-stats-divider"></view><view><text>MD · PDF</text><text class="zk-stat-label">常用格式</text></view><view class="zk-stats-divider"></view><view><text>只读</text><text class="zk-stat-label">安全阅读</text></view></view>

    <view class="zk-section-head zk-trending-head">
      <view><text class="zk-eyebrow">ALL DOCUMENTS</text><text class="zk-section-title">全部文档</text></view>
      <text class="zk-section-link" @tap="openMine">我的资料 ›</text>
    </view>
    <scroll-view scroll-x class="zk-chips">
      <view v-for="category in categories" :key="category" class="zk-chip" :class="{ active: activeCategory === category }" @tap="selectCategory(category)">{{ category }}</view>
    </scroll-view>
    <view v-if="loading && !filteredDocs.length" class="zk-state">正在加载知识库…</view>
    <view v-else-if="loadError && !filteredDocs.length" class="zk-state" @tap="loadCatalog">{{ loadError }}<text>点击重试</text></view>
    <view v-else-if="!filteredDocs.length" class="zk-state">暂时没有匹配的文档<text>登录后可上传自己的资料</text></view>
    <view v-else class="zk-doc-list">
      <view v-for="doc in filteredDocs" :key="doc.id" class="zk-doc-row" @tap="openDocument(doc)">
        <view class="zk-doc-cover" :class="coverClass(doc.format)">{{ doc.format.toUpperCase() }}</view>
        <view class="zk-doc-info"><text class="zk-doc-category">{{ doc.category }} · {{ doc.extractionStatus === 'needs_ocr' ? '待 OCR' : '可阅读' }}</text><text class="zk-doc-title">{{ doc.title }}</text><text class="zk-doc-meta">{{ doc.description || doc.fileName }}</text></view>
        <text class="zk-arrow">›</text>
      </view>
    </view>
    <view class="zk-footer">知库 · 让知识有序流动</view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { usePullDownRefresh, useReachBottom } from '@tarojs/taro'
import { libraryApi, type LibraryDocument } from '@/api'
import { showToast } from '@/utils/feedback'

definePageConfig({ navigationBarTitleText: '知库', enablePullDownRefresh: true, onReachBottomDistance: 80 })

const docs = ref<LibraryDocument[]>([])
const query = ref('')
const activeCategory = ref('全部')
const loading = ref(false)
const loadError = ref('')
const categories = computed(() => ['全部', ...new Set(docs.value.map((doc) => doc.category).filter(Boolean))])
const filteredDocs = computed(() => activeCategory.value === '全部' ? docs.value : docs.value.filter((doc) => doc.category === activeCategory.value))
const featured = computed(() => docs.value[0])

async function loadCatalog() {
  loading.value = true
  loadError.value = ''
  try {
    docs.value = await libraryApi.listCatalog(query.value.trim())
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '知识库暂不可用'
    if (loadError.value.includes('登录')) void Taro.navigateTo({ url: '/pages/auth/index' })
    else if (loadError.value.includes('服务地址')) showToast(loadError.value)
  } finally {
    loading.value = false
  }
}
function onQueryInput(event: { detail: { value: string } }) { query.value = event.detail.value }
function clearQuery() { query.value = ''; void loadCatalog() }
function selectCategory(category: string) { activeCategory.value = category }
function openDocument(doc: LibraryDocument) {
  void Taro.navigateTo({ url: `/pages/document/detail?id=${encodeURIComponent(doc.id)}` })
}
function openMine() { void Taro.switchTab({ url: '/pages/mine/index' }) }
function openAuth() { void Taro.navigateTo({ url: '/pages/auth/index' }) }
function coverClass(format: string) { return `format-${format.toLowerCase()}` }
function formatSize(bytes: number) { return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB` }

onMounted(loadCatalog)
usePullDownRefresh(async () => { try { await loadCatalog() } finally { Taro.stopPullDownRefresh() } })
useReachBottom(() => { /* pagination is added with the catalog admin's paging controls */ })
</script>

<style lang="scss">
@import '../../styles/tokens.scss';
.zk-page { min-height: 100vh; padding: 0 20px 30px; background: $bg; }
.zk-topbar { height: 68px; display:flex; align-items:center; justify-content:space-between; }
.zk-brand { display:flex; align-items:center; gap:10px; }
.zk-brand-mark { width:38px; height:38px; display:grid; place-items:center; border-radius:13px; background:$brand; color:#fff; font-size:19px; font-weight:800; }
.zk-brand-title,.zk-brand-subtitle { display:block; }
.zk-brand-title { font-size:16px; font-weight:700; }
.zk-brand-subtitle { margin-top:2px; color:$muted; font-size:10px; letter-spacing:1px; }
.zk-avatar { width:36px; height:36px; padding:0; border:0; border-radius:50%; background:#efc5b9; color:#74443d; font-weight:700; line-height:36px; }
.zk-hero { position:relative; padding:17px 0 19px; }
.zk-eyebrow { display:block; color:#b1aeb0; font-size:9px; font-weight:700; letter-spacing:1.4px; }
.zk-hero-title { margin-top:8px; font-size:26px; font-weight:750; letter-spacing:-.7px; }
.zk-hero-title text { color:$brand; }
.zk-hero-desc { margin-top:6px; color:#898c93; font-size:11px; }
.zk-hero-mark { position:absolute; top:14px; right:9px; color:$brand-soft; font-size:68px; }
.zk-search { height:48px; padding:0 13px; display:flex; align-items:center; gap:9px; border:1px solid $border; border-radius:14px; background:$card; box-shadow:0 5px 16px rgba($shadow,.035); }
.zk-search-icon { color:#b8bac0; font-size:24px; }
.zk-search input { flex:1; min-width:0; font-size:12px; }
.zk-clear { color:#a5a7ad; font-size:22px; }
.zk-section-head { display:flex; align-items:flex-end; justify-content:space-between; margin:25px 0 11px; }
.zk-section-title { display:block; margin-top:4px; font-size:17px; font-weight:700; }
.zk-section-link { color:#999ca3; font-size:10px; padding-bottom:2px; }
.zk-feature-card { position:relative; min-height:212px; overflow:hidden; padding:16px 17px; border-radius:20px; color:#fff; background:linear-gradient(118deg,$slate-dark 0%,$slate 59%,$sage 100%); box-shadow:0 12px 25px rgba($slate-dark,.15); }
.zk-feature-card:after { content:''; position:absolute; top:23px; right:-46px; width:215px; height:168px; border:1px solid rgba(255,255,255,.15); border-radius:50%; box-shadow:0 0 0 16px rgba(255,255,255,.025),0 0 0 32px rgba(255,255,255,.02); }
.zk-feature-empty { background:linear-gradient(118deg,$slate-dark,$sage-dark); }
.zk-feature-tag { display:inline-block; padding:5px 8px; border-radius:6px; background:rgba(255,255,255,.15); font-size:9px; }
.zk-feature-kind { position:relative; z-index:1; margin-top:15px; color:rgba(255,255,255,.68); font-size:9px; }
.zk-feature-title { position:relative; z-index:1; max-width:75%; margin-top:8px; font-size:22px; font-weight:700; line-height:1.35; }
.zk-feature-title-line { display:block; }
.zk-feature-desc { position:relative; z-index:1; max-width:82%; margin-top:6px; color:rgba(255,255,255,.73); font-size:10px; line-height:1.5; }
.zk-feature-footer { position:relative; z-index:1; margin-top:13px; color:rgba(255,255,255,.8); font-size:9px; }
.zk-feature-footer text { margin:0 5px; }
.zk-feature-index { position:absolute; right:13px; bottom:1px; color:rgba(255,255,255,.07); font-size:57px; font-weight:800; }
.zk-feature-cta { position:relative; z-index:1; margin:14px 0 0; padding:0 13px; height:34px; line-height:34px; border:0; border-radius:9px; color:$brand; background:#fff; font-size:10px; }
.zk-stats { display:flex; align-items:center; justify-content:space-around; margin:15px 2px 0; }
.zk-stats view { display:flex; flex-direction:column; gap:3px; }
.zk-stats text { font-size:13px; font-weight:700; }
.zk-stat-label { color:#a1a3a9; font-size:9px; }
.zk-stats-divider { height:24px; border-left:1px solid #e7e8eb; }
.zk-trending-head { margin-top:26px; }
.zk-chips { width:100%; white-space:nowrap; margin:12px 0 7px; }
.zk-chip { display:inline-block; margin-right:8px; padding:7px 14px; border:1px solid $border; border-radius:18px; color:$muted; font-size:10px; }
.zk-chip.active { border-color:$brand; color:$brand-dark; background:$brand-light; font-weight:600; }
.zk-doc-row { display:flex; min-height:82px; align-items:center; gap:11px; border-bottom:1px solid #eceef1; }
.zk-doc-cover { width:54px; height:58px; display:grid; place-items:center; flex-shrink:0; border-radius:12px; color:#fff; background:linear-gradient(145deg,$sage-light,$sage); font-size:10px; font-weight:700; }
.format-pdf { background:linear-gradient(145deg,$amber-light,$amber); }
.format-docx { background:linear-gradient(145deg,$blue-light,$blue); }
.zk-doc-info { min-width:0; flex:1; display:flex; flex-direction:column; gap:4px; }
.zk-doc-category { color:#92959c; font-size:9px; }
.zk-doc-title { overflow:hidden; color:$ink; font-size:12px; font-weight:650; text-overflow:ellipsis; white-space:nowrap; }
.zk-doc-meta { overflow:hidden; color:#a2a4aa; font-size:9px; text-overflow:ellipsis; white-space:nowrap; }
.zk-arrow { color:#b6b8be; font-size:21px; }
.zk-state { padding:24px 8px; color:#989ba2; text-align:center; font-size:11px; line-height:1.8; }
.zk-state text { display:block; color:$brand; }
.zk-footer { margin-top:25px; color:#c0c1c6; font-size:9px; letter-spacing:1px; text-align:center; }
</style>
