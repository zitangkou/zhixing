<template>
  <div class="page">
    <div class="intro">
      <div>
        <h2>言遇英语 · 内容工作台</h2>
        <p>管理场景课程和练习内容。只有已发布的场景与单元会出现在学员端。</p>
      </div>
      <el-button :loading="loading" @click="load">刷新数据</el-button>
    </div>

    <el-row :gutter="16" class="stats">
      <el-col :span="6"><el-card shadow="never"><div class="stat"><span>场景</span><strong>{{ summary.scenes }}</strong></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat"><span>课程单元</span><strong>{{ summary.units }}</strong></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat"><span>已发布</span><strong>{{ summary.publishedUnits }}</strong></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat"><span>学习完成</span><strong>{{ summary.completions }}</strong></div></el-card></el-col>
    </el-row>

    <el-tabs v-model="activeTab" class="content-tabs">
      <el-tab-pane label="场景管理" name="scenes">
        <div class="toolbar"><el-input v-model="sceneQuery" clearable placeholder="搜索场景" style="width: 240px" /><el-button v-if="canWrite" type="primary" @click="editScene()">新增场景</el-button></div>
        <el-table :data="filteredScenes" v-loading="loading" row-key="id">
          <el-table-column prop="sortOrder" label="排序" width="80" />
          <el-table-column prop="title" label="场景名称" min-width="180" />
          <el-table-column prop="level" label="建议等级" width="140" />
          <el-table-column prop="description" label="简介" min-width="240" show-overflow-tooltip />
          <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.isPublished ? 'success' : 'info'">{{ row.isPublished ? '已发布' : '草稿' }}</el-tag></template></el-table-column>
          <el-table-column label="操作" width="180" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="showUnits(row)">课程</el-button><el-button v-if="canWrite" link type="primary" @click="editScene(row)">编辑</el-button><el-button v-if="canWrite" link type="danger" @click="removeScene(row)">删除</el-button></template></el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="课程单元" name="units">
        <div class="toolbar"><el-select v-model="unitSceneFilter" clearable placeholder="全部场景" style="width: 220px"><el-option v-for="scene in scenes" :key="scene.id" :label="scene.title" :value="scene.id" /></el-select><el-input v-model="unitQuery" clearable placeholder="搜索课程" style="width: 220px" /><el-button v-if="canWrite" type="primary" @click="editUnit()">新增课程</el-button></div>
        <el-table :data="filteredUnits" v-loading="loading" row-key="id">
          <el-table-column prop="sortOrder" label="排序" width="80" />
          <el-table-column prop="title" label="课程名称" min-width="190" />
          <el-table-column label="所属场景" min-width="160"><template #default="{ row }">{{ sceneName(row.sceneId) }}</template></el-table-column>
          <el-table-column prop="level" label="等级" width="110" />
          <el-table-column prop="durationMin" label="分钟" width="85" />
          <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.isPublished ? 'success' : 'info'">{{ row.isPublished ? '已发布' : '草稿' }}</el-tag></template></el-table-column>
          <el-table-column label="操作" width="140" fixed="right"><template #default="{ row }"><el-button v-if="canWrite" link type="primary" @click="editUnit(row)">编辑</el-button><el-button v-if="canWrite" link type="danger" @click="removeUnit(row)">删除</el-button></template></el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="sceneDialog" :title="sceneForm.id ? '编辑场景' : '新增场景'" width="560px">
      <el-form label-width="100px"><el-form-item label="场景名称"><el-input v-model="sceneForm.title" maxlength="128" /></el-form-item><el-form-item label="简介"><el-input v-model="sceneForm.description" type="textarea" :rows="2" /></el-form-item><el-form-item label="等级"><el-select v-model="sceneForm.level"><el-option v-for="level in levels" :key="level" :value="level" :label="level" /></el-select></el-form-item><el-form-item label="排序"><el-input-number v-model="sceneForm.sortOrder" :min="0" /></el-form-item><el-form-item label="发布"><el-switch v-model="sceneForm.isPublished" /></el-form-item></el-form>
      <template #footer><el-button @click="sceneDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveScene">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="unitDialog" :title="unitForm.id ? '编辑课程' : '新增课程'" width="720px">
      <el-form label-width="110px"><el-form-item label="所属场景"><el-select v-model="unitForm.sceneId" style="width:100%"><el-option v-for="scene in scenes" :key="scene.id" :label="scene.title" :value="scene.id" /></el-select></el-form-item><el-form-item label="课程名称"><el-input v-model="unitForm.title" maxlength="128" /></el-form-item><el-form-item label="学习目标"><el-input v-model="unitForm.goal" type="textarea" :rows="2" /></el-form-item><el-row :gutter="12"><el-col :span="8"><el-form-item label="等级"><el-select v-model="unitForm.level" style="width:100%"><el-option v-for="level in levels" :key="level" :value="level" :label="level" /></el-select></el-form-item></el-col><el-col :span="8"><el-form-item label="时长"><el-input-number v-model="unitForm.durationMin" :min="1" :max="180" /></el-form-item></el-col><el-col :span="8"><el-form-item label="排序"><el-input-number v-model="unitForm.sortOrder" :min="0" /></el-form-item></el-col></el-row><el-form-item label="课程内容 JSON"><el-input v-model="unitContentText" type="textarea" :rows="12" placeholder="{ &quot;dialogueAudioUrl&quot;: &quot;...&quot;, &quot;dialogue&quot;: [], &quot;phrases&quot;: [], &quot;prompt&quot;: &quot;...&quot; }" /></el-form-item><el-form-item label="发布"><el-switch v-model="unitForm.isPublished" /></el-form-item></el-form>
      <template #footer><el-button @click="unitDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveUnit">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type { EnglishScene, EnglishUnit } from '@/api/english'
