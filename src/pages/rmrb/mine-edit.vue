<template>
  <view class="page-mine-edit" :class="themeClass">
    <text class="hw-tip">平板手写：先点输入框，再切到手写输入法；多行框更适合长句手写。</text>
    <view class="meta-row">
      <view class="meta-date">
        <nut-input v-model="form.mineDate" placeholder="日期" />
      </view>
      <view class="meta-title">
        <nut-input v-model="form.articleTitle" placeholder="文章标题" />
      </view>
    </view>

    <scroll-view scroll-x class="tab-scroll">
      <view class="tab-row">
        <text
          v-for="tab in tabs"
          :key="tab.key"
          class="tab"
          :class="{ on: activeTab === tab.key }"
          @tap="activeTab = tab.key"
        >
          {{ tab.label }}
        </text>
      </view>
    </scroll-view>

    <!-- 规范词（骨架之后） -->
    <view v-show="activeTab === 'terms'" class="section">
      <view class="sec-head">
        <text class="sec-title">② 规范词</text>
        <view class="sec-actions">
          <text class="sec-add" @tap="addTermCategory">+ 分类</text>
          <text class="sec-add" @tap="addTermRow">+ 添加</text>
        </view>
      </view>
      <text class="field-tip">多个词可用顿号分隔；解释会同步到规范词库。电脑端在分类上滚轮可快速切换</text>
      <view v-for="(t, i) in termRows" :key="'term-' + i" class="term-block">
        <view class="term-line">
          <view class="term-input">
            <nut-input v-model="t.term" placeholder="规范词（可顿号分隔）" />
          </view>
          <WheelPicker
            :range="categoryNames"
            :value="categoryIndex(t.category)"
            @change="(e) => onTermCategory(i, e)"
          >
            <view class="mini-select">{{ shortCat(t.category) }} ▾</view>
          </WheelPicker>
          <text class="x-del" @tap="removeTerm(i)">×</text>
        </view>
        <view v-if="splitPreview(t.term).length > 1" class="chip-row">
          <text v-for="(w, wi) in splitPreview(t.term)" :key="wi" class="chip">{{ w }}</text>
        </view>
        <nut-input v-model="t.plainWord" placeholder="解释：词义/语境/可替换的普通说法" />
      </view>
      <view v-if="!termRows.length" class="empty-hint" @tap="addTermRow">点击添加规范词</view>
    </view>

    <!-- 经典金句 -->
    <view v-show="activeTab === 'quotes'" class="section">
      <view class="sec-head">
        <text class="sec-title">③ 经典金句</text>
        <text class="sec-add" @tap="addQuoteRow">+ 添加</text>
      </view>
      <view v-for="(q, i) in quoteRows" :key="'q-' + i" class="quote-block">
        <view class="term-line">
          <view class="term-input grow">
            <nut-input v-model="q.text" placeholder="金句原文" />
          </view>
          <text class="x-del" @tap="quoteRows.splice(i, 1)">×</text>
        </view>
        <nut-input v-model="q.source" placeholder="来源（如：清代万斯大）" />
        <nut-input v-model="q.meaning" placeholder="释义（如：有利于百姓的事，再小也要去做）" />
      </view>
      <view v-if="!quoteRows.length" class="empty-hint" @tap="addQuoteRow">如：利民之事，丝发必兴</view>
    </view>

    <!-- 高频动词 -->
    <view v-show="activeTab === 'verbs'" class="section">
      <view class="sec-head">
        <text class="sec-title">④ 高频动词</text>
        <view class="sec-actions">
          <text class="sec-add" @tap="addVerbCategory">+ 分类</text>
          <text class="sec-add" @tap="addVerbRow">+ 添加</text>
        </view>
      </view>
      <text class="field-tip">多个动词可用顿号分隔，如：优化、推行、倒逼</text>
      <view v-for="(v, i) in verbRows" :key="'verb-' + i" class="term-block">
        <view class="term-line">
          <view class="term-input">
            <nut-input v-model="v.verb" placeholder="动词（可顿号分隔）" />
          </view>
          <WheelPicker
            :range="verbCategoryNames"
            :value="verbCategoryIndex(v.category)"
            @change="(e) => onVerbCategory(i, e)"
          >
            <view class="mini-select">{{ shortCat(v.category) }} ▾</view>
          </WheelPicker>
          <text class="x-del" @tap="verbRows.splice(i, 1)">×</text>
        </view>
        <nut-input v-model="v.usage" placeholder="适用语境（可选）" />
        <view v-if="splitPreview(v.verb).length > 1" class="chip-row">
          <text v-for="(w, wi) in splitPreview(v.verb)" :key="wi" class="chip verb">{{ w }}</text>
        </view>
      </view>
      <view v-if="!verbRows.length" class="empty-hint" @tap="addVerbRow">点击添加高频动词</view>
    </view>

    <!-- ① 论证骨架：先梳理结构 -->
    <view v-show="activeTab === 'argument'" class="section">
      <view class="sec-head">
        <text class="sec-title">① 论证骨架</text>
        <text class="sec-add" @tap="showNewSkeleton = !showNewSkeleton">
          {{ showNewSkeleton ? '收起' : '+ 模版' }}
        </text>
      </view>

      <WheelPicker :range="skeletonNames" :value="skeletonIndex" @change="onSkeletonPick">
        <view class="select-bar">
          <text class="select-bar-label">模版</text>
          <text class="select-bar-value">{{ selectedSkeleton?.name || '请选择' }} ▾</text>
        </view>
      </WheelPicker>

      <view v-if="showNewSkeleton" class="new-skel">
        <view class="term-line">
          <view class="term-input grow">
            <nut-input v-model="newSkel.name" placeholder="模版名" />
          </view>
          <WheelPicker
            :range="['线性', '总分']"
            :value="newSkel.mode === 'points' ? 1 : 0"
            @change="onNewSkelMode"
          >
            <view class="mini-select">{{ newSkel.mode === 'points' ? '总分' : '线性' }} ▾</view>
          </WheelPicker>
        </view>
        <nut-input
          v-if="newSkel.mode === 'linear'"
          v-model="newSkel.labels"
          placeholder="步骤：问题,原因,对策"
        />
        <nut-button size="mini" type="primary" block :loading="creatingSkel" @click="createSkeleton">
          创建并选用
        </nut-button>
      </view>

      <template v-if="selectedSkeleton">
        <template v-if="argument.mode === 'linear'">
          <view v-for="(f, i) in argument.fields" :key="f.key || i" class="slot-line">
            <text class="slot-tag">{{ f.label || f.key }}</text>
            <view class="slot-body">
              <nut-textarea v-model="f.content" :rows="2" :placeholder="`填${f.label || f.key}`" />
            </view>
            <VoiceInputBtn v-model="f.content" />
          </view>
        </template>
        <template v-else>
          <view class="slot-line">
            <text class="slot-tag">总论点</text>
            <view class="slot-body">
              <nut-textarea v-model="argument.overview" :rows="2" placeholder="一句话总论点" />
            </view>
            <VoiceInputBtn v-model="argument.overview" />
          </view>
          <view class="method-box">
            <WheelPicker
              :range="overviewMethodNames"
              :value="overviewMethodIndex"
              @change="onOverviewMethodPick"
            >
              <view class="select-bar compact">
                <text class="select-bar-label">论证方法</text>
                <text class="select-bar-value">{{ argument.overviewMethod || '选择预设' }} ▾</text>
              </view>
            </WheelPicker>
            <nut-textarea
              v-model="argument.overviewTemplate"
              :rows="2"
              placeholder="论证模板（可改）"
            />
          </view>

          <view v-for="(p, i) in argument.points" :key="i" class="point-block">
            <view class="point-head">
              <text class="point-idx">分论点{{ i + 1 }}</text>
              <text class="x-del" @tap="argument.points.splice(i, 1)">×</text>
            </view>
            <view class="slot-line">
              <text class="slot-tag">标题</text>
              <view class="slot-body">
                <nut-textarea
                  v-model="p.title"
                  :rows="2"
                  :placeholder="`如：纵向时间推进——领袖的持续关怀`"
                />
              </view>
              <VoiceInputBtn v-model="p.title" />
            </view>
            <view class="slot-line">
              <text class="slot-tag">论据</text>
              <view class="slot-body">
                <nut-textarea
                  v-model="p.evidence"
                  :rows="3"
                  placeholder="可选：事实、论述、案例（支撑本分论点）"
                />
              </view>
              <VoiceInputBtn v-model="p.evidence" />
            </view>
            <view class="slot-line">
              <text class="slot-tag">小结</text>
              <view class="slot-body">
                <nut-textarea
                  v-model="p.summary"
                  :rows="2"
                  placeholder="可选：本分论点收束一句"
                />
              </view>
              <VoiceInputBtn v-model="p.summary" />
            </view>
            <WheelPicker
              :range="pointMethodNames"
              :value="pointMethodIndex(p.method)"
              @change="(e) => onPointMethodPick(i, e)"
            >
              <view class="select-bar compact">
                <text class="select-bar-label">论证方法</text>
                <text class="select-bar-value">{{ p.method || '选择预设' }} ▾</text>
              </view>
            </WheelPicker>
            <nut-textarea
              v-model="p.methodNote"
              :rows="2"
              placeholder="方法说明（可选，选预设可自动带入）"
            />
            <nut-textarea
              v-model="p.template"
              :rows="2"
              placeholder="套用模板（可改）"
            />
          </view>
          <view class="slot-line">
            <text class="slot-tag">总结</text>
            <view class="slot-body">
              <nut-textarea v-model="argument.conclusion" :rows="2" placeholder="收束总结" />
            </view>
            <VoiceInputBtn v-model="argument.conclusion" />
          </view>
          <text class="sec-add inline" @tap="addPoint">+ 分论点</text>
        </template>
      </template>
    </view>

    <!-- 万能句式 -->
    <view v-show="activeTab === 'templates'" class="section">
      <view class="sec-head">
        <text class="sec-title">⑤ 万能句式</text>
        <text class="sec-add" @tap="addTemplate">+ 添加</text>
      </view>
      <view v-for="(tpl, i) in templates" :key="i" class="tpl-block">
        <view class="tpl-head">
          <WheelPicker
            :range="sentenceTypeNames"
            :value="sentenceTypeIndex(tpl.type)"
            @change="(e) => onSentenceType(i, e)"
          >
            <view class="mini-select wide">{{ sentenceTypeLabel(tpl.type) }} ▾</view>
          </WheelPicker>
          <text class="x-del" @tap="templates.splice(i, 1)">×</text>
        </view>
        <view class="voice-field">
          <view class="voice-field-body">
            <nut-textarea v-model="tpl.original" :rows="2" placeholder="原文句" />
          </view>
          <VoiceInputBtn v-model="tpl.original" />
        </view>
        <view class="voice-field">
          <view class="voice-field-body">
            <nut-textarea v-model="tpl.template" :rows="2" placeholder="套用模板（……）" />
          </view>
          <VoiceInputBtn v-model="tpl.template" />
        </view>
        <view class="voice-field">
          <view class="voice-field-body">
            <nut-textarea v-model="tpl.imitate" :rows="2" placeholder="仿写（可选）" />
          </view>
          <VoiceInputBtn v-model="tpl.imitate" />
        </view>
      </view>
    </view>

    <view class="foot">
      <nut-button type="primary" block :loading="saving" @click="onSaveSection">
        {{ saveLabel }}
      </nut-button>
      <nut-button
        v-if="taskId"
        plain
        type="primary"
        block
        class="daily-continue"
        :loading="saving"
        @click="goDailyAnswer"
      >
        完成拆解，继续作答
      </nut-button>
      <text v-if="mineId" class="del-link" @tap="onDelete">删除本条</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import { Button as NutButton, Input as NutInput, Textarea as NutTextarea } from '@nutui/nutui-taro'
