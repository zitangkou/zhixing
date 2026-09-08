<template>
  <view class="page-mw-list" :class="themeClass">
    <view
      v-if="dueCount > 0"
      class="start-cta"
      @tap="goQuiz"
    >
      <view class="start-main">
        <text class="start-title">开始今日复习</text>
        <text class="start-desc">推荐 {{ Math.min(dueCount, 15) }} 道 · 逐题刷，先回忆再揭晓</text>
      </view>
      <text class="start-arrow">›</text>
    </view>

    <view class="mw-header">
      <view class="filter-row">
        <text
          v-for="s in subjects"
          :key="s.value"
          class="filter-chip"
          :class="{ active: store.filterSubject === s.value }"
          @tap="store.setFilter(s.value)"
        >{{ s.label }}{{ store.bySubject[s.value] ? ` ${store.bySubject[s.value]}` : '' }}</text>
      </view>
      <view class="filter-toggle-row">
        <text class="filter-toggle" :class="{ on: dueOnly }" @tap="dueOnly = !dueOnly">只看待复习</text>
        <text class="filter-toggle" :class="{ on: !store.showMastered }" @tap="store.toggleMasteredFilter()">
          {{ store.showMastered ? '含已掌握' : '只看未掌握' }}
        </text>
      </view>
      <text class="srs-tip">记忆曲线 1→2→4→7→15→30 天；复习请用上方「开始今日复习」</text>
    </view>

    <view v-if="store.loading" class="state-box">
      <text class="state-title">加载中…</text>
      <text class="state-desc">正在同步错题本</text>
    </view>
    <view v-else-if="store.loadError" class="state-box">
      <text class="state-title">加载失败</text>
      <text class="state-desc">{{ store.loadError }}</text>
      <view class="state-btn" @tap="load">点击重试</view>
    </view>
    <view v-else-if="visibleList.length === 0" class="state-box">
      <text class="state-title">{{ dueOnly ? '今日无到期行测错题' : '还没有手动错题' }}</text>
      <text class="state-desc">在刷华图/真题时遇到错题，可以拍照或文字录入到这里</text>
    </view>

    <view v-else class="mw-list">
      <view v-for="w in visibleList" :key="w.id" class="mw-card" :class="{ mastered: w.mastered }">
        <view class="mw-meta">
          <text class="chip" :class="subjectChipClass(w.subject)">{{ w.subject || '未分类' }}</text>
          <text v-if="w.questionType" class="chip chip-soft">{{ w.questionType }}</text>
          <text v-if="w.wrongReason" class="chip chip-warn">{{ w.wrongReason }}</text>
          <text class="mw-time">{{ formatTime(w.lastWrongAt) }}</text>
        </view>
        <text v-if="w.knowledgePath" class="mw-kb" @tap="goKnowledge(w)">
          考点 · {{ formatKb(w.knowledgePath) }}
        </text>
        <text v-if="w.stem" class="mw-stem">{{ w.stem }}</text>
        <view v-if="w.images && w.images.length" class="mw-images">
          <image
            v-for="(img, idx) in w.images"
            :key="idx"
            class="mw-img"
            :src="resolveMediaUrl(img)"
            mode="aspectFill"
            @tap="previewImage(w.images, idx)"
          />
        </view>
        <view v-if="w.myAnswer || w.correctAnswer" class="mw-answer">
          <text v-if="w.myAnswer" class="ans-bad">我答：{{ w.myAnswer }}</text>
          <text v-if="w.correctAnswer" class="ans-ok">正确：{{ w.correctAnswer }}</text>
        </view>
        <text v-if="w.analysis" class="mw-analysis">{{ w.analysis }}</text>
        <text v-if="w.note" class="mw-note">{{ w.note }}</text>
        <text class="mw-schedule">{{ formatSchedule(w) }}</text>
        <view class="mw-actions">
          <text class="act" @tap="onReview(w, 'good')">复习+ {{ w.reviewCount }}</text>
          <text class="act" @tap="onReview(w, 'again')">忘了</text>
          <text v-if="w.knowledgePath" class="act" @tap="goKnowledge(w)">看框架</text>
          <text class="act" @tap="onToggleMaster(w)">{{ w.mastered ? '取消掌握' : '已掌握' }}</text>
          <text class="act" @tap="onEdit(w)">编辑</text>
          <text class="act danger" @tap="onDelete(w)">删除</text>
        </view>
      </view>
    </view>

    <view class="fab" @tap="onAdd">+ 录入错题</view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import { api } from '@/api'
