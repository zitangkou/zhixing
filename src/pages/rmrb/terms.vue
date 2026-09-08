<template>
  <view class="page-terms" :class="themeClass">
    <view class="filter-bar">
      <text
        v-for="t in statusTabs"
        :key="t.value"
        class="tab"
        :class="{ active: activeStatus === t.value }"
        @tap="activeStatus = t.value; load()"
      >{{ t.label }}</text>
    </view>

    <scroll-view
      scroll-x
      class="cat-scroll"
      :title="'电脑端可滚轮切换分类'"
      @wheel.stop.prevent="onCatWheel"
    >
      <view class="cat-row">
        <text
          v-for="c in catTabs"
          :key="c"
          class="cat"
          :class="{ on: activeCat === c }"
          @tap="activeCat = c; load()"
        >{{ c || '全部' }}</text>
      </view>
    </scroll-view>

    <view class="add-row">
      <nut-input v-model="newTerm" placeholder="规范词，多个用顿号分隔" class="add-input" />
      <WheelPicker
        :range="addCategoryNames"
        :value="addCategoryIndex"
        @change="onAddCategoryPick"
      >
        <view class="add-cat">{{ activeCat || categories[0] || '分类' }} ▾</view>
      </WheelPicker>
      <nut-button size="small" plain type="primary" @click="onAddCategory">+分类</nut-button>
      <nut-button size="small" type="primary" @click="onAdd">添加</nut-button>
    </view>
    <view v-if="splitPreview.length > 1" class="chip-row">
      <text v-for="(w, i) in splitPreview" :key="i" class="chip">{{ w }}</text>
    </view>

    <view v-if="loading" class="empty">加载中...</view>
    <view v-else-if="!terms.length" class="empty">
      <text class="empty-title">暂无规范词</text>
      <text class="empty-desc">三刀解剖保存后会按分类同步到这里</text>
    </view>

    <view v-else class="term-list">
      <view v-for="t in terms" :key="t.id" class="term-card" :class="{ mastered: t.mastered }">
        <view class="t-head">
          <text class="t-word">{{ t.term }}</text>
          <WheelPicker
            :range="categories"
            :value="Math.max(0, categories.indexOf(t.category || '其他'))"
            @change="(e) => onCategoryWheel(t, e)"
          >
            <text class="t-cat">{{ t.category || '其他' }} ▾</text>
          </WheelPicker>
          <text class="t-fam">★{{ t.familiarity }}</text>
        </view>
        <text v-if="t.usageNote" class="t-meaning">解释：{{ t.usageNote }}</text>
        <text v-if="t.sourceTitle" class="t-source">出处：{{ t.sourceTitle }}</text>
        <text v-if="t.exampleSentence" class="t-example">用法：{{ t.exampleSentence }}</text>
        <view class="t-actions">
          <text class="act" @tap="onMeaning(t)">补解释</text>
          <text class="act" @tap="onUsage(t)">补用法</text>
          <text class="act" @tap="onCategory(t)">改分类</text>
          <text v-if="!t.mastered" class="act" @tap="onReview(t)">熟悉+1</text>
          <text class="act" @tap="onMaster(t)">{{ t.mastered ? '取消掌握' : '已掌握' }}</text>
          <text class="act danger" @tap="onDelete(t)">删除</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { Button as NutButton, Input as NutInput } from '@nutui/nutui-taro'
import WheelPicker from '@/components/WheelPicker.vue'
import { api } from '@/api'
import { promptText, showConfirm, showToast } from '@/utils/platform'
import { RMRB_TERM_CATEGORIES_FALLBACK, splitRmrbTerms } from '@/utils/rmrb'
import type { ShenlunNormTerm } from '@/types'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '规范词库' })

const { themeClass } = useThemeClass()
const loading = ref(false)
const terms = ref<ShenlunNormTerm[]>([])
const activeStatus = ref<'learning' | 'mastered'>('learning')
const activeCat = ref('')
const newTerm = ref('')
const categories = ref<string[]>([...RMRB_TERM_CATEGORIES_FALLBACK])