import VoiceInputBtn from '@/components/VoiceInputBtn.vue'
import WheelPicker from '@/components/WheelPicker.vue'
import { api } from '@/api'
import { useDailyTaskStore } from '@/store/dailyTask'
import { flushFormBeforeSave } from '@/utils/formFlush'
import { promptText, showConfirm, showToast } from '@/utils/platform'
import {
  RMRB_ARGUMENT_METHOD_PRESETS_FALLBACK,
  RMRB_TERM_CATEGORIES_FALLBACK,
  RMRB_TEMPLATE_TYPES_FALLBACK,
  RMRB_VERB_CATEGORIES_FALLBACK,
  splitRmrbTerms,
} from '@/utils/rmrb'
import type {
  ShenlunArgumentFieldValue,
  ShenlunArgumentMethodPreset,
  ShenlunArgumentPoint,
  ShenlunMineTermItem,
  ShenlunQuoteItem,
  ShenlunSentenceType,
  ShenlunSkeletonTemplate,
  ShenlunTemplateItem,
  ShenlunVerbItem,
} from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '三刀解剖' })

const { themeClass } = useThemeClass()
const router = useRouter()
const dailyTaskStore = useDailyTaskStore()
const taskId = computed(() => (router.params?.taskId || '').trim())
const mineId = ref('')
const articleId = ref('')
/** 避免页面缓存导致重复 load；id 变化时强制重载 */
const loadedForId = ref<string | null>(null)
const saving = ref(false)
const creatingSkel = ref(false)
const showNewSkeleton = ref(false)

