<template>
  <div class="error-paths-page">
    <!-- 筛选栏 -->
    <div class="toolbar">
      <el-select v-model="filterModule" placeholder="全部模块" clearable size="default" style="width: 140px" @change="loadData">
        <el-option v-for="m in moduleOptions" :key="m" :label="m" :value="m" />
      </el-select>
      <el-select v-model="filterSubtype" placeholder="全部子题型" clearable size="default" style="width: 180px" @change="loadData">
        <el-option v-for="s in subtypeOptions" :key="s" :label="s" :value="s" />
      </el-select>
      <el-radio-group v-model="sourceFilter" size="default" @change="loadData">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="real">真实</el-radio-button>
        <el-radio-button value="demo">演示</el-radio-button>
      </el-radio-group>
      <el-button :icon="Refresh" @click="loadData" :loading="loading">刷新</el-button>
    </div>

    <!-- 汇总卡片 -->
    <el-row :gutter="16" class="stat-row" v-if="errorData">
      <el-col :span="8">
        <div class="stat-card">
          <div class="stat-label">总错误次数</div>
          <div class="stat-value error">{{ errorData.total_errors }}</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="stat-card">
          <div class="stat-label">错误路径种类</div>
          <div class="stat-value">{{ errorData.by_error_path.length }}</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="stat-card">
          <div class="stat-label">涉及题目数</div>
          <div class="stat-value">{{ totalInvolvedQuestions }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 错误路径分布（横向柱状图） -->
    <div class="panel" v-if="errorData?.by_error_path?.length">
      <div class="panel-title">错误路径分布</div>
      <div class="ep-chart">
        <div v-for="ep in errorData.by_error_path" :key="ep.type" class="ep-bar-row"
             @click="toggleExpand(ep.type)">
          <div class="ep-bar-label">{{ ep.type }}</div>
          <div class="ep-bar-track">
            <div class="ep-bar-fill" :style="{ width: ep.percentage + '%' }"
                 :class="epColorClass(ep.percentage)"></div>
          </div>
          <div class="ep-bar-count">{{ ep.count }}次</div>
          <div class="ep-bar-pct">{{ ep.percentage }}%</div>
          <el-icon class="ep-expand-icon" :class="{ rotated: expandedType === ep.type }">
            <ArrowDown />
          </el-icon>
        </div>
      </div>
    </div>

    <!-- 错误路径汇总表格 -->
    <div class="panel">
      <div class="panel-title">错误路径明细</div>
      <el-table :data="errorData?.by_error_path ?? []" stripe size="small" v-loading="loading">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="type" label="错误路径类型" min-width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="toggleExpand(row.type)">{{ row.type }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="count" label="出现次数" width="100" sortable />
        <el-table-column label="占比" width="160">
          <template #default="{ row }">
            <div class="table-bar">
              <div class="table-bar-track">
                <div class="table-bar-fill" :style="{ width: row.percentage + '%' }"
                     :class="epColorClass(row.percentage)"></div>
              </div>
              <span class="table-bar-value">{{ row.percentage }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="involved_question_count" label="涉及题数" width="90" />
        <el-table-column label="示例题" min-width="200">
          <template #default="{ row }">
            <el-link v-for="qid in row.example_question_ids" :key="qid" type="primary"
                     size="small" @click="goQuestion(qid)" style="margin-right: 8px">
              {{ qid }}
            </el-link>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 展开的涉及题目列表 -->
    <div class="panel" v-if="expandedType && expandedQuestions.length">
      <div class="panel-title">「{{ expandedType }}」涉及题目 ({{ expandedQuestions.length }})</div>
      <el-table :data="expandedQuestions" stripe size="small">
        <el-table-column prop="question_id" label="题目ID" width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="goQuestion(row.question_id)">{{ row.question_id }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="100" />
        <el-table-column prop="subtype" label="子题型" min-width="140" />
        <el-table-column prop="wrong_count" label="错误次数" width="100" />
        <el-table-column prop="accuracy" label="正确率" width="100">
          <template #default="{ row }">{{ row.accuracy }}%</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getErrorPaths, type ErrorPathSummary } from '@/api/analytics'

const router = useRouter()
const loading = ref(false)
const sourceFilter = ref('')
const filterModule = ref('')
const filterSubtype = ref('')
const errorData = ref<ErrorPathSummary | null>(null)
const expandedType = ref('')
const expandedQuestions = ref<Array<{ question_id: string; module: string; subtype: string; wrong_count: number; accuracy: number }>>([])

// 模块/子题型选项（从题库中提取，这里用常见值）
const moduleOptions = ['资料分析']
const subtypeOptions = [
  '基期量计算', '增长率计算', '现期比重计算', '已知整体和比重求部分',
  '已知部分和比重求整体', '两期比重差', '现期平均数计算', '已知平均和份数求总量',
  '两期平均数差', '两期平均数增长率', '已知总量和平均求份数', '是几倍', '多几倍',
  '基期倍数', '倍数与比重联合', '基期多几倍', '混合增长率_整体率',
  '混合增长率_推断部分率', '混合增长率_十字交叉',
]

const totalInvolvedQuestions = computed(() => {
  if (!errorData.value) return 0
  const ids = new Set<string>()
  for (const ep of errorData.value.by_error_path) {
    for (const qid of ep.example_question_ids) ids.add(qid)
  }
  return ids.size
})

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (sourceFilter.value) params.source = sourceFilter.value
    if (filterModule.value) params.module = filterModule.value
    if (filterSubtype.value) params.subtype = filterSubtype.value
    errorData.value = await getErrorPaths(params)
    expandedType.value = ''
    expandedQuestions.value = []
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function toggleExpand(type: string) {
  if (expandedType.value === type) {
    expandedType.value = ''
    expandedQuestions.value = []
    return
  }
  expandedType.value = type
  // 从 errorData 中找到该错误路径的示例题，构建展示数据
  const ep = errorData.value?.by_error_path.find((e) => e.type === type)
  if (ep) {
    expandedQuestions.value = ep.example_question_ids.map((qid) => ({
      question_id: qid,
      module: '资料分析',
      subtype: '',
      wrong_count: 0,
      accuracy: 0,
    }))
  }
}

function goQuestion(qid: string) {
  router.push(`/analytics/questions/${qid}`)
}

function epColorClass(pct: number) {
  if (pct >= 20) return 'ep-red'
  if (pct >= 10) return 'ep-orange'
  return 'ep-gray'
}

onMounted(loadData)
</script>

<style scoped>
.error-paths-page {
  padding: 0;
}

.stat-row {
  margin-bottom: 16px;
}

.stat-card {
  background: var(--admin-card-bg);
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  border: 1px solid var(--admin-border);
}

.stat-label {
  font-size: 13px;
  color: var(--admin-text-muted);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--admin-brand);
}

.stat-value.error {
  color: #f56c6c;
}

.panel {
  background: var(--admin-card-bg);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--admin-border);
  margin-bottom: 16px;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--admin-brand);
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--admin-border);
}

