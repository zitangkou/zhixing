<template>
  <view v-if="article" class="page-rmrb-detail" :class="[themeClass, { 'is-html': showHtmlLayout }]">
    <template v-if="!showParse">
      <text class="title selectable-text" user-select selectable>{{ article.title }}</text>
      <view class="meta">
        <nut-tag type="primary" plain size="small">{{ article.source }}</nut-tag>
        <text>{{ article.publishDate }}</text>
      </view>
      <view v-if="themeChips.length" class="tags">
        <nut-tag v-for="t in themeChips" :key="t" type="primary" plain size="small">{{ t }}</nut-tag>
      </view>
      <ArticleHtml v-if="article.contentHtml" :html="article.contentHtml" />
      <text v-else class="content selectable-text" user-select selectable>{{ article.content || '暂无原文，请管理员补全文稿。' }}</text>
    </template>

    <template v-else-if="showParse">
      <ArticleHtml v-if="parseHtml" :html="parseHtml" />
      <view v-else class="empty-parse">
        <text class="empty-title">暂无解析 HTML</text>
        <text class="empty-desc">请管理员在后台对该文「导入解析」粘贴精拆 HTML。仍可点「去开采」跟做。</text>
      </view>
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
import { Button as NutButton, Tag as NutTag } from '@nutui/nutui-taro'
import ArticleHtml from '@/components/ArticleHtml.vue'
import { api } from '@/api'
import { useDailyTaskStore } from '@/store/dailyTask'
import { showToast } from '@/utils/platform'
import type { RmrbArticle } from '@/types'
import { looksLikeHtml, unescapeHtmlIfNeeded } from '@/utils/articleContent'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '时评原文' })

const { themeClass } = useThemeClass()
const router = useRouter()
const dailyTaskStore = useDailyTaskStore()
const article = ref<RmrbArticle | null>(null)
const showParse = ref((router.params?.view || '') === 'demo')
const demo = computed(() => article.value?.teachingExample || null)
const parseHtml = computed(() => {
  const raw = unescapeHtmlIfNeeded(demo.value?.displayHtml || '')
  return looksLikeHtml(raw) ? raw : ''
})
const showHtmlLayout = computed(() =>
  (!showParse.value && !!article.value?.contentHtml) || (showParse.value && !!parseHtml.value),
)
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
    background: $page-bg;
  }
  .title {
    display: block;
    font-size: 18px;
    font-weight: 700;
    line-height: 1.5;
    margin-bottom: 10px;
  }
  .meta {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    font-size: 12px;
    color: $text-muted;
    flex-wrap: wrap;
  }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 12px;
  }
  .anchor {
    @include card;
    padding: 10px 12px;
    margin-bottom: 12px;
    .line { display: block; font-size: 13px; line-height: 1.55; margin-bottom: 4px; }
    .line:last-child { margin-bottom: 0; }
  }
  .empty-parse {
    padding: 48px 24px;
    text-align: center;
    .empty-title { display: block; font-size: 16px; font-weight: 600; margin-bottom: 8px; }
    .empty-desc { display: block; font-size: 13px; color: $text-muted; line-height: 1.6; }
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
    z-index: 20;
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
