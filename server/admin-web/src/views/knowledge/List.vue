<template>
  <div class="page">
    <div class="toolbar">
      <el-upload
        :show-file-list="false"
        :before-upload="onBeforeUpload"
        :http-request="onUploadMd"
        accept=".md"
      >
        <el-button type="primary" :loading="uploading">上传 Markdown</el-button>
      </el-upload>
    </div>

    <el-alert
      v-if="treeList.length"
      type="success"
      :closable="false"
      style="margin-bottom: 12px"
      :title="`共 ${treeList.length} 棵知识树（通过上传 Markdown 新增/更新）`"
    >
      <div style="font-size: 12px; color: #666; margin-top: 4px">
        <el-tag v-for="t in treeList" :key="t.treeKey" size="small" style="margin-right: 6px">
          {{ t.title }}
        </el-tag>
      </div>
    </el-alert>

    <el-tabs v-model="activeKey" @tab-change="onTabChange">
      <el-tab-pane v-for="t in treeList" :key="t.treeKey" :label="t.title" :name="t.treeKey" />
    </el-tabs>

    <div v-if="!treeList.length" class="empty-wrap">
      <el-empty description="暂无知识树，请先上传 Markdown 文件" />
    </div>
    <div v-else-if="!activeKey" class="empty-wrap">
      <el-empty description="请选择一棵知识树" />
    </div>

    <div v-else class="tree-pane">
      <div class="tree-toolbar">
        <el-button type="primary" @click="openCreateDialog(null)">新增根节点</el-button>
        <el-button type="danger" plain @click="onDeleteTree">删除整棵树</el-button>
      </div>

      <el-tree
        :data="treeData"
        :props="{ label: 'title', children: 'children' }"
        node-key="id"
        default-expand-all
        :expand-on-click-node="false"
        style="margin-top: 12px"
      >
        <template #default="{ data }">
          <span class="tree-row">
            <span class="tree-title">
              <el-icon v-if="data.isStarred" class="star-icon"><Star /></el-icon>
              {{ data.title }}
              <el-tag v-if="data.sourceFile" size="small" type="info" style="margin-left: 6px">
                {{ data.sourceFile }}:{{ data.sourceLine || data.sortOrder }}
              </el-tag>
            </span>
            <span class="tree-actions" @click.stop>
              <el-dropdown trigger="click" @command="(cmd: string) => onNodeCommand(cmd, data)">
                <el-button text type="primary">操作</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="star">
                      {{ data.isStarred ? '取消重点' : '标为重点' }}
                    </el-dropdown-item>
                    <el-dropdown-item command="note">
                      备注{{ data.myNote ? '（已有）' : '' }}
                    </el-dropdown-item>
                    <el-dropdown-item command="child">添加子节点</el-dropdown-item>
                    <el-dropdown-item command="edit">编辑标题</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>
                      <span class="danger-text">删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </span>
          </span>
        </template>
      </el-tree>
    </div>

    <!-- 新增节点对话框 -->
    <el-dialog v-model="createVisible" :title="createTitle" width="460px">
      <el-form label-width="80px">
        <el-form-item label="所属树">
          <el-input :model-value="activeKey" disabled />
        </el-form-item>
        <el-form-item v-if="createParent" label="父节点">
          <el-input :model-value="createParent.title" disabled />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="createForm.title" placeholder="节点标题" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="createForm.content" type="textarea" :rows="3" placeholder="可选，节点详细说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑标题/内容对话框 -->
    <el-dialog v-model="editVisible" title="编辑节点" width="460px">
      <el-form label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="editForm.content" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="我的备注">
          <el-input v-model="editForm.myNote" type="textarea" :rows="3" placeholder="App 端也会显示" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onEditSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 备注 quick dialog -->
    <el-dialog v-model="noteVisible" title="节点备注" width="460px">
      <el-input v-model="noteText" type="textarea" :rows="4" placeholder="给这个节点加一句自己的笔记..." />
      <template #footer>
        <el-button @click="noteVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSaveNote">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Star } from '@element-plus/icons-vue'
import {
  createKnowledgeNode,
  deleteKnowledgeNode,
  deleteKnowledgeTree,
  fetchKnowledgeTrees,
  updateKnowledgeNode,
  uploadKnowledgeMd,
  type KnowledgeNode,
  type KnowledgeTree,
} from '@/api/knowledge'

const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const trees = ref<KnowledgeTree[]>([])
const activeKey = ref('')
const currentTree = ref<KnowledgeNode[]>([])

const treeList = computed(() => trees.value)

const treeData = computed(() => currentTree.value)

