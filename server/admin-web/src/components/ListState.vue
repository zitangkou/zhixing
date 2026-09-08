<template>
  <div v-if="loading && !hasData" class="list-state">
    <el-skeleton :rows="6" animated />
  </div>
  <div v-else-if="error && !hasData" class="list-state">
    <el-empty :description="error">
      <el-button type="primary" @click="$emit('retry')">重试</el-button>
    </el-empty>
  </div>
  <div v-else-if="!hasData" class="list-state">
    <el-empty :description="emptyText">
      <slot name="empty-action" />
    </el-empty>
  </div>
  <slot v-else />
</template>
<script setup lang="ts">
defineProps<{ loading: boolean; error?: string; hasData: boolean; emptyText?: string }>()
defineEmits<{ retry: [] }>()
</script>
<style scoped>
.list-state { padding: 24px 0; }
</style>
