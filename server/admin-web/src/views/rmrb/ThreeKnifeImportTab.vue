<template>
  <div>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      将三刀解剖法练习的 Markdown 粘贴到下方，点击「解析预览」确认结构化结果，再点击「导入保存」写入开采本。
    </el-alert>

    <div class="import-layout">
      <!-- 左侧：Markdown 输入 -->
      <div class="input-panel">
        <div class="panel-header">
          <span>Markdown 原文</span>
          <el-button size="small" @click="markdown = ''">清空</el-button>
        </div>
        <el-input
          v-model="markdown"
          type="textarea"
          :rows="24"
          placeholder="粘贴三刀解剖 Markdown 全文…"
          class="md-input"
        />
      </div>

      <!-- 右侧：预览结果 -->
      <div class="preview-panel">
        <div class="panel-header">
          <span>解析预览</span>
          <el-button
            size="small"
            type="primary"
            :loading="previewing"
            :disabled="!markdown.trim()"
            @click="doPreview"
          >
            解析预览
          </el-button>
        </div>

        <div v-if="!summary && !previewError" class="preview-empty">
          点击「解析预览」查看结构化结果
        </div>

        <el-alert v-if="previewError" type="error" :title="previewError" :closable="false" style="margin-bottom: 12px" />

        <template v-if="summary">
          <!-- 摘要卡片 -->
          <div class="summary-cards">
            <div class="card">
              <div class="card-title">文章标题</div>
              <div class="card-value">{{ summary.articleTitle || '—' }}</div>
            </div>
            <div class="card">
              <div class="card-title">练习日期</div>
              <div class="card-value">{{ summary.mineDate }}</div>
            </div>
          </div>
          <div class="summary-stats">
            <el-tag type="primary">规范词 {{ summary.termsCount }}</el-tag>
            <el-tag type="warning">金句 {{ summary.quotesCount }}</el-tag>
            <el-tag type="success">动词 {{ summary.verbsCount }}</el-tag>
            <el-tag type="info">分论点 {{ summary.pointsCount }}</el-tag>
            <el-tag type="danger">句式 {{ summary.templatesCount }}</el-tag>
          </div>

          <!-- 详细预览 -->
          <el-collapse v-if="parsed" style="margin-top: 12px">
            <el-collapse-item title="规范词" :name="'terms'">
              <el-table :data="parsedTerms" size="small" max-height="200">
                <el-table-column prop="term" label="规范词" width="120" />
                <el-table-column prop="category" label="分类" width="120" />
                <el-table-column prop="plainWord" label="普通表达" />
              </el-table>
            </el-collapse-item>
            <el-collapse-item title="金句" :name="'quotes'">
              <el-table :data="parsedQuotes" size="small" max-height="160">
                <el-table-column prop="text" label="金句" />
                <el-table-column prop="source" label="出处" width="120" />
                <el-table-column prop="meaning" label="释义" />
              </el-table>
            </el-collapse-item>
            <el-collapse-item title="高频动词" :name="'verbs'">
              <el-table :data="parsedVerbs" size="small" max-height="160">
                <el-table-column prop="verb" label="动词" width="100" />
                <el-table-column prop="usage" label="适用语境" />
              </el-table>
            </el-collapse-item>
            <el-collapse-item title="论证骨架" :name="'argument'">
              <div v-if="parsedArgument" class="argument-preview">
                <div v-if="parsedArgument.overview" class="arg-overview">
                  <strong>总骨架：</strong>
                  <pre>{{ parsedArgument.overview }}</pre>
                </div>
                <div v-for="(pt, i) in parsedArgument.points" :key="i" class="arg-point">
                  <strong>分论点 {{ i + 1 }}：{{ pt.title }}</strong>
                  <div v-if="pt.method" class="arg-method">方法：{{ pt.method }}</div>
                  <div v-if="pt.template" class="arg-template">
                    <strong>套用模板：</strong>
                    <pre>{{ pt.template }}</pre>
                  </div>
                </div>
              </div>
            </el-collapse-item>
            <el-collapse-item title="万能句式" :name="'templates'">
              <div v-for="(t, i) in parsedTemplates" :key="i" class="template-item">
                <el-tag size="small" type="info">{{ t.type?.toUpperCase() }} · {{ t.typeName }}</el-tag>
                <div class="tpl-original"><strong>原文：</strong>{{ t.original }}</div>
                <div v-if="t.template" class="tpl-pattern"><strong>模板：</strong>{{ t.template }}</div>
              </div>
            </el-collapse-item>
          </el-collapse>

          <!-- 导入按钮 -->
          <div class="import-actions">
            <el-button
              type="success"
              :loading="importing"
              @click="doImport"
            >
              导入保存到开采本
            </el-button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  importThreeKnife,
  previewThreeKnife,
  type ThreeKnifePreviewResult,
  type ThreeKnifeSummary,
} from '@/api/rmrb'

const markdown = ref('')
const previewing = ref(false)
const importing = ref(false)
const previewError = ref('')
const summary = ref<ThreeKnifeSummary | null>(null)
const parsed = ref<Record<string, unknown> | null>(null)

const parsedTerms = computed(() => (parsed.value?.terms as Array<Record<string, string>>) || [])
const parsedQuotes = computed(() => (parsed.value?.quotes as Array<Record<string, string>>) || [])
const parsedVerbs = computed(() => (parsed.value?.verbs as Array<Record<string, string>>) || [])
const parsedArgument = computed(() => parsed.value?.argument as {
  overview?: string
  conclusion?: string
  points?: Array<{ title: string; method?: string; template?: string }>
} | undefined)
const parsedTemplates = computed(() => (parsed.value?.templates as Array<Record<string, string>>) || [])

async function doPreview() {
  if (!markdown.value.trim()) return
  previewing.value = true
  previewError.value = ''
  summary.value = null
  parsed.value = null
  try {
    const res: ThreeKnifePreviewResult = await previewThreeKnife(markdown.value)
    summary.value = res.summary
    parsed.value = res.parsed
  } catch (e) {
    previewError.value = e instanceof Error ? e.message : '解析失败'
  } finally {
    previewing.value = false
  }
}

async function doImport() {
  if (!markdown.value.trim()) return
  importing.value = true
  try {
    const res = await importThreeKnife(markdown.value)
    ElMessage.success(
      `已导入「${res.summary.articleTitle}」：${res.summary.termsCount} 规范词、${res.summary.templatesCount} 句式、${res.summary.pointsCount} 分论点`,
    )
    markdown.value = ''
    summary.value = null
    parsed.value = null
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.import-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.input-panel,
.preview-panel {
  flex: 1;
  min-width: 0;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-weight: 600;
}
.md-input :deep(textarea) {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 12px;
  line-height: 1.6;
}
.preview-empty {
  color: #999;
  text-align: center;
  padding: 60px 0;
}
.summary-cards {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}
.card {
  flex: 1;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
}
.card-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.card-value {
  font-size: 15px;
  font-weight: 600;
}
.summary-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.argument-preview pre {
  white-space: pre-wrap;
  font-size: 12px;
  margin: 4px 0;
  background: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
}
.arg-point {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px dashed #e4e7ed;
}
.arg-method {
  color: #67c23a;
  font-size: 13px;
  margin: 4px 0;
}
.template-item {
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}
.tpl-original,
.tpl-pattern {
  font-size: 13px;
  margin-top: 4px;
}
.import-actions {
  margin-top: 16px;
  text-align: right;
}
</style>
