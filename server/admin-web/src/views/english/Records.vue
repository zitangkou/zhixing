<template>
  <div class="page">
    <div class="heading"><div><h2>言遇英语 · 学习记录</h2><p>最近 200 条单元完成记录；当前只显示匿名学员标识。</p></div><el-button :loading="loading" @click="load">刷新</el-button></div>
    <el-table :data="records" v-loading="loading" row-key="id" empty-text="暂无学习记录">
      <el-table-column prop="learner" label="学员" width="150" />
      <el-table-column prop="unitTitle" label="完成课程" min-width="240" />
      <el-table-column label="完成时间" min-width="190"><template #default="{ row }">{{ formatDate(row.completedAt) }}</template></el-table-column>
      <el-table-column label="建议复习时间" min-width="190"><template #default="{ row }">{{ formatDate(row.nextReviewAt) }}</template></el-table-column>
    </el-table>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { EnglishRecord } from '@/api/english'
import { fetchEnglishRecords } from '@/api/english'
const loading = ref(false)
const records = ref<EnglishRecord[]>([])
function formatDate(value: string) { return new Date(value).toLocaleString('zh-CN', { hour12: false }) }
async function load() {
  loading.value = true
  try { records.value = await fetchEnglishRecords() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '学习记录加载失败') }
  finally { loading.value = false }
}
onMounted(load)
</script>
<style scoped>
.heading { display:flex; justify-content:space-between; margin-bottom:18px; }
.heading h2 { margin:0 0 8px; font-size:20px; }
.heading p { margin:0; color:#77817d; }
</style>
