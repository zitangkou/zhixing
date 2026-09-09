<template>
  <!-- eslint-disable-next-line vue/no-v-html, vue/no-v-text-v-html-on-component -->
  <view v-if="isH5" class="html-article" v-html="fragment" />
  <rich-text v-else class="html-article" :nodes="fragment" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { htmlToFragment } from '@/utils/articleContent'

const props = defineProps<{ html: string }>()
const isH5 = process.env.TARO_ENV === 'h5'
const fragment = computed(() => htmlToFragment(props.html))
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.html-article {
  display: block;
  background: $page-bg;
  color: $text-primary;
  font-size: 15px;
  line-height: 1.75;
  word-break: break-word;
  overflow-x: hidden;

  :deep(html),
  :deep(body) {
    background-color: $page-bg !important;
    color: $text-primary;
    margin: 0;
  }

  :deep(img),
  :deep(table),
  :deep(video) {
    max-width: 100%;
    height: auto;
  }

  :deep(a) {
    color: $primary-color;
  }
}
</style>
