<template>
  <div class="question-analytics">
    <!-- 返回 + 标题 -->
    <div class="page-header">
      <el-button :icon="ArrowLeft" link @click="router.back()">返回</el-button>
      <span class="page-title">单题分析 — {{ questionId }}</span>
    </div>

    <div v-loading="loading">
      <!-- 题目信息卡 -->
      <div class="panel">
        <div class="panel-title">题目信息</div>
        <div class="question-info" v-if="questionMeta">
          <div class="info-row">
            <el-tag type="primary" size="small">{{ questionMeta.module || '资料分析' }}</el-tag>
            <el-tag size="small">{{ questionMeta.subtype }}</el-tag>
            <el-tag :type="difficultyTagType(questionMeta.difficulty)" size="small">{{ difficultyLabel(questionMeta.difficulty) }}</el-tag>
            <el-tag type="success" size="small">正确答案: {{ optionDist?.correct_answer }}</el-tag>
          </div>
          <div class="question-stem">{{ questionMeta.stem }}</div>
          <div class="question-options" v-if="questionMeta.options">
            <div v-for="(text, label) in questionMeta.options" :key="label" class="opt-line"
                 :class="{ 'opt-correct': label === optionDist?.correct_answer }">
              <span class="opt-label">{{ label }}.</span>
              <span class="opt-text">{{ text }}</span>
              <el-icon v-if="label === optionDist?.correct_answer" class="opt-check"><CircleCheck /></el-icon>
            </div>
          </div>
        </div>
        <el-empty v-else description="题目元数据未找到（可能不在生成题库中）" :image-size="60" />
      </div>

      <!-- 正确率 + 选项分布 -->
      <el-row :gutter="16">
        <el-col :span="10">
          <div class="panel">
            <div class="panel-title">正确率统计</div>
            <div class="accuracy-display" v-if="qAccuracy">
              <div class="acc-circle" :class="accCircleClass">
                <span class="acc-num">{{ qAccuracy.accuracy_rate }}%</span>
                <span class="acc-label">正确率</span>
              </div>
              <div class="acc-stats">
                <div class="acc-stat">
                  <div class="acc-stat-num">{{ qAccuracy.total_attempts }}</div>
                  <div class="acc-stat-label">总作答</div>
                </div>
                <div class="acc-stat">
                  <div class="acc-stat-num correct">{{ qAccuracy.correct_count }}</div>
                  <div class="acc-stat-label">正确</div>
                </div>
                <div class="acc-stat">
                  <div class="acc-stat-num wrong">{{ qAccuracy.total_attempts - qAccuracy.correct_count }}</div>
                  <div class="acc-stat-label">错误</div>
                </div>
                <div class="acc-stat">
                  <div class="acc-stat-num">{{ formatTime(qAccuracy.avg_time_ms) }}</div>
                  <div class="acc-stat-label">平均用时</div>
                </div>
              </div>
            </div>
          </div>
        </el-col>

        <el-col :span="14">
          <div class="panel">
            <div class="panel-title">选项分布</div>
            <div v-if="optionDist" class="option-chart">
              <div v-for="opt in optionDist.option_distribution" :key="opt.label"
                   class="option-bar-row" :class="{ 'opt-correct-row': opt.is_correct }">
                <div class="opt-bar-label" :class="{ 'correct-label': opt.is_correct }">{{ opt.label }}</div>
                <div class="opt-bar-track">
                  <div class="opt-bar-fill" :class="opt.is_correct ? 'fill-correct' : 'fill-wrong'"
                       :style="{ width: Math.max(opt.percentage, 2) + '%' }"></div>
                </div>
                <div class="opt-bar-count">{{ opt.count }}次</div>
                <div class="opt-bar-pct">{{ opt.percentage }}%</div>
                <el-icon v-if="opt.is_correct" class="opt-bar-icon"><CircleCheck /></el-icon>
              </div>
              <!-- 异常提示 -->
              <div v-if="optionDist.anomalies?.length" class="anomaly-box">
                <el-icon><Warning /></el-icon>
                <span v-for="a in optionDist.anomalies" :key="a" class="anomaly-text">{{ a }}</span>
              </div>
            </div>
            <el-empty v-else description="暂无作答数据" :image-size="60" />
          </div>
        </el-col>
      </el-row>

      <!-- 错因分布 + 干扰项溯源 -->
      <el-row :gutter="16">
        <el-col :span="12">
          <div class="panel">
            <div class="panel-title">错因分布（{{ qErrorPaths?.total_wrong ?? 0 }}次错误）</div>
            <div v-if="qErrorPaths?.error_path_distribution?.length" class="error-dist">
              <div v-for="ep in qErrorPaths.error_path_distribution" :key="ep.type" class="ep-row">
                <div class="ep-type">{{ ep.type }}</div>
                <div class="ep-bar-track">
                  <div class="ep-bar-fill" :style="{ width: ep.percentage + '%' }"></div>
                </div>
                <div class="ep-count">{{ ep.count }}次</div>
                <div class="ep-pct">{{ ep.percentage }}%</div>
              </div>
            </div>
            <el-empty v-else description="暂无错误数据" :image-size="60" />
          </div>
        </el-col>

        <el-col :span="12">
          <div class="panel">
            <div class="panel-title">干扰项溯源</div>
            <div v-if="qErrorPaths?.distractor_trace?.length" class="distractor-list">
              <div v-for="d in qErrorPaths.distractor_trace" :key="d.option" class="distractor-item">
                <div class="distractor-header">
                  <el-tag type="danger" size="small">选项 {{ d.option }}</el-tag>
                  <span class="distractor-type">{{ d.type }}</span>
                </div>
                <div class="distractor-formula" v-if="d.error_formula">
                  <span class="df-label">错误公式:</span>
                  <code>{{ d.error_formula }}</code>
                </div>
                <div class="distractor-value" v-if="d.computed_value">
                  <span class="df-label">计算值:</span>
                  <code>{{ d.computed_value }}</code>
                </div>
              </div>
            </div>
            <el-empty v-else description="该题无干扰项标注" :image-size="60" />
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, CircleCheck, Warning } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getQuestionAccuracy,
  getOptionDistribution,
  getQuestionErrorPaths,
  type QuestionAccuracy,
  type OptionDistribution,
  type QuestionErrorPaths,
} from '@/api/analytics'

