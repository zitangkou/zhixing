<template>
  <view class="page-mines" :class="themeClass">
    <view class="stats-card" v-if="stats">
      <view class="stat">
        <text class="num">{{ stats.weekMineDays }}/{{ stats.weekMineTarget }}</text>
        <text class="label">本周开采</text>
      </view>
      <view class="stat">
        <text class="num">{{ stats.termCount }}</text>
        <text class="label">规范词</text>
      </view>
      <view class="stat">
        <text class="num">{{ stats.weekDrillCount || 0 }}</text>
        <text class="label">本周练习</text>
      </view>
    </view>

    <view class="hint">每天一行：先梳理骨架，再摘规范词 / 金句 / 动词 / 句式。点开卡片可继续编辑。</view>

    <view class="actions">
      <nut-button type="primary" size="small" @click="goEdit()">今日开采</nut-button>
      <nut-button plain type="primary" size="small" @click="go('/pages/rmrb/drill')">阶梯训练</nut-button>
      <nut-button plain type="primary" size="small" @click="go('/pages/rmrb/terms')">规范词库</nut-button>
    </view>

    <view v-if="loading" class="empty">加载中...</view>
    <view v-else-if="!list.length" class="empty">
      <text class="empty-title">暂无开采记录</text>
      <text class="empty-desc">读完人民时评后点「三刀解剖」</text>
    </view>

    <view v-else class="mine-list">
      <view v-for="m in list" :key="m.id" class="mine-card" @tap="goEdit(m.id)">
        <!-- 头 -->
        <view class="mine-head">
          <text class="mine-date">{{ m.mineDate }}</text>
          <view class="mine-meta">
            <text v-if="termCount(m)" class="meta-chip">规范词 {{ termCount(m) }}</text>
            <text v-if="quoteCount(m)" class="meta-chip">金句 {{ quoteCount(m) }}</text>
            <text v-if="verbCount(m)" class="meta-chip">动词 {{ verbCount(m) }}</text>
            <text v-if="m.templates?.length" class="meta-chip">句式 {{ m.templates.length }}</text>
          </view>
        </view>
        <text class="mine-title">{{ m.articleTitle || '（粘贴开采）' }}</text>

        <!-- 骨架 -->
        <view v-if="hasArgument(m)" class="block">
          <view class="block-head">
            <text class="block-title">论证骨架</text>
            <text v-if="m.argument?.templateName" class="block-tag">{{ m.argument.templateName }}</text>
          </view>

          <view v-if="m.argument?.overview || m.argumentChain" class="kv">
            <text class="kv-label">总论点</text>
            <text class="kv-body">{{ m.argument?.overview || m.argumentChain }}</text>
          </view>
          <view v-if="m.argument?.overviewMethod" class="kv subtle">
            <text class="kv-label">论证方法</text>
            <text class="kv-body">{{ m.argument.overviewMethod }}</text>
          </view>
          <view v-if="m.argument?.overviewTemplate" class="kv subtle">
            <text class="kv-label">套用模板</text>
            <text class="kv-body mono">{{ m.argument.overviewTemplate }}</text>
          </view>

          <!-- 分论点 -->
          <view v-if="m.argument?.points?.length" class="point-list">
            <view
              v-for="(p, i) in m.argument.points"
              :key="i"
              class="point-card"
            >
              <text class="point-idx">分论点 {{ i + 1 }}</text>
              <text class="point-title">{{ p.title || p.claim || '（未填标题）' }}</text>
              <view v-if="p.evidence" class="kv">
                <text class="kv-label">论据</text>
                <text class="kv-body">{{ p.evidence }}</text>
              </view>
              <view v-if="p.summary" class="kv">
                <text class="kv-label">小结</text>
                <text class="kv-body">{{ p.summary }}</text>
              </view>
              <view v-if="p.method" class="kv subtle">
                <text class="kv-label">论证方法</text>
                <text class="kv-body">{{ p.method }}</text>
              </view>
              <view v-if="p.methodNote" class="kv subtle">
                <text class="kv-label">方法说明</text>
                <text class="kv-body">{{ p.methodNote }}</text>
              </view>
              <view v-if="p.template" class="kv subtle">
                <text class="kv-label">套用模板</text>
                <text class="kv-body mono">{{ p.template }}</text>
              </view>
            </view>
          </view>

          <!-- 线性骨架 -->
          <view v-else-if="m.argument?.fields?.length" class="field-list">
            <view v-for="(f, i) in m.argument.fields" :key="i" class="kv">
              <text class="kv-label">{{ f.label || f.key || `步骤${i + 1}` }}</text>
              <text class="kv-body">{{ f.content || '（未填）' }}</text>
            </view>
          </view>

          <!-- 总结 -->
          <view v-if="m.argument?.conclusion" class="kv conclusion">
            <text class="kv-label">总结</text>
            <text class="kv-body">{{ m.argument.conclusion }}</text>
          </view>
        </view>

        <!-- 金句 -->
        <view v-if="(m.quotes || []).length" class="block">
          <view class="block-head">
            <text class="block-title">经典金句</text>
            <text class="block-count">{{ quoteCount(m) }}</text>
          </view>
          <view
            v-for="(q, i) in (m.quotes || []).filter((x) => x.text?.trim())"
            :key="'q' + i"
            class="quote-item"
          >
            <text class="quote-text">「{{ q.text }}」</text>
            <text v-if="q.source" class="quote-meta">出处：{{ q.source }}</text>
            <text v-if="q.meaning" class="quote-meta">释义：{{ q.meaning }}</text>
          </view>
        </view>

        <!-- 规范词 -->
        <view v-if="termCount(m)" class="block">
          <view class="block-head">
            <text class="block-title">规范词</text>
            <text class="block-count">{{ termCount(m) }}</text>
          </view>
          <view class="term-table">
            <view v-for="(t, i) in termRows(m)" :key="'t' + i" class="term-row">
              <text class="term-word">{{ t.term }}</text>
              <text v-if="t.category" class="term-cat">{{ t.category }}</text>
              <text v-if="t.plainWord" class="term-plain">{{ t.plainWord }}</text>
            </view>
          </view>
        </view>

        <!-- 动词 -->
        <view v-if="verbCount(m)" class="block">
          <view class="block-head">
            <text class="block-title">高频动词</text>
            <text class="block-count">{{ verbCount(m) }}</text>
          </view>
          <view class="term-table">
            <view v-for="(v, i) in verbRows(m)" :key="'v' + i" class="term-row">
              <text class="term-word verb">{{ v.verb }}</text>
              <text v-if="v.category" class="term-cat">{{ v.category }}</text>
              <text v-if="v.usage" class="term-plain">{{ v.usage }}</text>
            </view>
          </view>
        </view>

        <!-- 句式 -->
        <view v-if="(m.templates || []).length" class="block">
          <view class="block-head">
            <text class="block-title">万能句式</text>
            <text class="block-count">{{ m.templates.length }}</text>
          </view>
          <view
            v-for="(tpl, i) in (m.templates || []).filter((x) => x.original?.trim() || x.template?.trim() || x.imitate?.trim())"
            :key="'tpl' + i"
            class="tpl-item"
          >
            <text class="tpl-type">{{ tpl.typeName || tpl.type || `句式 ${i + 1}` }}</text>
            <view v-if="tpl.original" class="kv">
              <text class="kv-label">原文</text>
              <text class="kv-body">{{ tpl.original }}</text>
            </view>
            <view v-if="tpl.template" class="kv">
              <text class="kv-label">模板</text>
              <text class="kv-body mono">{{ tpl.template }}</text>
            </view>
            <view v-if="tpl.imitate" class="kv">
              <text class="kv-label">仿写</text>
              <text class="kv-body">{{ tpl.imitate }}</text>
            </view>
          </view>
        </view>

        <text class="card-foot">点击继续编辑 ›</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import { api } from '@/api'
