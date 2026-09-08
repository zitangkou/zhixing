<template>
  <view class="zl-page" :class="themeClass">
    <view class="zl-hero-card">
      <view v-if="showLoadSkeleton" class="zl-hero-row zl-hero-skeleton">
        <view v-for="item in 3" :key="item" class="zl-hero-item">
          <view class="zl-skeleton zl-skeleton-num" />
          <view class="zl-skeleton zl-skeleton-label" />
        </view>
      </view>
      <view v-else class="zl-hero-row">
        <view class="zl-hero-item">
          <text class="zl-hero-num">{{ ready ? overview.todaySets : '—' }}</text>
          <text class="zl-hero-label">今日组数</text>
        </view>
        <view class="zl-hero-item">
          <text class="zl-hero-num">
            {{
              ready && overview.todayTotal ? `${overview.todayCorrect}/${overview.todayTotal}` : '—'
            }}
          </text>
          <text class="zl-hero-label">今日正确</text>
        </view>
        <view class="zl-hero-item">
          <text class="zl-hero-num">{{ ready ? overview.drillSetCount : '—' }}</text>
          <text class="zl-hero-label">可练材料组</text>
        </view>
      </view>
    </view>

    <view v-if="loadError && !ready" class="zl-state-box">
      <text class="zl-state-title">加载失败</text>
      <text class="zl-state-desc">{{ loadError }}</text>
      <view class="zl-state-btn" @tap="load">点击重试</view>
    </view>

    <view v-else>
      <view v-if="ready && overview.usingSampleOnly" class="zl-tip-banner">
        <text class="zl-tip-title">当前仅有联调样例</text>
        <text class="zl-tip-desc"
          >请在管理后台「试卷题库」导入真题资料分析；示例见 server/data/ziliao/examples/</text
        >
      </view>

      <view v-if="showLoadSkeleton" class="zl-block zl-block-skeleton">
        <view class="zl-skeleton-row" />
        <view class="zl-skeleton-row" />
        <view class="zl-skeleton-row" />
      </view>

      <view v-else>
        <view v-if="weakTypes.length" class="zl-block">
          <text class="zl-block-title">今日建议</text>
          <text class="zl-block-sub">按练习正确率与考试频率推荐薄弱题型</text>
          <view class="zl-entry-list">
            <view v-for="w in weakTypes" :key="w.code" class="zl-entry-row" @tap="startByType(w)">
              <view class="zl-entry-text">
                <text class="zl-entry-name">{{ w.name }}</text>
                <text class="zl-entry-desc">
                  {{ w.reason }}
                  <text v-if="w.accuracy != null">
                    · 正确率 {{ Math.round(w.accuracy * 100) }}%</text
                  >
                </text>
              </view>
              <text class="zl-entry-arrow">练 ›</text>
            </view>
          </view>
        </view>

        <view class="zl-block">
          <text class="zl-block-title">专项练习</text>
          <view class="zl-entry-list">
            <view class="zl-entry-row" @tap="startRandom">
              <view class="zl-entry-text">
                <text class="zl-entry-name">随机练一组</text>
                <text class="zl-entry-desc">材料题 · 真题优先，样例自动降权</text>
              </view>
              <text class="zl-entry-arrow">›</text>
            </view>
            <view class="zl-entry-row" @tap="go('/pages/ziliao/types')">
              <view class="zl-entry-text">
                <text class="zl-entry-name">按题型练</text>
                <text class="zl-entry-desc">增长 / 比重 / 倍数…</text>
              </view>
              <text class="zl-entry-arrow">›</text>
            </view>
            <view class="zl-entry-row" @tap="go('/pages/question/manual-list?subject=资料')">
              <view class="zl-entry-text">
                <text class="zl-entry-name">资料错题本</text>
                <text class="zl-entry-desc">专项错题复习</text>
              </view>
              <text class="zl-entry-arrow">›</text>
            </view>
          </view>
        </view>

        <view class="zl-block">
          <text class="zl-block-title">学习资源</text>
          <view class="zl-entry-grid">
            <view class="zl-entry-item" @tap="go('/pages/ziliao/formulas')">
              <view class="zl-entry-icon tone-red">
                <Edit :color="brandColor" size="20" />
              </view>
              <text class="zl-entry-name">公式库</text>
              <text class="zl-entry-desc">{{
                ready ? `${overview.formulaCount} 个` : '核心公式'
              }}</text>
            </view>
            <view class="zl-entry-item" @tap="go('/pages/ziliao/types')">
              <view class="zl-entry-icon tone-amber">
                <Category :color="brandColor" size="20" />
              </view>
              <text class="zl-entry-name">题型模型</text>
              <text class="zl-entry-desc">{{ ready ? `${overview.typeCount} 种` : '高频题型' }}</text>
            </view>
            <view class="zl-entry-item" @tap="go('/pages/ziliao/tricks')">
              <view class="zl-entry-icon tone-blue">
                <Star :color="brandColor" size="20" />
              </view>
              <text class="zl-entry-name">速算技巧</text>
              <text class="zl-entry-desc">{{ ready ? `${overview.trickCount} 个` : '首数截位' }}</text>
            </view>
            <view class="zl-entry-item" @tap="go('/pages/knowledge/index?treeKey=资料分析')">
              <view class="zl-entry-icon tone-green">
                <Order :color="brandColor" size="20" />
              </view>
              <text class="zl-entry-name">知识框架</text>
              <text class="zl-entry-desc">知识树浏览</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useDidShow, usePullDownRefresh } from '@tarojs/taro'
