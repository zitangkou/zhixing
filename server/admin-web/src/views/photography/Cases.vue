<template>
  <div class="page">
    <div class="heading"><div><h2>摄影作品案例</h2><p>维护有授权依据的案例，拆解可观察证据，并关联一项可执行练习。</p></div><el-button :loading="loading" @click="load">刷新</el-button></div>
    <el-alert title="当前为人工编辑和审核发布；此页面不会自动调用 AI，也不接收用户练习照片。" type="info" :closable="false" show-icon />
    <div class="toolbar"><el-input v-model="query" clearable placeholder="搜索案例标题、作者或主题" style="width:300px" /><el-button v-if="canWrite" type="primary" @click="edit()">新增案例</el-button></div>
    <el-table :data="filtered" v-loading="loading" row-key="id">
      <el-table-column prop="sortOrder" label="排序" width="70" /><el-table-column prop="title" label="案例标题" min-width="190" />
      <el-table-column prop="author" label="作者" width="120" /><el-table-column prop="category" label="主题" width="90" />
      <el-table-column prop="licenseType" label="授权类型" width="110" />
      <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.isPublished ? 'success' : 'info'">{{ row.isPublished ? '已发布' : '草稿' }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="145" fixed="right"><template #default="{ row }"><el-button v-if="canWrite" link type="primary" @click="edit(row)">编辑</el-button><el-button v-if="canWrite" link type="danger" @click="remove(row)">删除</el-button></template></el-table-column>
    </el-table>
    <el-dialog v-model="dialog" :title="form.id ? '编辑摄影案例' : '新增摄影案例'" width="900px" top="5vh">
      <el-scrollbar max-height="70vh"><el-form label-width="125px" class="case-form">
        <el-alert title="后台上传的图片由知行服务提供；直接填写外部图片地址时，需使用微信已配置的 HTTPS downloadFile 合法域名。发布前请核实作品授权。" type="warning" :closable="false" />
        <el-divider content-position="left">作品与授权</el-divider>
        <el-form-item label="案例标题"><el-input v-model="form.title" maxlength="160" /></el-form-item>
        <el-form-item label="案例图片"><div class="image-field"><el-upload accept="image/png,image/jpeg" :show-file-list="false" :http-request="uploadImage"><el-button :loading="uploading">上传 PNG / JPEG</el-button></el-upload><img v-if="imagePreview" :src="imagePreview" alt="案例图片预览"/><span v-else>单张不超过 5MB；图片将从知行服务域名提供。</span></div></el-form-item>
        <el-form-item label="作品来源 URL"><el-input v-model="form.sourceUrl" /></el-form-item>
        <el-row :gutter="12"><el-col :span="12"><el-form-item label="作者署名"><el-input v-model="form.author" /></el-form-item></el-col><el-col :span="12"><el-form-item label="授权类型"><el-select v-model="form.licenseType" style="width:100%"><el-option label="自有作品" value="自有作品"/><el-option label="已获授权" value="已获授权"/><el-option label="公共领域" value="公共领域"/><el-option label="其他许可" value="其他许可"/></el-select></el-form-item></el-col></el-row>
        <el-form-item label="授权范围/备注"><el-input v-model="form.licenseNote" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="12"><el-col :span="8"><el-form-item label="主题"><el-input v-model="form.category" /></el-form-item></el-col><el-col :span="8"><el-form-item label="难度"><el-select v-model="form.level" style="width:100%"><el-option label="入门" value="入门"/><el-option label="进阶" value="进阶"/></el-select></el-form-item></el-col><el-col :span="8"><el-form-item label="排序"><el-input-number v-model="form.sortOrder" :min="0" /></el-form-item></el-col></el-row>
        <el-divider content-position="left">作品拆解（每行一条观察）</el-divider>
        <el-form-item label="画面观察"><el-input v-model="observationsText" type="textarea" :rows="4" placeholder="只写图像直接呈现的内容和证据" /></el-form-item>
        <el-form-item label="EXIF 参数"><el-input v-model="exifText" type="textarea" :rows="3" placeholder="JSON 对象；没有 EXIF 留空，禁止填写猜测值" /></el-form-item>
        <el-form-item label="摄影推断"><el-input v-model="inferencesText" type="textarea" :rows="4" placeholder="每行一条：推断 | 画面证据 | 置信度（高/中/低）" /></el-form-item>
        <el-divider content-position="left">一个主练习与复盘标准</el-divider>
        <el-form-item label="练习标题"><el-input v-model="form.practiceTitle" /></el-form-item><el-form-item label="练习目标"><el-input v-model="form.practiceGoal" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="练习步骤"><el-input v-model="practiceStepsText" type="textarea" :rows="4" placeholder="每行一条，建议固定条件后只改变一个变量" /></el-form-item>
        <el-form-item label="主要变量"><el-input v-model="form.practiceVariable" /></el-form-item><el-form-item label="复盘标准"><el-input v-model="criteriaText" type="textarea" :rows="3" placeholder="每行一条可观察标准" /></el-form-item>
        <el-row :gutter="12"><el-col :span="8"><el-form-item label="预计分钟"><el-input-number v-model="form.durationMin" :min="1" :max="240" /></el-form-item></el-col><el-col :span="8"><el-form-item label="发布到小程序"><el-switch v-model="form.isPublished" /></el-form-item></el-col></el-row>
      </el-form></el-scrollbar>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { deletePhotographyCase, fetchPhotographyCases, savePhotographyCase, uploadPhotographyCaseImage, type PhotographyCase } from '@/api/photography'