import { splitRmrbTerms } from '@/utils/rmrb'
import type { ShenlunMineLog, ShenlunStats } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '开采本' })

const { themeClass } = useThemeClass()
const loading = ref(false)
const list = ref<ShenlunMineLog[]>([])
const stats = ref<ShenlunStats | null>(null)

function termRows(m: ShenlunMineLog) {
  const out: { term: string; category: string; plainWord: string }[] = []
  for (const t of m.terms || []) {
    if (typeof t === 'string') {
      for (const w of splitRmrbTerms(t)) out.push({ term: w, category: '', plainWord: '' })
      continue
    }
    const parts = splitRmrbTerms(t.term)
    const words = parts.length ? parts : [t.term].filter(Boolean)
    for (const w of words) {
      out.push({
        term: w,
        category: t.category || '',
        plainWord: t.plainWord || '',
      })
    }
  }
  return out
}

function verbRows(m: ShenlunMineLog) {
  const out: { verb: string; category: string; usage: string }[] = []
  for (const v of m.verbs || []) {
    const parts = splitRmrbTerms(v.verb)
    const words = parts.length ? parts : [v.verb].filter(Boolean)
    for (const w of words) {
      out.push({
        verb: w,
        category: v.category || '',
        usage: v.usage || '',
      })
    }
  }
  return out
}

function termCount(m: ShenlunMineLog) {
  return termRows(m).length
}
function quoteCount(m: ShenlunMineLog) {
  return (m.quotes || []).filter((q) => q.text?.trim()).length
}
function verbCount(m: ShenlunMineLog) {
  return verbRows(m).length
}

