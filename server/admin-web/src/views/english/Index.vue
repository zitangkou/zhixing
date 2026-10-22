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
          <el-table-column label="素材" width="100"><template #default="{ row }">{{ mediaLabel(row) }}</template></el-table-column>
          <el-table-column label="授权" width="120"><template #default="{ row }"><el-tag :type="rightsTag(row)">{{ rightsLabel(row) }}</el-tag></template></el-table-column>
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
      <el-form label-width="110px"><el-form-item label="所属场景"><el-select v-model="unitForm.sceneId" style="width:100%"><el-option v-for="scene in scenes" :key="scene.id" :label="scene.title" :value="scene.id" /></el-select></el-form-item><el-form-item label="课程名称"><el-input v-model="unitForm.title" maxlength="128" /></el-form-item><el-form-item label="学习目标"><el-input v-model="unitForm.goal" type="textarea" :rows="2" /></el-form-item><el-row :gutter="12"><el-col :span="8"><el-form-item label="等级"><el-select v-model="unitForm.level" style="width:100%"><el-option v-for="level in levels" :key="level" :value="level" :label="level" /></el-select></el-form-item></el-col><el-col :span="8"><el-form-item label="时长"><el-input-number v-model="unitForm.durationMin" :min="1" :max="180" /></el-form-item></el-col><el-col :span="8"><el-form-item label="排序"><el-input-number v-model="unitForm.sortOrder" :min="0" /></el-form-item></el-col></el-row>
        <el-divider content-position="left">视听素材与授权</el-divider>
        <el-form-item label="媒体类型"><el-select v-model="mediaForm.type" style="width:100%"><el-option label="纯对话/文本" value="text" /><el-option label="音频" value="audio" /><el-option label="视频" value="video" /><el-option label="视频 + 音频" value="video_audio" /></el-select></el-form-item>
        <div class="media-upload-row"><el-button :loading="mediaUploading" @click="mediaInput?.click()">上传音频/视频文件</el-button><span>MP3、M4A、WAV、AAC、MP4、MOV；单文件不超过 80MB</span><input ref="mediaInput" class="hidden-input" type="file" accept=".mp3,.m4a,.wav,.aac,.mp4,.mov" @change="handleMediaUpload" /></div>
        <el-form-item v-if="mediaForm.type === 'audio' || mediaForm.type === 'video_audio'" label="音频 URL"><el-input v-model="mediaForm.audioUrl" placeholder="填写 HTTPS 音频地址" /></el-form-item>
        <el-form-item v-if="mediaForm.type === 'video' || mediaForm.type === 'video_audio'" label="视频 URL"><el-input v-model="mediaForm.videoUrl" placeholder="填写已获授权、可在小程序播放的视频地址" /></el-form-item>
        <el-form-item label="官方来源链接"><el-input v-model="mediaForm.sourceUrl" placeholder="用于来源记录；外链播放需另行验证小程序平台规则" /></el-form-item>
        <el-form-item label="素材授权"><el-select v-model="mediaForm.rightsStatus" style="width:100%"><el-option label="待核验" value="pending_review" /><el-option label="仅官方外链" value="link_only" /><el-option label="已获托管许可" value="licensed_hosting" /><el-option label="不可使用" value="rejected" /></el-select></el-form-item>
        <el-form-item label="素材说明"><el-input v-model="mediaForm.rightsNote" type="textarea" :rows="2" placeholder="授权凭证、许可范围或审核备注" /></el-form-item>
        <el-divider content-position="left">台词与逐句时间轴</el-divider>
        <div class="editor-head"><span>填写句子专属音频，或填写整段音频中的起止秒数。</span><div><el-button size="small" :disabled="!selectedMediaFile" :loading="subtitleTranscribing" @click="handleSubtitleTranscribe">自动生成字幕</el-button><el-button size="small" :loading="subtitleImporting" @click="subtitleInput?.click()">导入 SRT/VTT</el-button><el-button size="small" @click="addTranscriptLine">添加台词</el-button><input ref="subtitleInput" class="hidden-input" type="file" accept=".srt,.vtt" @change="handleSubtitleImport" /></div></div>
        <p class="asr-note">先选择并上传音视频，再可用同一文件生成字幕。自动转写支持 MP3、M4A、WAV、MP4（不超过 20MB），需配置服务端 ASR；素材会发送给配置的服务商，结果仅作待校对草稿。</p>
        <div v-for="(line, index) in transcriptLines" :key="index" class="transcript-line">
          <div class="line-heading"><strong>第 {{ index + 1 }} 句</strong><el-button link type="danger" @click="transcriptLines.splice(index, 1)">删除</el-button></div>
          <el-row :gutter="10"><el-col :span="5"><el-input v-model="line.speaker" placeholder="说话人" /></el-col><el-col :span="19"><el-input v-model="line.en" placeholder="英文台词" /></el-col></el-row>
          <el-input v-model="line.zh" class="line-zh" placeholder="中文释义" />
          <el-row :gutter="10"><el-col :span="14"><el-input v-model="line.audioUrl" placeholder="可选：该句独立音频 HTTPS URL" /></el-col><el-col :span="5"><el-input-number v-model="line.startSeconds" :min="0" :precision="2" :step="0.5" controls-position="right" /></el-col><el-col :span="5"><el-input-number v-model="line.endSeconds" :min="0" :precision="2" :step="0.5" controls-position="right" /></el-col></el-row>
        </div>
        <el-divider content-position="left">核心表达与开口任务</el-divider>
        <div class="editor-head"><span>每课建议选择 2–3 个可迁移表达。</span><el-button size="small" @click="addPhrase">添加表达</el-button></div>
        <div v-for="(phrase, index) in phraseLines" :key="index" class="phrase-line"><el-input v-model="phrase.en" placeholder="英文句块" /><el-input v-model="phrase.zh" placeholder="中文用法说明" /><el-button link type="danger" @click="phraseLines.splice(index, 1)">删除</el-button></div>
        <el-form-item label="自主表达任务"><el-input v-model="lessonPrompt" type="textarea" :rows="3" placeholder="用一个新情境引导学习者换信息表达" /></el-form-item>
        <el-collapse class="advanced-json"><el-collapse-item title="高级 JSON（扩展字段）" name="advanced"><p>台词、核心表达和自主表达任务以本表单为准；JSON 中的其他扩展字段会保留。</p><el-input v-model="unitContentText" type="textarea" :rows="10" /></el-collapse-item></el-collapse>
        <el-form-item label="发布"><el-switch v-model="unitForm.isPublished" /></el-form-item></el-form>
      <template #footer><el-button @click="unitDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveUnit">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type { EnglishScene, EnglishUnit } from '@/api/english'