type TabKey = 'argument' | 'terms' | 'quotes' | 'verbs' | 'templates'
const tabs: { key: TabKey; label: string }[] = [
  { key: 'argument', label: '骨架' },
  { key: 'terms', label: '规范词' },
  { key: 'quotes', label: '金句' },
  { key: 'verbs', label: '动词' },
  { key: 'templates', label: '句式' },
]
/** 解剖流程：先骨架，再规范词/金句/动词/句式 */
const activeTab = ref<TabKey>('argument')
const saveLabel = computed(() => {
  const map: Record<TabKey, string> = {
    argument: '保存骨架',
    terms: '保存规范词',
    quotes: '保存金句',
    verbs: '保存动词',
    templates: '保存句式',
  }
  return map[activeTab.value]
})

const categories = ref<string[]>([...RMRB_TERM_CATEGORIES_FALLBACK])
const verbCategories = ref<string[]>([...RMRB_VERB_CATEGORIES_FALLBACK])
const methodPresets = ref<ShenlunArgumentMethodPreset[]>(
  RMRB_ARGUMENT_METHOD_PRESETS_FALLBACK.map((p) => ({ ...p })),
)
const skeletons = ref<ShenlunSkeletonTemplate[]>([])
const sentenceTypes = ref<ShenlunSentenceType[]>(
  RMRB_TEMPLATE_TYPES_FALLBACK.map((t, i) => ({
    id: String(i),
    code: t.value,
    name: t.label,
    tip: t.tip,
    sortOrder: i,
    isEnabled: true,
  })),
)

const today = new Date().toISOString().slice(0, 10)
const form = ref({
  mineDate: today,
  articleTitle: decodeURIComponent(router.params?.title || ''),
})

const termRows = ref<ShenlunMineTermItem[]>([
  { term: '', category: categories.value[0] || '其他', plainWord: '' },
])
const quoteRows = ref<ShenlunQuoteItem[]>([])
const verbRows = ref<ShenlunVerbItem[]>([])

