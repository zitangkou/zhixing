<template>
  <div class="page">
    <div class="heading">
      <div><h2>摄影学习内容管理</h2><p>维护学员端技巧课程与五阶段摄影知识地图。</p></div>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-row :gutter="14" class="stats">
      <el-col :span="8"><el-card shadow="never"><div class="metric"><span>知识阶段</span><strong>{{ summary.stages }}</strong></div></el-card></el-col>
      <el-col :span="8"><el-card shadow="never"><div class="metric"><span>技巧课程</span><strong>{{ summary.lessons }}</strong></div></el-card></el-col>
      <el-col :span="8"><el-card shadow="never"><div class="metric"><span>已发布课程</span><strong>{{ summary.publishedLessons }}</strong></div></el-card></el-col>
    </el-row>

    <el-tabs v-model="activeTab" class="content-tabs">
      <el-tab-pane label="技巧课程" name="courses">
        <div class="toolbar">
          <el-select v-model="stageFilter" clearable placeholder="全部知识阶段" style="width:220px"><el-option v-for="stage in stages" :key="stage.id" :label="stage.title" :value="stage.id" /></el-select>
          <el-input v-model="query" clearable placeholder="搜索标题、原理或拍摄任务" style="width:280px" />
          <el-button v-if="canWrite" type="primary" @click="editLesson()">新增技巧课</el-button>
        </div>
        <el-table :data="filteredLessons" v-loading="loading" row-key="id">
          <el-table-column prop="sortOrder" label="排序" width="72" />
          <el-table-column prop="title" label="课程标题" min-width="200" />
          <el-table-column prop="category" label="主题" width="100" />
          <el-table-column label="知识阶段" min-width="130"><template #default="{ row }">{{ stageName(row.stageId) }}</template></el-table-column>
          <el-table-column prop="durationMin" label="分钟" width="78" />
          <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.isPublished ? 'success' : 'info'">{{ row.isPublished ? '已发布' : '草稿' }}</el-tag></template></el-table-column>
          <el-table-column label="操作" width="150" fixed="right"><template #default="{ row }"><el-button v-if="canWrite" link type="primary" @click="editLesson(row)">编辑</el-button><el-button v-if="canWrite" link type="danger" @click="removeLesson(row)">删除</el-button></template></el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="知识地图" name="map">
        <div class="toolbar"><span class="hint">发布的阶段会出现在小程序知识地图中。</span><el-button v-if="canWrite" type="primary" @click="editStage()">新增阶段</el-button></div>
        <el-table :data="stages" v-loading="loading" row-key="id">
          <el-table-column prop="sortOrder" label="排序" width="80" />
          <el-table-column prop="title" label="阶段名称" width="180" />
          <el-table-column prop="items" label="知识主题" min-width="270" />
          <el-table-column prop="description" label="阶段说明" min-width="250" />
          <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.isPublished ? 'success' : 'info'">{{ row.isPublished ? '已发布' : '隐藏' }}</el-tag></template></el-table-column>
          <el-table-column label="操作" width="150" fixed="right"><template #default="{ row }"><el-button v-if="canWrite" link type="primary" @click="editStage(row)">编辑</el-button><el-button v-if="canWrite" link type="danger" @click="removeStage(row)">删除</el-button></template></el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="stageDialog" :title="stageForm.id ? '编辑知识阶段' : '新增知识阶段'" width="560px">
      <el-form label-width="100px"><el-form-item label="阶段名称"><el-input v-model="stageForm.title" maxlength="128" /></el-form-item><el-form-item label="知识主题"><el-input v-model="stageForm.items" maxlength="512" placeholder="例如：光线方向 · 光质 · 色温" /></el-form-item><el-form-item label="阶段说明"><el-input v-model="stageForm.description" type="textarea" :rows="3" /></el-form-item><el-form-item label="排序"><el-input-number v-model="stageForm.sortOrder" :min="0" /></el-form-item><el-form-item label="发布"><el-switch v-model="stageForm.isPublished" /></el-form-item></el-form>
      <template #footer><el-button @click="stageDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveStage">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="lessonDialog" :title="lessonForm.id ? '编辑技巧课' : '新增技巧课'" width="760px">
      <el-form label-width="110px">
        <el-form-item label="知识阶段"><el-select v-model="lessonForm.stageId" style="width:100%"><el-option v-for="stage in stages" :key="stage.id" :label="stage.title" :value="stage.id" /></el-select></el-form-item>
        <el-row :gutter="12"><el-col :span="15"><el-form-item label="课程标题"><el-input v-model="lessonForm.title" maxlength="160" /></el-form-item></el-col><el-col :span="9"><el-form-item label="主题分类"><el-input v-model="lessonForm.category" maxlength="64" /></el-form-item></el-col></el-row>
        <el-form-item label="副标题"><el-input v-model="lessonForm.subtitle" maxlength="256" /></el-form-item>
        <el-row :gutter="12"><el-col :span="8"><el-form-item label="难度"><el-select v-model="lessonForm.level" style="width:100%"><el-option label="入门" value="入门" /><el-option label="进阶" value="进阶" /></el-select></el-form-item></el-col><el-col :span="8"><el-form-item label="时长（分）"><el-input-number v-model="lessonForm.durationMin" :min="1" :max="240" /></el-form-item></el-col><el-col :span="8"><el-form-item label="排序"><el-input-number v-model="lessonForm.sortOrder" :min="0" /></el-form-item></el-col></el-row>
        <el-form-item label="原理说明"><el-input v-model="lessonForm.principle" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="练习步骤"><el-input v-model="stepsText" type="textarea" :rows="4" placeholder="每行一条练习步骤" /></el-form-item>
        <el-form-item label="拍摄任务"><el-input v-model="lessonForm.task" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="复盘提示"><el-input v-model="lessonForm.review" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="发布到小程序"><el-switch v-model="lessonForm.isPublished" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="lessonDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveLesson">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type { PhotographyLesson, PhotographyStage } from '@/api/photography'
