<template>
  <div class="analytics-dashboard">
    <!-- 顶部筛选 -->
    <div class="toolbar">
      <el-radio-group v-model="sourceFilter" size="default" @change="loadData">
        <el-radio-button value="">全部数据</el-radio-button>
        <el-radio-button value="real">真实数据</el-radio-button>
        <el-radio-button value="demo">演示数据</el-radio-button>
      </el-radio-group>
      <el-button :icon="Refresh" @click="loadData" :loading="loading">刷新</el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">总练习人次</div>
          <div class="stat-value">{{ dashboard?.total_attempts ?? 0 }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">总正确率</div>
          <div class="stat-value" :class="accuracyClass">{{ dashboard?.overall_accuracy ?? 0 }}%</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">平均用时</div>
          <div class="stat-value">{{ formatTime(dashboard?.avg_time_ms) }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">活跃题目数</div>
          <div class="stat-value">{{ dashboard?.active_question_count ?? 0 }}</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="content-row">
      <!-- 模块正确率 -->
      <el-col :span="12">
        <div class="panel">
          <div class="panel-title">模块正确率</div>
          <div class="bar-chart" v-if="accuracy.by_module.length">
            <div v-for="item in accuracy.by_module" :key="item.module" class="bar-row">
              <div class="bar-label">{{ item.module }}</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: item.accuracy + '%' }" :class="barColorClass(item.accuracy)"></div>
              </div>
              <div class="bar-value">{{ item.accuracy }}% <span class="bar-sub">({{ item.attempts }}次)</span></div>
            </div>
          </div>
          <el-empty v-else description="暂无数据" :image-size="60" />
        </div>
      </el-col>

      <!-- 高频错误路径 TOP5 -->
      <el-col :span="12">
        <div class="panel">
          <div class="panel-title">高频错误路径 TOP5</div>
          <div v-if="dashboard?.top_error_paths?.length" class="error-list">
            <div v-for="(ep, idx) in dashboard.top_error_paths" :key="ep.type" class="error-item">
              <div class="error-rank" :class="'rank-' + (idx + 1)">{{ idx + 1 }}</div>
              <div class="error-info">
                <div class="error-type">{{ ep.type }}</div>
                <div class="error-bar-track">
                  <div class="error-bar-fill" :style="{ width: ep.percentage + '%' }"></div>
                </div>
              </div>
              <div class="error-stats">
                <div class="error-count">{{ ep.count }}次</div>
                <div class="error-pct">{{ ep.percentage }}%</div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无错误数据" :image-size="60" />
        </div>
      </el-col>
    </el-row>

    <!-- 低正确率题 TOP10 -->
    <div class="panel full-width">
      <div class="panel-title">低正确率题 TOP10</div>
      <el-table :data="dashboard?.low_accuracy_top10 ?? []" stripe size="small" v-loading="loading">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="question_id" label="题目ID" width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="goQuestion(row.question_id)">{{ row.question_id }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="100" />
        <el-table-column prop="subtype" label="子题型" min-width="140" />
        <el-table-column prop="difficulty" label="难度" width="70">
          <template #default="{ row }">{{ difficultyLabel(row.difficulty) }}</template>
        </el-table-column>
        <el-table-column prop="attempts" label="练习次数" width="90" />
        <el-table-column label="正确率" width="160">
          <template #default="{ row }">
            <div class="table-bar">
              <div class="table-bar-track">
                <div class="table-bar-fill" :style="{ width: row.accuracy + '%' }" :class="barColorClass(row.accuracy)"></div>
              </div>
              <span class="table-bar-value">{{ row.accuracy }}%</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 疑似歧义题预警 -->
    <div class="panel full-width" v-if="dashboard?.ambiguous_questions?.length || dashboard?.disputed_questions?.length">
      <div class="panel-title warning-title">
        <el-icon><Warning /></el-icon>
        疑似歧义/争议题预警
      </div>
      <el-table :data="allWarningQuestions" stripe size="small">
        <el-table-column prop="question_id" label="题目ID" width="180">
          <template #default="{ row }">
            <el-link type="danger" @click="goQuestion(row.question_id)">{{ row.question_id }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="100" />
        <el-table-column prop="subtype" label="子题型" min-width="140" />
        <el-table-column prop="attempts" label="练习次数" width="90" />
        <el-table-column prop="accuracy" label="正确率" width="90">
          <template #default="{ row }">{{ row.accuracy }}%</template>
        </el-table-column>
        <el-table-column label="异常标记" min-width="200">
          <template #default="{ row }">
            <el-tag v-for="a in row.anomalies" :key="a" type="danger" size="small" effect="plain" class="warn-tag">{{ a }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Warning } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDashboard, getAccuracy, type DashboardData, type AccuracySummary } from '@/api/analytics'

const router = useRouter()
const loading = ref(false)
const sourceFilter = ref('')
const dashboard = ref<DashboardData | null>(null)
const accuracy = ref<AccuracySummary>({
  total_attempts: 0,
  correct_count: 0,
  accuracy_rate: 0,
  avg_time_ms: 0,
  by_module: [],
  by_subtype: [],
})

const accuracyClass = computed(() => {
  const v = dashboard.value?.overall_accuracy ?? 0
  if (v >= 70) return 'acc-high'
  if (v >= 50) return 'acc-mid'
  return 'acc-low'
})

const allWarningQuestions = computed(() => [
  ...(dashboard.value?.ambiguous_questions ?? []),
  ...(dashboard.value?.disputed_questions ?? []),
])

async function loadData() {
  loading.value = true
  try {
    const src = sourceFilter.value || undefined
    const [dash, acc] = await Promise.all([
      getDashboard(src),
      getAccuracy(src ? { source: src } : {}),
    ])
    dashboard.value = dash
    accuracy.value = acc
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function goQuestion(qid: string) {
  router.push(`/analytics/questions/${qid}`)
}

function formatTime(ms?: number) {
  if (!ms) return '-'
  const s = Math.round(ms / 1000)
  if (s < 60) return s + '秒'
  return Math.floor(s / 60) + '分' + (s % 60) + '秒'
}

function difficultyLabel(d: number) {
  return { 1: '简单', 2: '中等', 3: '较难', 4: '困难', 5: '极难' }[d] || '中等'
}

function barColorClass(acc: number) {
  if (acc >= 70) return 'bar-green'
  if (acc >= 50) return 'bar-orange'
  return 'bar-red'
}

onMounted(loadData)
</script>

<style scoped>
.analytics-dashboard {
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

.stat-value.acc-high { color: var(--admin-success); }
.stat-value.acc-mid { color: #e6a23c; }
.stat-value.acc-low { color: #f56c6c; }

.content-row {
  margin-bottom: 16px;
}

.panel {
  background: var(--admin-card-bg);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--admin-border);
  margin-bottom: 16px;
}

.panel.full-width {
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

.warning-title {
  color: #f56c6c;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 柱状图 */
.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-label {
  width: 80px;
  font-size: 13px;
  color: #606266;
  text-align: right;
  flex-shrink: 0;
}

.bar-track {
  flex: 1;
  height: 20px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.bar-fill.bar-green { background: linear-gradient(90deg, #67c23a, #07c160); }
.bar-fill.bar-orange { background: linear-gradient(90deg, #e6a23c, #f0a020); }
.bar-fill.bar-red { background: linear-gradient(90deg, #f56c6c, #ee0a24); }

.bar-value {
  width: 100px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  flex-shrink: 0;
}

.bar-sub {
  font-weight: 400;
  color: var(--admin-text-muted);
  font-size: 11px;
}

/* 错误路径列表 */
.error-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.error-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.error-rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.error-rank.rank-1 { background: #f56c6c; }
.error-rank.rank-2 { background: #e6a23c; }
.error-rank.rank-3 { background: #f0a020; }
.error-rank.rank-4, .error-rank.rank-5 { background: #909399; }

.error-info {
  flex: 1;
  min-width: 0;
}

.error-type {
  font-size: 13px;
  color: #303133;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.error-bar-track {
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
}

.error-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #f56c6c, #e6a23c);
  border-radius: 3px;
}

.error-stats {
  text-align: right;
  flex-shrink: 0;
}

.error-count {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.error-pct {
  font-size: 11px;
  color: var(--admin-text-muted);
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

.table-bar-fill.bar-green { background: #07c160; }
.table-bar-fill.bar-orange { background: #e6a23c; }
.table-bar-fill.bar-red { background: #f56c6c; }

.table-bar-value {
  font-size: 12px;
  font-weight: 600;
  width: 45px;
}

.warn-tag {
  margin: 2px;
}
</style>