function emptyPoint(): ShenlunArgumentPoint {
  return { title: '', claim: '', evidence: '', summary: '', method: '', methodNote: '', template: '' }
}

const argument = reactive<{
  templateId: string
  templateName: string
  mode: string
  overview: string
  conclusion: string
  overviewMethod: string
  overviewTemplate: string
  fields: ShenlunArgumentFieldValue[]
  points: ShenlunArgumentPoint[]
}>({
  templateId: '',
  templateName: '',
  mode: 'points',
  overview: '',
  conclusion: '',
  overviewMethod: '',
  overviewTemplate: '',
  fields: [],
  points: [emptyPoint()],
})

const templates = ref<ShenlunTemplateItem[]>([
  { type: 'dialectic', typeName: '对比转折型', original: '', template: '', imitate: '' },
])

const newSkel = reactive({
  name: '',
  mode: 'linear' as 'linear' | 'points',
  labels: '问题,原因,对策',
})

const categoryNames = computed(() => categories.value)
const verbCategoryNames = computed(() => verbCategories.value)
const skeletonNames = computed(() => skeletons.value.map((s) => s.name))
const sentenceTypeNames = computed(() => sentenceTypes.value.map((t) => t.name))
const overviewPresets = computed(() =>
  methodPresets.value.filter((p) => p.scope === 'overview' || !p.scope),
)
const pointPresets = computed(() =>
  methodPresets.value.filter((p) => p.scope === 'point' || !p.scope),
)
const overviewMethodNames = computed(() => [
  '不选',
  ...overviewPresets.value.map((p) => p.name),
  ...pointPresets.value.map((p) => p.name),
])
const pointMethodNames = computed(() => [
  '不选',
  ...pointPresets.value.map((p) => p.name),
  ...overviewPresets.value.map((p) => p.name),
])
const selectedSkeleton = computed(
  () => skeletons.value.find((s) => s.id === argument.templateId) || null,
)
const skeletonIndex = computed(() => {
  const i = skeletons.value.findIndex((s) => s.id === argument.templateId)
  return i >= 0 ? i : 0
})
const overviewMethodIndex = computed(() => {
  const i = overviewMethodNames.value.indexOf(argument.overviewMethod)
  return i >= 0 ? i : 0
})

function splitPreview(raw: string) {
  return splitRmrbTerms(raw)
}

function shortCat(name: string) {
  if (!name) return '分类'
  return name.length > 4 ? name.slice(0, 4) : name
}

function categoryIndex(name: string) {
  const i = categories.value.indexOf(name)
  return i >= 0 ? i : 0
}

function verbCategoryIndex(name: string) {
  const i = verbCategories.value.indexOf(name)
  return i >= 0 ? i : 0
}

function sentenceTypeIndex(code: string) {
  const i = sentenceTypes.value.findIndex((t) => t.code === code)
  return i >= 0 ? i : 0
}

function sentenceTypeLabel(code: string) {
  const name = sentenceTypes.value.find((t) => t.code === code)?.name || code || '类型'
  return name.replace(/型$/, '')
}

function pointMethodIndex(name?: string) {
  if (!name) return 0
  const i = pointMethodNames.value.indexOf(name)
  return i >= 0 ? i : 0
}

function findPreset(name: string) {
  return methodPresets.value.find((p) => p.name === name)
}

function applySkeleton(tpl: ShenlunSkeletonTemplate, keepContent = false) {
  argument.templateId = tpl.id
  argument.templateName = tpl.name
  argument.mode = tpl.mode || tpl.structure?.mode || 'linear'
  if (argument.mode === 'linear') {
    const defs = tpl.structure?.fields || []
    const prev = keepContent ? new Map(argument.fields.map((f) => [f.key, f.content])) : new Map()
    argument.fields = defs.map((d) => ({
      key: d.key,
      label: d.label,
      content: prev.get(d.key) || '',
    }))
    argument.points = []
    if (!keepContent) {
      argument.overview = ''
      argument.overviewMethod = ''
      argument.overviewTemplate = ''
    }
  } else {
    if (!keepContent || !argument.points.length) {
      argument.points = [emptyPoint()]
    }
    if (!keepContent) {
      argument.conclusion = ''
      argument.overviewMethod = ''
      argument.overviewTemplate = ''
    }
    argument.fields = []
  }
}

function addTermRow() {
  termRows.value.push({
    term: '',
    category: categories.value[0] || '其他',
    plainWord: '',
  })
}

function removeTerm(i: number) {
  termRows.value.splice(i, 1)
}

function addQuoteRow() {
  quoteRows.value.push({ text: '', source: '', meaning: '' })
}

function addVerbRow() {
  verbRows.value.push({
    verb: '',
    usage: '',
    category: verbCategories.value[0] || '动词其他',
  })
}

function termPayload() {
  return termRows.value
    .filter((t) => t.term.trim())
    .map((t) => ({
      term: t.term.trim(),
      category: t.category || '其他',
      plainWord: (t.plainWord || '').trim(),
    }))
}

function quotePayload() {
  return quoteRows.value
    .filter((q) => q.text.trim())
    .map((q) => ({
      text: q.text.trim(),
      source: (q.source || '').trim(),
      meaning: (q.meaning || '').trim(),
    }))
}

