<template>
  <view class="zk-reader-page">
    <view v-if="loading" class="zk-reader-state">正在打开文档…</view>
    <view v-else-if="error" class="zk-reader-state" @tap="loadDocument">{{ error }}<text>点击重试</text></view>
    <template v-else-if="document">
      <view class="zk-reader-header">
        <text class="zk-reader-category">{{ document.category }} · {{ document.format.toUpperCase() }}</text>
        <text class="zk-reader-title">{{ document.title }}</text>
        <text class="zk-reader-meta">{{ document.fileName }} · {{ statusText }}</text>
      </view>
      <view v-if="document.extractionStatus === 'needs_ocr'" class="zk-ocr-note">暂时无法从扫描版 PDF 提取文本，OCR 功能接入后即可阅读。</view>
      <scroll-view v-else scroll-y class="zk-reader-scroll">
        <view class="zk-reader-content" user-select="false">
          <view v-for="(line, index) in contentLines" :key="index" class="zk-content-line" :class="line.kind">
            <text>{{ line.text }}</text>
          </view>
        </view>
      </scroll-view>
      <view class="zk-watermark" aria-hidden="true">{{ watermark }}</view>
      <view class="zk-reader-footer">只读阅读 · 页面含动态身份水印</view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { libraryApi, type LibraryDocument } from '@/api'

definePageConfig({ navigationBarTitleText: '文档阅读' })

const router = useRouter()
const document = ref<LibraryDocument | null>(null)
const loading = ref(false)
const error = ref('')
const isPersonal = computed(() => router.params?.source === 'mine')
const statusText = computed(() => document.value?.extractionStatus === 'truncated' ? '内容较长 · 已截取预览' : '安全阅读')
const watermark = computed(() => `${Taro.getStorageSync('zhiku_username') || '知库用户'} · 知库专属阅读`)
const contentLines = computed(() => (document.value?.extractedText || '').split(/\r?\n/).map((raw) => {
  const text = raw.trimEnd()
  if (/^#{1,3}\s/.test(text)) return { kind: 'heading', text: text.replace(/^#{1,3}\s+/, '') }
  if (/^>\s?/.test(text)) return { kind: 'quote', text: text.replace(/^>\s?/, '') }
  if (/^[-*]\s/.test(text)) return { kind: 'bullet', text: `•  ${text.replace(/^[-*]\s+/, '')}` }
  return { kind: text ? 'paragraph' : 'blank', text }
}))

async function loadDocument() {
  const id = router.params?.id || ''
  if (!id) { error.value = '文档地址无效'; return }
  loading.value = true
  error.value = ''
  try { document.value = isPersonal.value ? await libraryApi.getMyDocument(id) : await libraryApi.getCatalogDocument(id) }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '文档读取失败' }
  finally { loading.value = false }
}

onMounted(loadDocument)
</script>

<style lang="scss" scoped>
@import '../../styles/tokens.scss';
.zk-reader-page { position:relative; min-height:100vh; padding:0 20px 25px; background:$bg; }
.zk-reader-header { padding:19px 0 17px; }
.zk-reader-category { color:$brand; font-size:10px; font-weight:650; }
.zk-reader-title { display:block; margin-top:8px; color:$ink; font-size:22px; font-weight:750; line-height:1.38; }
.zk-reader-meta { display:block; margin-top:8px; color:$muted; font-size:9px; }
.zk-reader-scroll { height:calc(100vh - 190px); border:1px solid $border; border-radius:14px; background:$card; }
.zk-reader-content { padding:18px 16px 22px; color:$ink; }
.zk-content-line { min-height:9px; white-space:pre-wrap; overflow-wrap:anywhere; user-select:none; }
.zk-content-line.paragraph { margin:0 0 10px; color:$body; font-size:12px; line-height:1.85; }
.zk-content-line.heading { margin:15px 0 9px; color:$ink; font-size:15px; font-weight:700; }
.zk-content-line.quote { margin:12px 0; padding:9px 11px; border-left:2px solid $sage; border-radius:3px; color:$body; background:$sage-soft; font-size:11px; line-height:1.75; }
.zk-content-line.bullet { margin:0 0 8px; padding-left:4px; color:$body; font-size:11px; line-height:1.75; }
.zk-content-line.blank { height:7px; }
.zk-watermark { position:fixed; top:48%; left:-12%; width:124%; color:rgba(58,72,75,.075); font-size:14px; letter-spacing:2px; text-align:center; transform:rotate(-25deg); pointer-events:none; }
.zk-reader-footer { padding:12px 0; color:$muted; text-align:center; font-size:9px; }
.zk-reader-state { padding:45px 10px; color:$muted; text-align:center; font-size:11px; line-height:2; }
.zk-reader-state text { display:block; color:$brand; }
.zk-ocr-note { padding:17px; border-radius:12px; color:#97784c; background:$amber-soft; font-size:11px; line-height:1.7; }
</style>
