<template>
  <view class="points-badge" :class="[`tone-${tone}`]" @tap.stop="$emit('tap')">
    <StarFill :color="iconColor" size="12" />
    <text class="value">
      {{ points }}
    </text>
    <text v-if="showLabel" class="label"> 积分 </text>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { StarFill } from '@nutui/icons-vue-taro'
import { useBrandColor } from '@/utils/brandColor'

const props = withDefaults(
  defineProps<{
    points: number
    showLabel?: boolean
    /** on-brand: 红底半透明；plain: 白底文字感 */
    tone?: 'on-brand' | 'plain'
  }>(),
  {
    showLabel: false,
    tone: 'plain',
  },
)

defineEmits<{ tap: [] }>()

const { brandColor } = useBrandColor()
const iconColor = computed(() => (props.tone === 'on-brand' ? '#FFE08A' : brandColor.value))
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.points-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  line-height: 1;
  min-height: 44px;
  box-sizing: border-box;

  &:active {
    opacity: 0.85;
  }

  &.tone-on-brand {
    padding: 10px 12px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.18);
    .value {
      color: var(--zk-on-primary);
      font-weight: 600;
      font-size: 13px;
    }
    .label {
      color: rgba(255, 255, 255, 0.85);
      font-size: 12px;
    }
  }

  &.tone-plain {
    padding: 0;
    background: transparent;
    .value {
      color: $text-primary;
      font-weight: 600;
      font-size: 14px;
    }
    .label {
      color: $text-muted;
      font-size: 12px;
    }
  }
}
</style>