const statusTabs = [
  { value: 'learning' as const, label: '学习中' },
  { value: 'mastered' as const, label: '已掌握' },
]
const catTabs = ref<string[]>(['', ...categories.value])
const splitPreview = computed(() => splitRmrbTerms(newTerm.value))
const addCategoryNames = computed(() =>
  categories.value.length ? categories.value : ['其他'],
)
const addCategoryIndex = computed(() => {
  const names = addCategoryNames.value
  const cur = activeCat.value || names[0]
  const i = names.indexOf(cur)
  return i >= 0 ? i : 0
})

let catWheelAt = 0
function onCatWheel(e: WheelEvent) {
  const tabs = catTabs.value
  if (tabs.length <= 1) return
  const now = Date.now()
  if (now - catWheelAt < 90) return
  catWheelAt = now
  const delta = e.deltaY || e.deltaX
  if (!delta) return
  const dir = delta > 0 ? 1 : -1
  const cur = tabs.indexOf(activeCat.value)
  const from = cur >= 0 ? cur : 0
  const next = (from + dir + tabs.length) % tabs.length
  activeCat.value = tabs[next]
  load()
}

function onAddCategoryPick(e: { detail?: { value?: number } }) {
  const idx = Number(e?.detail?.value ?? 0)
  const name = addCategoryNames.value[idx]
  if (name) {
    activeCat.value = name
    load()
  }
}

async function loadMeta() {
  const res = await api.getRmrbMeta()
  if (res.code === 0 && res.data?.termCategories?.length) {
    categories.value = res.data.termCategories.map((c) => c.name)
    catTabs.value = ['', ...categories.value]
  }
}

async function load() {
  loading.value = true
  try {
    const res = await api.listRmrbTerms(activeStatus.value, activeCat.value || undefined)
    if (res.code === 0 && res.data) terms.value = res.data
  } finally {
    loading.value = false
  }
}

async function onAddCategory() {
  const raw = await promptText('新增规范词分类', { placeholder: '如：民生关切' })
  if (raw === null) return
  const name = raw.trim()
  if (!name) {
    showToast('请填写分类名')
    return
  }
  const r = await api.createRmrbTermCategory({ name, kind: 'term' })
  if (r.code !== 0 || !r.data) {
    showToast(r.message || '创建失败', 'error')
    return
  }
  if (!categories.value.includes(name)) {
    categories.value = [...categories.value, name]
    catTabs.value = ['', ...categories.value]
  }
  activeCat.value = name
  showToast(`已添加「${name}」`, 'success')
}

async function onAdd() {
  const term = newTerm.value.trim()
  if (!term) return
  const res = await api.addRmrbTerm({ term, category: activeCat.value || categories.value[0] || '其他' })
  if (res.code === 0) {
    newTerm.value = ''
    showToast(splitRmrbTerms(term).length > 1 ? '已拆分添加' : '已添加', 'success')
    load()
  } else {
    showToast(res.message || '添加失败', 'error')
  }
}

async function onMeaning(t: ShenlunNormTerm) {
  const content = await promptText('重点词解释', {
    placeholder: '词义、语境或可替换的普通说法',
    defaultValue: t.usageNote || '',
  })
  if (content === null) return
  const text = content.trim()
  const r = await api.updateRmrbTerm(t.id, { usageNote: text })
  if (r.code === 0 && r.data) {
    Object.assign(t, r.data)
    showToast('已更新解释', 'success')
  }
}

async function onUsage(t: ShenlunNormTerm) {
  const content = await promptText('补一句用法', {
    placeholder: '用这个规范词造一句',
    defaultValue: t.exampleSentence || '',
  })
  if (content === null) return
  const text = content.trim()
  const r = await api.updateRmrbTerm(t.id, { exampleSentence: text })
  if (r.code === 0 && r.data) Object.assign(t, r.data)
}

