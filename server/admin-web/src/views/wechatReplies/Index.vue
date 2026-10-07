<template>
  <div class="reply-page">
    <el-card shadow="never" class="intro-card">
      <div class="intro-head">
        <div>
          <h2>公众号消息回复</h2>
          <p>集中维护关注欢迎语、关键词回复和兜底文案。回调只使用已发布版本。</p>
        </div>
        <div class="version-badge">
          <span>线上版本</span>
          <strong>{{ state?.activeVersion ? `v${state.activeVersion}` : '未发布' }}</strong>
        </div>
      </div>
      <el-alert type="info" :closable="false" show-icon>
        编辑内容先保存为草稿；发布后才会影响公众号回调。链接可直接写入回复，也可使用 &#123;&#123;today_url&#125;&#125;、&#123;&#123;theory_url&#125;&#125;、&#123;&#123;rmrb_url&#125;&#125; 三个站内入口变量。
      </el-alert>
      <div class="status-line">
        <span>当前发布：{{ state?.releases.find(item => item.isCurrent)?.publishedAt || '暂无' }}</span>
        <span v-if="state?.updatedAt">草稿更新：{{ state.updatedAt }} · {{ state.updatedByName || '未知' }}</span>
      </div>
    </el-card>

    <el-tabs v-model="activeTab" class="main-tabs">
      <el-tab-pane label="回复配置" name="config">
        <el-card shadow="never" v-loading="loading" class="config-card">
          <template #header>
            <div class="section-head">
              <div><strong>基础回复</strong><span class="sub">用户关注、规则未命中或发送非文字消息时使用</span></div>
              <div class="button-row">
                <el-button @click="runValidation" :loading="validating">检查配置</el-button>
                <el-button @click="previewVisible = true">预览回复</el-button>
                <el-button v-if="auth.hasPermission('wechat_reply:write')" @click="saveDraft" :loading="saving">保存草稿</el-button>
                <el-button v-if="auth.hasPermission('wechat_reply:publish')" type="primary" @click="publishDraft" :loading="publishing">发布配置</el-button>
              </div>
            </div>
          </template>

          <el-alert v-if="validation && !validation.valid" type="error" :closable="false" title="配置检查未通过">
            <div v-for="issue in validation.errors" :key="issue">{{ issue }}</div>
          </el-alert>
          <el-alert v-if="validation?.warnings.length" class="validation-alert" type="warning" :closable="false" title="检查提示">
            <div v-for="issue in validation.warnings" :key="issue">{{ issue }}</div>
          </el-alert>

          <el-row :gutter="18" class="basic-replies">
            <el-col :xs="24" :lg="12">
              <el-form-item label="关注欢迎语">
                <el-input v-model="draft.welcomeReply" type="textarea" :rows="7" maxlength="4000" show-word-limit />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :lg="12">
              <el-form-item label="未命中关键词">
                <el-input v-model="draft.fallbackReply" type="textarea" :rows="7" maxlength="4000" show-word-limit />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :lg="12">
              <el-form-item label="非文字消息">
                <el-input v-model="draft.unsupportedMessageReply" type="textarea" :rows="3" maxlength="4000" show-word-limit />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :lg="12">
              <el-form-item label="其他事件">
                <el-input v-model="draft.unsupportedEventReply" type="textarea" :rows="3" maxlength="4000" show-word-limit />
              </el-form-item>
            </el-col>
          </el-row>

          <div class="section-head rules-head">
            <div><strong>关键词规则</strong><span class="sub">精确匹配优先；包含匹配按优先级、关键词长度稳定排序</span></div>
            <el-button v-if="auth.hasPermission('wechat_reply:write')" type="primary" plain @click="addRule">新增规则</el-button>
          </div>

          <el-empty v-if="!draft.keywordRules.length" description="还没有关键词规则" />
          <div v-for="(rule, index) in draft.keywordRules" :key="rule.id" class="rule-card">
            <div class="rule-top">
              <div class="rule-label">规则 {{ index + 1 }}</div>
              <el-form-item label="规则名称" class="rule-name"><el-input v-model="rule.name" maxlength="64" /></el-form-item>
              <el-form-item label="优先级"><el-input-number v-model="rule.priority" :min="-10000" :max="10000" controls-position="right" /></el-form-item>
              <el-form-item label="启用"><el-switch v-model="rule.enabled" /></el-form-item>
              <el-button v-if="auth.hasPermission('wechat_reply:write')" type="danger" link @click="removeRule(index)">删除</el-button>
            </div>
            <el-row :gutter="18">
              <el-col :xs="24" :lg="8">
                <el-form-item label="触发关键词">
                  <el-input :model-value="rule.keywords.join('\n')" type="textarea" :rows="5" placeholder="每行一个关键词，例如：&#10;十五五&#10;十五五规划" @update:model-value="setKeywords(rule, $event)" />
                </el-form-item>
                <el-form-item label="匹配方式">
                  <el-radio-group v-model="rule.matchType">
                    <el-radio value="exact">整句精确</el-radio>
                    <el-radio value="contains">消息包含</el-radio>
                  </el-radio-group>
                </el-form-item>
              </el-col>
              <el-col :xs="24" :lg="16">
                <el-form-item label="回复内容">
                  <el-input v-model="rule.responseText" type="textarea" :rows="7" maxlength="4000" show-word-limit placeholder="可直接填写文字、网盘链接或站内入口变量" />
                </el-form-item>
              </el-col>
            </el-row>
          </div>

          <div class="bottom-actions">
            <el-button @click="reloadDraft" :disabled="loading || saving">放弃未保存修改</el-button>
            <el-button @click="runValidation" :loading="validating">检查草稿</el-button>
            <el-button v-if="auth.hasPermission('wechat_reply:write')" @click="saveDraft" :loading="saving">保存草稿</el-button>
            <el-button v-if="auth.hasPermission('wechat_reply:publish')" type="primary" @click="publishDraft" :loading="publishing">发布配置</el-button>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="发布历史与回退" name="history">
        <el-card shadow="never" v-loading="loading">
          <el-alert type="info" :closable="false" show-icon class="history-note">
            每次发布都会保留不可覆盖的快照。回退会新建一个版本并切换线上指针，不会删除后续版本。
          </el-alert>
          <el-table :data="state?.releases || []" stripe>
            <el-table-column prop="version" label="版本" width="100"><template #default="{ row }">v{{ row.version }}</template></el-table-column>
            <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag v-if="row.isCurrent" type="success">线上版本</el-tag><span v-else>历史版本</span></template></el-table-column>
            <el-table-column prop="publishedAt" label="发布时间" min-width="180" />
            <el-table-column prop="publishedByName" label="操作人" width="140" />
            <el-table-column label="说明" min-width="150"><template #default="{ row }">{{ row.rollbackFromVersion ? `由 v${row.rollbackFromVersion} 回退生成` : '正常发布' }}</template></el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button v-if="!row.isCurrent && auth.hasPermission('wechat_reply:publish')" link type="primary" @click="rollback(row)">回退到此版</el-button>
                <span v-else-if="row.isCurrent" class="sub">当前使用</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!state?.releases.length" description="暂无发布版本" />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="previewVisible" title="回复预览" width="720px">
      <el-form label-width="100px">
        <el-form-item label="消息类型">
          <el-radio-group v-model="previewType"><el-radio value="text">文字消息</el-radio><el-radio value="subscribe">关注事件</el-radio></el-radio-group>
        </el-form-item>
        <el-form-item v-if="previewType === 'text'" label="模拟输入">
          <el-input v-model="previewMessage" maxlength="1000" placeholder="例如：十五五规划" @keyup.enter="runPreview" />
        </el-form-item>
        <el-form-item v-else label="事件"><el-tag>新用户关注</el-tag></el-form-item>
      </el-form>
      <div v-if="previewResult" class="preview-result">
        <div class="preview-meta">命中：{{ previewResult.intent }}<span v-if="previewResult.matchedRuleId"> · {{ previewResult.matchedRuleId }}</span></div>
        <pre>{{ previewResult.reply || '不回复' }}</pre>
      </div>
      <template #footer><el-button @click="previewVisible = false">关闭</el-button><el-button type="primary" :loading="previewing" @click="runPreview">生成预览</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import {
  fetchWechatReplyState,
  previewWechatReply,
  publishWechatReplyDraft,
  rollbackWechatReply,
  saveWechatReplyDraft,
  validateWechatReplyConfig,
  type WechatKeywordRule,
  type WechatReplyConfig,
  type WechatReplyPreview,
  type WechatReplyRelease,
  type WechatReplyState,
  type WechatReplyValidation,
} from '@/api/wechatReplies'

