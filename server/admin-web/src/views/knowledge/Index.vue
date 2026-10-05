<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { ApiRequestError } from '@/api/http'
import {
  activateKnowledgeVersion, createKnowledgeTree, fetchKnowledgeTrees,
  fetchStructuredKnowledge, previewStructuredKnowledge, previewStructuredMarkdown, publishKnowledgeTree,
  saveStructuredKnowledge, patchKnowledgeTree, uploadKnowledgeImage,
  type KnowledgeBlock, type KnowledgeTreeMeta, type StructuredIssue,
  type StructuredNode, type StructuredTree,
} from '@/api/knowledge'

const router = useRouter()
const route = useRoute()
const trees = ref<KnowledgeTreeMeta[]>([])
const activeKey = ref('')
const draft = ref<StructuredTree | null>(null)
const revision = ref(0)
const selectedId = ref('')
const editorTab = ref<'edit' | 'preview'>('edit')
const previewMode = ref<'directory' | 'overview'>('directory')
const previewPath = ref<string[]>([])
const previewQuery = ref('')
const issues = ref<StructuredIssue[]>([])
const saveState = ref('')
const loading = ref(false)
const publishing = ref(false)
const searchTree = ref('')
const treeRef = ref<{ filter: (value: string) => void }>()
const importVisible = ref(false)
const importing = ref(false)
const importMode = ref<'replace' | 'new'>('replace')
const importFileName = ref('')
const importPreview = ref<Awaited<ReturnType<typeof previewStructuredMarkdown>> | null>(null)
const newTreeTitle = ref('')
const newTreeKey = ref('')
watch(searchTree, value => treeRef.value?.filter(value))
let saveTimer: ReturnType<typeof setTimeout> | null = null
let saving: Promise<void> | null = null
let pending = false
let loadToken = 0

const activeMeta = computed(() => trees.value.find(t => t.treeKey === activeKey.value))
const selected = computed(() => {
  const walk = (nodes: StructuredNode[]): StructuredNode | null => {
    for (const node of nodes) { if (node.id === selectedId.value) return node; const child = walk(node.children); if (child) return child }
    return null
  }
  return walk(draft.value?.children || [])
})
const treeData = computed(() => draft.value?.children || [])
const previewNode = computed(() => {
  let nodes = draft.value?.children || []
  let found: StructuredNode | null = null
  for (const id of previewPath.value) { found = nodes.find(n => n.id === id) || null; if (!found) break; nodes = found.children }
  return found
})
const previewChildren = computed(() => previewNode.value?.children || draft.value?.children || [])
const previewHits = computed(() => {
  const q = previewQuery.value.trim().toLowerCase()
  if (!q) return []
  const out: StructuredNode[] = []
  const walk = (nodes: StructuredNode[]) => { for (const n of nodes) { if (n.title.toLowerCase().includes(q)) out.push(n); walk(n.children) } }
  walk(draft.value?.children || [])
  return out.slice(0, 80)
})
const nodeCount = computed(() => {
  const count = (nodes: StructuredNode[]): number => nodes.reduce((total, n) => total + 1 + count(n.children), 0)
  return count(draft.value?.children || [])
})
const groups = computed(() => {
  const children = draft.value?.children || []
  const defined = draft.value?.groups || []
  if (!defined.length) return [{ title: '全部分类', nodes: children }]
  const used = new Set<string>()
  const result = defined.map(g => ({ title: g.title, nodes: g.nodeIds.map(id => children.find(n => n.id === id)).filter((n): n is StructuredNode => !!n).filter(n => { used.add(n.id); return true }) })).filter(g => g.nodes.length)
  const rest = children.filter(n => !used.has(n.id))
  if (rest.length) result.push({ title: '其他分类', nodes: rest })
  return result
})

async function loadTrees(prefer = '') {
  trees.value = await fetchKnowledgeTrees()
  const next = prefer || activeKey.value
  activeKey.value = trees.value.some(t => t.treeKey === next) ? next : trees.value[0]?.treeKey || ''
}
async function loadDraft(key: string) {
  const token = ++loadToken
  if (!key) { draft.value = null; selectedId.value = ''; return }
  loading.value = true
  try {
    const result = await fetchStructuredKnowledge(key)
    if (token !== loadToken) return
    draft.value = result.tree
    revision.value = result.draftRevision
    issues.value = result.issues
    selectedId.value = ''
    previewPath.value = []
    previewQuery.value = ''
    pending = false
    saveState.value = '草稿已加载'
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '加载失败') }
  finally { if (token === loadToken) loading.value = false }
}
async function changeSubject(key: string) {
  await flushSave()
  if (pending) return
  activeKey.value = key
  await loadDraft(key)
}

