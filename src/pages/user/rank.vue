<template>
  <view class="page-rank" :class="themeClass">
    <view class="tabs">
      <view
        v-for="t in rankTypes"
        :key="t.key"
        class="tab"
        :class="{ active: activeType === t.key }"
        @tap="switchType(t.key)"
      >
        {{ t.label }}
      </view>
    </view>
    <RankList :list="questionStore.rankList" />
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import RankList from '@/components/RankList.vue'
import { useQuestionStore } from '@/store/question'
import { RANK_TYPE_LABELS, type RankType } from '@/constants'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '刷题排行榜' })

const { themeClass } = useThemeClass()
const questionStore = useQuestionStore()
const activeType = ref<RankType>('weekly')

const rankTypes = Object.entries(RANK_TYPE_LABELS).map(([key, label]) => ({
  key: key as RankType,
  label,
}))

onMounted(() => questionStore.fetchRankList(activeType.value))

function switchType(type: RankType) {
  activeType.value = type
  questionStore.fetchRankList(type)
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-rank {
  @include page-padding;
  .tabs {
    display: flex;
    background: $page-bg;
    border-radius: 8px;
    padding: 4px;
    margin-bottom: 16px;
    .tab {
      flex: 1;
      text-align: center;
      padding: 8px;
      font-size: 13px;
      border-radius: 6px;
      &.active { background: $card-bg; color: $primary-color; font-weight: 600; }
    }
  }
}
</style>
