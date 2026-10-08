<template>
  <view class="zk-mine-page">
    <view class="zk-mine-top"><view><text class="zk-eyebrow">YOUR SPACE</text><text class="zk-mine-title">我的</text></view><text class="zk-help" @tap="showHelp">帮助</text></view>
    <view class="zk-profile-card">
      <view class="zk-profile-mark">{{ isLoggedIn ? '林' : '知' }}</view>
      <view class="zk-profile-copy"><text class="zk-profile-name">{{ isLoggedIn ? username || '知库用户' : '欢迎来到知库' }}</text><text class="zk-profile-desc">{{ isLoggedIn ? '个人知识空间' : '登录后管理与阅读你的资料' }}</text></view>
      <button v-if="!isLoggedIn" class="zk-login-btn" @tap="openAuth">微信登录 ›</button>
      <text v-else class="zk-member" @tap="logout">退出登录</text>
    </view>

    <view class="zk-mine-section-head"><view><text class="zk-eyebrow">YOUR LIBRARY</text><text class="zk-section-title">我的文档</text></view><button class="zk-upload-btn" :disabled="uploading" @tap="chooseFile">{{ uploading ? '上传中…' : '＋ 上传资料' }}</button></view>
    <view class="zk-upload-hint">支持 MD、TXT、PDF、DOCX，单文件最大 20 MB</view>
    <view v-if="!isLoggedIn" class="zk-mine-empty"><text>登录后可上传文档并同步阅读进度</text><button @tap="openAuth">立即登录</button></view>
    <view v-else-if="loading && !myDocs.length" class="zk-mine-empty">正在读取你的资料…</view>
    <view v-else-if="!myDocs.length" class="zk-mine-empty"><text>还没有上传文档</text><button @tap="chooseFile">选择一份资料</button></view>
    <view v-else class="zk-my-docs">
      <view v-for="doc in myDocs" :key="doc.id" class="zk-my-doc" @tap="openDocument(doc)">
        <view class="zk-my-format" :class="`format-${doc.format}`">{{ doc.format.toUpperCase() }}</view>
        <view class="zk-my-doc-copy"><text class="zk-my-doc-title">{{ doc.title }}</text><text class="zk-my-doc-meta">{{ doc.extractionStatus === 'needs_ocr' ? '扫描版 PDF · 待 OCR' : '已解析 · 只对本人可见' }}</text></view>
        <text class="zk-remove" @tap.stop="removeDocument(doc)">删除</text>
      </view>
    </view>

    <view class="zk-settings-title"><text class="zk-eyebrow">PREFERENCES</text><text class="zk-section-title">相关配置</text></view>
    <view class="zk-setting-card">
      <view class="zk-setting-row" @tap="openPrivacy"><text class="zk-setting-icon icon-blue">隐</text><view><text class="zk-setting-name">隐私政策</text><text class="zk-setting-desc">了解资料收集、使用与删除方式</text></view><text class="zk-setting-arrow">›</text></view>
      <view class="zk-setting-row" @tap="openTerms"><text class="zk-setting-icon icon-gray">约</text><view><text class="zk-setting-name">用户服务协议</text><text class="zk-setting-desc">知库服务使用规则</text></view><text class="zk-setting-arrow">›</text></view>
      <view class="zk-setting-row" @tap="showAbout"><text class="zk-setting-icon icon-coral">i</text><view><text class="zk-setting-name">关于知库</text><text class="zk-setting-desc">版本 0.1.0 · 让知识有序流动</text></view><text class="zk-setting-arrow">›</text></view>
    </view>
    <view class="zk-mine-footer">知库 · 让知识有序流动</view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { libraryApi, type LibraryDocument } from '@/api'
import { showConfirm, showToast } from '@/utils/feedback'

definePageConfig({ navigationBarTitleText: '我的' })

const myDocs = ref<LibraryDocument[]>([])
const loading = ref(false)
const uploading = ref(false)
const token = ref(Taro.getStorageSync('zhiku_token') || '')
const username = ref(Taro.getStorageSync('zhiku_username') || '')
const isLoggedIn = computed(() => !!token.value)

function syncAuth() {
  token.value = Taro.getStorageSync('zhiku_token') || ''
  username.value = Taro.getStorageSync('zhiku_username') || ''
}

async function loadMyDocs() {
  syncAuth()
  if (!isLoggedIn.value) { myDocs.value = []; return }
  loading.value = true
  try { myDocs.value = await libraryApi.listMyDocuments() }
  catch (error) { showToast(error instanceof Error ? error.message : '资料读取失败') }
  finally { loading.value = false }
}
async function chooseFile() {
  if (!isLoggedIn.value) { openAuth(); return }
  if (uploading.value) return
  try {
    const selection = await Taro.chooseMessageFile({ count: 1, type: 'file', extension: ['md', 'txt', 'pdf', 'docx'] })
    const file = selection.tempFiles[0]
    if (!file) return
    uploading.value = true
    const result = await libraryApi.uploadMyDocument(file.path, file.name)
    showToast(result.extractionStatus === 'needs_ocr' ? '已上传，扫描版 PDF 待 OCR' : '上传并解析完成', 'success')
    await loadMyDocs()
  } catch (error) {
    const message = error instanceof Error ? error.message : '上传失败'
    if (!message.toLowerCase().includes('cancel')) showToast(message, 'error')
  } finally { uploading.value = false }
}
async function removeDocument(doc: LibraryDocument) {
  const confirmed = await showConfirm('删除文档', `确定删除「${doc.title}」及其原文件吗？`)
  if (!confirmed) return
  try { await libraryApi.deleteMyDocument(doc.id); await loadMyDocs(); showToast('文档已删除', 'success') }
  catch (error) { showToast(error instanceof Error ? error.message : '删除失败', 'error') }
}
function openDocument(doc: LibraryDocument) { void Taro.navigateTo({ url: `/pages/document/detail?id=${encodeURIComponent(doc.id)}&source=mine` }) }
function openAuth() { void Taro.navigateTo({ url: '/pages/auth/index' }) }
function openPrivacy() { void Taro.navigateTo({ url: '/pages/legal/privacy' }) }
function openTerms() { void Taro.navigateTo({ url: '/pages/legal/terms' }) }
function logout() {
  Taro.removeStorageSync('zhiku_token')
  Taro.removeStorageSync('zhiku_username')
  syncAuth()
  myDocs.value = []
  showToast('已退出登录', 'success')
}
function showHelp() { showToast('帮助与联系渠道暂未开放') }
function showAbout() { showToast('知库 · AI 知识库') }

