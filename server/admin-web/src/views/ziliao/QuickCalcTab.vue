<template>
  <div>
    <el-tabs v-model="subTab">
      <el-tab-pane label="训练题型" name="methods">
        <el-alert
          class="setup-guide"
          title="按题型管理训练；解题方法由每道题的解析给出。"
          description="训练按概念管理，题目形式由系统组合：分数比较包含两数比较、四数选极值和完整排序；增长量、增长率、基期量穿插计算题与四项计算辨析。预览会校验唯一答案和计算逻辑，学员答后查看逐项解析。"
          type="info"
          :closable="false"
          show-icon
        />
        <div class="toolbar">
          <el-button @click="loadMethods">刷新</el-button>
          <span class="tip">修改已发布题型会生成草稿；校验通过后再发布新版本。</span>
        </div>
        <el-table :data="methods" v-loading="loading" row-key="id">
          <el-table-column prop="name" label="训练题型" min-width="130" />
          <el-table-column prop="category" label="类型" width="90" />
          <el-table-column prop="scene" label="题目范围" min-width="240" show-overflow-tooltip />
          <el-table-column label="规则范围" width="140">
            <template #default="{ row }">{{ row.config.min }}–{{ row.config.max }}</template>
          </el-table-column>
          <el-table-column label="状态" width="220">
            <template #default="{ row }">
              <el-tag :type="row.status === 'published' ? 'success' : 'warning'">{{ row.status === 'published' ? `已发布 v${row.version}` : '草稿' }}</el-tag>
              <el-tooltip v-if="row.knowledgeStatus !== 'ready'" :content="row.knowledgeMessage" placement="top">
                <el-tag class="validation-tag" :type="row.knowledgeDraftResolved ? 'warning' : 'danger'">{{ knowledgeStatusLabel(row.knowledgeStatus) }}</el-tag>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="edit(row)">编辑</el-button>
              <el-button link type="primary" @click="preview(row)">预览校验</el-button>
              <el-button link type="primary" @click="showVersions(row)">版本</el-button>
              <el-tooltip :content="row.knowledgeMessage" :disabled="row.knowledgeResolved" placement="top">
                <span class="publish-button-wrap"><el-button link type="success" :disabled="!row.enabled || row.status === 'published' || !row.knowledgeResolved" @click="publish(row)">发布</el-button></span>
              </el-tooltip>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="训练效果" name="analytics">
        <el-alert
          class="setup-guide"
          title="查看学员已完成的速算训练表现"
          description="按时间范围汇总答题数、正确率、平均用时和错选分布，并按题目形式查看正确率与平均用时，便于发现薄弱题型并调整训练内容；数据是练习表现统计，帮助安排后续专项练习。"
          type="info"
          :closable="false"
          show-icon
        />
        <div class="toolbar">
          <el-select v-model="days" style="width: 140px" @change="loadAnalytics">
            <el-option :value="7" label="最近 7 天" /><el-option :value="30" label="最近 30 天" /><el-option :value="90" label="最近 90 天" />
          </el-select>
          <el-button @click="loadAnalytics">刷新</el-button>
          <span>完成训练 {{ analytics.sessions }} 组 · 答题 {{ analytics.attempts }} 题</span>
        </div>
        <el-table :data="analytics.methods" v-loading="analyticsLoading" row-key="method">
          <el-table-column prop="name" label="训练题型" min-width="140" />
          <el-table-column prop="attempts" label="答题数" width="100" />
          <el-table-column prop="accuracy" label="正确率" width="110"><template #default="{ row }">{{ row.accuracy }}%</template></el-table-column>
          <el-table-column prop="averageSeconds" label="平均用时" width="110"><template #default="{ row }">{{ row.averageSeconds }} 秒</template></el-table-column>
          <el-table-column label="解析建议方法" min-width="210"><template #default="{ row }">{{ strategyLabel(row.strategyCounts) }}</template></el-table-column>
          <el-table-column label="题目形式表现" min-width="260"><template #default="{ row }">{{ formPerformanceLabel(row.formPerformance) }}</template></el-table-column>
          <el-table-column label="错选分布" min-width="180"><template #default="{ row }">{{ wrongLabel(row.wrongOptions) }}</template></el-table-column>
        </el-table>
          <el-empty v-if="!analyticsLoading && !analytics.methods.length" description="所选时间段暂无已完成训练" />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="editVisible" title="编辑训练题型" width="680px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="题型名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="题型类别"><el-select v-model="form.category"><el-option label="比较" value="比较" /><el-option label="计算" value="计算" /></el-select></el-form-item>
        <el-form-item label="适用场景"><el-input v-model="form.scene" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="启用训练"><el-switch v-model="form.enabled" /></el-form-item>
        <el-collapse class="advanced-settings">
          <el-collapse-item title="高级设置（通常无需调整）" name="advanced">
            <el-form-item label="知识框架路径"><el-input v-model="form.knowledgePath" /></el-form-item>
            <el-form-item label="知识节点标题"><el-input v-model="form.nodeTitle" /></el-form-item>
            <el-form-item label="上级节点"><el-input v-model="form.nodeParent" /></el-form-item>
            <template v-if="['fraction-compare', 'base'].includes(form.code)">
              <el-form-item label="基础数值下限"><el-input-number v-model="form.config.min" :min="100" :max="99900" :step="100" /></el-form-item>
              <el-form-item label="基础数值上限"><el-input-number v-model="form.config.max" :min="200" :max="100000" :step="100" /></el-form-item>
            </template>
            <el-alert v-else title="此题型使用带来源的真实统计样本；难度控制抽取范围，基础数值上下限不适用。" type="info" :closable="false" />
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
        <template #header><b>{{ index + 1 }}. <el-tag size="small" effect="plain">{{ questionFormLabel(q.questionForm) }}</el-tag> {{ q.stem }}</b></template>
        <div class="formula" v-html="renderFormula(q.latex)" />
        <div class="plain">{{ q.plain }}</div>
        <div v-if="q.source?.sourceType" class="preview-source">
          <el-tag size="small" effect="plain">{{ sourceTypeLabel(q.source.sourceType) }}</el-tag>
          <span v-if="q.source.sourceLabel">{{ q.source.sourceLabel }}</span>
          <span v-else>按题型规则生成的教学模拟数据</span>
          <a
            v-for="url in q.source.sourceUrls || []"
            :key="url"
            :href="url"
            target="_blank"
            rel="noopener noreferrer"
          >查看来源</a>
        </div>
        <ol><li v-for="(option, i) in q.options" :key="i" :class="i === q.answer ? 'answer' : ''">{{ option }}<el-tag v-if="i === q.answer" type="success" size="small">正确答案</el-tag></li></ol>
        <h4 class="solution-heading">解题方法与公式</h4>
        <div v-for="step in q.steps" :key="step.text" class="solution-step">
          <p>{{ step.text }}</p>
          <div v-if="step.latex" class="step-formula" v-html="renderFormula(step.latex)" />
        </div>
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

