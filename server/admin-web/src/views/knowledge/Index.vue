<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createKnowledgeTree,
  deleteKnowledgeTree,
  fetchKnowledgeDoc,
  fetchKnowledgeTrees,
  fetchKnowledgeVersion,
  patchKnowledgeTree,
  previewKnowledgeMd,
  publishKnowledgeTree,
  saveKnowledgeDoc,
  uploadKnowledgeAssets,
  uploadKnowledgeMd,
  type KnowledgeIssue,
  type KnowledgeManifest,
  type KnowledgeTreeMeta,
  type MapNode,
} from '@/api/knowledge'
import MdEditor from './MdEditor.vue'
import MarkmapPreview from './MarkmapPreview.vue'
import VersionDrawer from './VersionDrawer.vue'
import { makeThumb, overviewTree, planSegment, rasterizeSvg } from './exportMap'

const trees = ref<KnowledgeTreeMeta[]>([])
const activeKey = ref('')
const md = ref('')
const draftRevision = ref(0)
const dirty = ref(false)
const loading = ref(false)
const saving = ref(false)
const previewing = ref(false)
const publishing = ref(false)
const issues = ref<KnowledgeIssue[]>([])
const previewTree = ref<MapNode | null>(null)
const stats = ref({ nodeCount: 0, leafCount: 0, maxDepth: 0 })
const rightTab = ref('preview')
const versionDrawer = ref(false)
const publishProgress = ref('')
const liveManifest = ref<KnowledgeManifest | null>(null)
const editorRef = ref<InstanceType<typeof MdEditor> | null>(null)
const markmapRef = ref<InstanceType<typeof MarkmapPreview> | null>(null)
const createVisible = ref(false)
const createForm = ref({ treeKey: '', title: '' })

const activeMeta = computed(() => trees.value.find((t) => t.treeKey === activeKey.value) || null)
const hasErrors = computed(() => issues.value.some((i) => i.level === 'error'))
const outlineData = computed(() => {
  const t = previewTree.value
  if (!t) return []
  const map = (n: MapNode): { id: string; label: string; line: number; children?: unknown[] } => ({
    id: n.path || n.id,
    label: n.title,
    line: n.line,
    children: (n.children || []).map(map),
  })
  return (t.children || []).map(map)
})

const draftCacheKey = computed(() => (activeKey.value ? `knowledge-draft:${activeKey.value}` : ''))

let previewTimer: ReturnType<typeof setTimeout> | null = null

async function loadTrees(preferKey?: string) {
  trees.value = await fetchKnowledgeTrees()
  const key = preferKey || activeKey.value || trees.value[0]?.treeKey || ''
  if (key && trees.value.some((t) => t.treeKey === key)) {
    activeKey.value = key
  } else {
    activeKey.value = trees.value[0]?.treeKey || ''
  }
}