function markChanged() {
  pending = true
  saveState.value = '待保存'
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => { void flushSave() }, 900)
}
async function flushSave() {
  if (saveTimer) { clearTimeout(saveTimer); saveTimer = null }
  if (saving) { await saving; if (pending && !saveState.value.includes('失败')) return flushSave(); return }
  if (!pending || !draft.value || !activeKey.value) return
  const key = activeKey.value
  const snapshot = JSON.parse(JSON.stringify(draft.value)) as StructuredTree
  const before = JSON.stringify(snapshot)
  pending = false
  saveState.value = '保存中…'
  saving = (async () => {
    try {
      const out = await saveStructuredKnowledge(key, snapshot, revision.value)
      if (activeKey.value !== key) return
      revision.value = out.draftRevision
      issues.value = out.issues
      if (draft.value && JSON.stringify(draft.value) !== before) pending = true
      saveState.value = pending ? '待保存' : '草稿已保存'
    } catch (error) {
      pending = true
      saveState.value = '保存失败，请检查内容后重试'
      const details = error instanceof ApiRequestError && error.data && typeof error.data === 'object'
        ? (error.data as { issues?: StructuredIssue[] }).issues || []
        : []
      if (details.length) {
        issues.value = details
        const firstInvalid = details.find(issue => issue.level === 'error' && issue.nodeId)
        if (firstInvalid?.nodeId) selectedId.value = firstInvalid.nodeId
        const text = details.map((issue, index) => `${index + 1}. ${issue.path || '知识框架'}：${issue.message.replace(`${issue.path}：`, '')}`).join('\n')
        void ElMessageBox.alert(text, '草稿保存失败：请按节点修正以下问题', {
          type: 'error',
          confirmButtonText: '知道了',
          customClass: 'knowledge-save-error-dialog',
        })
      } else {
        ElMessage.error(error instanceof Error ? error.message : '草稿保存失败')
      }
    }
  })()
  try { await saving } finally { saving = null }
  if (pending && saveState.value === '待保存') { saveTimer = setTimeout(() => { void flushSave() }, 500) }
}