import type { UploadRequestOptions } from 'element-plus'

const auth = useAuthStore()
const canWrite = computed(() => auth.permissions.includes('*') || auth.permissions.includes('photography:write'))
const rows = ref<PhotographyCase[]>([]); const loading = ref(false); const saving = ref(false); const dialog = ref(false); const query = ref('')
const observationsText = ref(''); const practiceStepsText = ref(''); const criteriaText = ref(''); const exifText = ref(''); const inferencesText = ref('')
const uploading = ref(false)
const empty = () => ({ id: '', title: '', imageUrl: '', sourceUrl: '', author: '', licenseType: '', licenseNote: '', category: '光线', level: '入门', observations: [] as string[], exif: {} as Record<string, string | number | null>, inferences: [] as PhotographyCase['inferences'], practiceTitle: '', practiceGoal: '', practiceSteps: [] as string[], practiceVariable: '', criteria: [] as string[], durationMin: 15, sortOrder: 0, isPublished: false })
const form = reactive(empty())
const filtered = computed(() => rows.value.filter((row) => `${row.title} ${row.author} ${row.category}`.toLowerCase().includes(query.value.toLowerCase())))
const imagePreview = computed(() => form.imageUrl.startsWith('/') ? `${window.location.origin}${form.imageUrl}` : form.imageUrl)
function lines(value: string) { return value.split('\n').map((line) => line.trim()).filter(Boolean) }
function parseInferences() { return lines(inferencesText.value).map((line) => { const [statement = '', evidence = '', confidence = '中'] = line.split('|').map((part) => part.trim()); return { statement, evidence, confidence } }) }
async function uploadImage(options: UploadRequestOptions) {
  if (options.file.size > 5 * 1024 * 1024) { ElMessage.warning('案例图片不能超过 5MB'); throw new Error('文件过大') }
  uploading.value = true
  try { const result = await uploadPhotographyCaseImage(options.file); form.imageUrl = result.url; ElMessage.success('案例图片已上传'); return result }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '图片上传失败'); throw error }
  finally { uploading.value = false }
}
async function load() { loading.value = true; try { rows.value = await fetchPhotographyCases() } catch (error) { ElMessage.error(error instanceof Error ? error.message : '案例加载失败') } finally { loading.value = false } }
function edit(row?: PhotographyCase) {
  Object.assign(form, empty(), row || { sortOrder: rows.value.length + 1 })
  observationsText.value = (row?.observations || []).join('\n'); practiceStepsText.value = (row?.practiceSteps || []).join('\n'); criteriaText.value = (row?.criteria || []).join('\n')
  exifText.value = row && Object.keys(row.exif).length ? JSON.stringify(row.exif, null, 2) : ''
  inferencesText.value = (row?.inferences || []).map((item) => `${item.statement} | ${item.evidence} | ${item.confidence}`).join('\n')
  dialog.value = true
}
async function save() {
  let exif: Record<string, string | number | null> = {}
  try { exif = exifText.value.trim() ? JSON.parse(exifText.value) : {}; if (!exif || Array.isArray(exif) || typeof exif !== 'object') throw new Error() } catch { return ElMessage.warning('EXIF 必须是 JSON 对象；未知参数请留空') }
  const observations = lines(observationsText.value); const practiceSteps = lines(practiceStepsText.value); const criteria = lines(criteriaText.value); const inferences = parseInferences()
  if (!form.title.trim() || !form.imageUrl.trim()) return ElMessage.warning('请填写案例标题和图片 URL')
  if (form.isPublished && (!form.sourceUrl.trim() || !form.author.trim() || !form.licenseType || !form.licenseNote.trim() || !observations.length || !form.practiceTitle.trim() || !form.practiceGoal.trim() || !practiceSteps.length || !form.practiceVariable.trim() || !criteria.length)) return ElMessage.warning('发布案例需补齐来源、署名授权、观察、练习目标/步骤/变量和复盘标准')
  saving.value = true
  try { const { id, ...rest } = form; await savePhotographyCase({ ...rest, observations, exif, inferences, practiceSteps, criteria }, id || undefined); dialog.value = false; ElMessage.success('案例已保存'); await load() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存案例失败') } finally { saving.value = false }
}
async function remove(row: PhotographyCase) { try { await ElMessageBox.confirm(`确定删除案例「${row.title}」？`, '删除案例', { type: 'warning' }); await deletePhotographyCase(row.id); ElMessage.success('案例已删除'); await load() } catch (error) { if (error !== 'cancel') ElMessage.error(error instanceof Error ? error.message : '删除失败') } }
onMounted(load)
</script>

<style scoped>
.heading{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px}.heading h2{margin:0 0 7px;font-size:20px}.heading p{margin:0;color:#77817d;font-size:13px}.toolbar{display:flex;gap:12px;margin:16px 0}.toolbar .el-button{margin-left:auto}.case-form{padding:8px 18px}.case-form :deep(.el-alert){margin-bottom:10px}.image-field{display:flex;align-items:center;gap:12px}.image-field img{width:120px;height:80px;object-fit:cover;border-radius:8px}.image-field span{color:#7b827d;font-size:12px}
</style>