import { Category, Edit, Order, Star } from '@nutui/icons-vue-taro'
import { api } from '@/api'
import type { ZiliaoOverview, ZiliaoWeakType } from '@/types'
import { showToast } from '@/utils/platform'
import { useBrandColor, useThemeClass } from '@/utils/brandColor'

const brandColor = useBrandColor()

definePageConfig({ navigationBarTitleText: '资料分析', enablePullDownRefresh: true })

const { themeClass } = useThemeClass()
const overview = ref<ZiliaoOverview>({
  formulaCount: 0,
  typeCount: 0,
  trickCount: 0,
  drillSetCount: 0,
  todaySets: 0,
  todayCorrect: 0,
  todayTotal: 0,
  weekSets: 0,
  weakTypes: [],
})
const ready = ref(false)
const loading = ref(false)
const loadError = ref('')
const hasLoadedOnce = ref(false)

const weakTypes = computed(() => overview.value.weakTypes || [])
const showLoadSkeleton = computed(() => loading.value && !ready.value)

function go(url: string) {
  Taro.navigateTo({ url })
}

async function load() {
  if (loading.value) return
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.getZiliaoOverview()
    if (res.code === 0 && res.data) {
      overview.value = res.data
      ready.value = true
    } else {
      ready.value = false
      loadError.value = res.message || '加载失败'
    }
  } catch (e: any) {
    ready.value = false
    loadError.value = e?.message || '网络错误'
  } finally {
    loading.value = false
    hasLoadedOnce.value = true
  }
}

async function pickSet(typeCode?: string) {
  const res = await api.listZiliaoDrillSets(typeCode)
  let sets = res.data || []
  if (!sets.length && typeCode) {
    const all = await api.listZiliaoDrillSets()
    sets = all.data || []
  }
  const real = sets.filter((s) => !s.isSample)
  const pool = real.length ? real : sets
  if (!pool.length) {
    showToast('暂无可练材料组，请先导入资料分析真题')
    return null
  }
  return pool[Math.floor(Math.random() * pool.length)]
}

async function startRandom() {
  const pick = await pickSet()
  if (!pick) return
  Taro.navigateTo({ url: `/pages/ziliao/drill?setId=${encodeURIComponent(pick.setId)}` })
}