async function loadDoc(treeKey: string) {
  if (!treeKey) {
    md.value = ''
    draftRevision.value = 0
    previewTree.value = null
    issues.value = []
    liveManifest.value = null
    return
  }
  loading.value = true
  try {
    const doc = await fetchKnowledgeDoc(treeKey)
    const cached = draftCacheKey.value ? localStorage.getItem(draftCacheKey.value) : null
    if (cached && cached !== doc.mdDraft) {
      try {
        await ElMessageBox.confirm('发现本地未提交草稿，是否恢复？', '本地草稿', {
          distinguishCancelAndClose: true,
          confirmButtonText: '恢复本地',
          cancelButtonText: '用服务器',
        })
        md.value = cached
        dirty.value = true
      } catch {
        md.value = doc.mdDraft
        dirty.value = false
        localStorage.removeItem(draftCacheKey.value)
      }
    } else {
      md.value = doc.mdDraft
      dirty.value = false
    }
    draftRevision.value = doc.draftRevision
    await runPreview()
    if (doc.liveVersion > 0) {
      try {
        const ver = await fetchKnowledgeVersion(treeKey, doc.liveVersion)
        liveManifest.value = ver.manifest || null
      } catch {
        liveManifest.value = null
      }
    } else {
      liveManifest.value = null
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

watch(activeKey, (k) => {
  void loadDoc(k)
})

function onMdChange(v: string) {
  md.value = v
  dirty.value = true
  if (draftCacheKey.value) localStorage.setItem(draftCacheKey.value, v)
  schedulePreview()
}

function schedulePreview() {
  if (previewTimer) clearTimeout(previewTimer)
  previewTimer = setTimeout(() => {
    void runPreview()
  }, 800)
}

async function runPreview() {
  previewing.value = true
  try {
    const res = await previewKnowledgeMd(md.value)
    previewTree.value = res.tree
    issues.value = res.issues || []
    stats.value = res.stats || { nodeCount: 0, leafCount: 0, maxDepth: 0 }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '预览失败')
  } finally {
    previewing.value = false
  }
}

async function onSave() {
  if (!activeKey.value) return
  saving.value = true
  try {
    const out = await saveKnowledgeDoc(activeKey.value, md.value, draftRevision.value)
    draftRevision.value = out.draftRevision
    issues.value = out.issues || issues.value
    dirty.value = false
    if (draftCacheKey.value) localStorage.removeItem(draftCacheKey.value)
    ElMessage.success('草稿已保存')
    await loadTrees(activeKey.value)
  } catch (e) {
    const msg = e instanceof Error ? e.message : '保存失败'
    if (msg.includes('他人') || msg.includes('冲突')) {
      try {
        await ElMessageBox.confirm(`${msg}。重新加载将丢弃本地修改。`, '版本冲突', {
          confirmButtonText: '重新加载',
          cancelButtonText: '取消',
          type: 'warning',
        })
        dirty.value = false
        if (draftCacheKey.value) localStorage.removeItem(draftCacheKey.value)
        await loadDoc(activeKey.value)
      } catch {
        /* cancel */
      }
    } else {
      ElMessage.error(msg)
    }
  } finally {
    saving.value = false
  }
}

async function sha8(text: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return [...new Uint8Array(buf)].map((x) => x.toString(16).padStart(2, '0')).join('').slice(0, 8)
}

/**
 * 为指定版本生成导图资源并上传：概览图 + 按实测尺寸递归拆分的分片 + 全树纯 SVG + tree.json。
 * 文件名全部为 ASCII（overview-xxxx.png / s01-02-xxxx.png），由服务端校验后重建 URL。
 */
async function generateAndUpload(version: number, tree: MapNode, activate: boolean) {
  const mmRef = markmapRef.value
  if (!mmRef) throw new Error('预览组件未就绪')
  const files: File[] = []
  const segmentsMeta: KnowledgeManifest['segments'] = []

  publishProgress.value = '生成概览图…'
  const ovPure = await mmRef.renderToPureSvg(overviewTree(tree), -1, tree)
  const ovRaster = await rasterizeSvg(ovPure, 'overview.png')
  const ovBase = `overview-${ovRaster.sha256.slice(0, 8)}`
  const ovThumb = await makeThumb(ovRaster.blob, `${ovBase}.thumb.png`)
  files.push(new File([ovRaster.blob], `${ovBase}.png`, { type: 'image/png' }))
  files.push(new File([ovThumb.blob], ovThumb.filename, { type: 'image/png' }))
  const overview = {
    url: `${ovBase}.png`,
    width: ovRaster.width,
    height: ovRaster.height,
    bytes: ovRaster.blob.size,
    thumbUrl: ovThumb.filename,
    thumbWidth: ovThumb.width,
    thumbHeight: ovThumb.height,
    sha256: ovRaster.sha256,
  }

  const branches = tree.children || []
  let bi = 0
  for (const branch of branches) {
    bi += 1
    publishProgress.value = `生成分片 ${bi}/${branches.length} · ${branch.title}`
    const key = `s${String(bi).padStart(2, '0')}`
    const jobs = await planSegment(branch, key, [tree.title], (t) => mmRef.renderToPureSvg(t, -1, tree))
    for (const job of jobs) {
      const raster = await rasterizeSvg(job.pure, `${job.key}.png`, job.scale)
      const base = `${job.key}-${raster.sha256.slice(0, 8)}`
      const thumb = await makeThumb(raster.blob, `${base}.thumb.png`)
      files.push(new File([raster.blob], `${base}.png`, { type: 'image/png' }))
      files.push(new File([thumb.blob], thumb.filename, { type: 'image/png' }))
      segmentsMeta.push({
        key: job.key,
        title: job.title,
        rootPath: job.rootPath,
        nodeCount: job.nodeCount,
        url: `${base}.png`,
        width: raster.width,
        height: raster.height,
        bytes: raster.blob.size,
        thumbUrl: thumb.filename,
        thumbWidth: thumb.width,
        thumbHeight: thumb.height,
        sha256: raster.sha256,
      })
    }
  }

  publishProgress.value = '生成全树 SVG…'
  const full = await mmRef.renderToPureSvg(tree, -1, tree)
  const svgName = `full-${await sha8(full.svg)}.svg`
  const svgBlob = new Blob([full.svg], { type: 'image/svg+xml' })
  files.push(new File([svgBlob], svgName, { type: 'image/svg+xml' }))
  const treeJson = JSON.stringify(tree)
  const treeJsonName = `tree-${await sha8(treeJson)}.json`
  files.push(new File([treeJson], treeJsonName, { type: 'application/json' }))

  publishProgress.value = '上传资源…'
  return uploadKnowledgeAssets(
    activeKey.value,
    version,
    {
      generatedAt: new Date().toISOString(),
      theme: 'brand-red',
      scale: 2,
      overview,
      segments: segmentsMeta,
      svg: { url: svgName, bytes: svgBlob.size },
      treeJsonUrl: treeJsonName,
    },
    files,
    activate,
  )
}

async function onPublish() {
  if (!activeKey.value || hasErrors.value) return
  if (dirty.value) {
    await onSave()
    if (dirty.value) return
  }
  publishing.value = true
  publishProgress.value = '发布中…'
  let publishedVersion = 0
  try {
    const pub = await publishKnowledgeTree(activeKey.value, draftRevision.value)
    if (!pub.tree) throw new Error('发布返回空树')
    publishedVersion = pub.version
    const up = await generateAndUpload(pub.version, pub.tree, true)
    liveManifest.value = up.manifest
    const d = up.nodeDiff
    ElMessage.success(
      d ? `v${up.liveVersion} 已上线（新增 ${d.added} · 归档 ${d.archived} · 移动 ${d.moved}）` : `v${up.liveVersion} 已上线`,
    )
    await loadTrees(activeKey.value)
    rightTab.value = 'live'
  } catch (e) {
    const msg = e instanceof Error ? e.message : '发布失败'
    ElMessage.error(
      publishedVersion ? `v${publishedVersion} 已发布但图片生成/上传失败：${msg}（可在「历史版本」中重新生成）` : msg,
    )
    await loadTrees(activeKey.value)
  } finally {
    publishing.value = false
    publishProgress.value = ''
  }
}

/** 历史版本抽屉：为已有版本重新生成图片（不新建版本；是否上线由 activate 决定）。 */
async function onRegenerate(payload: { version: number; activate: boolean }) {
  if (!activeKey.value || publishing.value) return
  publishing.value = true
  try {
    const ver = await fetchKnowledgeVersion(activeKey.value, payload.version)
    if (!ver.tree) throw new Error('版本数据为空')
    const up = await generateAndUpload(payload.version, ver.tree, payload.activate)
    ElMessage.success(payload.activate ? `v${payload.version} 图片已生成并上线` : `v${payload.version} 图片已生成`)
    if (up.liveVersion === payload.version) liveManifest.value = up.manifest
    await loadTrees(activeKey.value)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '生成失败')
  } finally {
    publishing.value = false
    publishProgress.value = ''
  }
}

async function onActivated() {
  await loadTrees(activeKey.value)
  await loadDoc(activeKey.value)
}

function onOutlineClick(data: { line: number }) {
  editorRef.value?.gotoLine(data.line)
}

function exportMd() {
  const blob = new Blob([md.value], { type: 'text/markdown;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${activeKey.value || 'knowledge'}.md`
  a.click()
  URL.revokeObjectURL(a.href)
}

async function onCreate() {
  const key = createForm.value.treeKey.trim()
  const title = createForm.value.title.trim() || key
  if (!key) {
    ElMessage.warning('请填写 treeKey')
    return
  }
  try {
    await createKnowledgeTree({ treeKey: key, title, md: `# ${title}\n\n` })
    createVisible.value = false
    createForm.value = { treeKey: '', title: '' }
    await loadTrees(key)
    ElMessage.success('已创建')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  }
}

async function onToggleVisible(v: boolean) {
  if (!activeKey.value) return
  try {
    await patchKnowledgeTree(activeKey.value, { isVisible: v })
    await loadTrees(activeKey.value)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '更新失败')
  }
}

async function onDeleteTree() {
  if (!activeKey.value) return
  try {
    await ElMessageBox.confirm(`归档并隐藏「${activeKey.value}」？节点不会物理删除。`, '删除知识树', {
      type: 'warning',
    })
    await deleteKnowledgeTree(activeKey.value)
    ElMessage.success('已删除')
    activeKey.value = ''
    await loadTrees()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e instanceof Error ? e.message : '删除失败')
    }
  }
}