function hasArgument(m: ShenlunMineLog) {
  const a = m.argument
  if (!a) return !!(m.argumentChain || '').trim()
  return !!(
    a.overview
    || a.conclusion
    || a.templateName
    || a.overviewMethod
    || (a.points && a.points.length)
    || (a.fields && a.fields.length)
    || (m.argumentChain || '').trim()
  )
}

async function load() {
  loading.value = true
  try {
    const [r1, r2] = await Promise.all([api.listRmrbMines(), api.getRmrbStats()])
    if (r1.code === 0 && r1.data) list.value = r1.data
    if (r2.code === 0 && r2.data) stats.value = r2.data
  } finally {
    loading.value = false
  }
}

function go(url: string) {
  Taro.navigateTo({ url })
}
function goEdit(id?: string) {
  Taro.navigateTo({ url: id ? `/pages/rmrb/mine-edit?id=${id}` : '/pages/rmrb/mine-edit' })
}

onMounted(load)
useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-mines {
  @include page-padding;
  padding-bottom: 48px;
}

.stats-card {
  @include card;
  display: flex;
  padding: 14px;
  margin-bottom: 10px;
  .stat {
    flex: 1;
    text-align: center;
    .num {
      display: block;
      font-size: 18px;
      font-weight: 700;
      color: $primary-color;
    }
    .label {
      font-size: 12px;
      color: $text-muted;
    }
  }
}

.hint {
  font-size: 12px;
  color: $text-muted;
  line-height: 1.5;
  margin-bottom: 12px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.empty {
  text-align: center;
  padding: 48px 20px;
  color: $text-muted;
  .empty-title {
    display: block;
    font-size: 15px;
    margin-bottom: 6px;
    color: $text-primary;
  }
}

.mine-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mine-card {
  @include card;
  padding: 16px;
}

.mine-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.mine-date {
  font-size: 14px;
  font-weight: 700;
  color: $text-primary;
}

.mine-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.meta-chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: $page-bg;
  color: $text-secondary;
}

.mine-title {
  display: block;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.45;
  color: $text-primary;
  margin-bottom: 14px;
}

.block {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid $border-color;
}

.block-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.block-title {
  font-size: 14px;
  font-weight: 700;
  color: $text-primary;
}

.block-tag,
.block-count {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: $primary-light;
  color: $primary-color;
  font-weight: 600;
}

.kv {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 8px;
  &.subtle .kv-label {
    color: $text-muted;
  }
  &.conclusion {
    margin-top: 12px;
    padding: 10px 12px;
    background: $primary-faint;
    border-radius: 8px;
    border-left: 3px solid $primary-color;
    .kv-label {
      color: $primary-color;
    }
  }
}

.kv-label {
  flex-shrink: 0;
  width: 64px;
  font-size: 12px;
  font-weight: 600;
  color: $primary-color;
  line-height: 1.55;
  padding-top: 1px;
}

.kv-body {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  line-height: 1.65;
  color: $text-primary;
  white-space: pre-wrap;
  word-break: break-word;
  &.mono {
    color: $text-secondary;
  }
}

.point-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 10px 0 4px;
}

.point-card {
  background: $page-bg;
  border-radius: 8px;
  padding: 12px;
}

.point-idx {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: $primary-color;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
}

.point-title {
  display: block;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.5;
  color: $text-primary;
  margin-bottom: 8px;
  word-break: break-word;
}

.field-list {
  margin: 4px 0;
}

.quote-item {
  margin-bottom: 10px;
  padding: 10px 12px;
  background: $page-bg;
  border-radius: 8px;
  &:last-child { margin-bottom: 0; }
}

.quote-text {
  display: block;
  font-size: 13px;
  line-height: 1.6;
  color: $text-primary;
  word-break: break-word;
}

.quote-meta {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: $text-muted;
  line-height: 1.45;
}

.term-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.term-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 8px;
  padding: 8px 10px;
  background: $page-bg;
  border-radius: 6px;
}

.term-word {
  font-size: 14px;
  font-weight: 700;
  color: $text-primary;
  &.verb { color: #2e7d32; }
}

.term-cat {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: $primary-light;
  color: $primary-color;
}

.term-plain {
  flex: 1 1 100%;
  font-size: 12px;
  color: $text-secondary;
  line-height: 1.5;
  word-break: break-word;
}

.tpl-item {
  margin-bottom: 10px;
  padding: 10px 12px;
  background: $page-bg;
  border-radius: 8px;
  &:last-child { margin-bottom: 0; }
}

.tpl-type {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: $primary-color;
  margin-bottom: 6px;
}

.card-foot {
  display: block;
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px dashed $border-color;
  text-align: right;
  font-size: 12px;
  color: $text-muted;
}
</style>
