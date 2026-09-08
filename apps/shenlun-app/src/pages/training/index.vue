<template>
  <view class="page-drill">
    <view class="tip">阶梯训练：关键词串联 → 句式仿写 → 口述概括。每天任选一项，写满就算完成。</view>

    <view class="tabs">
      <text
        v-for="t in tabs"
        :key="t.value"
        class="tab"
        :class="{ on: mode === t.value }"
        @tap="mode = t.value; prepare()"
      >{{ t.label }}</text>
    </view>

    <view class="prompt-card" v-if="promptText">
      <text class="prompt-label">今日题目</text>
      <text class="prompt-body">{{ promptText }}</text>
      <text class="refresh" @tap="prepare">换一组</text>
    </view>

    <view class="field">
      <view class="label-row">
        <text class="label">{{ modeHint }}</text>
        <VoiceInputBtn v-model="content" />
      </view>
      <nut-textarea v-model="content" :placeholder="placeholder" limit-show :max-length="500" />
    </view>

    <nut-button type="primary" block :loading="saving" @click="onSave">提交练习</nut-button>

    <view class="recent" v-if="recent.length">
      <text class="block-title">最近练习</text>
      <view v-for="d in recent" :key="d.id" class="log">
        <text class="log-type">{{ typeLabel(d.drillType) }}</text>
        <text class="log-content">{{ d.content }}</text>
        <text class="log-date">{{ d.createdAt.slice(0, 10) }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Button as NutButton, Textarea as NutTextarea } from '@nutui/nutui-taro'
import VoiceInputBtn from '@/components/VoiceInputBtn.vue'
import { api } from '@/api'
import { showToast } from '@/utils/platform'
import type { ShenlunDrillLog, ShenlunMineLog, ShenlunNormTerm } from '@/types'

definePageConfig({ navigationBarTitleText: '阶梯训练' })

const mode = ref<'sentence' | 'imitate' | 'oral'>('sentence')
const content = ref('')
const promptText = ref('')
const promptMeta = ref<{ termIds: string[]; mineId?: string }>({ termIds: [] })
const saving = ref(false)
const recent = ref<ShenlunDrillLog[]>([])
const terms = ref<ShenlunNormTerm[]>([])
const mines = ref<ShenlunMineLog[]>([])

const tabs = [
  { value: 'sentence' as const, label: '①造句' },
  { value: 'imitate' as const, label: '②仿写' },
  { value: 'oral' as const, label: '③口述' },
]

const modeHint = computed(() => ({
  sentence: '用下面 3 个规范词，写一句通顺的话（不求文采）',
  imitate: '换主题仿写一句（民生/教育/环保等）',
  oral: '合上材料，口头概括：是什么 / 原因 / 启发（可打字记录）',
}[mode.value]))

const placeholder = computed(() => ({
  sentence: '例：改革进入深水区，要啃硬骨头，最终要让群众有获得感。',
  imitate: '例：推进乡村振兴，既要防止千村一面，也要避免有面子没里子……',
  oral: '这篇讲的是……原因是……启发是……',
}[mode.value]))

function typeLabel(t: string) {
  return { sentence: '造句', imitate: '仿写', oral: '口述' }[t] || t
}

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function prepare() {
  content.value = ''
  if (mode.value === 'sentence') {
    const pool = terms.value.filter((t) => !t.mastered)
    const pick = shuffle(pool.length >= 3 ? pool : terms.value).slice(0, 3)
    if (!pick.length) {
      promptText.value = '词库暂空，请先完成三刀解剖积累规范词'
      promptMeta.value = { termIds: [] }
      return
    }
    promptText.value = pick.map((t) => t.term).join(' · ')
    promptMeta.value = { termIds: pick.map((t) => t.id) }
    return
  }
  if (mode.value === 'imitate') {
    const allTpl = mines.value.flatMap((m) =>
      (m.templates || [])
        .filter((t) => t.original || t.template)
        .map((t) => ({ mineId: m.id, title: m.articleTitle, ...t })),
    )
    const hit = shuffle(allTpl)[0]
    if (!hit) {
      promptText.value = '暂无句式，请先在三刀解剖中摘取万能句式'
      promptMeta.value = { termIds: [] }
      return
    }
    promptText.value = `【${hit.title || '开采记录'}】\n原文：${hit.original || '—'}\n模板：${hit.template || '—'}`
    promptMeta.value = { termIds: [], mineId: hit.mineId }
    return
  }
  const mine = shuffle(mines.value)[0]
  if (!mine) {
    promptText.value = '暂无开采文章，请先读一篇时评并做三刀解剖'
    promptMeta.value = { termIds: [] }
    return
  }
  promptText.value = `围绕《${mine.articleTitle || '今日时评'}》口述概括：是什么事？原因？启发？`
  promptMeta.value = { termIds: [], mineId: mine.id }
}

async function load() {
  const [r1, r2, r3] = await Promise.all([
    api.listRmrbTerms('learning'),
    api.listRmrbMines(),
    api.listRmrbDrills(),
  ])
  if (r1.code === 0 && r1.data) terms.value = r1.data
  if (r2.code === 0 && r2.data) mines.value = r2.data
  if (r3.code === 0 && r3.data) recent.value = r3.data.slice(0, 8)
  prepare()
}

async function onSave() {
  if (!content.value.trim()) {
    showToast('请先写练习内容')
    return
  }
  saving.value = true
  try {
    const res = await api.addRmrbDrill({
      drillType: mode.value,
      content: content.value.trim(),
      prompt: promptText.value,
      refMineId: promptMeta.value.mineId || null,
      refTermIds: promptMeta.value.termIds,
    })
    if (res.code === 0) {
      showToast('已记录，继续保持', 'success')
      content.value = ''
      await load()
    } else {
      showToast(res.message || '提交失败', 'error')
    }
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-drill {
  @include page-padding;
  padding-bottom: 40px;
}
.tip { font-size: 12px; color: $text-muted; line-height: 1.5; margin-bottom: 12px; }
.tabs { display: flex; gap: 8px; margin-bottom: 12px;
  .tab {
    flex: 1; text-align: center; padding: 8px; border-radius: 8px; background: $card-bg; font-size: 13px;
    &.on { background: $primary-light; color: $primary-color; font-weight: 700; }
  }
}
.prompt-card {
  @include card; padding: 12px; margin-bottom: 12px;
  .prompt-label { display: block; font-size: 12px; color: $primary-color; font-weight: 600; margin-bottom: 6px; }
  .prompt-body { display: block; font-size: 14px; line-height: 1.55; white-space: pre-wrap; }
  .refresh { display: inline-block; margin-top: 8px; font-size: 12px; color: $accent-blue; }
}
.field { margin-bottom: 14px;
  .label-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;
  }
  .label { font-size: 13px; font-weight: 600; flex: 1; }
}
.recent { margin-top: 20px;
  .block-title { display: block; font-size: 14px; font-weight: 700; margin-bottom: 8px; }
  .log {
    @include card; padding: 10px 12px; margin-bottom: 8px;
    .log-type { font-size: 11px; color: $primary-color; margin-right: 8px; }
    .log-content { display: block; font-size: 13px; line-height: 1.45; margin: 4px 0; }
    .log-date { font-size: 11px; color: $text-muted; }
  }
}
</style>
