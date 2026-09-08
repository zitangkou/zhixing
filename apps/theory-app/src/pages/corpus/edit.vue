<template>
  <view class="page-edit">
    <view class="status-bar">
      <text class="status-text">{{ statusLabel }}</text>
      <text v-if="promoted" class="promoted">已晋升规范词</text>
    </view>

    <scroll-view scroll-x class="tab-scroll">
      <view class="tab-row">
        <text
          v-for="t in tabs"
          :key="t.key"
          class="tab"
          :class="{ on: activeTab === t.key }"
          @tap="activeTab = t.key"
        >{{ t.label }}</text>
      </view>
    </scroll-view>

    <!-- 原文 -->
    <view v-show="activeTab === 'capture'" class="panel">
      <text class="panel-title">① 原文</text>
      <text class="panel-tip">词 / 专名 / 成语 / 诗典 记义；短语 / 句 / 结构 练表达。类型可后改。</text>

      <view class="field">
        <view class="label-row">
          <text class="label">原文</text>
          <VoiceInputBtn v-model="form.original" />
        </view>
        <nut-textarea
          v-model="form.original"
          :rows="5"
          placeholder="粘贴或口述：好词 / 好句"
        />
      </view>

      <view class="field">
        <text class="label">类型</text>
        <view class="chips">
          <text
            v-for="k in kinds"
            :key="k"
            class="chip"
            :class="{ on: form.kind === k }"
            @tap="form.kind = k"
          >{{ k }}</text>
        </view>
      </view>

      <view class="field">
        <text class="label">来源</text>
        <view class="chips">
          <text
            v-for="s in sources"
            :key="s"
            class="chip"
            :class="{ on: form.sourceType === s }"
            @tap="form.sourceType = s"
          >{{ s }}</text>
        </view>
      </view>

      <view class="field">
        <text class="label">出处（可选）</text>
        <nut-input v-model="form.sourceTitle" placeholder="标题 / 节目名 / 出处" />
      </view>

      <view v-if="isMeaningKind" class="field">
        <view class="label-row">
          <text class="label">释义</text>
          <VoiceInputBtn v-model="form.plainNote" />
        </view>
        <nut-textarea
          v-model="form.plainNote"
          :rows="3"
          placeholder="这个词/专名是什么意思？用自己的话写清楚"
        />
      </view>

      <view class="field">
        <text class="label">归属知识框架</text>
        <text class="field-tip">挂到考点树上，方便以后按框架串联回忆</text>
        <KnowledgePointPicker v-model="knowledge" />
      </view>
    </view>

    <!-- 澄清 -->
    <view v-show="activeTab === 'clarify'" class="panel">
      <text class="panel-title">② 澄清</text>
      <text class="panel-tip">写白话、打标签，防假懂</text>

      <view class="field">
        <text class="label">场景标签</text>
        <view class="chips">
          <text
            v-for="t in tagPresets"
            :key="t"
            class="chip"
            :class="{ on: form.tags.includes(t) }"
            @tap="toggleTag(t)"
          >{{ t }}</text>
        </view>
      </view>

      <view class="field">
        <view class="label-row">
          <text class="label">{{ isMeaningKind ? '释义' : '白话解释' }}</text>
          <VoiceInputBtn v-model="form.plainNote" />
        </view>
        <nut-textarea
          v-model="form.plainNote"
          :rows="4"
          :placeholder="isMeaningKind ? '专名/成语的意思，用自己的话' : '这句在说什么？用自己的话'"
        />
      </view>
    </view>

    <!-- 改写 -->
    <view v-show="activeTab === 'own'" class="panel">
      <text class="panel-title">③ 改写</text>
      <text class="panel-tip">写完「我的改写」才算占有</text>

      <view v-if="form.original" class="quote-box">
        <text class="quote-label">原文</text>
        <text class="quote-body">{{ form.original }}</text>
      </view>

      <view class="field">
        <view class="label-row">
          <text class="label">我的改写</text>
          <VoiceInputBtn v-model="form.rewrite" />
        </view>
        <nut-textarea
          v-model="form.rewrite"
          :rows="5"
          placeholder="不照抄，换成你能脱口而出的版本"
        />
      </view>
    </view>

    <!-- 运用 -->
    <view v-show="activeTab === 'use'" class="panel">
      <text class="panel-title">④ 运用</text>
      <text class="panel-tip">换主题仿写，或晋升到规范词库</text>

      <view class="field">
        <view class="label-row">
          <text class="label">仿写 / 造句</text>
          <VoiceInputBtn v-model="form.practice" />
        </view>
        <nut-textarea
          v-model="form.practice"
          :rows="4"
          placeholder="换一个主题再写一句"
        />
      </view>

      <view v-if="id" class="more-actions">
        <view
          v-if="!promoted"
          class="more-btn primary"
          :class="{ disabled: promoting }"
          @tap="onPromote"
        >晋升到规范词库</view>
        <view class="more-btn" :class="{ disabled: marking }" @tap="onMarkUsed">标记已运用</view>
        <text class="del-link" @tap="onDelete">删除这条</text>
      </view>
    </view>

    <view class="save-bar">
      <nut-button type="primary" block :loading="saving" @click="onSaveSection">
        {{ saveLabel }}
      </nut-button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import { Button as NutButton, Input as NutInput, Textarea as NutTextarea } from '@nutui/nutui-taro'
