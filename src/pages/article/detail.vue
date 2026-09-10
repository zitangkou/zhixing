<template>
  <view v-if="article" class="page-detail" :class="[themeClass, { 'is-html': isHtmlArticle }]">
    <text class="title">{{ article.title }}</text>
    <view class="meta">
      <nut-tag type="primary" plain size="small">{{ article.source }}</nut-tag>
      <text>{{ article.publishDate }}</text>
    </view>
    <view class="tags">
      <nut-tag v-for="t in article.tags" :key="t" type="primary" plain size="small">{{ t }}</nut-tag>
    </view>

    <ArticleHtml v-if="isHtmlArticle" :html="displayHtml" />
    <text v-else class="full-text">{{ plainFullText }}</text>

    <view class="footer">
      <nut-button
        type="primary"
        block
        class="primary-btn"
        @click="finishRead"
      >
        {{ finishReadLabel }}
      </nut-button>
      <nut-button
        plain
        type="primary"
        block
        @click="goQuiz"
      >
        考点练习
      </nut-button>
    </view>
  </view>
  <nut-skeleton v-else rows="6" animated />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Taro from '@tarojs/taro'
import { Button as NutButton, Skeleton as NutSkeleton, Tag as NutTag } from '@nutui/nutui-taro'
import ArticleHtml from '@/components/ArticleHtml.vue'
import { useArticleStore } from '@/store/article'
import { useDailyTaskStore } from '@/store/dailyTask'
import { articleDisplayHtml, getArticleFullContent } from '@/utils/articleContent'
import { isLoggedIn, requireLogin } from '@/utils/auth'
import { showConfirm, showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '文章详情' })

const { themeClass } = useThemeClass()
const articleStore = useArticleStore()
const dailyTaskStore = useDailyTaskStore()
const readDone = ref(false)
const article = ref(articleStore.currentArticle)
const displayHtml = computed(() => (article.value ? articleDisplayHtml(article.value) : ''))
const isHtmlArticle = computed(() => !!displayHtml.value)
const plainFullText = computed(() => {
  if (!article.value) return ''
  if (article.value.content?.trim()) return article.value.content
  return getArticleFullContent(article.value)
})

const taskId = ref('')
const dailyTask = computed(() => dailyTaskStore.tasks.find((item) => item.id === taskId.value) || null)
const dailyReadDone = computed(() => (dailyTask.value?.progress.currentStep || 0) >= 2)

const finishReadLabel = computed(() => {
  if (!isLoggedIn()) return '登录后记录阅读'
  if (taskId.value) {
    return dailyReadDone.value ? '本次精读已完成' : '完成原文精读'
  }
  if (readDone.value) return '已完成阅读'
  return '完成阅读 (+3积分)'
})

function detailUrl() {
  if (!article.value) return '/pages/article/detail'
  const taskQuery = taskId.value ? `&taskId=${encodeURIComponent(taskId.value)}` : ''
  return `/pages/article/detail?id=${article.value.id}${taskQuery}`
}

function quizUrl() {
  if (!article.value) return '/pages/question/taking'
  const taskQuery = taskId.value ? `&taskId=${encodeURIComponent(taskId.value)}` : ''
  return `/pages/question/taking?articleId=${article.value.id}${taskQuery}`
}

async function ensureLogin(reason: string, redirectUrl: string) {
  if (isLoggedIn()) return true
  const ok = await showConfirm('需要登录', reason, { confirmText: '去登录', cancelText: '再看看' })
  if (!ok) return false
  requireLogin(redirectUrl)
  return false
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
  }
})

async function finishRead() {
  if (!article.value) return
  if (!(await ensureLogin('登录后才能保存阅读进度并发放积分。', detailUrl()))) return
  if (taskId.value ? dailyReadDone.value : readDone.value) {
    showToast('已完成阅读')
    return
  }
  const points = await articleStore.markAsRead(article.value.id)
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

async function goQuiz() {
  if (!article.value) return
  if (taskId.value && !dailyReadDone.value) {
    showToast('请先完成原文精读')
    return
  }
  if (!(await ensureLogin('登录后才能保存练习进度与积分。', quizUrl()))) return
  Taro.navigateTo({ url: quizUrl() })
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-detail {
  padding: 16px;
  padding-bottom: 140px;
  .title { display: block; font-size: 18px; font-weight: 700; line-height: 1.5; margin-bottom: 10px; }
  .meta {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    font-size: 12px;
    color: $text-muted;
    flex-wrap: wrap;
  }
  .tags { display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap; }
  .full-text {
    display: block;
    font-size: 15px;
    line-height: 1.85;
    color: $text-primary;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .footer {
    position: fixed;
    z-index: 20;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
    background: $card-bg;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.06);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
}
</style>
