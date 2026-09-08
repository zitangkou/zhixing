<template>
  <div class="page">
    <div v-if="title || $slots.extra" class="page-head">
      <h2 v-if="title" class="page-title">{{ title }}</h2>
      <div class="page-extra">
        <slot name="extra" />
      </div>
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{ title?: string }>()
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.page-extra {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