import KnowledgePointPicker from '@/components/KnowledgePointPicker.vue'
import VoiceInputBtn from '@/components/VoiceInputBtn.vue'
import { api } from '@/api'
import {
  CORPUS_KINDS_FALLBACK,
  CORPUS_SOURCE_TYPES_FALLBACK,
  CORPUS_TAG_PRESETS_FALLBACK,
  corpusStatusLabel,
} from '@/utils/corpus'
import { flushFormBeforeSave } from '@/utils/formFlush'
import type { KnowledgePickValue } from '@/utils/knowledge'
import { showConfirm, showToast } from '@/utils/platform'

definePageConfig({ navigationBarTitleText: '语料编辑' })

type TabKey = 'capture' | 'clarify' | 'own' | 'use'

const router = useRouter()
const id = ref('')
/** 避免页面缓存导致重复 load；id 变化时强制重载 */
const loadedForId = ref<string | null>(null)
const saving = ref(false)
const promoting = ref(false)
const marking = ref(false)
const status = ref('inbox')
const promoted = ref(false)
const activeTab = ref<TabKey>('capture')

const tabs: { key: TabKey; label: string }[] = [
  { key: 'capture', label: '原文' },
  { key: 'clarify', label: '澄清' },
  { key: 'own', label: '改写' },
  { key: 'use', label: '运用' },
]

const saveLabel = computed(() => {
  const map: Record<TabKey, string> = {
    capture: '保存原文',
    clarify: '保存澄清',
    own: '保存改写',
    use: '保存运用',
  }
  return map[activeTab.value]
})

const kinds = ref([...CORPUS_KINDS_FALLBACK])
const sources = ref([...CORPUS_SOURCE_TYPES_FALLBACK])
const tagPresets = ref([...CORPUS_TAG_PRESETS_FALLBACK])

const form = reactive({
  original: '',
  kind: '句',
  sourceType: '其他',
  sourceTitle: '',
  tags: [] as string[],
  plainNote: '',
  rewrite: '',
  practice: '',
})

const knowledge = ref<KnowledgePickValue>({
  nodeId: '',
  treeKey: '',
  path: '',
})

const MEANING_KINDS = new Set(['词', '专名', '成语', '诗典'])
const isMeaningKind = computed(() => MEANING_KINDS.has(form.kind))
const statusLabel = computed(() => corpusStatusLabel(status.value))

function knowledgePayload() {
  return {
    knowledgeNodeId: knowledge.value.nodeId || null,
    knowledgeTreeKey: knowledge.value.treeKey || '',
    knowledgePath: knowledge.value.path || '',
  }
}

function toggleTag(t: string) {
  const i = form.tags.indexOf(t)
  if (i >= 0) form.tags.splice(i, 1)
  else form.tags.push(t)
}

