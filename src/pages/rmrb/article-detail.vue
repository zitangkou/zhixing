<template>
  <view v-if="article" class="page-rmrb-detail" :class="[themeClass, { 'is-html': showParse && !!demo?.displayHtml }]">
    <template v-if="!showParse">
      <text class="source">{{ article.source }} · {{ article.publishDate }}</text>
      <text class="title selectable-text" user-select selectable>{{ article.title }}</text>
      <view v-if="themeChips.length" class="tags">
        <text v-for="t in themeChips" :key="t" class="tag">{{ t }}</text>
      </view>
      <text class="content selectable-text" user-select selectable>{{ article.content || '暂无原文，请管理员补全文稿。' }}</text>
    </template>

    <template v-else-if="demo">
      <view v-if="demo.displayHtml" class="html-wrap">
        <iframe
          v-if="isH5"
          class="html-frame"
          title="时评解析"
          sandbox="allow-same-origin"
          :srcdoc="htmlDocument"
          @load="onFrameLoad"
        />
        <rich-text v-else class="html-body" :nodes="demo.displayHtml" />
      </view>
      <template v-else>
      <view class="block">
        <text class="block-kicker">考题定位</text>
        <text class="line">主题：{{ demo.examAnchor.theme }}</text>
        <text class="line">标题机关：{{ demo.examAnchor.titleDevice }}</text>
        <text class="line">立意路径：{{ demo.examAnchor.stancePath }}</text>
      </view>
      <view class="block">
        <text class="block-kicker">原文摘录</text>
        <text class="excerpt selectable-text" user-select selectable>{{ demo.sourceExcerpt }}</text>
      </view>
      <view class="block">
        <text class="block-kicker">总骨架</text>
        <text class="line">开头范式：{{ demo.argument.openingPattern }}</text>
        <text class="line">过渡：{{ demo.argument.transition }}</text>
        <text class="line">总论点：{{ demo.argument.overview }}</text>
        <view v-for="(pt, i) in demo.argument.points" :key="i" class="point">
          <text class="point-title">分论点 {{ i + 1 }} {{ pt.title }}</text>
          <text class="line">论据：{{ pt.evidence }}</text>
          <text class="line">小结：{{ pt.summary }}</text>
          <text class="line">方法：{{ pt.method }}</text>
        </view>
        <text class="line">总结：{{ demo.argument.conclusion }}</text>
      </view>
      <view class="block">
        <text class="block-kicker">规范词 / 语录 / 动词 / 句式</text>
        <text class="line">规范词 {{ demo.terms.length }} · 语录 {{ demo.quotes.length }} · 动词 {{ demo.verbs.length }} · 句式 {{ demo.templates.length }}</text>
        <text v-for="q in demo.quotes" :key="q.text" class="quote">{{ q.text }}（{{ q.source }}）</text>
      </view>
      <view class="block">
        <text class="block-kicker">迁移指南</text>
        <text class="line">适用：{{ demo.transferGuide.examFit }}</text>
        <text class="line">警示：{{ demo.transferGuide.caution }}</text>
        <text class="excerpt">{{ demo.transferGuide.imitateDemo }}</text>
      </view>
      </template>
    </template>

    <view class="footer">
      <template v-if="!showParse">
        <view class="footer-row">
          <nut-button
            plain
            type="primary"
            class="footer-half"
            :disabled="!demo"
            @click="openParse"
          >
            {{ demo ? '时评解析' : '暂无解析' }}
          </nut-button>
          <nut-button type="primary" class="footer-half" @click="goMine">去开采</nut-button>
        </view>
      </template>
      <template v-else>
        <view class="footer-row">
          <nut-button plain type="primary" class="footer-half" @click="closeParse">返回原文</nut-button>
          <nut-button type="primary" class="footer-half" @click="goMine">去开采</nut-button>
        </view>
      </template>
    </view>
  </view>
  <view v-else class="empty" :class="themeClass">加载中...</view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import { api } from '@/api'
import { useDailyTaskStore } from '@/store/dailyTask'
import { showToast } from '@/utils/platform'
import type { RmrbArticle } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '时评原文' })

const { themeClass } = useThemeClass()
const router = useRouter()
const dailyTaskStore = useDailyTaskStore()
const article = ref<RmrbArticle | null>(null)
const showParse = ref((router.params?.view || '') === 'demo')
const demo = computed(() => article.value?.teachingExample || null)
const isH5 = process.env.TARO_ENV === 'h5'
const themeChips = computed(() => {
  const seen = new Set<string>()
  const out: string[] = []
  const extra = (demo.value?.examAnchor?.theme || '').split(/[｜|/、，,]+/)
  for (const raw of [...(article.value?.tags || []), ...extra]) {
    const item = String(raw || '').trim()
    if (!item || seen.has(item)) continue
    seen.add(item)
    out.push(item)
  }
  return out
})

