<template>
  <view v-if="article" class="page-detail">
    <view class="tabs">
      <view class="tab" :class="{ active: tab === 'content' }" @tap="tab = 'content'">正文</view>
      <view class="tab" :class="{ active: tab === 'mindmap' }" @tap="tab = 'mindmap'">知识框架</view>
    </view>

    <view v-show="tab === 'content'" class="content-panel">
      <text class="title">{{ article.title }}</text>
      <view class="meta">
        <nut-tag type="primary" plain size="small">{{ article.source }}</nut-tag>
        <text>{{ article.publishDate }}</text>
        <text class="section-count">共 {{ sectionStats.readable }} 节</text>
      </view>
      <view class="tags">
        <nut-tag v-for="t in article.tags" :key="t" size="small">{{ t }}</nut-tag>
      </view>

      <view class="read-progress">
        <view class="progress-bar">
          <view class="progress-fill" :style="{ width: readProgress + '%' }" />
        </view>
        <text class="progress-text">
          已读 {{ readSectionCount }}/{{ sectionStats.readable }} 节（{{ readProgress }}%）
        </text>
      </view>

      <view class="mode-switch">
        <view class="mode-btn" :class="{ active: readMode === 'list' }" @tap="readMode = 'list'">目录模式</view>
        <view class="mode-btn" :class="{ active: readMode === 'pager' }" @tap="enterPagerMode">翻页模式</view>
      </view>

      <ArticleOutline
        v-if="readMode === 'list' && topSections.length"
        :items="topSections"
        :active-id="activeChapterId"
        :read-ids="readSectionIds"
        @select="scrollToSection"
      />

      <SectionPager
        v-if="readMode === 'pager'"
        :section="currentPagerSection"
        :index="pagerIndex"
        :total="readableSections.length"
        :is-read="currentPagerSection ? isSectionRead(currentPagerSection.id) : false"
        @prev="goPrevSection"
        @next="goNextSection"
        @mark-read="markCurrentPagerRead"
      />

      <scroll-view
        v-show="readMode === 'list'"
        scroll-y
        class="section-scroll"
        :scroll-into-view="scrollTarget"
        scroll-with-animation
      >
        <ArticleSections
          :sections="article.sections"
          :open-ids="openIds"
          :read-ids="readSectionIds"
          @toggle="toggleSection"
          @read="markSectionRead"
        />
      </scroll-view>
    </view>

    <view v-show="tab === 'mindmap'" class="mindmap-panel">
      <MindMap :nodes="article.mindMap.children || []" />
      <nut-button plain type="primary" block class="expand-btn" @click="goMindMap">
        全屏查看思维导图
      </nut-button>
    </view>

    <view class="footer">
      <view class="footer-row">
        <nut-button plain type="primary" class="footer-half" @click="onCopyArticle">复制正文</nut-button>
        <nut-button plain type="primary" class="footer-half" @click="goCorpusQuick">记入语料</nut-button>
      </view>
      <nut-button
        type="primary"
        block
        class="primary-btn"
        :disabled="taskId ? dailyReadDone : readDone"
        @click="finishRead"
      >
        {{ finishReadLabel }}
      </nut-button>
      <nut-button plain type="primary" block @click="goQuiz">开始答题</nut-button>
    </view>
    <CorpusSelectCapture
      v-if="article"
      source-type="报纸"
      :source-title="article.title"
      :bottom-offset="188"
    />
  </view>
  <nut-skeleton v-else rows="6" animated />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Taro from '@tarojs/taro'
import { Button as NutButton, Skeleton as NutSkeleton, Tag as NutTag } from '@nutui/nutui-taro'
import ArticleOutline from '@/components/ArticleOutline.vue'
import ArticleSections from '@/components/ArticleSections.vue'
import CorpusSelectCapture from '@/components/CorpusSelectCapture.vue'
import MindMap from '@/components/MindMap.vue'
import SectionPager from '@/components/SectionPager.vue'
import { useArticleStore } from '@/store/article'
import { useDailyTaskStore } from '@/store/dailyTask'
import {
  countSections,
  flattenSections,
  getReadableSections,
  getTopLevelSections,
} from '@/utils/articleContent'
import { buildCorpusEditUrl } from '@/utils/corpus'
import { showToast, copyText } from '@/utils/platform'
import type { Article } from '@/types'