import { useManualWrongStore } from '@/store/manualWrong'
import { formatKnowledgeLabel } from '@/utils/knowledge'
import { resolveMediaUrl } from '@/utils/media'
import { showConfirm, showToast } from '@/utils/platform'
import type { ManualWrong } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '行测错题本' })

const { themeClass } = useThemeClass()
const router = useRouter()
const store = useManualWrongStore()
const fromReview = router.params?.from === 'review'
const redirected = ref(false)
const dueOnly = ref(router.params?.unmastered === '1' || fromReview)
if (router.params?.unmastered === '1') {
  store.showMastered = false
}
const subjectParam = router.params?.subject ? decodeURIComponent(router.params.subject) : ''
if (subjectParam) {
  store.setFilter(subjectParam)
}

const dueCount = computed(() =>
  store.list.filter((w) => !w.mastered && (w.due || !w.nextReviewAt)).length,
)

const visibleList = computed(() => {
  let arr = store.filtered
  if (dueOnly.value) arr = arr.filter((w) => w.due || (!w.mastered && !w.nextReviewAt))
  return arr
})

function goQuiz() {
  Taro.navigateTo({ url: '/pages/question/manual-quiz' })
}

const subjects = [
  { value: '', label: '全部' },
  { value: '常识', label: '常识' },
  { value: '言语', label: '言语' },
  { value: '数量', label: '数量' },
  { value: '判断', label: '判断' },
  { value: '资料', label: '资料' },
]

function subjectChipClass(s: string) {
  return {
    常识: 'chip-blue',
    言语: 'chip-green',
    数量: 'chip-purple',
    判断: 'chip-amber',
    资料: 'chip-red',
  }[s] || 'chip-soft'
}

function formatTime(iso: string) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatKb(path: string) {
  return formatKnowledgeLabel(path)
}

function goKnowledge(w: ManualWrong) {
  const key = w.knowledgeTreeKey || ''
  Taro.navigateTo({
    url: key ? `/pages/knowledge/index?treeKey=${encodeURIComponent(key)}` : '/pages/knowledge/index',
  })
}

function previewImage(images: string[], idx: number) {
  Taro.previewImage({
    urls: images.map(resolveMediaUrl),
    current: resolveMediaUrl(images[idx]),
  })
}

async function load() {
  await store.fetch()
  if (fromReview && !redirected.value && dueCount.value > 0) {
    redirected.value = true
    Taro.redirectTo({ url: '/pages/question/manual-quiz' })
  }
}

onMounted(load)
useDidShow(() => {
  if (!redirected.value) load()
})

function onAdd() {
  Taro.navigateTo({ url: '/pages/question/manual-edit' })
}

function onEdit(w: ManualWrong) {
  Taro.navigateTo({ url: `/pages/question/manual-edit?id=${w.id}` })
}

function formatSchedule(w: ManualWrong) {
  if (w.mastered) return '已掌握'
  if (w.due || !w.nextReviewAt) return `待复习 · 第 ${(w.reviewStage || 0) + 1} 档`
  const d = new Date(w.nextReviewAt)
  if (Number.isNaN(d.getTime())) return '待安排'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `下次 ${pad(d.getMonth() + 1)}-${pad(d.getDate())} · 第 ${(w.reviewStage || 0) + 1} 档`
}

async function onToggleMaster(w: ManualWrong) {
  await store.update(w.id, { mastered: !w.mastered })
  showToast(w.mastered ? '已取消掌握' : '已标记掌握', 'success')
}

async function onReview(w: ManualWrong, result: 'good' | 'again' = 'good') {
  const res = await api.reviewManualWrong(w.id, result)
  if (res.code === 0 && res.data) {
    const idx = store.list.findIndex((x) => x.id === w.id)
    if (idx >= 0) store.list[idx] = res.data
    showToast(
      result === 'again'
        ? '已重置，明天再来'
        : res.data.mastered
          ? '已掌握，移出复习队列'
          : '已安排下次复习',
      'success',
    )
  } else {
    showToast(res.message || '记录失败', 'error')
  }
}