const htmlDocument = computed(() => {
  const raw = demo.value?.displayHtml || ''
  if (!raw) return ''
  if (/<html[\s>]/i.test(raw)) return raw
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>${raw}</body></html>`
})

function onFrameLoad(e: Event) {
  const frame = e.target as HTMLIFrameElement
  const doc = frame.contentDocument
  if (!doc?.documentElement) return
  const height = Math.max(doc.documentElement.scrollHeight, doc.body?.scrollHeight || 0, 480)
  frame.style.height = `${height}px`
}

async function load() {
  const id = router.params?.id || ''
  if (!id) return
  const res = await api.getRmrbArticle(id)
  if (res.code === 0 && res.data) {
    article.value = { ...res.data, tags: res.data.tags || [] }
  } else {
    showToast(res.message || '加载失败', 'error')
  }
}

function syncNavTitle() {
  Taro.setNavigationBarTitle({ title: showParse.value ? '时评解析' : '时评原文' })
}

function closeParse() {
  showParse.value = false
  syncNavTitle()
}

function openParse() {
  if (!demo.value) {
    showToast('这篇还没有解析')
    return
  }
  showParse.value = true
  syncNavTitle()
}

async function goMine() {
  if (!article.value) return
  const taskId = (router.params?.taskId || '').trim()
  const task = dailyTaskStore.tasks.find((item) => item.id === taskId)
  if (taskId && task?.progress.state === 'in_progress') {
    try {
      await dailyTaskStore.saveDraft(
        taskId,
        { ...task.progress.draft, articleId: article.value.id, readCompleted: true },
        1,
        task.totalSteps,
      )
    } catch {
      showToast('阅读进度暂未同步，将继续进入拆解', 'error')
    }
  }
  const title = encodeURIComponent(article.value.title || '')
  const taskQuery = taskId ? `&taskId=${encodeURIComponent(taskId)}` : ''
  Taro.navigateTo({
    url: `/pages/rmrb/mine-edit?articleId=${article.value.id}&title=${title}${taskQuery}`,
  })
}

onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-rmrb-detail {
  @include page-padding;
  padding-bottom: 88px;
  &.is-html {
    padding: 0 0 88px;
    background: #faf9f5;
  }
  .source { display: block; font-size: 12px; color: $text-muted; margin-bottom: 8px; }
  .title {
    display: block;
    font-size: 20px;
    font-weight: 700;
    line-height: 1.45;
    margin-bottom: 8px;
  }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 10px;
    .tag {
      font-size: 12px;
      color: $primary-color;
      background: $primary-light;
      padding: 3px 10px;
      border-radius: 4px;
    }
  }
  .anchor {
    @include card;
    padding: 10px 12px;
    margin-bottom: 12px;
    .line { display: block; font-size: 13px; line-height: 1.55; margin-bottom: 4px; }
    .line:last-child { margin-bottom: 0; }
  }
  .html-wrap {
    margin: 0;
    overflow: visible;
  }
  .html-frame {
    display: block;
    width: 100%;
    border: 0;
    min-height: 70vh;
    background: #faf9f5;
  }
  .html-body {
    font-size: 14px;
    line-height: 1.7;
    color: $text-primary;
    word-break: break-word;
    :deep(table) { width: 100%; font-size: 12px; }
    :deep(h2) { font-size: 16px; color: $primary-color; }
    :deep(a) { color: $primary-color; }
  }
  .block {
    @include card;
    padding: 12px;
    margin-bottom: 12px;
  }
  .block-kicker {
    display: block;
    font-size: 12px;
    font-weight: 700;
    color: $primary-color;
    margin-bottom: 8px;
  }
  .line, .quote {
    display: block;
    font-size: 13px;
    line-height: 1.6;
    color: $text-primary;
    margin-bottom: 6px;
  }
  .point { margin: 8px 0; }
  .point-title { display: block; font-size: 14px; font-weight: 600; margin-bottom: 4px; }
  .excerpt, .content {
    display: block;
    font-size: 15px;
    line-height: 1.85;
    color: $text-primary;
    white-space: pre-wrap;
  }
  .selectable-text {
    -webkit-user-select: text;
    user-select: text;
  }
  .footer {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
    background: $card-bg;
    box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.06);
    .footer-row {
      display: flex;
      gap: 8px;
    }
    .footer-half { flex: 1; }
  }
  .empty { text-align: center; color: $text-muted; padding: 40px; }
}
</style>
