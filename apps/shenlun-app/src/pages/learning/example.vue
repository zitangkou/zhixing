<template>
  <view class="learning-page">
    <view v-if="loading" class="state-box">正在加载教研示范…</view>
    <view v-else-if="error" class="state-box" @tap="load">{{ error }}，点击重试</view>
    <template v-else-if="bundle">
      <view class="learning-head">
        <text class="kicker">申论学习 · {{ bundle.article.publishDate }}</text>
        <text class="title">{{ bundle.article.title }}</text>
        <text class="note">{{ bundle.article.source }} · 免费阅读与练习</text>
      </view>

      <scroll-view scroll-x class="nav-scroll">
        <view class="nav-row">
          <button class="nav-chip" :class="{ active: section === 'article' }" @tap="section = 'article'">读原文</button>
          <button class="nav-chip" :class="{ active: section === 'example' }" @tap="section = 'example'">看三刀</button>
          <button class="nav-chip" :class="{ active: section === 'practice' }" @tap="section = 'practice'">做短练习</button>
        </view>
      </scroll-view>

      <template v-if="section === 'article'">
        <view class="learning-card">
          <text class="card-label">学习提示</text>
          <text class="body">先独立阅读全文，判断中心观点和行文结构；读完再看示范，不必追求一次读透。</text>
        </view>
        <view class="learning-card">
          <text class="card-label">原文</text>
          <text class="article-body">{{ bundle.article.content || '暂未提供全文' }}</text>
        </view>
        <button class="primary-action" @tap="section = 'example'">读完了，看三刀示范</button>
      </template>

      <template v-else-if="section === 'example'">
        <view class="learning-card">
          <text class="card-label">材料节选</text>
          <text class="body">{{ bundle.example.sourceExcerpt }}</text>
        </view>

        <view class="cut-heading">
          <text class="cut-number">01</text>
          <view><text class="cut-title">第一刀 · 论证骨架</text><text class="note">看文章如何立论与推进</text></view>
        </view>
        <view class="learning-card">
          <text class="field-name">总论点</text>
          <text class="body">{{ bundle.example.argument.overview }}</text>
          <view
            v-for="(point, index) in bundle.example.argument.points"
            :key="`${index}-${point.title}`"
            class="point"
          >
            <text class="point-index">分论点 {{ index + 1 }}</text>
            <text class="point-title">{{ point.title || point.claim }}</text>
            <view class="field"><text class="field-name">论据</text><text class="body">{{ point.evidence }}</text></view>
            <view class="field"><text class="field-name">小结</text><text class="body">{{ point.summary }}</text></view>
            <view class="method">
              <text class="method-name">{{ point.method }}</text>
              <text class="body">{{ point.methodNote }}</text>
              <text class="template-text">套用模板：{{ point.template }}</text>
            </view>
          </view>
          <view class="field"><text class="field-name">总结</text><text class="body">{{ bundle.example.argument.conclusion }}</text></view>
        </view>

        <view class="cut-heading">
          <text class="cut-number">02</text>
          <view><text class="cut-title">第二刀 · 规范表达</text><text class="note">把好词、金句和动词带走</text></view>
        </view>
        <view class="learning-card">
          <text class="field-name">规范词</text>
          <view class="chip-row"><text v-for="item in bundle.example.terms" :key="item.term" class="term-chip">{{ item.term }} · {{ item.category }}</text></view>
          <template v-if="bundle.example.quotes.length">
            <text class="field-name spaced">经典金句</text>
            <view v-for="quote in bundle.example.quotes" :key="quote.text" class="expression">
              <text class="body">{{ quote.text }}</text><text class="note">{{ quote.source }}{{ quote.meaning ? ` · ${quote.meaning}` : '' }}</text>
            </view>
          </template>
          <template v-if="bundle.example.verbs.length">
            <text class="field-name spaced">高频动词</text>
            <view v-for="verb in bundle.example.verbs" :key="verb.verb" class="expression">
              <text class="method-name">{{ verb.verb }}</text><text class="body">{{ verb.usage }}</text>
            </view>
          </template>
        </view>

        <view class="cut-heading">
          <text class="cut-number">03</text>
          <view><text class="cut-title">第三刀 · 万能句式</text><text class="note">从原句提炼可迁移模板</text></view>
        </view>
        <view v-for="(item, index) in bundle.example.templates" :key="`${index}-${item.type}`" class="learning-card">
          <text class="point-index">{{ item.typeName || item.type }}</text>
          <view class="field"><text class="field-name">原句</text><text class="body">{{ item.original }}</text></view>
          <view class="field"><text class="field-name">模板</text><text class="template-text">{{ item.template }}</text></view>
          <view class="field"><text class="field-name">仿写</text><text class="body">{{ item.imitate }}</text></view>
        </view>
        <button class="primary-action" @tap="section = 'practice'">看懂了，完成短练习</button>
        <button v-if="loggedIn" class="secondary-action" @tap="openPersonalMine">进入原版个人三刀开采</button>
      </template>

      <template v-else>
        <view class="learning-card">
          <text class="card-label">今日短练习</text>
          <text class="body">{{ bundle.example.practice.prompt }}</text>
          <textarea
            v-model="answer"
            class="answer-input"
            :maxlength="bundle.example.practice.maxLength"
            placeholder="先独立写，再查看参考"
            placeholder-class="answer-placeholder"
            @input="save"
          />
          <view class="count" :class="{ invalid: answerLength > 0 && !lengthValid }">
            {{ answerLength }} / {{ bundle.example.practice.minLength }}～{{ bundle.example.practice.maxLength }} 字
          </view>
          <text class="field-name spaced">提交前自查</text>
          <view
            v-for="(item, index) in bundle.example.practice.checks"
            :key="item"
            class="check-row"
            @tap="toggleCheck(index)"
          >
            <text class="check-box" :class="{ checked: checks[index] }">{{ checks[index] ? '✓' : '' }}</text>
            <text class="body">{{ item }}</text>
          </view>
          <button v-if="!revealed" class="primary-action inner" @tap="reveal">完成并查看参考</button>
        </view>

        <view v-if="revealed" class="learning-card reference-card">
          <text class="card-label">参考对照</text>
          <text class="body">{{ bundle.example.practice.referenceAnswer }}</text>
          <text class="reference-note">这是教研参考，不是 AI 评分。请比较观点、结构和表达，不必逐字一致。</text>
          <button class="secondary-action" @tap="editAgain">返回修改</button>
        </view>
        <text class="storage-note">练习记录仅保存在当前设备；清理缓存或更换设备会丢失。</text>
      </template>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { api, type ShenlunLearningBundle } from '@/api'
