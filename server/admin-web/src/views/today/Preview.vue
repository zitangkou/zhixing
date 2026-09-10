<template>
  <PageShell title="今日学员端">
    <template #extra>
      <el-button @click="load">刷新</el-button>
    </template>

    <el-alert type="info" :closable="false" class="intro">
      学员首页优先展示勾了「今日推荐」且已发布的时政、时评。两边都没有勾选时，会各取最近一篇已发布内容兜底。
    </el-alert>

    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-head">
              <span>时政 · 今日推荐</span>
              <el-button link type="primary" @click="router.push('/articles')">去文章管理</el-button>
            </div>
          </template>
          <el-skeleton v-if="loading" :rows="3" animated />
          <el-empty v-else-if="!theory.length" description="未勾选今日推荐，学员将看到最近一篇已发布时政" />
          <ul v-else class="pick-list">
            <li v-for="row in theory" :key="row.id">
              <button type="button" class="pick-link" @click="router.push(`/articles/${row.id}`)">
                {{ row.title }}
              </button>
              <span class="muted">{{ row.publishDate || row.status }}</span>
            </li>
          </ul>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-head">
              <span>时评 · 今日推荐</span>
              <el-button link type="primary" @click="router.push('/rmrb/articles')">去时评文章</el-button>
            </div>
          </template>
          <el-skeleton v-if="loading" :rows="3" animated />
          <el-empty v-else-if="!rmrb.length" description="未勾选今日推荐，学员将看到最近一篇已发布时评" />
          <ul v-else class="pick-list">
            <li v-for="row in rmrb" :key="row.id">
              <span class="pick-title">{{ row.title }}</span>
              <span class="muted">{{ row.isPublished ? '已发布' : '未发布' }} · {{ row.publishDate }}</span>
            </li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </PageShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageShell from '@/components/PageShell.vue'
import { fetchArticles } from '@/api/articles'
import { fetchRmrbArticles, type RmrbArticle } from '@/api/rmrb'
import type { Article } from '@/types'

const router = useRouter()
const loading = ref(false)
const theory = ref<Article[]>([])
const rmrb = ref<RmrbArticle[]>([])

async function load() {
  loading.value = true
  theory.value = []
  rmrb.value = []
  try {
    const articles = await fetchArticles({ page: 1, page_size: 50, is_daily: true, status: 'published' })
    theory.value = articles.items || []
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '时政列表加载失败')
  }
  try {
    const rmrbRows = await fetchRmrbArticles()
    rmrb.value = (rmrbRows || []).filter((row) => row.isDaily)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '时评列表加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.intro { margin-bottom: 16px; }
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.pick-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.pick-list li {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.pick-list li:last-child { border-bottom: none; }
.pick-link {
  margin: 0;
  padding: 0;
  border: none;
  background: none;
  text-align: left;
  font: inherit;
  color: var(--el-color-primary);
  cursor: pointer;
}
.pick-title { font-weight: 600; }
.muted { font-size: 12px; color: var(--el-text-color-secondary); }
.el-col { margin-bottom: 16px; }
</style>