onMounted(loadMyDocs)
useDidShow(() => { syncAuth(); void loadMyDocs() })
</script>

<style lang="scss" scoped>
@import '../../styles/tokens.scss';
.zk-mine-page { min-height:100vh; padding:0 20px 32px; background:$bg; }
.zk-mine-top { display:flex; align-items:center; justify-content:space-between; padding:25px 0 17px; }
.zk-eyebrow { display:block; color:#b1aeb0; font-size:9px; font-weight:700; letter-spacing:1.4px; }
.zk-mine-title { display:block; margin-top:5px; font-size:24px; font-weight:750; }
.zk-help { color:$muted; font-size:11px; }
.zk-profile-card { display:flex; min-height:82px; align-items:center; gap:11px; padding:15px; border-radius:17px; color:#fff; background:linear-gradient(125deg,#2b4148,#506967); box-shadow:0 10px 22px rgba(43,64,69,.13); }
.zk-profile-mark { width:45px; height:45px; display:grid; place-items:center; border-radius:50%; color:#74443d; background:#efc5b9; font-size:17px; font-weight:700; }
.zk-profile-copy { min-width:0; flex:1; display:flex; flex-direction:column; gap:5px; }
.zk-profile-name { overflow:hidden; font-size:14px; font-weight:700; text-overflow:ellipsis; white-space:nowrap; }
.zk-profile-desc { color:rgba(255,255,255,.68); font-size:9px; }
.zk-login-btn { padding:0 10px; height:31px; line-height:31px; border:0; border-radius:8px; color:#435752; background:#fff; font-size:9px; }
.zk-member { color:rgba(255,255,255,.8); font-size:9px; }
.zk-mine-section-head,.zk-settings-title { display:flex; align-items:flex-end; justify-content:space-between; margin:25px 0 9px; }
.zk-section-title { display:block; margin-top:4px; font-size:17px; font-weight:700; }
.zk-upload-btn { height:31px; margin:0; padding:0 10px; line-height:31px; border:0; border-radius:8px; color:#fff; background:$brand; font-size:10px; }
.zk-upload-hint { margin:0 0 8px; color:$muted; font-size:9px; }
.zk-mine-empty { padding:25px 10px; border:1px dashed $border; border-radius:13px; color:$muted; text-align:center; font-size:10px; }
.zk-mine-empty button { display:block; height:31px; margin:12px auto 0; padding:0 13px; line-height:31px; border:1px solid $border; border-radius:8px; color:$brand; background:#fff; font-size:10px; }
.zk-my-docs,.zk-setting-card { overflow:hidden; border:1px solid #eff0f2; border-radius:14px; background:#fff; }
.zk-my-doc { display:flex; min-height:66px; align-items:center; gap:10px; padding:9px 11px; border-bottom:1px solid #f0f1f3; }
.zk-my-doc:last-child { border-bottom:0; }
.zk-my-format { width:41px; height:43px; display:grid; flex-shrink:0; place-items:center; border-radius:9px; color:#fff; background:#78968f; font-size:8px; font-weight:700; }
.format-pdf { background:#c68c58; }.format-docx { background:#64879c; }.format-txt { background:#8495a5; }
.zk-my-doc-copy { min-width:0; flex:1; display:flex; flex-direction:column; gap:5px; }
.zk-my-doc-title { overflow:hidden; color:#303239; font-size:11px; font-weight:650; text-overflow:ellipsis; white-space:nowrap; }
.zk-my-doc-meta { color:#9a9da4; font-size:9px; }
.zk-remove { padding:7px 2px 7px 8px; color:#bd7770; font-size:9px; }
.zk-settings-title { margin-top:26px; }
.zk-setting-row { display:flex; min-height:59px; align-items:center; gap:10px; margin:0 11px; border-bottom:1px solid #f0f1f3; }
.zk-setting-row:last-child { border-bottom:0; }
.zk-setting-icon { width:32px; height:32px; display:grid; place-items:center; border-radius:9px; font-size:13px; }
.icon-coral { color:#d96e60; background:#fff0ed; }.icon-blue { color:#6b8aa1; background:#eaf1f5; }.icon-gray { color:#898d96; background:#f0f1f3; }
.zk-setting-row view { flex:1; }
.zk-setting-name,.zk-setting-desc { display:block; }.zk-setting-name { color:#36383e; font-size:10px; font-weight:600; }.zk-setting-desc { margin-top:4px; color:#a3a5ac; font-size:8px; }
.zk-setting-arrow { color:#b7b9bf; font-size:19px; }
.zk-mine-footer { margin-top:26px; color:#c0c1c6; text-align:center; font-size:9px; letter-spacing:1px; }
</style>