function freshNode(): StructuredNode { return { id: `kn${crypto.randomUUID().replace(/-/g, '').slice(0, 12)}`, title: '新知识点', blocks: [], children: [] } }
function findParent(id: string, nodes = draft.value?.children || [], parent: StructuredNode | null = null): { parent: StructuredNode | null; list: StructuredNode[]; index: number } | null {
  for (let i = 0; i < nodes.length; i++) {
    if (nodes[i].id === id) return { parent, list: nodes, index: i }
    const nested = findParent(id, nodes[i].children, nodes[i]); if (nested) return nested
  }
  return null
}
function addRoot() { selectedId.value = ''; addNode(false) }
function onTreeDrop() {
  if (draft.value) {
    const roots = new Set(draft.value.children.map(n => n.id))
    draft.value.groups.forEach(g => { g.nodeIds = g.nodeIds.filter(id => roots.has(id)) })
  }
  markChanged()
}
function addNode(asChild: boolean) {
  if (!draft.value) return
  const node = freshNode()
  const pos = selectedId.value ? findParent(selectedId.value) : null
  const siblings = asChild && selected.value ? selected.value.children : pos?.list || draft.value.children
  let suffix = 1
  while (siblings.some(n => n.title === node.title)) node.title = `新知识点 ${suffix++}`
  if (asChild && selected.value) selected.value.children.push(node)
  else if (pos) pos.list.splice(pos.index + 1, 0, node)
  else draft.value.children.push(node)
  selectedId.value = node.id
  editorTab.value = 'edit'
  markChanged()
}
async function removeNode() {
  const pos = findParent(selectedId.value)
  if (!pos) return
  try { await ElMessageBox.confirm(`删除「${pos.list[pos.index].title}」及其下级节点？发布前只影响草稿。`, '删除节点', { type: 'warning' }) } catch { return }
  pos.list.splice(pos.index, 1)
  selectedId.value = pos.parent?.id || ''
  markChanged()
}
function moveNode(offset: number) {
  const pos = findParent(selectedId.value)
  if (!pos) return
  const next = pos.index + offset
  if (next < 0 || next >= pos.list.length) return
  const [node] = pos.list.splice(pos.index, 1)
  pos.list.splice(next, 0, node)
  markChanged()
}
function addBlock(type: KnowledgeBlock['type']) {
  if (!selected.value) return
  const block = type === 'text' ? { type, text: '' } : type === 'formula' ? { type, latex: '', plain: '' } : type === 'image' ? { type, url: '', alt: '' } : { type, question: '', answer: '' }
  selected.value.blocks.push(block as KnowledgeBlock)
  markChanged()
}
async function uploadImage(block: KnowledgeBlock, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || block.type !== 'image') return
  if (file.size > 3 * 1024 * 1024) { ElMessage.error('图片不能超过 3MB'); input.value = ''; return }
  try { const out = await uploadKnowledgeImage(file); block.url = out.url; markChanged() }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '上传失败') }
  finally { input.value = '' }
}
function removeBlock(index: number) { selected.value?.blocks.splice(index, 1); markChanged() }
function nodeGroup(id: string) { return draft.value?.groups.find(g => g.nodeIds.includes(id))?.title || '' }
function setGroup(id: string, title: string) {
  if (!draft.value) return
  draft.value.groups.forEach(g => { g.nodeIds = g.nodeIds.filter(x => x !== id) })
  draft.value.groups = draft.value.groups.filter(g => g.nodeIds.length)
  const name = title.trim()
  if (name) {
    let group = draft.value.groups.find(g => g.title === name)
    if (!group) { group = { title: name, nodeIds: [] }; draft.value.groups.push(group) }
    group.nodeIds.push(id)
  }
  markChanged()
}
function previewEnter(node: StructuredNode) { if (node.children.length) { previewPath.value.push(node.id); previewQuery.value = '' } else { previewPath.value.push(node.id) } }
function previewUp(index: number) { previewPath.value = previewPath.value.slice(0, index) }
function previewSearchEnter(node: StructuredNode) {
  const ids: string[] = []
  const walk = (nodes: StructuredNode[], path: string[]): boolean => { for (const n of nodes) { if (n.id === node.id) { ids.push(...path, n.id); return true } if (walk(n.children, [...path, n.id])) return true } return false }
  walk(draft.value?.children || [], [])
  previewPath.value = ids; previewQuery.value = ''
}
function formulaHtml(latex: string) { try { return katex.renderToString(latex, { throwOnError: false, output: 'html' }) } catch { return '' } }
async function onPublish() {
  if (!draft.value || !activeKey.value || publishing.value) return
  pending = true
  await flushSave()
  if (pending) return
  publishing.value = true
  try {
    const check = await previewStructuredKnowledge(draft.value, activeKey.value)
    issues.value = check.issues
    const errors = check.issues.filter(i => i.level === 'error')
    if (errors.length) { ElMessage.error(`有 ${errors.length} 项问题，请先修正`); return }
    await ElMessageBox.confirm(`将 ${check.stats.nodeCount} 个节点发布为新版本？新增 ${check.nodeDiffPreview?.added || 0} 个，保留 ${check.nodeDiffPreview?.kept || 0} 个，归档 ${check.nodeDiffPreview?.archived || 0} 个。学员端下次进入时会读取新结构。`, '确认发布', { type: 'warning' })
    if (pending || saving) { ElMessage.warning('草稿有新修改，请保存后重新发布'); return }
    const pub = await publishKnowledgeTree(activeKey.value, revision.value)
    const live = activeMeta.value?.liveVersion || 0
    const activated = await activateKnowledgeVersion(activeKey.value, pub.version, live, true)
    await loadTrees(activeKey.value)
    ElMessage.success(`v${activated.liveVersion} 已上线`)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '发布失败')
  } finally { publishing.value = false }
}
async function createSubject() {
  await flushSave()
  if (pending) return
  try {
    const { value } = await ElMessageBox.prompt('填写科目名称，例如“常识判断”', '新增科目', { inputPattern: /^.{1,32}$/, inputErrorMessage: '请填写 1–32 字' })
    const name = value.trim()
    await createKnowledgeTree({ treeKey: name, title: name })
    await loadTrees(name)
    await loadDraft(name)
    ElMessage.success('科目已创建，发布前学员不可见')
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '创建失败') }
}
function openMarkdownImport() {
  importMode.value = draft.value ? 'replace' : 'new'
  importFileName.value = ''
  importPreview.value = null
  newTreeTitle.value = ''
  newTreeKey.value = ''
  importVisible.value = true
}
function suggestedTreeKey(title: string) {
  return title.replace(/[^0-9A-Za-z_\-\u4e00-\u9fff]/g, '').slice(0, 32)
}
async function onMarkdownFileChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  importPreview.value = null
  if (!file) return
  importFileName.value = file.name
  if (!file.name.toLowerCase().endsWith('.md')) { ElMessage.error('请选择 .md 文件'); return }
  if (file.size > 1_000_000) { ElMessage.error('Markdown 文件不能超过 1MB'); return }
  try {
    const preview = await previewStructuredMarkdown(await file.text())
    importPreview.value = preview
    newTreeTitle.value = preview.tree.title
    newTreeKey.value = suggestedTreeKey(preview.tree.title)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'Markdown 解析失败')
  }
}
const duplicateImportKey = computed(() => trees.value.some(tree => tree.treeKey === newTreeKey.value.trim()))
async function confirmMarkdownImport() {
  const preview = importPreview.value
  if (!preview || importing.value) return
  const errors = preview.issues.filter(issue => issue.level === 'error')
  if (errors.length) { ElMessage.warning('请先修复 Markdown 结构错误，再导入'); return }
  if (importMode.value === 'new') {
    const key = newTreeKey.value.trim()
    const title = newTreeTitle.value.trim()
    if (!/^[0-9A-Za-z_\-\u4e00-\u9fff]{1,32}$/.test(key)) { ElMessage.warning('科目标识限 1–32 位中英文、数字、下划线或连字符'); return }
    if (!title || title.length > 64) { ElMessage.warning('科目名称限 1–64 字'); return }
    if (duplicateImportKey.value) { ElMessage.warning('该科目标识已存在，请修改标识或改为替换当前科目'); return }
  } else if (!activeKey.value) {
    ElMessage.warning('请先选择要替换的科目，或改为导入新科目'); return
  }

  importing.value = true
  try {
    await flushSave()
    if (pending || saving) { ElMessage.warning('当前草稿尚未保存，请保存成功后重试导入'); return }
    let targetKey = activeKey.value
    let baseRevision = revision.value
    if (importMode.value === 'replace') {
      await ElMessageBox.confirm(
        `将用「${preview.tree.title}」中的 ${preview.stats.nodeCount} 个节点替换「${activeMeta.value?.title || targetKey}」的当前草稿。已发布的线上版本不受影响。`,
        '确认替换当前草稿', { type: 'warning', confirmButtonText: '替换草稿', cancelButtonText: '取消' },
      )
    } else {
      targetKey = newTreeKey.value.trim()
      await createKnowledgeTree({ treeKey: targetKey, title: newTreeTitle.value.trim() })
      const created = await fetchStructuredKnowledge(targetKey)
      baseRevision = created.draftRevision
    }
    const saved = await saveStructuredKnowledge(targetKey, {
      ...preview.tree,
      title: importMode.value === 'new' ? newTreeTitle.value.trim() : preview.tree.title,
    }, baseRevision)
    importVisible.value = false
    await loadTrees(targetKey)
    await loadDraft(targetKey)
    ElMessage.success(`Markdown 已导入为结构化草稿（${saved.tree.children.length} 个一级节点）`)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : 'Markdown 导入失败')
  } finally {
    importing.value = false
  }
}
async function toggleVisibility(value: boolean) {
  if (!activeKey.value) return
  try { await patchKnowledgeTree(activeKey.value, { isVisible: value }); await loadTrees(activeKey.value) }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '更新失败') }
}
function onBeforeUnload(event: BeforeUnloadEvent) { if (pending || saving) { event.preventDefault(); event.returnValue = '' } }
async function openAdvancedPreview() {
  await flushSave()
  if (pending || !activeKey.value) return
  await router.push({ path: '/knowledge/legacy', query: { source: 'structured', treeKey: activeKey.value } })
}
onMounted(async () => {
  window.addEventListener('beforeunload', onBeforeUnload)
  const preferred = typeof route.query.treeKey === 'string' ? route.query.treeKey : ''
  await loadTrees(preferred)
  await loadDraft(activeKey.value)
  await nextTick()
})
onBeforeRouteLeave(async () => { await flushSave(); return !pending })
onBeforeUnmount(() => { window.removeEventListener('beforeunload', onBeforeUnload); if (saveTimer) clearTimeout(saveTimer) })
</script>