import { deleteEnglishScene, deleteEnglishUnit, fetchEnglishScenes, fetchEnglishSummary, fetchEnglishUnits, saveEnglishScene, saveEnglishUnit } from '@/api/english'

const auth = useAuthStore()
const canWrite = computed(() => auth.permissions.includes('*') || auth.permissions.includes('english:write'))
const loading = ref(false); const saving = ref(false); const activeTab = ref('scenes')
const scenes = ref<EnglishScene[]>([]); const units = ref<EnglishUnit[]>([])
const summary = reactive({ scenes: 0, units: 0, publishedUnits: 0, completions: 0 })
const sceneQuery = ref(''); const unitQuery = ref(''); const unitSceneFilter = ref('')
const sceneDialog = ref(false); const unitDialog = ref(false)
const levels = ['A1 入门', 'A2 日常', 'B1 进阶']
const sceneForm = reactive({ id: '', title: '', description: '', level: 'A1 入门', sortOrder: 0, isPublished: false })
const unitForm = reactive({ id: '', sceneId: '', title: '', level: 'A1 入门', durationMin: 8, goal: '', sortOrder: 0, isPublished: false })
const unitContentText = ref('{\n  "dialogueAudioUrl": "",\n  "dialogue": [],\n  "phrases": [],\n  "prompt": ""\n}')
const filteredScenes = computed(() => scenes.value.filter((row) => `${row.title} ${row.description}`.toLowerCase().includes(sceneQuery.value.toLowerCase())))
const filteredUnits = computed(() => units.value.filter((row) => (!unitSceneFilter.value || row.sceneId === unitSceneFilter.value) && `${row.title} ${row.goal}`.toLowerCase().includes(unitQuery.value.toLowerCase())))
function sceneName(id: string) { return scenes.value.find((row) => row.id === id)?.title || '—' }
async function load() {
  loading.value = true
  try {
    const [s, u, stats] = await Promise.all([fetchEnglishScenes(), fetchEnglishUnits(), fetchEnglishSummary()])
    scenes.value = s; units.value = u; Object.assign(summary, stats)
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '英语学习数据加载失败') }
  finally { loading.value = false }
}
function editScene(row?: EnglishScene) { Object.assign(sceneForm, row || { id: '', title: '', description: '', level: 'A1 入门', sortOrder: scenes.value.length + 1, isPublished: false }); sceneDialog.value = true }
function showUnits(row: EnglishScene) { unitSceneFilter.value = row.id; activeTab.value = 'units' }
async function saveScene() {
  if (!sceneForm.title.trim()) return ElMessage.warning('请填写场景名称')
  saving.value = true
  try { const { id, ...data } = sceneForm; await saveEnglishScene(data, id || undefined); sceneDialog.value = false; ElMessage.success('场景已保存'); await load() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') } finally { saving.value = false }
}
async function removeScene(row: EnglishScene) {
  try { await ElMessageBox.confirm(`确定删除场景「${row.title}」？`, '删除场景', { type: 'warning' }); await deleteEnglishScene(row.id); ElMessage.success('场景已删除'); await load() }
  catch (error) { if (error !== 'cancel') ElMessage.error(error instanceof Error ? error.message : '删除失败') }
}
function editUnit(row?: EnglishUnit) {
  Object.assign(unitForm, row || { id: '', sceneId: unitSceneFilter.value || scenes.value[0]?.id || '', title: '', level: 'A1 入门', durationMin: 8, goal: '', sortOrder: units.value.length + 1, isPublished: false })
  unitContentText.value = JSON.stringify(row?.content || { dialogueAudioUrl: '', dialogue: [], phrases: [], prompt: '' }, null, 2)
  unitDialog.value = true
}
async function saveUnit() {
  if (!unitForm.sceneId || !unitForm.title.trim()) return ElMessage.warning('请填写所属场景和课程名称')
  let content: Record<string, unknown>
  try { content = JSON.parse(unitContentText.value) as Record<string, unknown> } catch { return ElMessage.warning('课程内容必须是有效 JSON') }
  saving.value = true
  try { const { id, ...data } = unitForm; await saveEnglishUnit({ ...data, content }, id || undefined); unitDialog.value = false; ElMessage.success('课程已保存'); await load() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') } finally { saving.value = false }
}
async function removeUnit(row: EnglishUnit) {
  try { await ElMessageBox.confirm(`确定删除课程「${row.title}」？`, '删除课程', { type: 'warning' }); await deleteEnglishUnit(row.id); ElMessage.success('课程已删除'); await load() }
  catch (error) { if (error !== 'cancel') ElMessage.error(error instanceof Error ? error.message : '删除失败') }
}
onMounted(load)
</script>

<style scoped>
.intro { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:18px; }
.intro h2 { margin:0 0 8px; font-size:20px; }
.intro p { margin:0; color:#77817d; }
.stats { margin-bottom:18px; }
.stat { display:flex; flex-direction:column; gap:9px; color:#707b76; }
.stat strong { color:#256d73; font-size:25px; }
.content-tabs { background:#fff; padding:0 18px 18px; border-radius:8px; }
.toolbar { display:flex; gap:10px; margin:12px 0 16px; }
</style>