async function onDelete(w: ManualWrong) {
  const ok = await showConfirm('删除错题', '确定删除这道错题？')
  if (!ok) return
  await store.remove(w.id)
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-mw-list {
  @include page-padding;
  padding-bottom: 80px;
}

.start-cta {
  @include card;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, var(--zk-primary-light), var(--zk-primary-faint));
  border: 1px solid var(--zk-primary-soft);
  .start-main { flex: 1; min-width: 0; }
  .start-title {
    display: block;
    font-size: 16px;
    font-weight: 700;
    color: $text-primary;
  }
  .start-desc {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: $text-muted;
  }
  .start-arrow {
    font-size: 18px;
    color: $primary-color;
    font-weight: 600;
  }
}

.mw-header {
  margin-bottom: 14px;
  .srs-tip {
    display: block;
    margin-top: 8px;
    font-size: 11px;
    color: $text-muted;
  }
  .filter-toggle-row {
    display: flex;
    gap: 12px;
    margin-top: 8px;
  }
  .filter-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 8px;
  }
  .filter-chip {
    @include filter-tab;
    background: $card-bg;
    color: $text-secondary;
    &.active {
      background: $primary-color;
      color: $on-primary;
      font-weight: 600;
    }
  }
  .filter-toggle {
    font-size: 12px;
    color: $text-muted;
    &.on { color: $primary-color; font-weight: 600; }
  }
}

.empty {
  @include page-state-box;
}

.state-box { @include page-state-box; }

.mw-card {
  @include card;
  padding: 14px 16px;
  border-radius: $radius-lg;
  margin-bottom: 12px;
  &.mastered { opacity: 0.6; .mw-stem { text-decoration: line-through; color: $text-muted; } }
}

.mw-kb {
  display: block;
  font-size: 12px;
  color: $primary-color;
  font-weight: 600;
  margin-bottom: 8px;
  line-height: 1.4;
}

.mw-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
  .chip {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
  }
  .chip-red { color: $primary-color; background: $primary-light; }
  .chip-blue { color: $accent-blue; background: rgba($accent-blue, 0.1); }
  .chip-green { color: $accent-green; background: rgba($accent-green, 0.1); }
  .chip-purple { color: $accent-blue; background: rgba($accent-blue, 0.1); }
  .chip-amber { color: $accent-amber; background: rgba($accent-amber, 0.12); }
  .chip-soft { color: $text-secondary; background: $chip-bg; }
  .chip-warn { color: #c47d00; background: rgba(245, 166, 35, 0.12); }
  .mw-time { margin-left: auto; font-size: 11px; color: $text-muted; }
}

.mw-stem {
  display: block;
  font-size: 14px;
  line-height: 1.6;
  color: $text-primary;
  margin-bottom: 8px;
}

.mw-images {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
  .mw-img {
    width: 72px;
    height: 72px;
    border-radius: 6px;
    background: $page-bg;
  }
}

.mw-answer {
  display: flex;
  gap: 12px;
  margin-bottom: 6px;
  font-size: 13px;
  .ans-bad { color: $primary-color; }
  .ans-ok { color: $success; }
}

.mw-analysis {
  display: block;
  font-size: 12px;
  color: $text-secondary;
  line-height: 1.6;
  margin-bottom: 6px;
  padding: 8px 10px;
  background: $page-bg;
  border-radius: 6px;
}

.mw-schedule {
  display: block;
  font-size: 12px;
  color: $primary-color;
  margin: 6px 0 8px;
}
.mw-note {
  display: block;
  font-size: 12px;
  color: $text-muted;
  line-height: 1.5;
  margin-bottom: 8px;
}

.mw-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  border-top: 1px solid $border-color;
  padding-top: 4px;
  .act {
    @include list-act;
    font-size: 12px;
    color: $text-secondary;
    &.danger { color: $primary-color; margin-left: auto; }
  }
}

.fab {
  position: fixed;
  right: 16px;
  bottom: 24px;
  background: $primary-color;
  color: #fff;
  border-radius: 8px;
  padding: 12px 18px;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(16, 24, 40, 0.12);
  &:active { opacity: 0.9; }
}
</style>
