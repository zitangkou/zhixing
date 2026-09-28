<template>
  <!-- 小程序无 web-view / 无 markmap；导图走分片图 previewImage -->
  <view class="mm-weapp-placeholder" />
</template>

<script setup lang="ts">
defineProps<{
  tree: unknown
}>()
</script>

<style lang="scss" scoped>
.mm-weapp-placeholder {
  display: none;
}
</style>