function errorMessage(error: unknown, fallback: string) { return error instanceof Error ? error.message : fallback }
function knowledgeStatusLabel(status: QuickCalcMethod['knowledgeStatus']) {
  const labels: Record<QuickCalcMethod['knowledgeStatus'], string> = {
    ready: '知识关联正常', tree_unpublished: '知识框架待发布', tree_hidden: '知识树未开放',
    node_unpublished: '节点待上线', tree_missing: '知识树未导入', node_missing: '关联节点缺失', missing: '关联路径无效',
  }
  return labels[status] || '关联状态未知'
}
async function loadMethods() { loading.value = true; try { methods.value = await listQuickMethods() } catch (error) { ElMessage.error(errorMessage(error, '训练题型加载失败')) } finally { loading.value = false } }
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
  catch (error) { ElMessage.error(errorMessage(error, '训练题型保存失败')) }
  finally { saving.value = false }
}
async function preview(row: QuickCalcMethod) {
  try { previewResult.value = await previewQuickMethod(row.id); previewVisible.value = true }
  catch (error) { ElMessage.error(errorMessage(error, '样题生成或规则校验失败')) }
}
async function publish(row: QuickCalcMethod) {
  try { await ElMessageBox.confirm(`发布「${row.name}」的新版本？发布后学员端将使用该规则出题。`, '发布确认') }
  catch { return }
  try { await publishQuickMethod(row.id); ElMessage.success('规则已发布'); await loadMethods() }
  catch (error) { ElMessage.error(errorMessage(error, '规则发布失败')) }
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
function strategyLabel(items: Record<string, number>) { return Object.entries(items || {}).map(([k, v]) => `${k} ${v}题`).join(' · ') || '暂无记录' }
function sourceTypeLabel(type: string) {
  const labels: Record<string, string> = {
    'official-statistics-adaptation': '官方统计数据改编',
    'exam-data-adaptation': '真题数据改编（非原题复刻）',
    'teaching-simulation': '教学模拟',
  }
  return labels[type] || '来源待核'
}
function formPerformanceLabel(items: Record<string, { attempts: number; accuracy: number; averageSeconds: number }>) {
  return Object.entries(items || {}).map(([form, stats]) => `${form}：${stats.accuracy}%/${stats.averageSeconds}秒（${stats.attempts}题）`).join('；') || '暂无记录'
}
function questionFormLabel(form?: string) {
  const labels: Record<string, string> = {
    pair: '两个分数比较', 'multi-extrema': '多分数选极值', 'multi-sort': '多分数排序',
    calculation: '直接计算', 'calculation-correct': '计算辨析·选正确项', 'calculation-incorrect': '计算辨析·选错误项',
    'material-correct': '综合材料·选正确项', 'material-incorrect': '综合材料·选错误项',
    'share-current': '现期比重', 'share-base': '基期比重', 'share-change': '两期比重差',
    'average-current': '单位平均数', 'average-change': '平均数变化量', 'average-growth': '平均数增长率',
    'multiple-current': '现期倍数', 'multiple-base': '基期倍数', 'multiple-excess': '多几倍辨析',
    'mixed-rate': '加权混合增长率', 'interval-growth': '隔年增长率', 'annual-growth': '年均增长率',
    'annual-amount': '年均增长量', 'contribution-rate': '贡献率', 'growth-pull': '拉动百分点',
  }
  return labels[form || ''] || '计算题'
}
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
.validation-tag { margin-left: 6px; }
.publish-button-wrap { display: inline-flex; }
.formula { margin: 12px 0; font-family: ui-monospace, monospace; font-size: 16px; }
.solution-step p { margin-bottom: 4px; }
.solution-heading { margin: 16px 0 8px; color: var(--el-text-color-primary); font-size: 14px; }
.step-formula { margin: 4px 0 12px; overflow-x: auto; }
.plain { color: var(--el-text-color-secondary); font-size: 13px; }
.preview-source { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 8px; color: var(--el-text-color-secondary); font-size: 13px; }
.preview-source a { color: var(--el-color-primary); }
li { margin: 8px 0; }
.answer { color: var(--el-color-success); font-weight: 600; }
.answer .el-tag { margin-left: 8px; }
</style>