function verbPayload() {
  return verbRows.value
    .filter((v) => v.verb.trim())
    .map((v) => ({
      verb: v.verb.trim(),
      usage: (v.usage || '').trim(),
      category: v.category || '动词其他',
    }))
}

function addPoint() {
  argument.points.push(emptyPoint())
}

function addTemplate() {
  const first = sentenceTypes.value[0]
  templates.value.push({
    type: first?.code || 'dialectic',
    typeName: first?.name || '',
    original: '',
    template: '',
    imitate: '',
  })
}

function onTermCategory(i: number, e: any) {
  const idx = Number(e?.detail?.value ?? 0)
  const name = categories.value[idx]
  if (name && termRows.value[i]) termRows.value[i].category = name
}

function onVerbCategory(i: number, e: any) {
  const idx = Number(e?.detail?.value ?? 0)
  const name = verbCategories.value[idx]
  if (name && verbRows.value[i]) verbRows.value[i].category = name
}

function onSkeletonPick(e: any) {
  const idx = Number(e?.detail?.value ?? 0)
  const tpl = skeletons.value[idx]
  if (tpl) applySkeleton(tpl, false)
}

function onSentenceType(i: number, e: any) {
  const idx = Number(e?.detail?.value ?? 0)
  const t = sentenceTypes.value[idx]
  if (t && templates.value[i]) {
    templates.value[i].type = t.code
    templates.value[i].typeName = t.name
  }
}

function onNewSkelMode(e: any) {
  newSkel.mode = Number(e?.detail?.value) === 1 ? 'points' : 'linear'
}

function onOverviewMethodPick(e: any) {
  const idx = Number(e?.detail?.value ?? 0)
  const name = overviewMethodNames.value[idx]
  if (!name || name === '不选') {
    argument.overviewMethod = ''
    return
  }
  argument.overviewMethod = name
  const preset = findPreset(name)
  if (preset) {
    if (!argument.overviewTemplate.trim()) argument.overviewTemplate = preset.template
  }
}

function onPointMethodPick(i: number, e: any) {
  const idx = Number(e?.detail?.value ?? 0)
  const name = pointMethodNames.value[idx]
  const p = argument.points[i]
  if (!p) return
  if (!name || name === '不选') {
    p.method = ''
    return
  }
  p.method = name
  const preset = findPreset(name)
  if (preset) {
    if (!(p.methodNote || '').trim()) p.methodNote = preset.note
    if (!(p.template || '').trim()) p.template = preset.template
  }
}

async function promptNewCategory(kind: 'term' | 'verb') {
  const title = kind === 'verb' ? '新增动词分类' : '新增规范词分类'
  const raw = await promptText(title, {
    placeholder: kind === 'verb' ? '如：情感色彩' : '如：民生关切',
  })
  if (raw === null) return
  const name = raw.trim()
  if (!name) {
    showToast('请填写分类名')
    return
  }
  const r = await api.createRmrbTermCategory({ name, kind })
  if (r.code !== 0 || !r.data) {
    showToast(r.message || '创建失败', 'error')
    return
  }
  if (kind === 'verb') {
    if (!verbCategories.value.includes(name)) verbCategories.value = [...verbCategories.value, name]
  } else if (!categories.value.includes(name)) {
    categories.value = [...categories.value, name]
  }
  showToast(`已添加「${name}」`, 'success')
}

function addTermCategory() {
  promptNewCategory('term')
}

function addVerbCategory() {
  promptNewCategory('verb')
}

async function createSkeleton() {
  if (!newSkel.name.trim()) {
    showToast('请填写模版名称')
    return
  }
  creatingSkel.value = true
  try {
    const structure =
      newSkel.mode === 'linear'
        ? {
            mode: 'linear',
            fields: newSkel.labels
              .split(/[,，、]/)
              .map((s) => s.trim())
              .filter(Boolean)
              .map((label, i) => ({ key: `step_${i + 1}`, label, placeholder: '' })),
            pointFields: [],
          }
        : {
            mode: 'points',
            fields: [],
            overviewLabel: '总论点',
            overviewPlaceholder: '一句话总论点',
            pointFields: [
              { key: 'title', label: '标题', placeholder: '分论点标题' },
              { key: 'evidence', label: '论据', placeholder: '可选' },
              { key: 'summary', label: '小结', placeholder: '可选' },
            ],
          }
    if (newSkel.mode === 'linear' && !structure.fields.length) {
      showToast('请填写步骤标签')
      return
    }
    const res = await api.createRmrbSkeletonTemplate({
      name: newSkel.name.trim(),
      description: '',
      mode: newSkel.mode,
      structure,
    })
    if (res.code === 0 && res.data) {
      skeletons.value = [...skeletons.value, res.data]
      applySkeleton(res.data, false)
      showNewSkeleton.value = false
      newSkel.name = ''
      showToast('模版已创建', 'success')
    } else {
      showToast(res.message || '创建失败', 'error')
    }
  } finally {
    creatingSkel.value = false
  }
}