async function loadTrees() {
  loading.value = true
  try {
    trees.value = await fetchKnowledgeTrees()
    if (trees.value.length && !activeKey.value) {
      activeKey.value = trees.value[0].treeKey
      await loadTree(activeKey.value)
    } else if (activeKey.value) {
      await loadTree(activeKey.value)
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadTree(key: string) {
  try {
    const t = trees.value.find((x) => x.treeKey === key)
    if (t) {
      currentTree.value = t.nodes
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  }
}

function onTabChange(key: string) {
  activeKey.value = key
  loadTree(key)
}

function onBeforeUpload(file: File) {
  if (!file.name.endsWith('.md')) {
    ElMessage.warning('仅支持 .md 文件')
    return false
  }
  if (file.size > 1 * 1024 * 1024) {
    ElMessage.warning('文件不能超过 1MB')
    return false
  }
  return true
}

async function onUploadMd(options: { file: File }) {
  uploading.value = true
  try {
    const r = await uploadKnowledgeMd(options.file, true)
    ElMessage.success(`已上传并更新知识树：${r.treeKey}`)
    await loadTrees()
    if (r.treeKey) {
      activeKey.value = r.treeKey
      await loadTree(r.treeKey)
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '上传失败')
  } finally {
    uploading.value = false
  }
}

// ===== 新增节点 =====
const createVisible = ref(false)
const createParent = ref<KnowledgeNode | null>(null)
const createForm = reactive({ title: '', content: '' })

const createTitle = computed(() =>
  createParent.value ? `在「${createParent.value.title}」下新增子节点` : `在「${activeKey.value}」下新增根节点`,
)

function openCreateDialog(parent: KnowledgeNode | null) {
  createParent.value = parent
  createForm.title = ''
  createForm.content = ''
  createVisible.value = true
}

async function onCreate() {
  if (!createForm.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  saving.value = true
  try {
    await createKnowledgeNode({
      treeKey: activeKey.value,
      parentId: createParent.value?.id || null,
      title: createForm.title.trim(),
      content: createForm.content,
    })
    createVisible.value = false
    await loadTrees()
    ElMessage.success('已创建')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  } finally {
    saving.value = false
  }
}

// ===== 编辑节点 =====
const editVisible = ref(false)
const editTarget = ref<KnowledgeNode | null>(null)
const editForm = reactive({ title: '', content: '', myNote: '' })

function openEditDialog(node: KnowledgeNode) {
  editTarget.value = node
  editForm.title = node.title
  editForm.content = node.content
  editForm.myNote = node.myNote
  editVisible.value = true
}

async function onEditSave() {
  if (!editTarget.value) return
  if (!editForm.title.trim()) {
    ElMessage.warning('标题不能为空')
    return
  }
  saving.value = true
  try {
    await updateKnowledgeNode(editTarget.value.id, {
      title: editForm.title.trim(),
      content: editForm.content,
      myNote: editForm.myNote,
    })
    editVisible.value = false
    await loadTrees()
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

// ===== 备注 quick =====
const noteVisible = ref(false)
const noteTarget = ref<KnowledgeNode | null>(null)
const noteText = ref('')

function openNoteDialog(node: KnowledgeNode) {
  noteTarget.value = node
  noteText.value = node.myNote
  noteVisible.value = true
}

async function onSaveNote() {
  if (!noteTarget.value) return
  saving.value = true
  try {
    await updateKnowledgeNode(noteTarget.value.id, { myNote: noteText.value })
    noteVisible.value = false
    await loadTrees()
    ElMessage.success('备注已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleStar(node: KnowledgeNode) {
  try {
    await updateKnowledgeNode(node.id, { isStarred: !node.isStarred })
    await loadTrees()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  }
}

function onNodeCommand(cmd: string, data: KnowledgeNode) {
  if (cmd === 'star') toggleStar(data)
  else if (cmd === 'note') openNoteDialog(data)
  else if (cmd === 'child') openCreateDialog(data)
  else if (cmd === 'edit') openEditDialog(data)
  else if (cmd === 'delete') onDeleteNode(data)
}

async function onDeleteNode(node: KnowledgeNode) {
  try {
    await ElMessageBox.confirm(`确定删除「${node.title}」及其所有子节点？`, '提示', { type: 'warning' })
    await deleteKnowledgeNode(node.id)
    await loadTrees()
    ElMessage.success('已删除')
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e instanceof Error ? e.message : '删除失败')
    }
  }
}

async function onDeleteTree() {
  try {
    await ElMessageBox.confirm(`确定删除整棵「${activeKey.value}」知识树？`, '危险操作', { type: 'error' })
    await deleteKnowledgeTree(activeKey.value)
    ElMessage.success('已删除')
    activeKey.value = ''
    currentTree.value = []
    await loadTrees()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e instanceof Error ? e.message : '删除失败')
    }
  }
}

onMounted(() => {
  loadTrees()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
.empty-wrap {
  padding: 24px 0;
}
.tree-pane {
  background: var(--admin-card-bg);
  padding: 16px;
  border-radius: 6px;
}
.tree-toolbar {
  display: flex;
  gap: 8px;
}
.tree-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  padding-right: 8px;
  min-height: 36px;
  gap: 12px;
}
.star-icon {
  color: var(--admin-brand);
  margin-right: 4px;
}
.danger-text {
  color: var(--el-color-danger);
}
.tree-title {
  display: flex;
  align-items: center;
  gap: 4px;
}
.tree-actions {
  display: flex;
  gap: 4px;
}
</style>
