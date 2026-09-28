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
import { makeThumb, overviewTree, rasterizeSvg, sliceTree } from './exportMap'

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

async function onPublish() {
  if (!activeKey.value || hasErrors.value) return
  if (dirty.value) {
    await onSave()
    if (dirty.value) return
  }
  publishing.value = true
  publishProgress.value = '发布中…'
  try {
    const pub = await publishKnowledgeTree(activeKey.value, draftRevision.value)
    const tree = pub.tree
    if (!tree) throw new Error('发布返回空树')
    const version = pub.version
    const files: File[] = []
    const segmentsMeta: KnowledgeManifest['segments'] = []

    publishProgress.value = '生成概览图…'
    const ovTree = overviewTree(tree)
    const ovSvg = await markmapRef.value!.renderToPureSvg(ovTree, -1)
    const ovSha8prefix = 'overview'
    const ovRaster = await rasterizeSvg(ovSvg, `${ovSha8prefix}.png`)
    const ovName = `overview-${ovRaster.sha256.slice(0, 8)}.png`
    const ovThumb = await makeThumb(ovRaster.blob, `overview-${ovRaster.sha256.slice(0, 8)}.thumb.png`)
    files.push(new File([ovRaster.blob], ovName, { type: 'image/png' }))
    files.push(new File([ovThumb.blob], ovThumb.filename, { type: 'image/png' }))
    const overview = {
      url: ovName,
      width: ovRaster.width,
      height: ovRaster.height,
      bytes: ovRaster.blob.size,
      thumbUrl: ovThumb.filename,
      thumbWidth: ovThumb.width,
      thumbHeight: ovThumb.height,
      sha256: ovRaster.sha256,
    }

    const planSegs = pub.exportPlan?.segments || []
    let i = 0
    for (const seg of planSegs) {
      i += 1
      publishProgress.value = `生成分片 ${i}/${planSegs.length} · ${seg.title}`
      const sliced = sliceTree(tree, seg.rootPath, `${tree.title} › ${seg.title}`)
      if (!sliced) continue
      // 大分支：若节点过多，按 depth1 再拆
      const kids = sliced.children || []
      const jobs: { key: string; title: string; rootPath: string; nodeCount: number; node: MapNode }[] = []
      if (seg.nodeCount > 80 && kids.length > 1) {
        for (const k of kids) {
          const cnt = countNodes(k)
          jobs.push({
            key: `${seg.key}--${k.path.replace(/\//g, '-')}`,
            title: `${seg.title} › ${k.title}`,
            rootPath: k.path,
            nodeCount: cnt,
            node: {
              ...sliced,
              title: `${tree.title} › ${seg.title} › ${k.title}`,
              children: [k],
            },
          })
        }
      } else {
        jobs.push({ key: seg.key, title: seg.title, rootPath: seg.rootPath, nodeCount: seg.nodeCount, node: sliced })
      }
      for (const job of jobs) {
        const svg = await markmapRef.value!.renderToPureSvg(job.node, -1)
        const raster = await rasterizeSvg(svg, `${job.key}.png`)
        // 若 scale 过低说明图太大，在前端已按 4096 压；仍过大则跳过二次拆（后端会校验）
        const name = `${job.key}-${raster.sha256.slice(0, 8)}.png`
        const thumb = await makeThumb(raster.blob, `${job.key}-${raster.sha256.slice(0, 8)}.thumb.png`)
        files.push(new File([raster.blob], name, { type: 'image/png' }))
        files.push(new File([thumb.blob], thumb.filename, { type: 'image/png' }))
        segmentsMeta.push({
          key: job.key,
          title: job.title,
          rootPath: job.rootPath,
          nodeCount: job.nodeCount,
          url: name,
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
    const fullSvg = await markmapRef.value!.renderToPureSvg(tree, 2)
    const svgName = `full-${(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(fullSvg)).then((b) => [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join(''))).slice(0, 8)}.svg`
    const svgBlob = new Blob([fullSvg], { type: 'image/svg+xml' })
    files.push(new File([svgBlob], svgName, { type: 'image/svg+xml' }))

    const treeJsonName = `tree.json`
    const treeJsonBlob = new Blob([JSON.stringify(tree)], { type: 'application/json' })
    files.push(new File([treeJsonBlob], treeJsonName, { type: 'application/json' }))

    const manifest: KnowledgeManifest = {
      version,
      generatedAt: new Date().toISOString(),
      theme: 'brand-red',
      scale: 2,
      overview,
      segments: segmentsMeta,
      svg: { url: svgName, bytes: svgBlob.size },
      treeJsonUrl: treeJsonName,
    }

    publishProgress.value = '上传资源…'
    const up = await uploadKnowledgeAssets(activeKey.value, version, manifest, files)
    liveManifest.value = up.manifest
    ElMessage.success(`v${up.liveVersion} 已上线`)
    await loadTrees(activeKey.value)
    rightTab.value = 'live'
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '发布失败')
  } finally {
    publishing.value = false
    publishProgress.value = ''
  }
}

function countNodes(n: MapNode): number {
  return 1 + (n.children || []).reduce((s, c) => s + countNodes(c), 0)
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
    const r = await uploadKnowledgeMd(opt.file)
    ElMessage.success(`已导入草稿：${r.treeKey}`)
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

    <VersionDrawer v-model="versionDrawer" :tree-key="activeKey" @rolled-back="loadDoc(activeKey)" />
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
