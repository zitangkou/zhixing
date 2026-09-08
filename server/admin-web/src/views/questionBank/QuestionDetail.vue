<template>
  <div class="page">
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="goBack">&larr; 返回列表</el-button>
        <h2 class="page-title">题目详情</h2>
        <el-tag v-if="detail" :type="statusTagType(detail.lifecycle_status)" size="small">
          {{ LIFECYCLE_LABELS[detail.lifecycle_status] || detail.lifecycle_status }}
        </el-tag>
        <el-tag v-if="detail?.has_high_risk_flag" type="danger" size="small">高风险</el-tag>
      </div>
      <div class="header-right">
        <el-button v-if="detail?.lifecycle_status !== 'active'" type="success" @click="onPublish">发布</el-button>
        <el-button v-else type="warning" @click="onUnpublish">下线</el-button>
      </div>
    </div>

    <ListState :loading="loading" :error="loadError" :has-data="!!detail" empty-text="题目不存在">
      <template v-if="detail">
        <!-- 基本信息 -->
        <el-descriptions :column="4" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="题目ID">{{ detail.id }}</el-descriptions-item>
          <el-descriptions-item label="来源类型">{{ originLabel(detail.origin_type) }}</el-descriptions-item>
          <el-descriptions-item label="科目">{{ detail.subject }}</el-descriptions-item>
          <el-descriptions-item label="模块">{{ detail.module }}</el-descriptions-item>
          <el-descriptions-item label="子题型">{{ detail.subtype || '-' }}</el-descriptions-item>
          <el-descriptions-item label="题型">{{ detail.response_type }}</el-descriptions-item>
          <el-descriptions-item label="难度">{{ detail.difficulty }}</el-descriptions-item>
          <el-descriptions-item label="关联试卷">{{ detail.paper_count }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatTime(detail.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="canonical_hash" :span="2">{{ detail.canonical_hash }}</el-descriptions-item>
        </el-descriptions>

        <!-- Tab 页签 -->
        <el-tabs v-model="activeTab">
          <!-- 题面 -->
          <el-tab-pane label="题面" name="content">
            <div v-if="detail.current_version" class="content-panel">
              <div class="field-block">
                <div class="field-label">题干</div>
                <div class="field-value pre-wrap">{{ detail.current_version.stem }}</div>
              </div>
              <div v-if="detail.current_version.items?.length" class="field-block">
                <div class="field-label">组合条目</div>
                <div class="field-value">
                  <pre class="json-pre">{{ JSON.stringify(detail.current_version.items, null, 2) }}</pre>
                </div>
              </div>
              <div v-if="detail.current_version.options" class="field-block">
                <div class="field-label">选项</div>
                <div class="field-value options-list">
                  <div v-for="(val, key) in detail.current_version.options" :key="key" class="option-item">
                    <span class="option-label">{{ key }}.</span>
                    <span>{{ val }}</span>
                  </div>
                </div>
              </div>
              <div class="field-block">
                <div class="field-label">正确答案</div>
                <div class="field-value">
                  <el-tag v-if="detail.current_version.correct_answer" type="success" size="large">
                    {{ formatAnswer(detail.current_version.correct_answer) }}
                  </el-tag>
                  <el-tag v-else type="danger" size="large">缺答案</el-tag>
                </div>
              </div>
              <div class="field-block">
                <div class="field-label">解析</div>
                <div class="field-value pre-wrap">
                  <span v-if="detail.current_version.explanation">{{ detail.current_version.explanation }}</span>
                  <span v-else class="text-muted">（无解析）</span>
                </div>
              </div>
              <div v-if="detail.current_version.topic || detail.current_version.tag" class="field-block">
                <div class="field-label">考点/标签</div>
                <div class="field-value">
                  <el-tag v-if="detail.current_version.topic" size="small" style="margin-right: 6px">{{ detail.current_version.topic }}</el-tag>
                  <el-tag v-if="detail.current_version.tag" size="small">{{ detail.current_version.tag }}</el-tag>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无版本内容" />
          </el-tab-pane>

          <!-- 出处 -->
          <el-tab-pane label="出处" name="provenance">
            <div v-if="detail.positions.length" class="content-panel">
              <el-table :data="detail.positions" size="small" border>
                <el-table-column prop="paper_title" label="试卷" min-width="180" />
                <el-table-column prop="exam_year" label="年份" width="70" />
                <el-table-column prop="paper_type" label="卷种" width="100" />
                <el-table-column prop="section_name" label="模块" width="130" />
                <el-table-column prop="number" label="题号" width="60" />
                <el-table-column prop="source_key" label="来源标识" min-width="180" show-overflow-tooltip />
                <el-table-column label="provenance" min-width="160">
                  <template #default="{ row }">
                    <span v-if="row.provenance" class="json-inline">{{ JSON.stringify(row.provenance) }}</span>
                    <span v-else class="text-muted">-</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <el-empty v-else description="暂无关联题位" />

            <div v-if="detail.materials.length" style="margin-top: 16px">
              <h4>关联材料</h4>
              <el-table :data="detail.materials" size="small" border>
                <el-table-column prop="title" label="标题" min-width="150" />
                <el-table-column prop="material_type" label="类型" width="100" />
                <el-table-column prop="content_summary" label="内容摘要" min-width="200" show-overflow-tooltip />
                <el-table-column prop="role" label="角色" width="80" />
              </el-table>
            </div>
          </el-tab-pane>

          <!-- 版本 -->
          <el-tab-pane :label="`版本 (${detail.versions.length})`" name="versions">
            <div class="content-panel">
              <el-table :data="detail.versions" size="small" border>
                <el-table-column prop="version_no" label="版本号" width="80" />
                <el-table-column prop="stem_summary" label="题干摘要" min-width="200" show-overflow-tooltip />
                <el-table-column prop="change_summary" label="变更说明" min-width="150" show-overflow-tooltip />
                <el-table-column prop="content_hash" label="内容哈希" width="160" show-overflow-tooltip />
                <el-table-column label="创建时间" width="160">
                  <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
                </el-table-column>
                <el-table-column label="当前版本" width="90">
                  <template #default="{ row }">
                    <el-tag v-if="row.id === detail.current_version_id" type="success" size="small">当前</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-tab-pane>

          <!-- 质量 -->
          <el-tab-pane label="质量" name="quality">
            <div class="content-panel">
              <div class="quality-summary">
                <div class="quality-item">
                  <span class="quality-label">高风险标记：</span>
                  <el-tag v-if="detail.has_high_risk_flag" type="danger" size="small">
                    {{ detail.high_risk_flags.join(', ') }}
                  </el-tag>
                  <el-tag v-else type="success" size="small">无</el-tag>
                </div>
                <div class="quality-item">
                  <span class="quality-label">全部质量标记：</span>
                  <template v-if="detail.quality_flags.length">
                    <el-tag v-for="f in detail.quality_flags" :key="f" size="small" style="margin-right: 4px">{{ f }}</el-tag>
                  </template>
                  <span v-else class="text-muted">无</span>
                </div>
                <div class="quality-item">
                  <span class="quality-label">答案完整性：</span>
                  <el-tag v-if="detail.current_version?.correct_answer" type="success" size="small">完整</el-tag>
                  <el-tag v-else type="danger" size="small">缺失</el-tag>
                </div>
                <div class="quality-item">
                  <span class="quality-label">解析完整性：</span>
                  <el-tag v-if="detail.current_version?.explanation" type="success" size="small">完整</el-tag>
                  <el-tag v-else type="warning" size="small">缺失（警告）</el-tag>
                </div>
              </div>

              <el-alert
                v-if="detail.has_high_risk_flag"
                type="error"
                :closable="false"
                style="margin-top: 12px"
                title="该题目存在高风险质量标记，无法通过发布门禁。请先处理质量问题后再发布。"
              />
              <el-alert
                v-else-if="!detail.current_version?.correct_answer"
                type="error"
                :closable="false"
                style="margin-top: 12px"
                title="该题目缺少答案，无法通过发布门禁。"
              />
              <el-alert
                v-else-if="!detail.current_version?.explanation"
                type="warning"
                :closable="false"
                style="margin-top: 12px"
                title="该题目缺少解析，可发布但建议补充解析。"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </ListState>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ListState from '@/components/ListState.vue'
import {
  fetchQBQuestionDetail,
  publishQBQuestion,
  unpublishQBQuestion,
  ORIGIN_TYPE_OPTIONS,
  LIFECYCLE_LABELS,
  type QBQuestionDetail,
} from '@/api/questionBank'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const loadError = ref('')
const detail = ref<QBQuestionDetail | null>(null)
const activeTab = ref('content')

async function load() {
  const id = route.params.id as string
  loading.value = true
  loadError.value = ''
  try {
    detail.value = await fetchQBQuestionDetail(id)
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/question-bank/questions')
}

async function onPublish() {
  if (!detail.value) return
  try {
    await ElMessageBox.confirm('确认发布该题目？发布前将执行门禁检查。', '发布确认', { type: 'warning' })
    const res = await publishQBQuestion(detail.value.id)
    if (res.warnings?.length) {
      ElMessage.warning(res.warnings.join('；'))
    } else {
      ElMessage.success('发布成功')
    }
    detail.value.lifecycle_status = 'active'
  } catch (e: unknown) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : '发布失败')
    }
  }
}