definePageConfig({ navigationBarTitleText: '文章详情' })

const articleStore = useArticleStore()
const dailyTaskStore = useDailyTaskStore()
const tab = ref<'content' | 'mindmap'>('content')
const readMode = ref<'list' | 'pager'>('list')
const readDone = ref(false)
const article = ref<Article | null>(articleStore.currentArticle)
const openIds = ref<Set<string>>(new Set())
const activeChapterId = ref('')
const scrollTarget = ref('')
const pagerIndex = ref(0)
const taskId = ref('')
const dailyTask = computed(() => dailyTaskStore.tasks.find((item) => item.id === taskId.value) || null)
const dailyReadDone = computed(() => (dailyTask.value?.progress.currentStep || 0) >= 2)

const sectionStats = computed(() =>
  article.value?.sections?.length
    ? countSections(article.value.sections)
    : { total: 0, readable: 0, levels: {} },
)

const topSections = computed(() =>
  article.value?.sections ? getTopLevelSections(article.value.sections) : [],
)

const readableSections = computed(() =>
  article.value?.sections ? getReadableSections(article.value.sections) : [],
)

const readSectionIds = computed(() => {
  if (!article.value) return new Set<string>()
  return new Set(articleStore.getReadSectionIds(article.value.id))
})

const readSectionCount = computed(() => readSectionIds.value.size)

const readProgress = computed(() => {
  if (!article.value) return 0
  return articleStore.getSectionReadProgress(article.value.id, sectionStats.value.readable)
})

const currentPagerSection = computed(() => readableSections.value[pagerIndex.value] || null)

const finishReadLabel = computed(() => {
  if (taskId.value) {
    return dailyReadDone.value ? '本次精读已完成' : '完成原文精读'
  }
  if (readDone.value) return '已阅读 +3积分'
  const allRead = article.value
    ? articleStore.isAllSectionsRead(
        article.value.id,
        readableSections.value.map((s) => s.id),
      )
    : false
  return allRead ? '完成阅读 (+3积分)' : `完成阅读 (+3积分) · 还剩 ${sectionStats.value.readable - readSectionCount.value} 节`
})

function isSectionRead(sectionId: string) {
  return article.value ? articleStore.isSectionRead(article.value.id, sectionId) : false
}

function markSectionRead(sectionId: string) {
  if (!article.value) return
  articleStore.markSectionRead(article.value.id, sectionId)
}

function initOpenState(sections: Article['sections']) {
  const ids = new Set<string>()
  const first = sections[0]
  if (first) {
    ids.add(first.id)
    first.children?.forEach((child) => {
      ids.add(child.id)
      child.children?.forEach((grand) => ids.add(grand.id))
    })
  }
  openIds.value = ids
  activeChapterId.value = first?.id || ''
}

function initPagerIndex() {
  const firstUnread = readableSections.value.findIndex(
    (s) => article.value && !articleStore.isSectionRead(article.value.id, s.id),
  )
  pagerIndex.value = firstUnread >= 0 ? firstUnread : 0
}

function enterPagerMode() {
  readMode.value = 'pager'
  initPagerIndex()
  if (currentPagerSection.value) {
    markSectionRead(currentPagerSection.value.id)
  }
}

function goPrevSection() {
  if (pagerIndex.value > 0) pagerIndex.value--
}

function goNextSection() {
  if (pagerIndex.value < readableSections.value.length - 1) pagerIndex.value++
}

function markCurrentPagerRead() {
  if (currentPagerSection.value) markSectionRead(currentPagerSection.value.id)
}

watch(pagerIndex, (idx) => {
  const sec = readableSections.value[idx]
  if (sec) markSectionRead(sec.id)
})