import { deletePhotographyLesson, deletePhotographyStage, fetchPhotographyLessons, fetchPhotographyStages, fetchPhotographySummary, savePhotographyLesson, savePhotographyStage } from '@/api/photography'

const auth = useAuthStore()
const route = useRoute()
const canWrite = computed(() => auth.permissions.includes('*') || auth.permissions.includes('photography:write'))
const loading = ref(false); const saving = ref(false)
const activeTab = ref(route.path.endsWith('/map') ? 'map' : 'courses')
const summary = reactive({ stages: 0, lessons: 0, publishedLessons: 0 })
const stages = ref<PhotographyStage[]>([]); const lessons = ref<PhotographyLesson[]>([])
const stageFilter = ref(''); const query = ref('')
const stageDialog = ref(false); const lessonDialog = ref(false)
const stageForm = reactive({ id: '', title: '', items: '', description: '', sortOrder: 0, isPublished: true })
const lessonForm = reactive({ id: '', stageId: '', category: '光线', title: '', subtitle: '', level: '入门', durationMin: 10, principle: '', task: '', review: '', sortOrder: 0, isPublished: false })
const stepsText = ref('')
const filteredLessons = computed(() => lessons.value.filter((row) => (!stageFilter.value || row.stageId === stageFilter.value) && `${row.title} ${row.category} ${row.principle} ${row.task}`.toLowerCase().includes(query.value.toLowerCase())))
function stageName(id: string) { return stages.value.find((row) => row.id === id)?.title || '—' }
async function load() {
  loading.value = true
  try { const [stageRows, lessonRows, stats] = await Promise.all([fetchPhotographyStages(), fetchPhotographyLessons(), fetchPhotographySummary()]); stages.value = stageRows; lessons.value = lessonRows; Object.assign(summary, stats) }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '摄影学习内容加载失败') }
  finally { loading.value = false }
}
function editStage(row?: PhotographyStage) { Object.assign(stageForm, row || { id: '', title: '', items: '', description: '', sortOrder: stages.value.length + 1, isPublished: true }); stageDialog.value = true }
function editLesson(row?: PhotographyLesson) { Object.assign(lessonForm, row || { id: '', stageId: stages.value[0]?.id || '', category: '光线', title: '', subtitle: '', level: '入门', durationMin: 10, principle: '', task: '', review: '', sortOrder: lessons.value.length + 1, isPublished: false }); stepsText.value = row?.steps.join('\n') || ''; lessonDialog.value = true }
async function saveStage() {
  if (!stageForm.title.trim()) return ElMessage.warning('请填写阶段名称')
  saving.value = true
  try { const { id, ...data } = stageForm; await savePhotographyStage(data, id || undefined); stageDialog.value = false; ElMessage.success('知识阶段已保存'); await load() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') } finally { saving.value = false }
}
async function saveLesson() {
  if (!lessonForm.stageId || !lessonForm.title.trim() || !lessonForm.principle.trim() || !lessonForm.task.trim()) return ElMessage.warning('请填写所属阶段、标题、原理和拍摄任务')
  const steps = stepsText.value.split('\n').map((item) => item.trim()).filter(Boolean)
  if (!steps.length) return ElMessage.warning('请至少填写一条练习步骤')
  saving.value = true
  try { const { id, ...data } = lessonForm; await savePhotographyLesson({ ...data, steps }, id || undefined); lessonDialog.value = false; ElMessage.success('技巧课已保存'); await load() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败') } finally { saving.value = false }
}
async function removeStage(row: PhotographyStage) {
  try { await ElMessageBox.confirm(`确定删除知识阶段「${row.title}」？`, '删除阶段', { type: 'warning' }); await deletePhotographyStage(row.id); ElMessage.success('阶段已删除'); await load() }
  catch (error) { if (error !== 'cancel') ElMessage.error(error instanceof Error ? error.message : '删除失败') }
}
async function removeLesson(row: PhotographyLesson) {
  try { await ElMessageBox.confirm(`确定删除技巧课「${row.title}」？`, '删除课程', { type: 'warning' }); await deletePhotographyLesson(row.id); ElMessage.success('课程已删除'); await load() }
  catch (error) { if (error !== 'cancel') ElMessage.error(error instanceof Error ? error.message : '删除失败') }
}
watch(() => route.path, (path) => { activeTab.value = path.endsWith('/map') ? 'map' : 'courses' })
onMounted(load)
</script>

<style scoped>
.heading { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px; }
.heading h2 { margin:0 0 7px; font-size:20px; }
.heading p,.hint { margin:0; color:#77817d; font-size:13px; }
.stats { margin-bottom:16px; }
.metric { display:flex; flex-direction:column; gap:9px; color:#71807a; }
.metric strong { color:#315e52; font-size:25px; }
.content-tabs { min-height:460px; padding:0 16px 18px; border-radius:8px; background:#fff; }
.toolbar { display:flex; align-items:center; gap:10px; margin:12px 0 16px; }
.toolbar .el-button { margin-left:auto; }
</style>