function applyMine(m: Awaited<ReturnType<typeof api.getRmrbMine>>['data']) {
  if (!m) return
  form.value = {
    mineDate: m.mineDate,
    articleTitle: m.articleTitle || form.value.articleTitle,
  }
  articleId.value = m.articleId || articleId.value
  termRows.value = (m.terms?.length
    ? m.terms
    : [{ term: '', category: categories.value[0] || '其他', plainWord: '' }]
  ).map((t) => ({
    term: t.term || '',
    category: t.category || categories.value[0] || '其他',
    plainWord: t.plainWord || '',
  }))

  quoteRows.value = (m.quotes || []).map((q) => ({
    text: q.text || '',
    source: q.source || '',
    meaning: q.meaning || '',
  }))
  verbRows.value = (m.verbs || []).map((v) => ({
    verb: v.verb || '',
    usage: v.usage || '',
    category: v.category || verbCategories.value[0] || '动词其他',
  }))

  const arg = m.argument
  argument.templateId = arg?.templateId || ''
  argument.templateName = arg?.templateName || ''
  argument.mode = arg?.mode || (arg?.fields?.length ? 'linear' : 'points')
  argument.overview = arg?.overview || m.argumentChain || ''
  argument.conclusion = arg?.conclusion || ''
  argument.overviewMethod = arg?.overviewMethod || ''
  argument.overviewTemplate = arg?.overviewTemplate || ''
  argument.fields = (arg?.fields || []).map((f) => ({
    key: f.key || '',
    label: f.label || '',
    content: f.content || '',
  }))
  if (arg?.points?.length) {
    argument.points = arg.points.map((p) => {
      // 兼容旧数据：标题为空时用 claim；不再把论据/小结并进标题
      const title = (p.title || '').trim() || (p.claim || '').trim()
      return {
        title,
        claim: '',
        evidence: (p.evidence || '').trim(),
        summary: (p.summary || '').trim(),
        method: p.method || '',
        methodNote: p.methodNote || '',
        template: p.template || '',
      }
    })
  } else {
    argument.points = [emptyPoint()]
  }

  if (argument.templateId) {
    const tpl = skeletons.value.find((s) => s.id === argument.templateId)
    if (tpl && argument.mode === 'linear' && !argument.fields.length) {
      applySkeleton(tpl, true)
    }
  } else if (skeletons.value.length && !argument.overview && !argument.fields.length) {
    applySkeleton(skeletons.value[0], false)
  }

  const firstType = sentenceTypes.value[0]
  templates.value = (m.templates?.length
    ? m.templates
    : [{ type: firstType?.code || 'dialectic', original: m.templateSentence || '', template: '', imitate: '' }]
  ).map((t) => ({
    type: t.type || firstType?.code || 'dialectic',
    typeName: t.typeName || sentenceTypeLabel(t.type || ''),
    original: t.original || '',
    template: t.template || '',
    imitate: t.imitate || '',
  }))
}

async function loadMeta() {
  const res = await api.getRmrbMeta()
  if (res.code !== 0 || !res.data) return
  if (res.data.termCategories?.length) {
    categories.value = res.data.termCategories.map((c) => c.name)
  }
  if (res.data.verbCategories?.length) {
    verbCategories.value = res.data.verbCategories.map((c) => c.name)
  }
  if (res.data.skeletonTemplates?.length) {
    skeletons.value = res.data.skeletonTemplates
  }
  if (res.data.sentenceTypes?.length) {
    sentenceTypes.value = res.data.sentenceTypes
  }
  if (res.data.argumentMethodPresets?.length) {
    methodPresets.value = res.data.argumentMethodPresets
  }
}

async function loadExisting() {
  const currentId = (router.params?.id || '').trim()
  if (loadedForId.value === currentId) return
  mineId.value = currentId
  articleId.value = (router.params?.articleId || '').trim()

  await loadMeta()
  if (currentId) {
    const res = await api.getRmrbMine(currentId)
    if (res.code === 0) applyMine(res.data)
    loadedForId.value = currentId
    return
  }
  if (skeletons.value.length && !argument.templateId) {
    applySkeleton(skeletons.value[0], false)
  }
  const res = await api.getRmrbMineByDate(form.value.mineDate)
  if (res.code === 0 && res.data) {
    mineId.value = res.data.id
    applyMine(res.data)
  }
  loadedForId.value = ''
}

async function ensureMineId(): Promise<string | null> {
  if (mineId.value) return mineId.value
  const date = form.value.mineDate.trim() || today
  const byDate = await api.getRmrbMineByDate(date)
  if (byDate.code === 0 && byDate.data) {
    mineId.value = byDate.data.id
    // 只补标题等元信息，不覆盖已有内容块
    if (!form.value.articleTitle.trim() && byDate.data.articleTitle) {
      form.value.articleTitle = byDate.data.articleTitle
    }
    return mineId.value
  }
  const res = await api.upsertRmrbMine({
    mineDate: date,
    articleId: articleId.value || null,
    articleTitle: form.value.articleTitle.trim(),
    terms: [],
    quotes: [],
    verbs: [],
    argument: {
      templateId: '',
      templateName: '',
      mode: 'points',
      overview: '',
      conclusion: '',
      overviewMethod: '',
      overviewTemplate: '',
      fields: [],
      points: [],
    },
    templates: [],
  })
  if (res.code === 0 && res.data) {
    mineId.value = res.data.id
    return mineId.value
  }
  showToast(res.message || '创建开采失败', 'error')
  return null
}