async function onUploadMd(opt: { file: File }) {
  try {
    let r = await uploadKnowledgeMd(opt.file)
    if (r.import?.error === 'draft_dirty') {
      try {
        await ElMessageBox.confirm(
          `「${r.treeKey}」的草稿有未发布的修改，导入会覆盖草稿（已发布版本不受影响）。确定覆盖？`,
          '覆盖草稿',
          { type: 'warning', confirmButtonText: '覆盖', cancelButtonText: '取消' },
        )
      } catch {
        return
      }
      r = await uploadKnowledgeMd(opt.file, true)
    }
    if (r.import?.ok === false) {
      ElMessage.error(`导入失败：${String(r.import.error || '未知错误')}`)
      return
    }
    ElMessage.success(r.import?.unchanged ? `内容未变化：${r.treeKey}` : `已导入草稿：${r.treeKey}`)
    await loadTrees(r.treeKey)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '上传失败')
  }
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (!dirty.value) return
  e.preventDefault()
  e.returnValue = ''
}

onMounted(async () => {
  window.addEventListener('beforeunload', onBeforeUnload)
  await loadTrees()
  await nextTick()
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  if (previewTimer) clearTimeout(previewTimer)
})

function mediaUrl(u?: string) {
  if (!u) return ''
  if (u.startsWith('http')) return u
  return u
}
</script>