const auth = useAuthStore()
const state = ref<WechatReplyState | null>(null)
const draft = reactive<WechatReplyConfig>({ welcomeReply: '', fallbackReply: '', unsupportedMessageReply: '', unsupportedEventReply: '', keywordRules: [] })
const loading = ref(false)
const saving = ref(false)
const publishing = ref(false)
const validating = ref(false)
const previewing = ref(false)
const activeTab = ref('config')
const validation = ref<WechatReplyValidation | null>(null)
const previewVisible = ref(false)
const previewType = ref<'text' | 'subscribe'>('text')
const previewMessage = ref('')
const previewResult = ref<WechatReplyPreview | null>(null)

function copyConfig(source: WechatReplyConfig) {
  Object.assign(draft, structuredClone(source))
}

async function loadState() {
  loading.value = true
  try {
    state.value = await fetchWechatReplyState()
    copyConfig(state.value.draft)
    validation.value = null
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取公众号回复配置失败')
  } finally {
    loading.value = false
  }
}

function setKeywords(rule: WechatKeywordRule, value: string) {
  rule.keywords = value.split(/[\n,，、]+/).map(item => item.trim()).filter(Boolean)
}

function addRule() {
  const id = `custom_${crypto.randomUUID().replace(/-/g, '').slice(0, 12)}`
  draft.keywordRules.push({ id, name: '新关键词规则', keywords: [], matchType: 'exact', responseText: '', enabled: true, priority: 100 })
}