function buildArgumentPayload() {
  const points = argument.points.filter(
    (p) =>
      p.title.trim()
      || (p.evidence || '').trim()
      || (p.summary || '').trim()
      || p.method
      || (p.methodNote || '').trim()
      || p.template,
  )
  return {
    templateId: argument.templateId,
    templateName: argument.templateName,
    mode: argument.mode,
    overview: argument.overview.trim(),
    conclusion: argument.conclusion.trim(),
    overviewMethod: argument.overviewMethod.trim(),
    overviewTemplate: argument.overviewTemplate.trim(),
    fields: argument.fields,
    points:
      argument.mode === 'points'
        ? points.map((p) => ({
            title: p.title.trim(),
            claim: '',
            evidence: (p.evidence || '').trim(),
            summary: (p.summary || '').trim(),
            method: (p.method || '').trim(),
            methodNote: (p.methodNote || '').trim(),
            template: (p.template || '').trim(),
          }))
        : [],
  }
}

async function onSaveSection() {
  await flushFormBeforeSave()

  const tab = activeTab.value
  if (tab === 'terms' && !termPayload().length) {
    showToast('请至少填写一个规范词')
    return false
  }
  if (tab === 'quotes' && !quotePayload().length) {
    showToast('请至少填写一条金句')
    return false
  }
  if (tab === 'verbs' && !verbPayload().length) {
    showToast('请至少填写一个动词')
    return false
  }
  if (tab === 'argument') {
    const arg = buildArgumentPayload()
    const hasArg =
      !!arg.overview ||
      !!arg.conclusion ||
      arg.points.length > 0 ||
      arg.fields.some((f) => f.content.trim()) ||
      !!arg.templateId
    if (!hasArg) {
      showToast('请填写骨架内容或选择模版')
      return false
    }
  }
  if (tab === 'templates') {
    const tpls = templates.value.filter((t) => t.original.trim() || t.template.trim() || t.imitate.trim())
    if (!tpls.length) {
      showToast('请至少填写一句式')
      return false
    }
  }

  saving.value = true
  try {
    const id = await ensureMineId()
    if (!id) return false

    const meta = {
      articleId: articleId.value || null,
      articleTitle: form.value.articleTitle.trim(),
    }
    let patch: Parameters<typeof api.updateRmrbMine>[1] = { ...meta }
    if (tab === 'terms') patch = { ...meta, terms: termPayload() }
    else if (tab === 'quotes') patch = { ...meta, quotes: quotePayload() }
    else if (tab === 'verbs') patch = { ...meta, verbs: verbPayload() }
    else if (tab === 'argument') patch = { ...meta, argument: buildArgumentPayload() }
    else if (tab === 'templates') {
      patch = {
        ...meta,
        templates: templates.value.filter(
          (t) => t.original.trim() || t.template.trim() || t.imitate.trim(),
        ),
      }
    }

    const res = await api.updateRmrbMine(id, patch)
    if (res.code === 0) {
      showToast(
        tab === 'terms' ? '规范词已保存并同步词库' : `${saveLabel.value.replace('保存', '')}已保存`,
        'success',
      )
      if (res.data) applyMine(res.data)
      const task = dailyTaskStore.tasks.find((item) => item.id === taskId.value)
      if (taskId.value && task?.progress.state === 'in_progress') {
        try {
          await dailyTaskStore.saveDraft(
            taskId.value,
            {
              ...task.progress.draft,
              articleId: articleId.value,
              mineId: mineId.value,
              lastSection: tab,
            },
            2,
            task.totalSteps,
          )
        } catch {
          showToast('开采内容已保存，任务进度稍后同步', 'error')
        }
      }
      return true
    } else {
      showToast(res.message || '保存失败', 'error')
      return false
    }
  } finally {
    saving.value = false
  }
}

async function goDailyAnswer() {
  const saved = await onSaveSection()
  if (!saved || !taskId.value) return
  Taro.navigateTo({
    url: `/pages/shenlun/training?taskId=${encodeURIComponent(taskId.value)}`,
  })
}

async function onDelete() {
  if (!mineId.value) return
  const ok = await showConfirm('删除开采', '确定删除这条开采记录？')
  if (!ok) return
  const res = await api.deleteRmrbMine(mineId.value)
  if (res.code === 0) {
    showToast('已删除', 'success')
    Taro.navigateBack()
  } else {
    showToast(res.message || '删除失败', 'error')
  }
}