const route = useRoute()
const router = useRouter()
const questionId = computed(() => route.params.id as string)

const loading = ref(false)
const qAccuracy = ref<QuestionAccuracy | null>(null)
const optionDist = ref<OptionDistribution | null>(null)
const qErrorPaths = ref<QuestionErrorPaths | null>(null)

interface QuestionMeta {
  module: string
  subtype: string
  difficulty: number
  stem: string
  options: Record<string, string>
}
const questionMeta = ref<QuestionMeta | null>(null)

const accCircleClass = computed(() => {
  const v = qAccuracy.value?.accuracy_rate ?? 0
  if (v >= 70) return 'circle-high'
  if (v >= 50) return 'circle-mid'
  return 'circle-low'
})

async function loadData() {
  loading.value = true
  try {
    const [acc, opt, err] = await Promise.all([
      getQuestionAccuracy(questionId.value),
      getOptionDistribution(questionId.value),
      getQuestionErrorPaths(questionId.value),
    ])
    qAccuracy.value = acc
    optionDist.value = opt
    qErrorPaths.value = err

    // 题目元数据：从选项分布构建 options，题干等信息后续可扩展
    questionMeta.value = {
      module: '资料分析',
      subtype: '',
      difficulty: 2,
      stem: '',
      options: {},
    }

    // 构建 options 从 option_distribution
    if (opt.option_distribution?.length) {
      const opts: Record<string, string> = {}
      for (const o of opt.option_distribution) {
        opts[o.label] = o.text
      }
      questionMeta.value.options = opts
    }
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function formatTime(ms?: number) {
  if (!ms) return '-'
  const s = Math.round(ms / 1000)
  return s + '秒'
}

function difficultyLabel(d: number) {
  return { 1: '简单', 2: '中等', 3: '较难', 4: '困难', 5: '极难' }[d] || '中等'
}

function difficultyTagType(d: number) {
  return { 1: 'success', 2: 'warning', 3: 'danger', 4: 'danger', 5: 'info' }[d] || 'warning'
}

onMounted(loadData)
</script>

<style scoped>
.question-analytics {
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--admin-brand);
}

.panel {
  background: var(--admin-card-bg);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--admin-border);
  margin-bottom: 16px;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--admin-brand);
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--admin-border);
}