import { showToast } from '@/utils/platform'
import { isLoggedIn } from '@/utils/auth'

type Section = 'article' | 'example' | 'practice'
interface SavedPractice { answer?: string; checks?: boolean[]; revealed?: boolean; updatedAt?: string }

const router = useRouter()
const articleId = String(router.params?.id || '').trim()
const bundle = ref<ShenlunLearningBundle | null>(null)
const loading = ref(true)
const error = ref('')
const section = ref<Section>('article')
const answer = ref('')
const checks = ref<boolean[]>([])
const revealed = ref(false)
const loggedIn = isLoggedIn()
const storageKey = computed(() => `shenlun-learning:${articleId}:${bundle.value?.revision || ''}`)
const answerLength = computed(() => answer.value.trim().length)
const lengthValid = computed(() => {
  const practice = bundle.value?.example.practice
  return Boolean(practice && answerLength.value >= practice.minLength && answerLength.value <= practice.maxLength)
})
const checksValid = computed(() => checks.value.length > 0 && checks.value.every(Boolean))

function restore() {
  if (!bundle.value) return
  let saved: SavedPractice = {}
  try { saved = Taro.getStorageSync(storageKey.value) || {} } catch { /* 阅读不依赖本机存储。 */ }
  answer.value = typeof saved.answer === 'string' ? saved.answer.slice(0, bundle.value.example.practice.maxLength) : ''
  checks.value = bundle.value.example.practice.checks.map((_, index) => saved.checks?.[index] === true)
  revealed.value = saved.revealed === true && lengthValid.value && checksValid.value
}

function save() {
  try { Taro.setStorageSync(storageKey.value, { answer: answer.value, checks: checks.value, revealed: revealed.value, updatedAt: new Date().toISOString() }) }
  catch { showToast('本机保存失败，离开页面后可能丢失练习') }
}

function toggleCheck(index: number) {
  checks.value[index] = !checks.value[index]
  if (!checksValid.value) revealed.value = false
  save()
}

function reveal() {
  if (!lengthValid.value) {
    showToast(`请完成 ${bundle.value?.example.practice.minLength || 0}～${bundle.value?.example.practice.maxLength || 0} 字作答`)
    return
  }
  if (!checksValid.value) {
    showToast('请先完成全部自查项')
    return
  }
  revealed.value = true
  save()
}

function editAgain() {
  revealed.value = false
  save()
}

function openPersonalMine() {
  Taro.navigateTo({ url: `/pages/reading/detail?id=${encodeURIComponent(articleId)}` })
}