useDidShow(() => {
  const currentId = (router.params?.id || '').trim()
  if (loadedForId.value !== currentId) {
    loadedForId.value = null
  }
  loadExisting()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-mine-edit {
  @include page-padding;
  padding-bottom: 88px;
}

.meta-row {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  align-items: stretch;
  .meta-date {
    width: 118px;
    flex: 0 0 118px;
  }
  .meta-title { flex: 1; min-width: 0; }
}

.tab-scroll {
  white-space: nowrap;
  margin: 0 0 12px;
}
.tab-row {
  display: inline-flex;
  gap: 6px;
  padding-bottom: 2px;
}
.tab {
  display: inline-block;
  font-size: 13px;
  padding: 6px 12px;
  border-radius: 8px;
  background: $card-bg;
  color: $text-secondary;
  border: 1px solid $border-color;
  &.on {
    background: $primary-color;
    color: $on-primary;
    border-color: $primary-color;
    font-weight: 600;
  }
}

.section {
  @include card;
  padding: 10px 12px;
  margin-bottom: 10px;
}

.sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.sec-title { font-size: 14px; font-weight: 700; color: $text-primary; }
.sec-actions { display: flex; gap: 12px; }
.sec-add {
  font-size: 12px; color: $primary-color; font-weight: 600;
  &.inline { display: inline-block; margin-top: 4px; }
}
.field-tip {
  display: block;
  font-size: 11px;
  color: $text-muted;
  margin: -2px 0 8px;
  line-height: 1.4;
}

.term-block {
  margin-bottom: 8px;
}

.quote-block {
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.term-line {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  .term-input {
    flex: 1;
    min-width: 0;
    &.grow { flex: 1; }
  }
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 6px 2px;
}
.chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: $primary-light;
  color: $primary-color;
  &.verb {
    background: rgba(46, 125, 50, 0.12);
    color: #2e7d32;
  }
}

.mini-select {
  flex-shrink: 0;
  min-width: 72px;
  max-width: 96px;
  padding: 6px 8px;
  font-size: 12px;
  color: $primary-color;
  background: $primary-light;
  border-radius: 6px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  &.wide { min-width: 100px; max-width: 160px; text-align: left; }
}

.x-del {
  flex-shrink: 0;
  width: 22px;
  text-align: center;
  font-size: 18px;
  line-height: 1;
  color: $text-muted;
  &:active { color: $danger; }
}

.empty-hint {
  font-size: 12px;
  color: $text-muted;
  padding: 6px 0;
}

.select-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  margin-bottom: 8px;
  background: $page-bg;
  border-radius: 6px;
  &.compact { padding: 6px 8px; margin-bottom: 6px; }
  .select-bar-label { font-size: 12px; color: $text-muted; flex-shrink: 0; margin-right: 8px; }
  .select-bar-value {
    font-size: 13px; font-weight: 600; color: $text-primary;
    flex: 1; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
}

.method-box {
  margin-bottom: 8px;
}

.new-skel {
  background: $page-bg;
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.slot-line {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  .slot-tag {
    flex-shrink: 0;
    width: 36px;
    font-size: 12px;
    font-weight: 600;
    color: $primary-color;
    line-height: 32px;
  }
  .slot-body { flex: 1; min-width: 0; }
}
.voice-field {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  .voice-field-body { flex: 1; min-width: 0; }
}

.point-block {
  background: $page-bg;
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  .point-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .point-idx { font-size: 12px; font-weight: 600; color: $primary-color; }
  .slot-line {
    align-items: flex-start;
    .slot-tag {
      line-height: 1.35;
      padding-top: 10px;
    }
  }
}

.tpl-block {
  background: $page-bg;
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  .tpl-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 2px;
  }
}

.foot {
  position: sticky;
  bottom: 0;
  z-index: 20;
  margin-top: 12px;
  padding: 10px 0 calc(10px + env(safe-area-inset-bottom));
  background: linear-gradient(180deg, transparent, $page-bg 28%);
  .daily-continue { margin-top: 8px; }
  .del-link {
    display: block;
    text-align: center;
    margin-top: 12px;
    font-size: 13px;
    color: $danger;
  }
}

.page-mine-edit {
  .hw-tip {
    display: block;
    font-size: 11px;
    color: $text-muted;
    line-height: 1.45;
    margin-bottom: 10px;
  }
  :deep(.nut-input) {
    padding: 6px 10px !important;
    min-height: 32px;
    background: $input-bg;
    border-radius: 6px;
  }
  :deep(.nut-textarea) {
    padding: 8px 10px !important;
    background: $input-bg;
    border-radius: 6px;
    min-height: 72px;
  }
  :deep(.nut-input-inner),
  :deep(.input-text),
  :deep(.nut-input__input),
  :deep(.nut-textarea__textarea),
  :deep(.nut-textarea textarea) {
    font-size: 13px !important;
  }
  .term-line :deep(.nut-input),
  .slot-line :deep(.nut-input),
  .slot-line :deep(.nut-textarea),
  .meta-row :deep(.nut-input) {
    background: $page-bg;
  }
  /* 日期框收紧内边距，完整显示 YYYY-MM-DD，不挤占标题宽度 */
  .meta-date :deep(.nut-input) {
    padding: 6px 4px !important;
  }
  .meta-date :deep(.nut-input__input),
  .meta-date :deep(.input-text),
  .meta-date :deep(.nut-input-inner) {
    font-size: 12px !important;
    letter-spacing: 0;
    text-align: center;
  }
  .point-block :deep(.nut-input),
  .point-block :deep(.nut-textarea),
  .tpl-block :deep(.nut-input),
  .tpl-block :deep(.nut-textarea),
  .new-skel :deep(.nut-input),
  .method-box :deep(.nut-textarea),
  .quote-block :deep(.nut-input),
  .term-block :deep(.nut-input) {
    background: $input-bg;
  }
}
</style>