function removeRule(index: number) {
  draft.keywordRules.splice(index, 1)
}

function currentConfig(): WechatReplyConfig {
  return structuredClone(draft)
}

async function runValidation() {
  validating.value = true
  try {
    validation.value = await validateWechatReplyConfig(currentConfig())
    if (validation.value.valid) ElMessage.success(validation.value.warnings.length ? '配置检查通过，请查看提示' : '配置检查通过')
    else ElMessage.warning('配置有错误，请按提示修正')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '配置检查失败')
  } finally {
    validating.value = false
  }
}

async function saveDraft() {
  saving.value = true
  try {
    state.value = await saveWechatReplyDraft(currentConfig())
    copyConfig(state.value.draft)
    ElMessage.success('草稿已保存；线上仍使用当前发布版本')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存草稿失败')
  } finally {
    saving.value = false
  }
}

async function publishDraft() {
  publishing.value = true
  try {
    state.value = await saveWechatReplyDraft(currentConfig())
    copyConfig(state.value.draft)
    const result = await validateWechatReplyConfig(currentConfig())
    validation.value = result
    if (!result.valid) {
      ElMessage.error(result.errors.join('；'))
      return
    }
    if (result.warnings.length) {
      await ElMessageBox.confirm(result.warnings.join('\n'), '配置有提示', { confirmButtonText: '继续发布', cancelButtonText: '返回修改', type: 'warning' })
    }
    await ElMessageBox.confirm('发布后，公众号回调将立即使用这套回复规则。', '发布回复配置', { confirmButtonText: '确认发布', cancelButtonText: '取消', type: 'info' })
    state.value = await publishWechatReplyDraft()
    copyConfig(state.value.draft)
    validation.value = null
    ElMessage.success(`已发布 v${state.value.activeVersion}`)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '发布失败')
  } finally {
    publishing.value = false
  }
}