async function applyCategory(t: ShenlunNormTerm, cat: string) {
  if (!cat || cat === t.category) return
  const r = await api.updateRmrbTerm(t.id, { category: cat })
  if (r.code === 0 && r.data) {
    Object.assign(t, r.data)
    showToast(`已改为「${cat}」`, 'success')
  } else {
    showToast(r.message || '更新失败', 'error')
  }
}

async function onCategoryWheel(t: ShenlunNormTerm, e: { detail?: { value?: number } }) {
  const cat = categories.value[Number(e?.detail?.value ?? 0)]
  if (cat) await applyCategory(t, cat)
}

async function onCategory(t: ShenlunNormTerm) {
  try {
    const res = await Taro.showActionSheet({ itemList: [...categories.value] })
    const cat = categories.value[res.tapIndex]
    if (!cat) return
    await applyCategory(t, cat)
  } catch {
    /* 取消 */
  }
}

async function onReview(t: ShenlunNormTerm) {
  const fam = Math.min(5, t.familiarity + 1)
  const res = await api.updateRmrbTerm(t.id, { familiarity: fam })
  if (res.code === 0 && res.data) {
    Object.assign(t, res.data)
    showToast(`熟悉度 → ${fam}`, 'success')
  }
}

async function onMaster(t: ShenlunNormTerm) {
  const res = await api.updateRmrbTerm(t.id, {
    mastered: !t.mastered,
    familiarity: t.mastered ? 1 : 5,
  })
  if (res.code === 0) {
    showToast(t.mastered ? '已取消' : '已掌握', 'success')
    load()
  }
}

async function onDelete(t: ShenlunNormTerm) {
  const ok = await showConfirm('删除规范词', `确定删除「${t.term}」？`)
  if (!ok) return
  const res = await api.deleteRmrbTerm(t.id)
  if (res.code === 0) {
    terms.value = terms.value.filter((x) => x.id !== t.id)
    showToast('已删除', 'success')
  }
}

onMounted(async () => {
  await loadMeta()
  await load()
})
useDidShow(load)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-terms { @include page-padding; padding-bottom: 40px; }
.filter-bar { display: flex; gap: 8px; margin-bottom: 10px;
  .tab {
    flex: 1; text-align: center; padding: 8px; border-radius: 8px; background: $card-bg; font-size: 13px;
    &.active { background: $primary-light; color: $primary-color; font-weight: 600; }
  }
}
.cat-scroll { white-space: nowrap; margin-bottom: 12px; }
.cat-row { display: inline-flex; gap: 6px; }
.cat {
  display: inline-block; font-size: 12px; padding: 4px 10px; border-radius: 8px; background: $card-bg; color: $text-secondary;
  &.on { background: $primary-color; color: $on-primary; }
}
.add-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
  .add-input { flex: 1; min-width: 0; }
  .add-cat {
    flex-shrink: 0;
    font-size: 12px;
    padding: 6px 8px;
    border-radius: 6px;
    background: $primary-light;
    color: $primary-color;
    white-space: nowrap;
    max-width: 88px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}
.chip-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;
  .chip { font-size: 11px; padding: 2px 8px; border-radius: 4px; background: $primary-light; color: $primary-color; }
}
.empty { text-align: center; padding: 48px 20px; color: $text-muted;
  .empty-title { display: block; font-size: 15px; margin-bottom: 6px; color: $text-primary; }
}
.term-list { display: flex; flex-direction: column; gap: 10px; }
.term-card {
  @include card; padding: 14px;
  &.mastered { opacity: 0.75; }
  .t-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;
    .t-word { font-size: 17px; font-weight: 700; }
    .t-cat { font-size: 11px; padding: 1px 6px; border-radius: 4px; background: $primary-light; color: $primary-color; }
    .t-fam { font-size: 12px; color: $primary-color; margin-left: auto; }
  }
  .t-note, .t-source, .t-example, .t-meaning { display: block; font-size: 12px; color: $text-muted; line-height: 1.45; margin-bottom: 4px; }
  .t-meaning { color: $text-secondary; }
  .t-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px;
    .act { font-size: 13px; color: $primary-color; }
    .danger { color: $danger; }
  }
}
</style>