async function load() {
  loading.value = true
  error.value = ''
  if (!articleId) {
    error.value = '学习链接缺少文章'
    loading.value = false
    return
  }
  const response = await api.getLearningArticle(articleId)
  if (response.code === 0 && response.data) {
    bundle.value = response.data
    restore()
  } else error.value = response.message || '学习内容加载失败'
  loading.value = false
}

onMounted(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.learning-page { @include page-padding; padding-bottom: calc(32px + env(safe-area-inset-bottom)); }
.state-box { @include card; margin-top: 28px; color: $text-muted; text-align: center; }
.learning-head { padding: 8px 0 16px; }
.kicker { display: block; color: $primary-color; font-size: 12px; }
.title { display: block; margin: 8px 0; color: $text-primary; font-size: 22px; font-weight: 700; line-height: 1.5; }
.note { display: block; color: $text-muted; font-size: 12px; line-height: 1.7; }
.nav-scroll { margin-bottom: 12px; white-space: nowrap; }
.nav-row { display: inline-flex; gap: 8px; }
.nav-chip { @include hit-target; margin: 0; padding: 7px 16px; border: 1px solid $border-color; border-radius: 22px; background: $card-bg; color: $text-secondary; font-size: 13px; line-height: 28px; }
.nav-chip::after, .primary-action::after, .secondary-action::after { border: 0; }
.nav-chip.active { border-color: $primary-color; background: $primary-light; color: $primary-color; font-weight: 700; }
.learning-card { @include card; }
.card-label, .field-name { display: block; margin-bottom: 8px; color: $text-primary; font-size: 14px; font-weight: 700; }
.body { display: block; color: $text-primary; font-size: 14px; line-height: 1.8; white-space: pre-wrap; }
.article-body { display: block; color: $text-primary; font-size: 16px; line-height: 1.95; white-space: pre-wrap; }
.primary-action, .secondary-action { @include hit-target; width: 100%; margin: 12px 0 4px; border: 0; border-radius: 22px; font-size: 14px; font-weight: 700; }
.primary-action { background: linear-gradient(135deg, $primary-color, $primary-dark); color: $on-primary; }
.secondary-action { border: 1px solid $primary-color; background: $card-bg; color: $primary-color; }
.primary-action.inner { margin-top: 18px; }
.cut-heading { display: flex; align-items: center; gap: 12px; margin: 22px 2px 10px; }
.cut-number { color: $primary-color; font-size: 25px; font-weight: 750; }
.cut-title { display: block; color: $text-primary; font-size: 17px; font-weight: 700; }
.point { margin-top: 16px; padding-top: 16px; border-top: 1px solid $border-color; }
.point-index { display: block; color: $primary-color; font-size: 12px; font-weight: 700; }
.point-title { display: block; margin-top: 6px; color: $text-primary; font-size: 16px; font-weight: 700; line-height: 1.6; }
.field { margin-top: 13px; }
.method { margin-top: 13px; padding: 12px; border-radius: 10px; background: $primary-faint; }
.method-name { display: block; margin-bottom: 4px; color: $primary-color; font-size: 13px; font-weight: 700; }
.template-text { display: block; margin-top: 7px; color: $primary-dark; font-size: 13px; line-height: 1.7; }
.chip-row { display: flex; flex-wrap: wrap; gap: 7px; }
.term-chip { padding: 6px 9px; border-radius: 7px; background: $primary-light; color: $primary-color; font-size: 12px; }
.spaced { margin-top: 18px; }
.expression { padding: 10px 0; border-bottom: 1px solid $border-color; }
.expression:last-child { border-bottom: 0; }
.answer-input { width: 100%; min-height: 150px; box-sizing: border-box; margin-top: 14px; padding: 13px; border: 1px solid $border-color; border-radius: 12px; background: $input-bg; color: $text-primary; font-size: 15px; line-height: 1.8; }
.answer-placeholder { color: $text-muted; }
.count { margin-top: 6px; color: $text-muted; font-size: 11px; text-align: right; }
.count.invalid { color: $danger; }
.check-row { @include hit-target; justify-content: flex-start; gap: 10px; }
.check-box { display: flex; width: 22px; height: 22px; flex: 0 0 22px; align-items: center; justify-content: center; border: 1px solid $border-color; border-radius: 7px; color: $on-primary; font-size: 13px; }
.check-box.checked { border-color: $primary-color; background: $primary-color; }
.reference-card { border: 1px solid $primary-soft; }
.reference-note, .storage-note { display: block; margin-top: 12px; color: $text-muted; font-size: 11px; line-height: 1.7; }
.storage-note { margin: 14px 2px 0; }
</style>