<template>
  <div v-loading="loading || publishing" class="knowledge-workbench">
    <div class="topbar">
      <div class="top-main">
        <el-select :model-value="activeKey" @change="changeSubject" placeholder="选择科目" class="subject-select">
          <el-option v-for="item in trees" :key="item.treeKey" :label="item.title" :value="item.treeKey" />
        </el-select>
        <el-button @click="createSubject">新增科目</el-button>
        <el-button v-if="draft" @click="openMarkdownImport">导入 Markdown</el-button>
        <span v-if="draft" class="status">{{ saveState }} · 线上 v{{ activeMeta?.liveVersion || '—' }}</span>
        <div class="top-spacer" />
        <el-button v-if="draft" type="primary" :loading="publishing" :disabled="loading" @click="onPublish">发布</el-button>
        <el-button v-if="draft" @click="openAdvancedPreview">更多操作</el-button>
      </div>
      <div v-if="draft" class="top-sub">
        <span>{{ nodeCount }} 个节点 · {{ issues.filter(i => i.level === 'error').length }} 项需处理</span>
        <el-switch :model-value="activeMeta?.isVisible || false" :disabled="!activeMeta?.liveVersion" active-text="学员可见" inactive-text="暂时隐藏" @change="toggleVisibility" />
      </div>
  </div>

    <el-dialog v-model="importVisible" title="导入 Markdown 知识结构" width="700px" destroy-on-close>
      <el-alert
        title="先解析并预览，再写入结构化草稿。此入口不会调用旧版 Markdown 覆盖接口。"
        type="info" :closable="false" show-icon class="import-tip"
      />
      <label class="import-file-button"><input type="file" accept=".md,text/markdown" @change="onMarkdownFileChange" />选择 .md 文件</label>
      <span v-if="importFileName" class="import-filename">{{ importFileName }}</span>
      <template v-if="importPreview">
        <el-divider content-position="left">导入方式</el-divider>
        <el-radio-group v-model="importMode" :disabled="importing">
          <el-radio value="new">导入为新科目</el-radio>
          <el-radio value="replace" :disabled="!draft">替换当前科目草稿</el-radio>
        </el-radio-group>
        <el-alert v-if="importMode === 'replace'" :title="`目标科目：${activeMeta?.title || activeKey}。只替换草稿，线上已发布版本保留。`" type="warning" :closable="false" class="import-tip" />
        <el-form v-else label-width="100px" class="import-form">
          <el-form-item label="科目名称"><el-input v-model="newTreeTitle" maxlength="64" /></el-form-item>
          <el-form-item label="科目标识"><el-input v-model="newTreeKey" maxlength="32" /><div v-if="duplicateImportKey" class="import-error">该标识已存在，请修改</div></el-form-item>
        </el-form>
        <div class="import-stats">{{ importPreview.stats.nodeCount }} 个节点 · {{ importPreview.stats.leafCount }} 个末级节点 · 最大深度 {{ Math.max(importPreview.stats.maxDepth + 1, 0) }} 层</div>
        <div class="import-preview-tree"><el-tree :data="importPreview.tree.children" node-key="id" default-expand-all :props="{ label: 'title', children: 'children' }" /></div>
        <div v-if="importPreview.issues.length" class="import-issues">
          <div v-for="(issue, index) in importPreview.issues" :key="`${issue.code || ''}-${index}`" :class="issue.level">
            {{ issue.message }}<span v-if="issue.path"> · {{ issue.path }}</span>
          </div>
        </div>
        <el-alert v-else title="Markdown 结构检查通过，可以导入。" type="success" :closable="false" class="import-tip" />
      </template>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importPreview || importPreview.issues.some(issue => issue.level === 'error')" @click="confirmMarkdownImport">确认导入为草稿</el-button>
      </template>
    </el-dialog>

    <el-empty v-if="!draft" description="选择或新增科目后开始维护" />
    <div v-else class="workspace">
      <section class="tree-pane">
        <div class="pane-head"><strong>知识结构</strong><el-button link type="primary" @click="addRoot">＋ 一级分类</el-button></div>
        <el-input v-model="searchTree" clearable placeholder="查找节点（拖动可调整层级）" class="tree-search" />
        <el-tree ref="treeRef" draggable @node-drop="onTreeDrop"
          :data="treeData" node-key="id" :props="{ label: 'title', children: 'children' }"
          :filter-node-method="(value: string, data: StructuredNode) => data.title.includes(value)"
          :current-node-key="selectedId" highlight-current class="tree-view"
          @node-click="(data: StructuredNode) => { selectedId = data.id; editorTab = 'edit' }"
        />
        <div class="tree-actions">
          <el-button size="small" :disabled="!selected" @click="addNode(true)">新增下级</el-button>
          <el-button size="small" :disabled="!selected" @click="addNode(false)">新增同级</el-button>
          <el-button size="small" :disabled="!selected" @click="moveNode(-1)">上移</el-button>
          <el-button size="small" :disabled="!selected" @click="moveNode(1)">下移</el-button>
          <el-button size="small" type="danger" plain :disabled="!selected" @click="removeNode">删除</el-button>
        </div>
      </section>

      <section class="detail-pane">
        <el-tabs v-model="editorTab" class="detail-tabs">
          <el-tab-pane label="编辑内容" name="edit">
            <div v-if="!selected" class="editor-scroll">
              <h3>科目设置</h3>
              <el-form label-position="top">
                <el-form-item label="科目名称"><el-input v-model="draft.title" maxlength="64" @input="markChanged" /></el-form-item>
                <el-form-item label="小程序简介"><el-input v-model="draft.description" type="textarea" :rows="3" maxlength="240" @input="markChanged" /></el-form-item>
              </el-form>
              <p class="hint">左侧选择节点编辑。一级分类可设置展示分组；未设置时直接按顺序展示。</p>
            </div>
            <div v-else class="editor-scroll">
              <h3>{{ selected.title }}</h3>
              <el-form label-position="top">
                <el-form-item label="节点名称"><el-input v-model="selected.title" maxlength="200" @input="markChanged" /></el-form-item>
                <el-form-item v-if="findParent(selected.id)?.parent === null" label="首页展示分组（可选）">
                  <el-input :model-value="nodeGroup(selected.id)" placeholder="例如：解题方法" @change="setGroup(selected.id, String($event))" />
                </el-form-item>
              </el-form>
              <div class="blocks-head"><strong>节点内容</strong><span class="hint">可留空，只展示结构</span></div>
              <div v-for="(block, index) in selected.blocks" :key="index" class="block-editor">
                <div class="block-top"><strong>{{ { text: '文字', formula: '公式', image: '图片', example: '例题' }[block.type] }}</strong><el-button link type="danger" @click="removeBlock(index)">移除</el-button></div>
                <el-input v-if="block.type === 'text'" v-model="block.text" type="textarea" :rows="4" placeholder="填写讲解或提示" @input="markChanged" />
                <template v-else-if="block.type === 'formula'">
                  <el-input v-model="block.latex" placeholder="LaTeX 公式，例如 \frac{B-A}{A}" @input="markChanged" />
                  <el-input v-model="block.plain" placeholder="必填：可读式，例如（现期－基期）÷基期" @input="markChanged" />
                  <div v-if="block.latex" class="formula-preview" v-html="formulaHtml(block.latex)" />
                </template>
                <template v-else-if="block.type === 'image'"><label class="hint">上传 PNG / JPEG（最多 3MB）<input type="file" accept="image/png,image/jpeg" @change="uploadImage(block, $event)" /></label><el-input v-model="block.url" placeholder="HTTPS 图片地址" @input="markChanged" /><el-input v-model="block.alt" placeholder="图片说明" @input="markChanged" /></template>
                <template v-else><el-input v-model="block.question" type="textarea" :rows="3" placeholder="例题题干" @input="markChanged" /><el-input v-model="block.answer" type="textarea" :rows="3" placeholder="解析" @input="markChanged" /></template>
              </div>
              <div class="add-block">
                <el-button size="small" @click="addBlock('text')">＋ 文字</el-button>
                <el-button size="small" @click="addBlock('formula')">＋ 公式</el-button>
                <el-button size="small" @click="addBlock('image')">＋ 图片</el-button>
                <el-button size="small" @click="addBlock('example')">＋ 例题</el-button>
              </div>
              <div v-if="issues.length" class="issues"><div v-for="(issue, i) in issues.slice(0, 12)" :key="i" :class="issue.level">{{ issue.message }}</div></div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="手机预览" name="preview">
            <div class="phone-wrap"><div class="phone">
              <div class="phone-hero"><small>知识框架 · 草稿预览</small><h2>{{ draft.title }}</h2><p>{{ draft.description || '按分类逐层浏览，找到知识点所在的位置。' }}</p></div>
              <div class="phone-body">
                <div class="phone-crumb"><span @click="previewUp(0)">{{ draft.title }}</span><span v-for="(id, i) in previewPath" :key="id" @click="previewUp(i + 1)"> › {{ findParent(id)?.list[findParent(id)!.index].title }}</span></div>
                <div class="phone-tabs"><span :class="{ active: previewMode === 'directory' }" @click="previewMode = 'directory'">逐层浏览</span><span :class="{ active: previewMode === 'overview' }" @click="previewMode = 'overview'">结构总览</span></div>
                <template v-if="previewMode === 'directory'">
                  <el-input v-model="previewQuery" placeholder="搜索知识节点" size="small" clearable />
                  <template v-if="previewQuery"><div class="phone-meta">找到 {{ previewHits.length }} 个节点</div><div v-for="n in previewHits" :key="n.id" class="phone-row" @click="previewSearchEnter(n)">{{ n.title }} ›</div></template>
                  <template v-else-if="previewNode && !previewNode.children.length"><h3>{{ previewNode.title }}</h3><div v-if="!previewNode.blocks.length" class="phone-meta">当前只有知识结构，讲解待补充。</div><div v-for="(b, i) in previewNode.blocks" :key="i" class="phone-block"><div v-if="b.type === 'text'">{{ b.text }}</div><div v-else-if="b.type === 'formula'"><div v-html="formulaHtml(b.latex)" />{{ b.plain }}</div><div v-else-if="b.type === 'image'"><img :src="b.url" :alt="b.alt" /><small>{{ b.alt }}</small></div><div v-else>例题：{{ b.question }}<br />解析：{{ b.answer }}</div></div></template>
                  <template v-else-if="!previewPath.length"><div v-for="group in groups" :key="group.title"><h3>{{ group.title }}</h3><div v-for="n in group.nodes" :key="n.id" class="phone-row" @click="previewEnter(n)">{{ n.title }} <small>{{ n.children.length }} 个分支 ›</small></div></div></template>
                  <template v-else><h3>{{ previewNode?.title }}</h3><div v-for="(b, i) in previewNode?.blocks || []" :key="i" class="phone-block"><div v-if="b.type === 'text'">{{ b.text }}</div><div v-else-if="b.type === 'formula'"><div v-html="formulaHtml(b.latex)" />{{ b.plain }}</div><div v-else-if="b.type === 'image'"><img :src="b.url" :alt="b.alt" /><small>{{ b.alt }}</small></div><div v-else>例题：{{ b.question }}<br />解析：{{ b.answer }}</div></div><div v-for="n in previewChildren" :key="n.id" class="phone-row" @click="previewEnter(n)">{{ n.title }} <small>{{ n.children.length ? `${n.children.length} 个分支` : '末级' }} ›</small></div></template>
                </template>
                <template v-else><p class="phone-meta">只展示前两层，点击可继续逐层浏览。</p><div v-for="n in draft.children" :key="n.id" class="phone-overview"><strong @click="previewPath = [n.id]; previewMode = 'directory'">{{ n.title }} ›</strong><div class="phone-chips"><span v-for="child in n.children" :key="child.id" @click="previewPath = [n.id, child.id]; previewMode = 'directory'">{{ child.title }}</span></div></div></template>
              </div>
            </div></div>
          </el-tab-pane>
        </el-tabs>
      </section>
    </div>
  </div>