/* 题目信息 */
.info-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.question-stem {
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
  margin-bottom: 14px;
  padding: 10px 14px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 3px solid var(--admin-brand);
}

.question-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.opt-line {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #fafafa;
  font-size: 13px;
}

.opt-line.opt-correct {
  background: #f0f9eb;
  border: 1px solid #07c160;
}

.opt-label {
  font-weight: 700;
  color: var(--admin-brand);
  width: 20px;
}

.opt-text {
  flex: 1;
  color: #303133;
}

.opt-check {
  color: #07c160;
  font-size: 18px;
}

/* 正确率圆环 */
.accuracy-display {
  display: flex;
  align-items: center;
  gap: 24px;
}

.acc-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.acc-circle.circle-high { background: linear-gradient(135deg, #07c160, #67c23a); }
.acc-circle.circle-mid { background: linear-gradient(135deg, #e6a23c, #f0a020); }
.acc-circle.circle-low { background: linear-gradient(135deg, #f56c6c, #ee0a24); }

.acc-num {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}

.acc-label {
  font-size: 12px;
  color: rgba(255,255,255,0.85);
}

.acc-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  flex: 1;
}

.acc-stat {
  text-align: center;
}

.acc-stat-num {
  font-size: 22px;
  font-weight: 700;
  color: var(--admin-brand);
}

.acc-stat-num.correct { color: #07c160; }
.acc-stat-num.wrong { color: #f56c6c; }

.acc-stat-label {
  font-size: 12px;
  color: var(--admin-text-muted);
  margin-top: 2px;
}

/* 选项分布柱状图 */
.option-chart {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.opt-bar-label {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #606266;
  flex-shrink: 0;
}

.opt-bar-label.correct-label {
  background: #07c160;
  color: #fff;
}

.opt-bar-track {
  flex: 1;
  height: 22px;
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}

.opt-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.opt-bar-fill.fill-correct { background: linear-gradient(90deg, #07c160, #67c23a); }
.opt-bar-fill.fill-wrong { background: linear-gradient(90deg, #f56c6c, #e6a23c); }

.opt-bar-count {
  width: 50px;
  font-size: 12px;
  color: #606266;
  text-align: right;
  flex-shrink: 0;
}

.opt-bar-pct {
  width: 50px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  text-align: right;
  flex-shrink: 0;
}

.opt-bar-icon {
  color: #07c160;
  flex-shrink: 0;
}

.anomaly-box {
  margin-top: 12px;
  padding: 10px 14px;
  background: #fef0f0;
  border-radius: 6px;
  border: 1px solid #f56c6c;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: #f56c6c;
}

.anomaly-text {
  font-size: 12px;
  line-height: 1.6;
}

/* 错因分布 */
.error-dist {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ep-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ep-type {
  width: 110px;
  font-size: 12px;
  color: #606266;
  text-align: right;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ep-bar-track {
  flex: 1;
  height: 18px;
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}

.ep-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #f56c6c, #e6a23c);
  border-radius: 4px;
}

.ep-count {
  width: 45px;
  font-size: 12px;
  color: #606266;
  text-align: right;
  flex-shrink: 0;
}

.ep-pct {
  width: 45px;
  font-size: 12px;
  font-weight: 600;
  color: #303133;
  text-align: right;
  flex-shrink: 0;
}

/* 干扰项溯源 */
.distractor-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.distractor-item {
  padding: 10px 14px;
  background: #fafafa;
  border-radius: 6px;
  border-left: 3px solid #f56c6c;
}

.distractor-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.distractor-type {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.distractor-formula,
.distractor-value {
  font-size: 12px;
  color: #606266;
  margin-top: 4px;
}

.df-label {
  color: var(--admin-text-muted);
  margin-right: 6px;
}

.distractor-formula code,
.distractor-value code {
  background: #fff;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  color: #f56c6c;
  border: 1px solid #eee;
}
</style>
