<template>
  <div>
    <el-tabs v-model="subTab">
      <el-tab-pane label="训练方法" name="methods">
        <el-alert
          class="setup-guide"
          title="配置流程：检查方法说明 → 预览校验 → 发布。首次配置通常不需要改高级设置。"
          description="只有调整题目数值范围、难度或知识框架关联时，才展开编辑窗口中的高级设置。发布后学员端才会使用该方法出题。"
          type="info"
          :closable="false"
          show-icon
        />
        <div class="toolbar">
          <el-button @click="loadMethods">刷新</el-button>
          <span class="tip">修改已发布方法会生成草稿；校验通过后再发布新版本。</span>
        </div>
        <el-table :data="methods" v-loading="loading" row-key="id">
          <el-table-column prop="name" label="方法" min-width="130" />
          <el-table-column prop="category" label="类型" width="90" />
          <el-table-column prop="scene" label="适用场景" min-width="240" show-overflow-tooltip />
          <el-table-column label="规则范围" width="140">
            <template #default="{ row }">{{ row.config.min }}–{{ row.config.max }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }"><el-tag :type="row.status === 'published' ? 'success' : 'warning'">{{ row.status === 'published' ? `已发布 v${row.version}` : '草稿' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="edit(row)">编辑</el-button>
              <el-button link type="primary" @click="preview(row)">预览校验</el-button>
              <el-button link type="primary" @click="showVersions(row)">版本</el-button>
              <el-button link type="success" :disabled="!row.enabled || row.status === 'published'" @click="publish(row)">发布</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="训练效果" name="analytics">
        <div class="toolbar">
          <el-select v-model="days" style="width: 140px" @change="loadAnalytics">
            <el-option :value="7" label="最近 7 天" /><el-option :value="30" label="最近 30 天" /><el-option :value="90" label="最近 90 天" />
          </el-select>
          <el-button @click="loadAnalytics">刷新</el-button>
          <span>完成训练 {{ analytics.sessions }} 组 · 答题 {{ analytics.attempts }} 题</span>
        </div>
        <el-table :data="analytics.methods" v-loading="analyticsLoading" row-key="method">
          <el-table-column prop="name" label="训练方法" min-width="140" />
          <el-table-column prop="attempts" label="答题数" width="100" />
          <el-table-column prop="accuracy" label="正确率" width="110"><template #default="{ row }">{{ row.accuracy }}%</template></el-table-column>
          <el-table-column prop="averageSeconds" label="平均用时" width="110"><template #default="{ row }">{{ row.averageSeconds }} 秒</template></el-table-column>
          <el-table-column label="错选分布" min-width="180"><template #default="{ row }">{{ wrongLabel(row.wrongOptions) }}</template></el-table-column>
        </el-table>
        <el-empty v-if="!analyticsLoading && !analytics.methods.length" description="所选时间段暂无已完成训练" />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="editVisible" title="编辑训练方法" width="680px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="方法名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="方法类别"><el-select v-model="form.category"><el-option label="比较" value="比较" /><el-option label="计算" value="计算" /></el-select></el-form-item>
        <el-form-item label="适用场景"><el-input v-model="form.scene" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="启用训练"><el-switch v-model="form.enabled" /></el-form-item>
        <el-collapse class="advanced-settings">
          <el-collapse-item title="高级设置（通常无需调整）" name="advanced">
            <el-form-item label="知识框架路径"><el-input v-model="form.knowledgePath" /></el-form-item>
            <el-form-item label="知识节点标题"><el-input v-model="form.nodeTitle" /></el-form-item>
            <el-form-item label="上级节点"><el-input v-model="form.nodeParent" /></el-form-item>
            <el-form-item label="基础数值下限"><el-input-number v-model="form.config.min" :min="100" :max="99900" :step="100" /></el-form-item>
            <el-form-item label="基础数值上限"><el-input-number v-model="form.config.max" :min="200" :max="100000" :step="100" /></el-form-item>
            <el-form-item label="难度级别"><el-rate v-model="form.config.difficulty" :max="5" /></el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form>
      <template #footer><el-button @click="editVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存为草稿</el-button></template>
    </el-dialog>

    <el-drawer v-model="previewVisible" title="样题预览与规则校验" size="60%">
      <el-alert v-if="previewResult" :title="previewResult.valid ? '全部校验通过：题目计算正确，知识节点已解析' : `题目计算${previewResult.mathValid ? '通过' : '未通过'}；${previewResult.validationMessage}`" :type="previewResult.valid ? 'success' : previewResult.mathValid ? 'warning' : 'error'" :closable="false" />
      <el-descriptions v-if="previewResult" :column="1" border class="preview-meta">
        <el-descriptions-item label="适用场景">{{ previewResult.method.scene }}</el-descriptions-item>
        <el-descriptions-item label="知识框架">{{ previewResult.method.knowledgePath }}</el-descriptions-item>
      </el-descriptions>
      <el-card v-for="(q, index) in previewResult?.questions || []" :key="index" class="preview-card">
        <template #header><b>{{ index + 1 }}. {{ q.stem }}</b></template>
        <div class="formula" v-html="renderFormula(q.latex)" />
        <div class="plain">{{ q.plain }}</div>
        <ol><li v-for="(option, i) in q.options" :key="i" :class="i === q.answer ? 'answer' : ''">{{ option }}<el-tag v-if="i === q.answer" type="success" size="small">正确答案</el-tag></li></ol>
        <p v-for="step in q.steps" :key="step.text">{{ step.text }} {{ step.latex }}</p>
        <el-text type="warning">易错点：{{ q.pitfall }}</el-text>
      </el-card>
    </el-drawer>

    <el-dialog v-model="versionsVisible" title="已发布版本" width="720px">
      <el-table :data="versions" row-key="version">
        <el-table-column prop="version" label="版本" width="90"><template #default="{ row }">v{{ row.version }}</template></el-table-column>
        <el-table-column prop="publishedAt" label="发布时间" min-width="180" />
        <el-table-column label="规则快照" min-width="250">
          <template #default="{ row }">{{ row.snapshot.name }} · {{ row.snapshot.config?.min }}–{{ row.snapshot.config?.max }} · 难度 {{ row.snapshot.config?.difficulty }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100"><template #default="{ row }"><el-button link type="warning" :disabled="row.version === activeVersion" @click="rollback(row.version)">回滚</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!versions.length" description="暂无发布记录" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { getQuickAnalytics, listQuickMethods, listQuickMethodVersions, previewQuickMethod, publishQuickMethod, rollbackQuickMethod, saveQuickMethod, type QuickCalcMethod } from '@/api/ziliao'

