<template>
  <view class="page-xingce-hub" :class="themeClass">
    <template v-if="moduleMode">
      <view class="hub-head">
        <text class="hub-title">{{ paperTitle }}</text>
        <text class="hub-sub">选择模块开始刷题</text>
      </view>
      <view v-if="loading" class="state-card">正在加载…</view>
      <view v-else-if="!modules.length" class="state-card">
        <text class="state-title">该套卷暂无可练真题</text>
      </view>
      <view v-else class="module-grid">
        <view
          v-for="item in modules"
          :key="item.key"
          class="module-item"
          :class="{ disabled: item.count <= 0 }"
          @tap="openModule(item)"
        >
          <text class="module-name">{{ item.name }}</text>
          <text class="module-count">{{ item.count > 0 ? `${item.count} 题可练` : '暂无可练' }}</text>
        </view>
      </view>
    </template>

    <template v-else>
      <view class="hub-head">
        <text class="hub-title">行测真题</text>
        <text class="hub-sub">先选年度套卷，再按题型练习</text>
      </view>

      <view v-if="loading" class="state-card">正在加载题库…</view>
      <view v-else-if="!papers.length" class="state-card">
        <text class="state-title">还没有可练真题</text>
        <text class="state-desc">导入 2023–2025 有答案的行测 JSON 后会出现在这里。</text>
      </view>
      <view v-else class="paper-groups">
        <view v-for="group in paperGroups" :key="group.year" class="year-block">
          <text class="year-label">{{ group.year }} 年</text>
          <view class="paper-list">
            <view
              v-for="item in group.items"
              :key="`${item.year}-${item.paperType}`"
              class="paper-item"
              :class="{ disabled: item.count <= 0 }"
              @tap="openPaper(item)"
            >
              <text class="paper-name">{{ item.title }}</text>
              <text class="paper-count">{{ item.count > 0 ? `${item.count} 题可练` : '暂无可练' }}</text>
              <text class="paper-arrow">›</text>
            </view>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import { api } from '@/api'
import type { XingceCatalogModule, XingceCatalogPaper } from '@/types'
import { showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '行测真题' })

const { themeClass } = useThemeClass()
const router = useRouter()
const loading = ref(true)
const papers = ref<XingceCatalogPaper[]>([])
const modules = ref<XingceCatalogModule[]>([])
const year = ref(0)
const paperType = ref('')

function paperDisplayTitle(y: number, pt: string) {
  const suffix =
    pt === '省级' ? '省级' : pt === '市地级' ? '市地' : pt === '行政执法类' ? '执法' : pt
  return `${y} 国考行测·${suffix}`
}

const moduleMode = computed(() => year.value > 0 && !!paperType.value)
const paperTitle = computed(() => paperDisplayTitle(year.value, paperType.value))

const paperGroups = computed(() => {
  const map = new Map<number, XingceCatalogPaper[]>()
  for (const p of papers.value) {
    const list = map.get(p.year) || []
    list.push(p)
    map.set(p.year, list)
  }
  return [...map.entries()]
    .sort((a, b) => b[0] - a[0])
    .map(([yearKey, items]) => ({ year: yearKey, items }))
})

function syncRoute() {
  year.value = Number(router.params?.year || 0)
  const raw = router.params?.paperType || ''
  paperType.value = raw ? decodeURIComponent(String(raw)) : ''
}

async function loadPapers() {
  loading.value = true
  const res = await api.getXingceCatalog()
  loading.value = false
  if (res.code !== 0) {
    showToast(res.message || '题库加载失败', 'error')
    return
  }
  papers.value = res.data?.papers || []
}

async function loadModules() {
  if (!year.value || !paperType.value) {
    loading.value = false
    showToast('缺少套卷参数', 'error')
    return
  }
  loading.value = true
  const res = await api.getXingceCatalog({ year: year.value, paperType: paperType.value })
  loading.value = false
  if (res.code !== 0) {
    showToast(res.message || '加载失败', 'error')
    return
  }
  modules.value = res.data?.modules || []
}

function openPaper(item: XingceCatalogPaper) {
  if (item.count <= 0) {
    showToast('该套卷暂无可练真题')
    return
  }
  Taro.navigateTo({
    url: `/pages/question/xingce-hub?year=${item.year}&paperType=${encodeURIComponent(item.paperType)}`,
  })
}

function openModule(item: XingceCatalogModule) {
  if (item.count <= 0) {
    showToast('该模块暂无可练真题')
    return
  }
  Taro.navigateTo({
    url: `/pages/question/xingce?module=${encodeURIComponent(item.key)}&year=${year.value}&paperType=${encodeURIComponent(paperType.value)}`,
  })
}

useDidShow(() => {
  syncRoute()
  if (moduleMode.value) {
    Taro.setNavigationBarTitle({ title: '套卷题型' })
    void loadModules()
  } else {
    Taro.setNavigationBarTitle({ title: '行测真题' })
    void loadPapers()
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-xingce-hub {
  @include page-padding;
  .hub-head {
    margin-bottom: 16px;
    .hub-title {
      display: block;
      font-size: 22px;
      font-weight: 700;
      color: $text-primary;
      margin-bottom: 6px;
    }
    .hub-sub {
      display: block;
      font-size: 13px;
      color: $text-muted;
    }
  }
  .state-card {
    @include card;
    padding: 28px 16px;
    text-align: center;
    color: $text-muted;
    .state-title {
      display: block;
      font-size: 15px;
      color: $text-secondary;
      margin-bottom: 6px;
    }
    .state-desc {
      display: block;
      font-size: 12px;
      line-height: 1.5;
    }
  }
  .year-block {
    margin-bottom: 20px;
    .year-label {
      display: block;
      font-size: 14px;
      font-weight: 600;
      color: $text-secondary;
      margin-bottom: 10px;
    }
  }
  .paper-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .paper-item {
    @include card;
    margin-bottom: 0;
    padding: 14px 16px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 8px;
    &.disabled {
      opacity: 0.5;
    }
    .paper-name {
      flex: 1;
      font-size: 15px;
      font-weight: 600;
      color: $text-primary;
      min-width: 0;
    }
    .paper-count {
      font-size: 12px;
      color: $text-muted;
    }
    .paper-arrow {
      font-size: 18px;
      color: $text-muted;
      margin-left: 4px;
    }
  }
  .module-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  .module-item {
    @include card;
    margin-bottom: 0;
    padding: 16px 14px;
    &.disabled {
      opacity: 0.5;
    }
    .module-name {
      display: block;
      font-size: 15px;
      font-weight: 600;
      color: $text-primary;
      margin-bottom: 6px;
    }
    .module-count {
      display: block;
      font-size: 12px;
      color: $text-muted;
    }
  }
}
</style>