</template>

<style scoped>
.knowledge-workbench{height:calc(100vh - 100px);min-height:620px;display:flex;flex-direction:column;gap:12px}.topbar{background:var(--el-bg-color);border:1px solid var(--el-border-color-lighter);border-radius:10px;padding:12px 16px}.top-main,.top-sub{display:flex;align-items:center;gap:10px}.top-sub{margin-top:9px;color:var(--el-text-color-secondary);font-size:12px}.subject-select{width:220px}.top-spacer{flex:1}.status,.hint{color:var(--el-text-color-secondary);font-size:12px}.workspace{flex:1;min-height:0;display:grid;grid-template-columns:minmax(300px,38%) 1fr;gap:12px}.tree-pane,.detail-pane{min-width:0;background:var(--el-bg-color);border:1px solid var(--el-border-color-lighter);border-radius:10px;min-height:0;display:flex;flex-direction:column;padding:14px}.pane-head,.blocks-head{display:flex;justify-content:space-between;align-items:center}.tree-search{margin:12px 0}.tree-view{flex:1;overflow:auto}.tree-actions{display:flex;flex-wrap:wrap;gap:6px;border-top:1px solid var(--el-border-color-lighter);padding-top:12px}.tree-actions .el-button{margin:0}.detail-tabs{height:100%;display:flex;flex-direction:column}.detail-tabs :deep(.el-tabs__content){flex:1;min-height:0}.detail-tabs :deep(.el-tab-pane){height:100%}.editor-scroll{height:100%;overflow:auto;padding:5px 5px 20px}.editor-scroll h3{margin:4px 0 18px}.block-editor{border:1px solid var(--el-border-color);border-radius:9px;padding:12px;margin:12px 0;display:flex;flex-direction:column;gap:10px}.block-top{display:flex;justify-content:space-between;align-items:center}.add-block{display:flex;gap:7px;flex-wrap:wrap;margin:14px 0}.add-block .el-button{margin:0}.formula-preview{padding:12px;background:var(--el-fill-color-light);overflow:auto}.issues{margin-top:20px;font-size:12px}.issues>div{padding:5px}.issues .error{color:var(--el-color-danger)}.issues .warning{color:var(--el-color-warning)}.phone-wrap{height:100%;overflow:auto;background:var(--el-fill-color-light);display:flex;justify-content:center;padding:10px}.phone{width:390px;max-width:100%;flex-shrink:0;min-height:620px;background:#f3f4f6;color:#1a1a1a;box-shadow:0 5px 24px #0001;border-radius:22px;overflow:hidden}.phone-hero{background:linear-gradient(155deg,#d0021b,#8b0000);color:white;padding:22px 20px}.phone-hero small{font-size:12px}.phone-hero h2{margin:18px 0 7px}.phone-hero p{font-size:12px;line-height:1.6}.phone-body{padding:15px}.phone-crumb{font-size:12px;color:#d0021b;white-space:nowrap;overflow:auto;margin-bottom:14px}.phone-crumb span{cursor:pointer}.phone-tabs{display:flex;background:white;border-radius:9px;padding:4px;margin-bottom:12px}.phone-tabs span{flex:1;text-align:center;padding:7px;cursor:pointer;font-size:12px}.phone-tabs .active{background:#fbeaec;color:#d0021b;border-radius:7px}.phone-body h3{font-size:15px;margin:14px 0 9px}.phone-row{background:white;border:1px solid #eee;border-radius:10px;padding:12px;margin:8px 0;cursor:pointer;font-size:13px;line-height:1.4}.phone-row small{display:block;color:#888;margin-top:5px}.phone-meta{color:#888;font-size:12px;line-height:1.6;margin:12px 0}.phone-block,.phone-overview{padding:12px;background:white;border-radius:10px;margin:9px 0;line-height:1.6;font-size:13px}.phone-block img{max-width:100%}.phone-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.phone-chips span{background:#f5f5f5;border-radius:6px;padding:5px 7px;cursor:pointer;font-size:11px}
.import-tip,.import-form{margin:12px 0}.import-file-button{display:inline-flex;align-items:center;border:1px solid var(--el-border-color);border-radius:6px;padding:8px 14px;color:var(--el-text-color-regular);cursor:pointer}.import-file-button:hover{color:var(--el-color-primary);border-color:var(--el-color-primary)}.import-file-button input{display:none}.import-filename{margin-left:10px;color:var(--el-text-color-secondary);font-size:13px}.import-stats{margin:14px 0;color:var(--el-text-color-secondary);font-size:13px}.import-preview-tree{max-height:230px;overflow:auto;border:1px solid var(--el-border-color-lighter);border-radius:6px;padding:8px}.import-issues{max-height:150px;overflow:auto;margin-top:12px;font-size:12px}.import-issues>div{padding:4px 0}.import-issues .error,.import-error{color:var(--el-color-danger)}.import-issues .warning{color:var(--el-color-warning)}.import-error{font-size:12px;line-height:20px}
@media(max-width:1100px){.knowledge-workbench{height:auto}.top-main{flex-wrap:wrap}.subject-select{width:180px}.workspace{grid-template-columns:minmax(0,1fr)}.tree-pane{height:320px}.detail-pane{height:700px}.top-sub{flex-wrap:wrap}.phone-wrap{box-sizing:border-box}}
</style>