function applyItem(d: {
  original: string
  kind: string
  sourceType: string
  sourceTitle?: string
  tags?: string[]
  plainNote?: string
  rewrite?: string
  practice?: string
  status: string
  promotedTermId?: string | null
  knowledgeNodeId?: string | null
  knowledgeTreeKey?: string
  knowledgePath?: string
}) {
  form.original = d.original
  form.kind = d.kind
  form.sourceType = d.sourceType
  form.sourceTitle = d.sourceTitle || ''
  form.tags = [...(d.tags || [])]
  form.plainNote = d.plainNote || ''
  form.rewrite = d.rewrite || ''
  form.practice = d.practice || ''
  status.value = d.status
  promoted.value = !!d.promotedTermId
  knowledge.value = {
    nodeId: d.knowledgeNodeId || '',
    treeKey: d.knowledgeTreeKey || '',
    path: d.knowledgePath || '',
  }
}

async function loadMeta() {
  const res = await api.getCorpusStats()
  if (res.code === 0 && res.data) {
    if (res.data.kinds?.length) kinds.value = res.data.kinds
    if (res.data.sourceTypes?.length) sources.value = res.data.sourceTypes
    if (res.data.tagPresets?.length) tagPresets.value = res.data.tagPresets
  }
}

async function loadItem() {
  const currentId = (router.params?.id || '').trim()
  if (loadedForId.value === currentId) return
  id.value = currentId
  if (!currentId) {
    loadedForId.value = ''
    applyQueryPrefill()
    return
  }
  const res = await api.getCorpusItem(currentId)
  if (res.code !== 0 || !res.data) {
    showToast('记录不存在')
    return
  }
  applyItem(res.data)
  loadedForId.value = currentId
}

/** 无 id 时先建一条（至少有原文） */
async function ensureId(): Promise<string | null> {
  if (id.value) return id.value
  if (!form.original.trim()) {
    showToast('请先填写原文')
    activeTab.value = 'capture'
    return null
  }
  const res = await api.createCorpusItem({
    original: form.original.trim(),
    kind: form.kind,
    sourceType: form.sourceType,
    sourceTitle: form.sourceTitle.trim(),
    tags: [...form.tags],
    plainNote: form.plainNote.trim(),
    rewrite: form.rewrite.trim(),
    practice: form.practice.trim(),
    ...knowledgePayload(),
  })
  if (res.code !== 0 || !res.data) {
    showToast(res.message || '创建失败')
    return null
  }
  id.value = res.data.id
  applyItem(res.data)
  return id.value
}

async function onSaveSection() {
  await flushFormBeforeSave()

  const tab = activeTab.value

  if (tab === 'capture' && !form.original.trim()) {
    showToast('请填写原文')
    return
  }

  saving.value = true
  try {
    if (!id.value) {
      if (tab !== 'capture' && !form.original.trim()) {
        showToast('请先保存原文')
        activeTab.value = 'capture'
        return
      }
      const created = await ensureId()
      if (!created) return
      if (tab === 'capture') {
        showToast('已保存')
        return
      }
    }

    let patch: Parameters<typeof api.updateCorpusItem>[1] = {}
    if (tab === 'capture') {
      patch = {
        original: form.original.trim(),
        kind: form.kind,
        sourceType: form.sourceType,
        sourceTitle: form.sourceTitle.trim(),
        // 专名等在原文页即可写释义，一并落库
        plainNote: form.plainNote.trim(),
        ...knowledgePayload(),
      }
    } else if (tab === 'clarify') {
      patch = {
        tags: [...form.tags],
        plainNote: form.plainNote.trim(),
      }
    } else if (tab === 'own') {
      patch = { rewrite: form.rewrite.trim() }
    } else if (tab === 'use') {
      patch = { practice: form.practice.trim() }
    }

    const res = await api.updateCorpusItem(id.value, patch)
    if (res.code !== 0 || !res.data) {
      showToast(res.message || '保存失败')
      return
    }
    applyItem(res.data)
    showToast('已保存')
  } finally {
    saving.value = false
  }
}

async function onPromote() {
  if (promoting.value) return
  if (!id.value) {
    showToast('请先保存原文')
    return
  }
  const ok = await showConfirm('晋升规范词', '将本条晋升到申论规范词库？')
  if (!ok) return
  promoting.value = true
  try {
    const res = await api.promoteCorpusToTerm(id.value)
    if (res.code !== 0) {
      showToast(res.message || '晋升失败')
      return
    }
    if (res.data) applyItem(res.data)
    showToast('已晋升')
  } finally {
    promoting.value = false
  }
}