import { deleteEnglishScene, deleteEnglishUnit, fetchEnglishScenes, fetchEnglishSubtitleJob, fetchEnglishSummary, fetchEnglishUnits, importEnglishSubtitles, saveEnglishScene, saveEnglishUnit, transcribeEnglishMedia, uploadEnglishMedia } from '@/api/english'

const auth = useAuthStore()
const canWrite = computed(() => auth.permissions.includes('*') || auth.permissions.includes('english:write'))
const loading = ref(false); const saving = ref(false); const activeTab = ref('scenes')
const mediaUploading = ref(false); const subtitleImporting = ref(false); const subtitleTranscribing = ref(false)
const mediaInput = ref<HTMLInputElement | null>(null); const subtitleInput = ref<HTMLInputElement | null>(null)
const selectedMediaFile = ref<File | null>(null)
const scenes = ref<EnglishScene[]>([]); const units = ref<EnglishUnit[]>([])
const summary = reactive({ scenes: 0, units: 0, publishedUnits: 0, completions: 0 })
const sceneQuery = ref(''); const unitQuery = ref(''); const unitSceneFilter = ref('')
const sceneDialog = ref(false); const unitDialog = ref(false)
const levels = ['A1 入门', 'A2 日常', 'B1 进阶']
const sceneForm = reactive({ id: '', title: '', description: '', level: 'A1 入门', sortOrder: 0, isPublished: false })
const unitForm = reactive({ id: '', sceneId: '', title: '', level: 'A1 入门', durationMin: 8, goal: '', sortOrder: 0, isPublished: false })
const unitContentText = ref('{\n  "dialogueAudioUrl": "",\n  "dialogue": [],\n  "phrases": [],\n  "prompt": ""\n}')
type TranscriptLine = { speaker: string; en: string; zh: string; audioUrl: string; startSeconds: number | null | undefined; endSeconds: number | null | undefined }
type PhraseLine = { en: string; zh: string }
const transcriptLines = ref<TranscriptLine[]>([])
const phraseLines = ref<PhraseLine[]>([])
const lessonPrompt = ref('')
const transcriptKey = ref<'transcript' | 'dialogue'>('dialogue')
const baseContent = ref<Record<string, unknown>>({})
const mediaForm = reactive({ type: 'text', audioUrl: '', videoUrl: '', posterUrl: '', sourceUrl: '', rightsStatus: 'pending_review', rightsNote: '', startSeconds: 0, endSeconds: 0 })
const filteredScenes = computed(() => scenes.value.filter((row) => `${row.title} ${row.description}`.toLowerCase().includes(sceneQuery.value.toLowerCase())))
const filteredUnits = computed(() => units.value.filter((row) => (!unitSceneFilter.value || row.sceneId === unitSceneFilter.value) && `${row.title} ${row.goal}`.toLowerCase().includes(unitQuery.value.toLowerCase())))
function sceneName(id: string) { return scenes.value.find((row) => row.id === id)?.title || '—' }
function mediaLabel(row: EnglishUnit) { const media = row.content.media as Record<string, unknown> | undefined; return media?.type === 'video_audio' ? '视频+音频' : media?.type === 'video' ? '视频' : media?.type === 'audio' || row.content.dialogueAudioUrl ? '音频' : '无' }
function rightsLabel(row: EnglishUnit) { const media = row.content.media as Record<string, unknown> | undefined; return ({ pending_review: '待核验', link_only: '仅外链', licensed_hosting: '已授权', rejected: '不可用' } as Record<string, string>)[String(media?.rightsStatus || '')] || '未设置' }
function rightsTag(row: EnglishUnit) { const media = row.content.media as Record<string, unknown> | undefined; return media?.rightsStatus === 'licensed_hosting' ? 'success' : media?.rightsStatus === 'rejected' ? 'danger' : 'warning' }
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
  selectedMediaFile.value = null
  Object.assign(unitForm, row || { id: '', sceneId: unitSceneFilter.value || scenes.value[0]?.id || '', title: '', level: 'A1 入门', durationMin: 8, goal: '', sortOrder: units.value.length + 1, isPublished: false })
  const content = row?.content || { dialogueAudioUrl: '', dialogue: [], phrases: [], prompt: '' }
  baseContent.value = JSON.parse(JSON.stringify(content)) as Record<string, unknown>
  transcriptKey.value = Array.isArray(content.transcript) ? 'transcript' : 'dialogue'
  const transcript = (content[transcriptKey.value] || []) as Record<string, unknown>[]
  transcriptLines.value = transcript.map((line) => ({ speaker: String(line.speaker || ''), en: String(line.en || ''), zh: String(line.zh || ''), audioUrl: String(line.audioUrl || ''), startSeconds: typeof line.startSeconds === 'number' ? line.startSeconds : undefined, endSeconds: typeof line.endSeconds === 'number' ? line.endSeconds : undefined }))
  phraseLines.value = Array.isArray(content.phrases) ? (content.phrases as Record<string, unknown>[]).map((phrase) => ({ en: String(phrase.en || ''), zh: String(phrase.zh || '') })) : []
  lessonPrompt.value = String(content.prompt || (content.tasks as Record<string, unknown> | undefined)?.roleplayPrompt || '')
  const media = (content.media || {}) as Record<string, unknown>
  Object.assign(mediaForm, { type: media.type || 'text', audioUrl: media.audioUrl || content.dialogueAudioUrl || '', videoUrl: media.videoUrl || '', posterUrl: media.posterUrl || '', sourceUrl: media.sourceUrl || '', rightsStatus: media.rightsStatus || 'pending_review', rightsNote: media.rightsNote || '', startSeconds: media.startSeconds || 0, endSeconds: media.endSeconds || 0 })
  unitContentText.value = JSON.stringify(content, null, 2)
  unitDialog.value = true
}
function addTranscriptLine() { transcriptLines.value.push({ speaker: '', en: '', zh: '', audioUrl: '', startSeconds: null, endSeconds: null }) }
function addPhrase() { phraseLines.value.push({ en: '', zh: '' }) }
async function handleMediaUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  mediaUploading.value = true
  try {
    const uploaded = await uploadEnglishMedia(file)
    const url = new URL(uploaded.url, window.location.origin).toString()
    selectedMediaFile.value = file
    if (uploaded.kind === 'audio') {
      mediaForm.audioUrl = url
      mediaForm.type = mediaForm.videoUrl ? 'video_audio' : 'audio'
    } else {
      mediaForm.videoUrl = url
      mediaForm.type = mediaForm.audioUrl ? 'video_audio' : 'video'
    }
    ElMessage.success('素材已上传；发布前请核验授权状态')
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '素材上传失败') }
  finally { mediaUploading.value = false }
}
async function handleSubtitleImport(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  subtitleImporting.value = true
  try {
    const imported = await importEnglishSubtitles(file)
    transcriptLines.value = imported.transcript.map((line) => ({ ...line, audioUrl: '' }))
    transcriptKey.value = 'transcript'
    ElMessage.success(`已导入 ${imported.count} 句字幕草稿，请逐句校对`)
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '字幕导入失败') }
  finally { subtitleImporting.value = false }
}
async function handleSubtitleTranscribe() {
  const file = selectedMediaFile.value
  if (!file) return
  if (file.size > 20 * 1024 * 1024) return ElMessage.warning('自动转写文件不能超过 20MB')
  subtitleTranscribing.value = true
  try {
    const task = await transcribeEnglishMedia(file)
    let result = await fetchEnglishSubtitleJob(task.id)
    for (let attempt = 0; attempt < 90 && (result.status === 'queued' || result.status === 'running'); attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 2000))
      result = await fetchEnglishSubtitleJob(task.id)
    }
    if (result.status === 'failed') throw new Error(result.errorMessage || '字幕生成失败')
    if (result.status !== 'succeeded') throw new Error('字幕生成耗时较长，请稍后重试；服务端不会自动发布该结果')
    transcriptLines.value = result.transcript.map((line) => ({ ...line, audioUrl: '' }))
    transcriptKey.value = 'transcript'
    ElMessage.success(`已生成 ${result.count} 句字幕草稿，请逐句校对`)
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '自动转写失败') }
  finally { subtitleTranscribing.value = false }
}
async function saveUnit() {
  if (!unitForm.sceneId || !unitForm.title.trim()) return ElMessage.warning('请填写所属场景和课程名称')
  let content: Record<string, unknown>
  try { content = JSON.parse(unitContentText.value) as Record<string, unknown> } catch { return ElMessage.warning('高级 JSON 必须是有效 JSON') }
  content = { ...baseContent.value, ...content }
  content[transcriptKey.value] = transcriptLines.value.filter((line) => line.en.trim()).map((line) => ({
    speaker: line.speaker.trim() || 'Speaker', en: line.en.trim(), zh: line.zh.trim(),
    ...(line.audioUrl.trim() ? { audioUrl: line.audioUrl.trim() } : {}),
    ...(typeof line.startSeconds === 'number' ? { startSeconds: Number(line.startSeconds) } : {}),
    ...(typeof line.endSeconds === 'number' ? { endSeconds: Number(line.endSeconds) } : {}),
  }))
  content.phrases = phraseLines.value.filter((phrase) => phrase.en.trim()).map((phrase) => ({ en: phrase.en.trim(), zh: phrase.zh.trim() }))
  content.prompt = lessonPrompt.value.trim()
  const validLines = transcriptLines.value.filter((line) => line.en.trim())
  const validPhrases = phraseLines.value.filter((phrase) => phrase.en.trim())
  if (unitForm.isPublished && validLines.length < 2) return ElMessage.warning('发布课程至少需要两句英文台词')
  if (unitForm.isPublished && validPhrases.length < 2) return ElMessage.warning('发布课程至少需要两个核心表达')
  if (unitForm.isPublished && !lessonPrompt.value.trim()) return ElMessage.warning('发布课程需要填写自主表达任务')
  if (validLines.some((line) => (typeof line.startSeconds === 'number') !== (typeof line.endSeconds === 'number') || (typeof line.startSeconds === 'number' && typeof line.endSeconds === 'number' && line.endSeconds <= line.startSeconds))) return ElMessage.warning('逐句时间轴请同时填写起止秒，并确保结束秒大于起始秒')
  const hasDirectMedia = !!mediaForm.audioUrl.trim() || !!mediaForm.videoUrl.trim()
  const hasAnyMedia = hasDirectMedia || !!mediaForm.sourceUrl.trim()
  if (unitForm.isPublished && mediaForm.rightsStatus === 'rejected') return ElMessage.warning('不可使用的素材不能发布')
  if (unitForm.isPublished && hasDirectMedia && mediaForm.rightsStatus !== 'licensed_hosting') return ElMessage.warning('小程序直播放地址发布前需确认已获得托管许可')
  if (unitForm.isPublished && hasAnyMedia && mediaForm.rightsStatus === 'pending_review') return ElMessage.warning('请先完成素材授权核验再发布')
  if (unitForm.isPublished && ['audio', 'video', 'video_audio'].includes(mediaForm.type) && !hasAnyMedia) return ElMessage.warning('请添加可用素材或改为纯对话/文本课')
  content.media = { type: mediaForm.type, audioUrl: mediaForm.audioUrl.trim(), videoUrl: mediaForm.videoUrl.trim(), posterUrl: mediaForm.posterUrl.trim(), sourceUrl: mediaForm.sourceUrl.trim(), rightsStatus: mediaForm.rightsStatus, rightsNote: mediaForm.rightsNote.trim(), startSeconds: Number(mediaForm.startSeconds) || 0, endSeconds: Number(mediaForm.endSeconds) || 0 }
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
.editor-head { display:flex; justify-content:space-between; align-items:center; color:#77817d; font-size:13px; margin:4px 0 10px; }
.editor-head > div { display:flex; gap:8px; }
.media-upload-row { display:flex; align-items:center; gap:12px; margin:0 0 14px 110px; color:#77817d; font-size:12px; }
.asr-note { margin:0 0 12px; color:#8a918e; font-size:12px; }
.hidden-input { display:none; }
.transcript-line { padding:12px; margin-bottom:10px; border:1px solid #e5ebe8; border-radius:8px; background:#fbfcfb; }
.line-heading { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; color:#52635e; }
.line-zh { margin:8px 0; }
.phrase-line { display:grid; grid-template-columns:1fr 1fr auto; gap:8px; margin-bottom:8px; }
.advanced-json { margin:12px 0; }
.advanced-json p { color:#77817d; font-size:13px; }
</style>
