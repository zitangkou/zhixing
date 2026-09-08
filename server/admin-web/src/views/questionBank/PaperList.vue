<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">真题试卷</h2>
      <el-button @click="load">刷新</el-button>
    </div>

    <div class="filter-bar">
      <el-input-number v-model="filterYear" :min="2000" :max="2030" placeholder="年份" clearable style="width: 120px" @change="load" />
      <el-select v-model="filterPaperType" placeholder="卷种" clearable style="width: 140px" @change="load">
        <el-option value="省级" label="省级" />
        <el-option value="市地级" label="市地级" />
        <el-option value="行政执法类" label="行政执法类" />
      </el-select>
    </div>

    <ListState :loading="loading" :error="loadError" :has-data="papers.length > 0" empty-text="暂无试卷">
      <el-table :data="papers" v-loading="loading && papers.length > 0" row-key="id">
        <el-table-column prop="exam_year" label="年份" width="80" />
        <el-table-column prop="paper_type" label="卷种" width="110" />
        <el-table-column prop="title" label="试卷名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="position_count" label="题位数" width="80" align="center" />
        <el-table-column label="答案覆盖率" width="110" align="center">
          <template #default="{ row }">
            <el-progress :percentage="row.answer_coverage" :stroke-width="14" :format="(p: number) => `${p}%`" />
          </template>
        </el-table-column>
        <el-table-column label="导入状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.import_status === 'completed' ? 'success' : 'warning'" size="small">
              {{ row.import_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="导入时间" width="160">
          <template #default="{ row }">{{ formatTime(row.import_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row.id)">查看详情</el-button>
            <el-button link type="primary" @click="goReconcile(row.id)">对账</el-button>
          </template>
        </el-table-column>
      </el-table>
    </ListState>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ListState from '@/components/ListState.vue'
import { fetchQBPapers, type QBPaperSummary } from '@/api/questionBank'

const router = useRouter()
const loading = ref(false)
const loadError = ref('')
const papers = ref<QBPaperSummary[]>([])
const filterYear = ref<number | undefined>(undefined)
const filterPaperType = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    papers.value = await fetchQBPapers({
      exam_year: filterYear.value,
      paper_type: filterPaperType.value || undefined,
    })
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function goDetail(id: string) {
  router.push(`/question-bank/papers/${id}`)
}

function goReconcile(id: string) {
  router.push(`/question-bank/papers/${id}?tab=reconcile`)
}

function formatTime(t: string | null) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

onMounted(load)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--admin-page-bg);
  border-radius: 6px;
}
</style>