async function onMarkUsed() {
  if (marking.value || !id.value) return
  marking.value = true
  try {
    const res = await api.updateCorpusItem(id.value, { markUsed: true })
    if (res.code !== 0) {
      showToast(res.message || '更新失败')
      return
    }
    if (res.data) applyItem(res.data)
    showToast('已标记运用')
  } finally {
    marking.value = false
  }
}

async function onDelete() {
  if (!id.value) return
  const ok = await showConfirm('删除语料', '删除这条语料？')
  if (!ok) return
  const res = await api.deleteCorpusItem(id.value)
  if (res.code !== 0) {
    showToast(res.message || '删除失败')
    return
  }
  showToast('已删除')
  Taro.navigateBack()
}

function applyQueryPrefill() {
  if (id.value) return
  const p = router.params || {}
  const pick = (key: string) => {
    const raw = p[key]
    if (raw == null || raw === '') return ''
    try {
      return decodeURIComponent(String(raw))
    } catch {
      return String(raw)
    }
  }
  const original = pick('original')
  const kind = pick('kind')
  const sourceType = pick('sourceType')
  const sourceTitle = pick('sourceTitle')
  const plainNote = pick('plainNote')
  if (original) form.original = original
  if (kind) form.kind = kind
  if (sourceType) form.sourceType = sourceType
  if (sourceTitle) form.sourceTitle = sourceTitle
  if (plainNote) form.plainNote = plainNote
  if (plainNote) activeTab.value = 'clarify'
}

useDidShow(async () => {
  const currentId = (router.params?.id || '').trim()
  if (loadedForId.value !== currentId) {
    loadedForId.value = null
  }
  await loadMeta()
  await loadItem()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-edit {
  padding: 16px 16px 100px;
  min-height: 100vh;
  box-sizing: border-box;
}

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  .status-text {
    font-size: 13px;
    color: $text-muted;
  }
  .promoted {
    font-size: 12px;
    color: $accent-green;
    font-weight: 600;
  }
}

.tab-scroll {
  white-space: nowrap;
  margin-bottom: 16px;
}
.tab-row {
  display: inline-flex;
  gap: 8px;
}
.tab {
  display: inline-block;
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 8px;
  background: $elevated;
  color: $text-secondary;
  border: 1px solid transparent;
  &.on {
    background: $primary-color;
    color: $on-primary;
    font-weight: 600;
  }
}

.panel {
  padding: 4px 0 8px;
}

.panel-title {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: $text-primary;
  margin-bottom: 6px;
}
.panel-tip {
  display: block;
  font-size: 13px;
  color: $text-muted;
  line-height: 1.45;
  margin-bottom: 20px;
}

.quote-box {
  margin-bottom: 20px;
  padding: 14px 16px;
  background: $elevated;
  border-radius: 8px;
  .quote-label {
    display: block;
    font-size: 12px;
    color: $text-muted;
    margin-bottom: 6px;
  }
  .quote-body {
    display: block;
    font-size: 14px;
    color: $text-secondary;
    line-height: 1.55;
  }
}

.field {
  margin-bottom: 22px;
  .label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: $text-secondary;
    margin-bottom: 10px;
  }
  .field-tip {
    display: block;
    margin: -4px 0 10px;
    font-size: 12px;
    color: $text-muted;
    line-height: 1.4;
  }
  .label-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    .label { margin-bottom: 0; }
  }
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  .chip {
    font-size: 13px;
    padding: 8px 12px;
    border-radius: 8px;
    background: $elevated;
    color: $text-secondary;
    &.on {
      background: $primary-light;
      color: $primary-color;
      font-weight: 600;
    }
  }
}

.more-actions {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  .more-btn {
    text-align: center;
    padding: 12px 16px;
    border-radius: 8px;
    border: 1px solid $border-color;
    font-size: 14px;
    color: $text-secondary;
    background: $card-bg;
    &.primary {
      border-color: $primary-color;
      color: $primary-color;
      font-weight: 600;
    }
    &.disabled { opacity: 0.5; }
  }
  .del-link {
    display: block;
    text-align: center;
    padding: 14px;
    color: $danger;
    font-size: 14px;
  }
}

.save-bar {
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 0 calc(12px + env(safe-area-inset-bottom));
  background: linear-gradient(180deg, transparent, $page-bg 28%);
  margin-top: 12px;
}
</style>