<template>
  <div v-loading="loading" class="page">
    <div class="topbar">
      <div class="tabs-row">
        <el-tabs v-model="activeKey" type="card" class="tree-tabs">
          <el-tab-pane v-for="t in trees" :key="t.treeKey" :label="t.title" :name="t.treeKey" />
        </el-tabs>
        <el-button size="small" @click="createVisible = true">＋ 新建</el-button>
        <el-upload :show-file-list="false" accept=".md" :http-request="onUploadMd">
          <el-button size="small">导入 md</el-button>
        </el-upload>
      </div>
      <div v-if="activeMeta" class="status-row">
        <el-tag v-if="dirty" type="warning" size="small">未保存</el-tag>
        <el-tag v-else-if="activeMeta.hasUnpublishedChanges" type="warning" size="small">草稿未发布</el-tag>
        <el-tag v-else type="success" size="small">已同步</el-tag>
        <span class="muted">
          线上 v{{ activeMeta.liveVersion || '—' }}
          <template v-if="activeMeta.livePublishedAt"> · {{ activeMeta.livePublishedAt }}</template>
          · 节点 {{ stats.nodeCount }} / 叶 {{ stats.leafCount }} / 深 {{ stats.maxDepth }}
        </span>
        <el-switch
          :model-value="activeMeta.isVisible"
          inline-prompt
          active-text="学员可见"
          inactive-text="隐藏"
          @change="onToggleVisible"
        />
        <el-button size="small" type="danger" plain @click="onDeleteTree">删除树</el-button>
      </div>
    </div>

    <div v-if="!trees.length" class="empty">
      <el-empty description="暂无知识树，请新建或导入 Markdown" />
    </div>

    <div v-else class="workspace">
      <div class="left">
        <MdEditor ref="editorRef" :model-value="md" :issues="issues" @update:model-value="onMdChange" />
        <div v-if="issues.length" class="issue-panel">
          <div
            v-for="(iss, idx) in issues"
            :key="idx"
            class="issue"
            :class="iss.level"
            @click="editorRef?.gotoLine(iss.line)"
          >
            L{{ iss.line }} · {{ iss.code }} · {{ iss.message }}
          </div>
        </div>
      </div>
      <div class="right">
        <el-tabs v-model="rightTab">
          <el-tab-pane label="导图预览" name="preview">
            <div class="preview-pane">
              <MarkmapPreview ref="markmapRef" :tree="previewTree" />
            </div>
          </el-tab-pane>
          <el-tab-pane label="大纲" name="outline">
            <el-tree
              :data="outlineData"
              :props="{ label: 'label', children: 'children' }"
              default-expand-all
              @node-click="onOutlineClick"
            />
          </el-tab-pane>
          <el-tab-pane label="线上图片" name="live">
            <div v-if="!liveManifest?.segments?.length && !liveManifest?.overview" class="muted pad">
              暂无线上导图资源
            </div>
            <div v-else class="live-grid">
              <div v-if="liveManifest?.overview" class="live-card">
                <div class="live-title">概览</div>
                <img :src="mediaUrl(liveManifest.overview.thumbUrl || liveManifest.overview.url)" alt="overview" />
              </div>
              <div v-for="s in liveManifest?.segments || []" :key="s.key" class="live-card">
                <div class="live-title">{{ s.title }}</div>
                <img :src="mediaUrl(s.thumbUrl || s.url)" :alt="s.title" />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <div class="footer">
      <el-button type="primary" :loading="saving" :disabled="!activeKey" @click="onSave">保存草稿</el-button>
      <el-button :loading="previewing" :disabled="!activeKey" @click="runPreview">更新思维导图</el-button>
      <el-button
        type="success"
        :loading="publishing"
        :disabled="!activeKey || hasErrors"
        @click="onPublish"
      >
        发布并生成图片
      </el-button>
      <el-button :disabled="!activeKey" @click="exportMd">导出 md</el-button>
      <el-button :disabled="!activeKey" @click="versionDrawer = true">历史版本</el-button>
      <span v-if="publishProgress" class="muted">{{ publishProgress }}</span>
    </div>

    <el-dialog v-model="createVisible" title="新建知识树" width="420px">
      <el-form label-width="80px">
        <el-form-item label="treeKey">
          <el-input v-model="createForm.treeKey" placeholder="如：申论" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="createForm.title" placeholder="默认与 treeKey 相同" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="onCreate">创建</el-button>
      </template>
    </el-dialog>

    <VersionDrawer
      v-model="versionDrawer"
      :tree-key="activeKey"
      :live-version="activeMeta?.liveVersion || 0"
      :busy="publishing"
      @rolled-back="loadDoc(activeKey)"
      @activated="onActivated"
      @regenerate="onRegenerate"
    />
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px);
  min-height: 560px;
  gap: 10px;
}
.topbar {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tabs-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tree-tabs {
  flex: 1;
  min-width: 0;
}
.status-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.workspace {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 45% 55%;
  gap: 12px;
}
.left,
.right {
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.left {
  gap: 8px;
}
.preview-pane {
  height: calc(100vh - 280px);
  min-height: 360px;
}
.issue-panel {
  max-height: 120px;
  overflow: auto;
  font-size: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: #fafafa;
}
.issue {
  padding: 4px 8px;
  cursor: pointer;
  border-bottom: 1px solid #eee;
}
.issue:hover {
  background: #f0f4ff;
}
.issue.error {
  color: #c45656;
}
.issue.warning {
  color: #b88230;
}
.footer {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 4px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.muted {
  color: #888;
  font-size: 12px;
}
.pad {
  padding: 12px;
}
.live-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  padding: 8px;
  overflow: auto;
  max-height: calc(100vh - 280px);
}
.live-card img {
  width: 100%;
  border: 1px solid #eee;
  border-radius: 4px;
  background: #fff;
}
.live-title {
  font-size: 12px;
  margin-bottom: 4px;
  color: #444;
}
.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