const subTab = ref('methods')
const methods = ref<QuickCalcMethod[]>([])
const loading = ref(false)
const analyticsLoading = ref(false)
const editVisible = ref(false)
const previewVisible = ref(false)
const versionsVisible = ref(false)
const saving = ref(false)
const currentId = ref('')
const days = ref(30)
const analytics = ref({ sessions: 0, attempts: 0, methods: [] as Awaited<ReturnType<typeof getQuickAnalytics>>['methods'] })
const previewResult = ref<Awaited<ReturnType<typeof previewQuickMethod>> | null>(null)
const versions = ref<Awaited<ReturnType<typeof listQuickMethodVersions>>>([])
const activeVersion = ref(0)
const versionsMethodId = ref('')
const form = reactive({ code: '', name: '', category: '比较', scene: '', knowledgePath: '', nodeTitle: '', nodeParent: '', config: { min: 1000, max: 9000, difficulty: 2 }, enabled: true, sortOrder: 0 })

async function loadMethods() { loading.value = true; try { methods.value = await listQuickMethods() } catch { ElMessage.error('训练方法加载失败') } finally { loading.value = false } }
async function loadAnalytics() { analyticsLoading.value = true; try { analytics.value = await getQuickAnalytics(days.value) } catch { ElMessage.error('训练统计加载失败') } finally { analyticsLoading.value = false } }
function edit(row: QuickCalcMethod) {
  currentId.value = row.id
  Object.assign(form, { ...row, config: { min: row.config.min ?? 1000, max: row.config.max ?? 9000, difficulty: row.config.difficulty ?? 2 } })
  editVisible.value = true
}
async function save() {
  if (form.config.min >= form.config.max) { ElMessage.error('数值上限必须大于下限'); return }
  saving.value = true
  try { await saveQuickMethod({ ...form }, currentId.value); editVisible.value = false; ElMessage.success('已保存为草稿，请预览校验后发布'); await loadMethods() }
  catch { ElMessage.error('训练方法保存失败') }
  finally { saving.value = false }
}
async function preview(row: QuickCalcMethod) {
  try { previewResult.value = await previewQuickMethod(row.id); previewVisible.value = true }
  catch { ElMessage.error('样题生成或规则校验失败') }
}
async function publish(row: QuickCalcMethod) {
  try { await ElMessageBox.confirm(`发布「${row.name}」的新版本？发布后学员端将使用该规则出题。`, '发布确认') }
  catch { return }
  try { await publishQuickMethod(row.id); ElMessage.success('规则已发布'); await loadMethods() }
  catch { ElMessage.error('规则发布失败，请先检查样题和启用状态') }
}
async function showVersions(row: QuickCalcMethod) {
  versionsMethodId.value = row.id
  activeVersion.value = row.version
  try { versions.value = await listQuickMethodVersions(row.id); versionsVisible.value = true }
  catch { ElMessage.error('版本记录加载失败') }
}
async function rollback(version: number) {
  try { await ElMessageBox.confirm(`将以已发布 v${version} 的规则内容创建并发布新版本，继续吗？`, '回滚确认') }
  catch { return }
  try {
    await rollbackQuickMethod(versionsMethodId.value, version)
    ElMessage.success('已按历史规则创建新发布版本')
    versionsVisible.value = false
    await loadMethods()
  } catch { ElMessage.error('历史规则回滚失败') }
}
function wrongLabel(items: Record<string, number>) { return Object.entries(items || {}).map(([k, v]) => `${k}：${v}`).join(' · ') || '暂无错选' }
function renderFormula(source: string) {
  try { return katex.renderToString(source || '', { throwOnError: false, output: 'html' }) }
  catch { return source || '（无公式）' }
}
onMounted(() => { void loadMethods(); void loadAnalytics() })
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
.setup-guide { margin-bottom: 14px; }
.advanced-settings { width: calc(100% - 120px); margin: 0 0 8px 120px; }
.tip { color: var(--el-text-color-secondary); font-size: 13px; }
.preview-card { margin-top: 14px; }
.preview-meta { margin-top: 14px; }
.formula { margin: 12px 0; font-family: ui-monospace, monospace; font-size: 16px; }
.plain { color: var(--el-text-color-secondary); font-size: 13px; }
li { margin: 8px 0; }
.answer { color: var(--el-color-success); font-weight: 600; }
.answer .el-tag { margin-left: 8px; }
</style>
