<template>
  <view class="rank-list">
    <view
      v-for="item in list"
      :key="item.userId"
      class="rank-item"
      :class="{ self: item.isSelf, top3: item.rank <= 3 }"
    >
      <view class="rank-num">
        <text v-if="item.rank === 1" class="medal gold"> 🥇 </text>
        <text v-else-if="item.rank === 2" class="medal silver"> 🥈 </text>
        <text v-else-if="item.rank === 3" class="medal bronze"> 🥉 </text>
        <text v-else>
          {{ item.rank }}
        </text>
      </view>
      <nut-avatar size="small">
        {{ item.nickname.slice(0, 1) }}
      </nut-avatar>
      <view class="info">
        <text class="name"> {{ item.nickname }}{{ item.isSelf ? '（我）' : '' }} </text>
      </view>
      <text class="score"> {{ item.score }}分 </text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { Avatar as NutAvatar } from '@nutui/nutui-taro'
import type { RankItem } from '@/types'

defineProps<{ list: RankItem[] }>()
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.rank-list {
  .rank-item {
    display: flex;
    align-items: center;
    padding: 14px 16px;
    background: $card-bg;
    margin-bottom: 8px;
    border-radius: 10px;
    &.self {
      background: $primary-light;
      border: 1px solid $primary-strong;
    }
    &.top3 .score {
      color: $primary-color;
      font-weight: 700;
    }
    .rank-num {
      width: 32px;
      text-align: center;
      font-weight: 600;
      .medal {
        font-size: 20px;
      }
    }
    .info {
      flex: 1;
      margin-left: 10px;
      .name {
        font-size: 14px;
      }
    }
    .score {
      font-size: 15px;
      font-weight: 600;
      color: $text-secondary;
    }
  }
}
</style>
