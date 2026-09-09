<template>
  <div>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      粘贴精拆 HTML，挂到当前时评的「时评解析」页，不会改原文。
    </el-alert>
    <el-form v-if="!boundArticleId" label-width="96px" style="margin-bottom: 12px">
      <el-form-item label="挂到时评" required>
        <el-select
          v-model="selectedId"
          filterable
          placeholder="先选一篇时评文章"
          style="width: 100%"
        >
          <el-option v-for="a in articleOptions" :key="a.id" :label="a.title" :value="a.id" />
        </el-select>
      </el-form-item>
    </el-form>
    <p v-else class="bound-title">当前时评：{{ boundTitle }}</p>
    <el-input
      v-model="displayHtml"
      type="textarea"
      :rows="18"
      placeholder="粘贴解析 HTML"
      class="html-input"
    />
    <div class="import-actions">
      <el-button @click="displayHtml = ''">清空</el-button>
      <el-button type="primary" :loading="importing" @click="doImport">导入解析</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchRmrbArticles, importThreeKnife, type RmrbArticle } from '@/api/rmrb'

const props = defineProps<{
  articleId?: string
  articleTitle?: string
}>()
const emit = defineEmits<{ imported: [] }>()

const boundArticleId = computed(() => (props.articleId || '').trim())
const selectedId = ref(boundArticleId.value)
const articleOptions = ref<RmrbArticle[]>([])
const boundTitle = computed(() => {
  if (props.articleTitle) return props.articleTitle
  return articleOptions.value.find((a) => a.id === selectedId.value)?.title || '已选时评'
})
const displayHtml = ref('')
const importing = ref(false)

watch(boundArticleId, (id) => {
  if (id) selectedId.value = id
})

async function doImport() {
  const articleId = selectedId.value.trim()
  if (!articleId) {
    ElMessage.warning('请先选择要挂解析的时评文章')
    return
  }
  if (!displayHtml.value.trim()) {
    ElMessage.warning('请粘贴解析 HTML')
    return
  }
  importing.value = true
  try {
    await importThreeKnife({ articleId, displayHtml: displayHtml.value })
    ElMessage.success('解析已挂上')
    displayHtml.value = ''
    emit('imported')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  if (!boundArticleId.value) {
    articleOptions.value = await fetchRmrbArticles()
  }
})
</script>

<style scoped>
.bound-title {
  margin: 0 0 12px;
  font-size: 14px;
  color: #606266;
}
.html-input :deep(textarea) {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 12px;
  line-height: 1.6;
}
.import-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
</style>