function toggleSection(id: string) {
  const next = new Set(openIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  openIds.value = next
}

function scrollToSection(id: string) {
  activeChapterId.value = id
  const next = new Set(openIds.value)
  next.add(id)
  flattenSections(article.value!.sections)
    .filter((s) => s.id === id || s.id.startsWith(`${id}-`))
    .forEach((s) => next.add(s.id))
  openIds.value = next
  scrollTarget.value = `sec-${id}`
}

onMounted(async () => {
  const params = Taro.getCurrentInstance().router?.params || {}
  const { id } = params
  taskId.value = (params.taskId || '').trim()
  if (taskId.value && !dailyTask.value) await dailyTaskStore.load()
  if (id) {
    const data = await articleStore.getArticleDetail(id)
    article.value = data || null
    readDone.value = articleStore.isRead(id)
    if (data?.sections?.length) {
      initOpenState(data.sections)
      initPagerIndex()
      // 打开文章即记为最近在学（含已读完再回来看）
      if (currentPagerSection.value) {
        markSectionRead(currentPagerSection.value.id)
      }
    }
  }
})

async function finishRead() {
  if (!article.value) return
  const allIds = readableSections.value.map((s) => s.id)
  if (!articleStore.isAllSectionsRead(article.value.id, allIds)) {
    showToast(`请先读完所有小节（${readSectionCount.value}/${allIds.length}）`)
    return
  }
  const points = readDone.value ? 0 : await articleStore.markAsRead(article.value.id)
  readDone.value = true
  if (taskId.value && dailyTask.value?.progress.state === 'in_progress') {
    try {
      await dailyTaskStore.saveDraft(
        taskId.value,
        { ...dailyTask.value.progress.draft, readingCompleted: true },
        2,
        dailyTask.value.totalSteps,
      )
    } catch (error) {
      showToast(error instanceof Error ? error.message : '精读进度保存失败', 'error')
      return
    }
  }
  showToast(points ? `阅读完成，+${points}积分` : '本次精读已完成', 'success')
}

function goQuiz() {
  if (!article.value) return
  if (taskId.value && !dailyReadDone.value) {
    showToast('请先完成本次原文精读')
    return
  }
  const taskQuery = taskId.value ? `&taskId=${encodeURIComponent(taskId.value)}` : ''
  Taro.navigateTo({ url: `/pages/question/taking?articleId=${article.value.id}${taskQuery}` })
}

async function onCopyArticle() {
  if (!article.value) return
  const parts = [article.value.title]
  for (const s of readableSections.value) {
    if (s.title) parts.push(s.title)
    if (s.content) parts.push(s.content)
  }
  await copyText(parts.filter(Boolean).join('\n\n'))
}

function goCorpusQuick() {
  if (!article.value) return
  Taro.navigateTo({
    url: buildCorpusEditUrl({
      sourceType: '报纸',
      sourceTitle: article.value.title || '',
      kind: '专名',
    }),
  })
}

function goMindMap() {
  if (!article.value) return
  Taro.navigateTo({ url: `/pages/article/mindmap?id=${article.value.id}` })
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-detail {
  padding: 16px;
  padding-bottom: 200px;
  .tabs {
    display: flex;
    background: $page-bg;
    border-radius: 8px;
    padding: 4px;
    margin-bottom: 16px;
    .tab {
      flex: 1;
      text-align: center;
      padding: 8px;
      border-radius: 6px;
      font-size: 14px;
      &.active { background: $card-bg; color: $primary-color; font-weight: 600; }
    }
  }
  .title { display: block; font-size: 18px; font-weight: 700; line-height: 1.5; margin-bottom: 10px; }
  .meta {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    font-size: 12px;
    color: $text-muted;
    flex-wrap: wrap;
    .section-count { color: $primary-color; }
  }
  .tags { display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap; }
  .read-progress {
    margin-bottom: 12px;
    .progress-bar {
      height: 4px;
      background: $border-color;
      border-radius: 2px;
      overflow: hidden;
      .progress-fill {
        height: 100%;
        background: $primary-color;
        transition: width 0.3s;
      }
    }
    .progress-text { font-size: 12px; color: $text-muted; margin-top: 6px; display: block; }
  }
  .mode-switch {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    .mode-btn {
      flex: 1;
      text-align: center;
      padding: 8px;
      border-radius: 8px;
      background: $page-bg;
      font-size: 13px;
      &.active {
        background: $primary-light;
        color: $primary-color;
        font-weight: 600;
      }
    }
  }
  .expand-btn { margin-top: 16px; }
  .footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
    background: $card-bg;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.06);
    display: flex;
    flex-direction: column;
    gap: 8px;
    .footer-row {
      display: flex;
      gap: 8px;
    }
    .footer-half {
      flex: 1;
    }
  }
}
</style>