async function onUnpublish() {
  if (!detail.value) return
  try {
    await ElMessageBox.confirm('确认下线该题目？', '下线确认', { type: 'warning' })
    await unpublishQBQuestion(detail.value.id)
    ElMessage.success('已下线')
    detail.value.lifecycle_status = 'retired'
  } catch (e: unknown) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : '下线失败')
    }
  }
}

function originLabel(t: string) {
  return ORIGIN_TYPE_OPTIONS.find((o) => o.value === t)?.label || t
}

function statusTagType(s: string) {
  if (s === 'active') return 'success'
  if (s === 'retired') return 'info'
  if (s === 'disputed') return 'danger'
  return 'info'
}

function formatAnswer(a: string | string[] | null) {
  if (Array.isArray(a)) return a.join('')
  return a || ''
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
.content-panel {
  padding: 4px 0;
}
.field-block {
  margin-bottom: 16px;
}
.field-label {
  font-weight: 600;
  color: var(--admin-text-muted);
  margin-bottom: 6px;
  font-size: 13px;
}
.field-value {
  font-size: 14px;
  line-height: 1.7;
}
.pre-wrap {
  white-space: pre-wrap;
  word-break: break-word;
}
.options-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.option-item {
  display: flex;
  gap: 8px;
}
.option-label {
  font-weight: 600;
  min-width: 20px;
}
.json-pre {
  background: var(--admin-page-bg);
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  margin: 0;
}
.json-inline {
  font-family: monospace;
  font-size: 12px;
  color: var(--admin-text-muted);
}
.text-muted {
  color: var(--admin-text-muted);
}
.quality-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.quality-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.quality-label {
  font-weight: 600;
  min-width: 100px;
}
</style>