async function reloadDraft() {
  await loadState()
  ElMessage.success('已载入服务器保存的草稿')
}

async function runPreview() {
  previewing.value = true
  try {
    previewResult.value = await previewWechatReply(
      previewMessage.value,
      currentConfig(),
      previewType.value === 'subscribe' ? 'event' : 'text',
      previewType.value === 'subscribe' ? 'subscribe' : '',
    )
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '生成预览失败')
  } finally {
    previewing.value = false
  }
}

async function rollback(release: WechatReplyRelease) {
  try {
    await ElMessageBox.confirm(`将线上回复恢复为 v${release.version} 的内容。系统会新建一个回退发布版本。`, '确认回退', { confirmButtonText: '确认回退', cancelButtonText: '取消', type: 'warning' })
    state.value = await rollbackWechatReply(release.id)
    copyConfig(state.value.draft)
    ElMessage.success(`已回退并生成 v${state.value.activeVersion}`)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '回退失败')
  }
}

onMounted(loadState)
</script>

<style scoped>
.reply-page { display: flex; flex-direction: column; gap: 16px; }
.intro-head, .section-head, .rule-top, .button-row, .status-line, .bottom-actions { display: flex; align-items: center; }
.intro-head, .section-head { justify-content: space-between; gap: 16px; }
.intro-head h2 { margin: 0; font-size: 20px; }
.intro-head p, .sub { color: var(--el-text-color-secondary); font-size: 13px; }
.intro-head p { margin: 6px 0 12px; }
.version-badge { min-width: 92px; padding: 10px 14px; text-align: center; border-radius: 10px; background: var(--el-color-primary-light-9); color: var(--el-color-primary); }
.version-badge span, .version-badge strong { display: block; }
.version-badge strong { margin-top: 4px; font-size: 20px; }
.status-line { justify-content: space-between; margin-top: 12px; color: var(--el-text-color-secondary); font-size: 12px; flex-wrap: wrap; gap: 8px; }
.main-tabs { background: transparent; }
.config-card { min-height: 400px; }
.section-head strong { margin-right: 12px; }
.button-row { gap: 8px; }
.basic-replies { margin-top: 4px; }
.rules-head { margin: 10px 0 16px; }
.rule-card { padding: 16px 16px 4px; margin-bottom: 14px; border: 1px solid var(--el-border-color-light); border-radius: 8px; }
.rule-top { gap: 12px; flex-wrap: wrap; }
.rule-label { min-width: 52px; color: var(--el-text-color-secondary); font-size: 13px; }
.rule-name { flex: 1; min-width: 180px; }
.rule-card :deep(.el-form-item) { margin-bottom: 14px; }
.rule-card :deep(.rule-name .el-form-item__content) { min-width: 160px; }
.bottom-actions { justify-content: flex-end; gap: 8px; padding-top: 16px; border-top: 1px solid var(--el-border-color-lighter); }
.validation-alert { margin-top: 12px; }
.preview-result { border: 1px solid var(--el-border-color-light); border-radius: 8px; background: var(--el-fill-color-light); }
.preview-meta { padding: 10px 14px; color: var(--el-text-color-secondary); border-bottom: 1px solid var(--el-border-color-lighter); }
.preview-result pre { padding: 12px 14px; margin: 0; white-space: pre-wrap; word-break: break-word; font: inherit; line-height: 1.6; }
.history-note { margin-bottom: 16px; }
@media (max-width: 820px) {
  .intro-head, .section-head { align-items: flex-start; flex-direction: column; }
  .button-row { flex-wrap: wrap; }
  .bottom-actions { flex-wrap: wrap; }
}
</style>
