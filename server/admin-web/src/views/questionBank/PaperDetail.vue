<template>
  <div class="page">
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="goBack">&larr; 返回列表</el-button>
        <h2 class="page-title">{{ paper?.title || '试卷详情' }}</h2>
      </div>
    </div>

    <ListState :loading="loading" :error="loadError" :has-data="!!paper" empty-text="试卷不存在">
      <template v-if="paper">
        <!-- 元信息 + 对账摘要 -->
        <el-descriptions :column="4" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="年份">{{ paper.exam_year }}</el-descriptions-item>
          <el-descriptions-item label="卷种">{{ paper.paper_type }}</el-descriptions-item>
          <el-descriptions-item label="考试类型">{{ paper.exam_kind }}</el-descriptions-item>
          <el-descriptions-item label="题位数">{{ paper.position_count }}</el-descriptions-item>
          <el-descriptions-item label="导入状态">
            <el-tag :type="paper.import_status === 'completed' ? 'success' : 'warning'" size="small">{{ paper.import_status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="schema版本">{{ paper.schema_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(paper.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatTime(paper.updated_at) }}</el-descriptions-item>
        </el-descriptions>

        <!-- 对账摘要卡片 -->
        <div v-if="reconcile" class="reconcile-cards">
          <div class="rc-card">
            <div class="rc-value">{{ reconcile.total_positions }}</div>
            <div class="rc-label">题位数</div>
          </div>
          <div class="rc-card" :class="{ 'rc-warn': reconcile.answer_coverage < 100 }">
            <div class="rc-value">{{ reconcile.answer_coverage }}%</div>
            <div class="rc-label">答案覆盖率</div>
          </div>
          <div class="rc-card" :class="{ 'rc-danger': reconcile.missing_count > 0 }">
            <div class="rc-value">{{ reconcile.missing_count }}</div>
            <div class="rc-label">断号数</div>
          </div>
          <div class="rc-card">
            <div class="rc-value">{{ reconcile.shared_question_count }}</div>
            <div class="rc-label">共享题数</div>
          </div>
          <div class="rc-card" :class="{ 'rc-danger': reconcile.high_risk_flag_count > 0 }">
            <div class="rc-value">{{ reconcile.high_risk_flag_count }}</div>
            <div class="rc-label">高风险标记</div>
          </div>
          <div class="rc-card">
            <div class="rc-value">{{ reconcile.without_explanation }}</div>
            <div class="rc-label">缺解析</div>
          </div>
        </div>

        <!-- Tab -->
        <el-tabs v-model="activeTab" @tab-change="onTabChange">
          <!-- 题位列表 -->
          <el-tab-pane label="题位列表" name="positions">
            <div v-if="positionGroups.length">
              <el-collapse v-model="activeSections">
                <el-collapse-item v-for="group in positionGroups" :key="group.section_id" :name="group.section_id">
                  <template #title>
                    <span class="section-title">
                      {{ group.section_name }}
                      <el-tag size="small" style="margin-left: 8px">{{ group.positions.length }} 题</el-tag>
                      <span class="section-range">{{ group.number_start }}-{{ group.number_end }}</span>
                    </span>
                  </template>
                  <el-table :data="group.positions" size="small" border>
                    <el-table-column prop="number" label="题号" width="60" align="center" />
                    <el-table-column label="题干摘要" min-width="240" show-overflow-tooltip>
                      <template #default="{ row }">
                        <span :class="{ 'text-danger': !row.has_answer }">{{ row.stem_summary }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="答案" width="70">
                      <template #default="{ row }">
                        <el-tag v-if="row.has_answer" type="success" size="small">{{ row.answer }}</el-tag>
                        <el-tag v-else type="danger" size="small">缺</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="状态" width="80">
                      <template #default="{ row }">
                        <el-tag :type="row.lifecycle_status === 'active' ? 'success' : 'info'" size="small">
                          {{ row.lifecycle_status }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="质量标记" min-width="140">
                      <template #default="{ row }">
                        <template v-if="row.quality_flags?.length">
                          <el-tag v-for="(f, i) in row.quality_flags" :key="i" size="small" type="warning" style="margin-right: 2px">
                            {{ typeof f === 'string' ? f : (f as Record<string, string>).flag || JSON.stringify(f) }}
                          </el-tag>
                        </template>
                        <span v-else class="text-muted">-</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="provenance" min-width="120" show-overflow-tooltip>
                      <template #default="{ row }">
                        <span v-if="row.provenance" class="json-inline">{{ JSON.stringify(row.provenance) }}</span>
                        <span v-else class="text-muted">-</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="80" fixed="right">
                      <template #default="{ row }">
                        <el-button link type="primary" @click="goQuestion(row.question_id)">详情</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-collapse-item>
              </el-collapse>
            </div>
            <el-empty v-else description="暂无题位数据" />
          </el-tab-pane>

          <!-- 对账报告 -->
          <el-tab-pane label="对账报告" name="reconcile">
            <div v-if="reconcile" class="reconcile-detail">
              <el-descriptions :column="3" border size="small" style="margin-bottom: 16px">
                <el-descriptions-item label="预期题量">{{ reconcile.expected_total }}</el-descriptions-item>
                <el-descriptions-item label="实际题位">{{ reconcile.total_positions }}</el-descriptions-item>
                <el-descriptions-item label="有答案">{{ reconcile.with_answer }}</el-descriptions-item>
                <el-descriptions-item label="缺答案">{{ reconcile.without_answer }}</el-descriptions-item>
                <el-descriptions-item label="缺解析">{{ reconcile.without_explanation }}</el-descriptions-item>
                <el-descriptions-item label="断号">{{ reconcile.missing_count > 0 ? reconcile.missing_numbers.join(', ') : '无' }}</el-descriptions-item>
              </el-descriptions>

              <h4>模块对账</h4>
              <el-table :data="reconcile.sections" size="small" border style="margin-bottom: 16px">
                <el-table-column prop="section_name" label="模块" min-width="140" />
                <el-table-column prop="number_range" label="题号范围" width="120" />
                <el-table-column prop="expected_count" label="预期题量" width="90" align="center" />
                <el-table-column prop="actual_count" label="实际题量" width="90" align="center" />
                <el-table-column prop="answer_count" label="有答案" width="90" align="center" />
                <el-table-column label="一致性" width="90" align="center">
                  <template #default="{ row }">
                    <el-tag v-if="row.expected_count === row.actual_count" type="success" size="small">一致</el-tag>
                    <el-tag v-else type="danger" size="small">不一致</el-tag>
                  </template>
                </el-table-column>
              </el-table>

              <h4>质量标记统计</h4>
              <el-table v-if="Object.keys(reconcile.flag_stats).length" :data="flagStatsList" size="small" border>
                <el-table-column prop="flag" label="标记" min-width="180" />
                <el-table-column prop="count" label="出现次数" width="100" align="center" />
              </el-table>
              <el-empty v-else description="无质量标记" :image-size="60" />

              <div v-if="reconcile.shared_questions.length" style="margin-top: 16px">
                <h4>共享题（前20）</h4>
                <el-table :data="reconcile.shared_questions" size="small" border>
                  <el-table-column prop="question_id" label="题目ID" width="200" />
                  <el-table-column prop="paper_count" label="关联试卷数" width="120" align="center" />
                  <el-table-column label="操作" width="80">
                    <template #default="{ row }">
                      <el-button link type="primary" @click="goQuestion(row.question_id)">详情</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
            <el-empty v-else description="加载中..." />
          </el-tab-pane>
        </el-tabs>
      </template>
    </ListState>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ListState from '@/components/ListState.vue'
import {
  fetchQBPaperDetail,
  fetchQBPaperPositions,
  fetchQBPaperReconcile,
  type QBPaperDetail,
  type QBPositionGroup,
  type QBReconcileReport,
} from '@/api/questionBank'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const loadError = ref('')
const paper = ref<QBPaperDetail | null>(null)
const positionGroups = ref<QBPositionGroup[]>([])
const reconcile = ref<QBReconcileReport | null>(null)
const activeTab = ref('positions')
const activeSections = ref<string[]>([])

const flagStatsList = computed(() => {
  if (!reconcile.value) return []
  return Object.entries(reconcile.value.flag_stats).map(([flag, count]) => ({ flag, count }))
})

async function loadPaper() {
  const id = route.params.id as string
  loading.value = true
  loadError.value = ''
  try {
    paper.value = await fetchQBPaperDetail(id)
    positionGroups.value = await fetchQBPaperPositions(id)
    activeSections.value = positionGroups.value.map((g) => g.section_id)
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadReconcile() {
  if (reconcile.value) return
  const id = route.params.id as string
  try {
    reconcile.value = await fetchQBPaperReconcile(id)
  } catch (e: unknown) {
    console.error('对账加载失败', e)
  }
}

function onTabChange(tab: string) {
  if (tab === 'reconcile') {
    loadReconcile()
  }
}

function goBack() {
  router.push('/question-bank/papers')
}

function goQuestion(id: string) {
  router.push(`/question-bank/questions/${id}`)
}

function formatTime(t: string | null) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

onMounted(() => {
  if (route.query.tab === 'reconcile') {
    activeTab.value = 'reconcile'
  }
  loadPaper()
  if (activeTab.value === 'reconcile') {
    loadReconcile()
  }
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.reconcile-cards {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.rc-card {
  flex: 1;
  min-width: 120px;
  padding: 14px;
  background: var(--admin-page-bg);
  border-radius: 8px;
  text-align: center;
  border: 1px solid var(--admin-border);
}
.rc-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--admin-brand);
}
.rc-label {
  font-size: 12px;
  color: var(--admin-text-muted);
  margin-top: 4px;
}
.rc-warn .rc-value {
  color: var(--el-color-warning);
}
.rc-danger .rc-value {
  color: var(--el-color-danger);
}
.section-title {
  font-weight: 600;
  font-size: 14px;
}
.section-range {
  margin-left: 12px;
  color: var(--admin-text-muted);
  font-size: 12px;
  font-weight: normal;
}
.text-danger {
  color: var(--el-color-danger);
}
.text-muted {
  color: var(--admin-text-muted);
}
.json-inline {
  font-family: monospace;
  font-size: 12px;
  color: var(--admin-text-muted);
}
.reconcile-detail h4 {
  margin: 16px 0 8px;
  font-size: 14px;
}
</style>
