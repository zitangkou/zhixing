<template>
  <view v-if="article" class="page-rmrb-detail" :class="themeClass">
    <text class="source">{{ article.source }} · {{ article.publishDate }}</text>
    <text class="title selectable-text" user-select selectable>{{ article.title }}</text>
    <view v-if="article.tags?.length" class="tags">
      <text v-for="t in article.tags" :key="t" class="tag">{{ t }}</text>
    </view>
    <text class="hw-tip">长按选中专名/成语可记入语料。开采本可用系统手写；若无效，点输入框后切换手写键盘。</text>
    <text class="content selectable-text" user-select selectable>{{ article.content }}</text>
    <view class="footer">
      <view class="footer-row">
        <nut-button plain type="primary" class="footer-half" @click="onCopy">复制全文</nut-button>
        <nut-button plain type="primary" class="footer-half" @click="goCorpusQuick">记入语料</nut-button>
      </view>
      <nut-button type="primary" block @click="goMine">三刀解剖</nut-button>
    </view>
    <CorpusSelectCapture
      source-type="报纸"
      :source-title="article.title"
      :bottom-offset="120"
    />
  </view>
  <view v-else class="empty" :class="themeClass">加载中...</view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import CorpusSelectCapture from '@/components/CorpusSelectCapture.vue'
import { api } from '@/api'
import { useDailyTaskStore } from '@/store/dailyTask'
import { buildCorpusEditUrl } from '@/utils/corpus'
import { copyText, showToast } from '@/utils/platform'
import type { RmrbArticle } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '时评详情' })

const { themeClass } = useThemeClass()
const router = useRouter()
const dailyTaskStore = useDailyTaskStore()
const article = ref<RmrbArticle | null>(null)

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

async function onCopy() {
  if (!article.value) return
  const text = `${article.value.title}\n\n${article.value.content || ''}`
  await copyText(text)
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

onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-rmrb-detail {
  @include page-padding;
  padding-bottom: 140px;
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
  .hw-tip {
    display: block;
    font-size: 11px;
    color: $text-muted;
    line-height: 1.45;
    margin-bottom: 12px;
  }
  .content {
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
  .empty { text-align: center; color: $text-muted; padding: 40px; }
}
</style>