async function startByType(w: ZiliaoWeakType) {
  const pick = await pickSet(w.code)
  if (!pick) return
  Taro.navigateTo({
    url: `/pages/ziliao/drill?setId=${encodeURIComponent(pick.setId)}&typeCode=${w.code}`,
  })
}

onMounted(async () => {
  await load()
  hasLoadedOnce.value = true
})

useDidShow(async () => {
  if (!hasLoadedOnce.value) return
  await load()
})

usePullDownRefresh(async () => {
  try {
    await load()
  } finally {
    Taro.stopPullDownRefresh()
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.zl-page {
  @include page-padding;
  padding-bottom: 48px;
}
.zl-hero-card {
  @include card;
  padding: 20px 16px;
}
.zl-hero-row {
  display: flex;
  gap: 8px;
}
.zl-hero-row.zl-hero-skeleton {
  justify-content: space-between;
}
.zl-hero-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.zl-hero-num {
  font-size: 21px;
  font-weight: 700;
  color: $text-primary;
}
.zl-hero-label {
  font-size: 12px;
  color: $text-muted;
}
.zl-tip-banner {
  background: var(--zk-warn-soft);
  border-radius: $radius-md;
  padding: 12px 16px;
  margin-bottom: 12px;
}
.zl-tip-title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: $accent-amber;
  margin-bottom: 4px;
}
.zl-tip-desc {
  display: block;
  font-size: 12px;
  color: $text-secondary;
  line-height: 1.5;
}
.zl-block {
  margin-bottom: 16px;
}
.zl-block-title {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 4px;
}
.zl-block-sub {
  display: block;
  font-size: 12px;
  color: $text-muted;
  margin-bottom: 8px;
}
.zl-entry-list {
  @include card;
  padding: 0;
  overflow: hidden;
  margin-bottom: 0;
}
.zl-entry-row {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid $border-color;
}
.zl-entry-row:last-child {
  border-bottom: none;
}
.zl-entry-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.zl-entry-name {
  font-size: 14px;
  color: $text-primary;
  font-weight: 500;
}
.zl-entry-desc {
  font-size: 12px;
  color: $text-muted;
}
.zl-entry-arrow {
  @include hit-target;
  color: $text-muted;
  font-size: 14px;
}
.zl-entry-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.zl-entry-item {
  @include card;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 0;
}
.zl-entry-icon {
  @include icon-tile;
  margin-bottom: 4px;
  &.tone-red { background: $primary-light; }
  &.tone-amber { background: rgba($accent-amber, 0.12); }
  &.tone-blue { background: rgba($accent-blue, 0.1); }
  &.tone-green { background: rgba($accent-green, 0.1); }
}
.zl-block-skeleton {
  @include card;
  padding: 16px;
  display: grid;
  gap: 10px;
}
.zl-skeleton-row {
  height: 16px;
  border-radius: 6px;
  background: linear-gradient(90deg, $elevated 20%, $border-color 50%, $elevated 80%);
  background-size: 200% 100%;
  animation: zl-shimmer 1.2s infinite;
}
.zl-skeleton {
  border-radius: 6px;
  background: linear-gradient(90deg, $elevated 20%, $border-color 50%, $elevated 80%);
  background-size: 200% 100%;
  animation: zl-shimmer 1.2s infinite;
}
.zl-skeleton-num {
  width: 60%;
  height: 18px;
}
.zl-skeleton-label {
  width: 80%;
  height: 10px;
}
.zl-state-box {
  @include page-state-box;
}
.zl-state-title {
  display: block;
  font-size: 15px;
  color: $text-secondary;
  margin-bottom: 6px;
}
.zl-state-desc {
  display: block;
  font-size: 13px;
  color: $text-muted;
  margin-bottom: 16px;
}
.zl-state-btn {
  @include hit-target;
  display: inline-flex;
  padding: 0 20px;
  background: $primary-light;
  color: $primary-color;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
}
@keyframes zl-shimmer {
  0% {
    background-position: -150% 0;
  }
  100% {
    background-position: 150% 0;
  }
}
</style>
