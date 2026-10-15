<template>
  <view class="math-text">
    <template v-for="(segment, index) in segments" :key="index">
      <text v-if="segment.type === 'text'" class="math-text-copy" selectable>
        {{
          segment.text
        }}
      </text>
      <LatexBlock
        v-else
        class="math-text-formula"
        :class="{ 'math-text-inline': !segment.display }"
        :latex="segment.text"
        :display-mode="segment.display"
        :show-plain="false"
      />
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import LatexBlock from '@/components/LatexBlock.vue'
import { splitMathText } from '@/utils/mathText'
const props = defineProps<{ text: string }>()
const segments = computed(() => splitMathText(props.text))
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
.math-text {
  color: $text-primary;
  line-height: 1.7;
  overflow-wrap: anywhere;
}
.math-text-copy {
  white-space: pre-wrap;
}
.math-text-formula {
  margin: 8px 0;
}
.math-text-inline {
  display: inline-block;
  width: auto;
  max-width: 100%;
  margin: 0 3px;
  vertical-align: middle;
}
</style>