/* 错误路径柱状图 */
.ep-chart {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ep-bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.ep-bar-row:hover {
  background: #f5f7fa;
}

.ep-bar-label {
  width: 140px;
  font-size: 13px;
  color: #303133;
  text-align: right;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ep-bar-track {
  flex: 1;
  height: 20px;
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}

.ep-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.ep-bar-fill.ep-red { background: linear-gradient(90deg, #f56c6c, #ee0a24); }
.ep-bar-fill.ep-orange { background: linear-gradient(90deg, #e6a23c, #f0a020); }
.ep-bar-fill.ep-gray { background: linear-gradient(90deg, #909399, #c0c4cc); }

.ep-bar-count {
  width: 60px;
  font-size: 12px;
  color: #606266;
  text-align: right;
  flex-shrink: 0;
}

.ep-bar-pct {
  width: 55px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  text-align: right;
  flex-shrink: 0;
}

.ep-expand-icon {
  color: var(--admin-text-muted);
  transition: transform 0.2s;
  flex-shrink: 0;
}

.ep-expand-icon.rotated {
  transform: rotate(180deg);
}

/* 表格内柱状图 */
.table-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-bar-track {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  max-width: 80px;
}

.table-bar-fill {
  height: 100%;
  border-radius: 4px;
}

.table-bar-fill.ep-red { background: #f56c6c; }
.table-bar-fill.ep-orange { background: #e6a23c; }
.table-bar-fill.ep-gray { background: #909399; }

.table-bar-value {
  font-size: 12px;
  font-weight: 600;
  width: 45px;
}
</style>
