<template>
  <div class="practice-proto">
    <!-- 原型标注 -->
    <el-alert type="info" :closable="false" class="proto-banner">
      <template #title>
        <strong>原型预览</strong> — Q7 资料分析最小学习闭环（今日任务 → 渐进训练 → 错因记录），不接入正式学员端
      </template>
    </el-alert>

    <!-- 顶部控制栏 -->
    <el-card class="control-card" shadow="never">
      <div class="control-row">
        <div class="control-item">
          <label class="control-label">技能</label>
          <el-select v-model="selectedSkill" placeholder="选择技能" style="width: 180px">
            <el-option
              v-for="s in skills"
              :key="s.skill"
              :label="s.name"
              :value="s.skill"
            />
          </el-select>
        </div>
        <div class="control-item">
          <label class="control-label">日期</label>
          <el-date-picker
            v-model="selectedDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 180px"
          />
        </div>
        <el-button type="primary" :loading="loading" @click="onGenerate">生成今日练习</el-button>
        <span v-if="pkg" class="pkg-info">
          {{ pkg.skill_name }} · {{ pkg.total_questions }}题 · {{ pkg.date }}
        </span>
      </div>
    </el-card>

    <template v-if="pkg">
      <!-- 方法示例区 -->
      <el-card class="section-card" shadow="never">
        <template #header>
          <div class="section-header">
            <span class="section-icon">①</span>
            <span>今日核心公式 &amp; 方法示例</span>
          </div>
        </template>
        <div class="formula-box">
          <div class="formula-text">{{ pkg.formula }}</div>
          <div class="formula-tip">{{ pkg.tip }}</div>
        </div>
        <div v-if="pkg.method_example" class="example-question">
          <div class="q-stem">{{ pkg.method_example.stem }}</div>
          <div class="material-preview" v-if="pkg.method_example.material.content">
            <el-collapse>
              <el-collapse-item title="查看材料" name="mat">
                <pre class="material-text">{{ pkg.method_example.material.content }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
          <div class="calc-tree">
            <div class="calc-title">计算树：</div>
            <div v-for="step in pkg.method_example.calc_tree" :key="step.step" class="calc-step">
              <span class="step-num">步骤{{ step.step }}</span>
              <span v-if="step.formula" class="step-formula">{{ step.formula }}</span>
              <span class="step-result">{{ step.result }}</span>
            </div>
          </div>
          <div class="answer-reveal">
            <el-button size="small" @click="showExampleAnswer = !showExampleAnswer">
              {{ showExampleAnswer ? '隐藏答案' : '展示答案与常见错误' }}
            </el-button>
            <div v-if="showExampleAnswer" class="answer-detail">
              <div class="correct-ans">正确答案：<strong>{{ pkg.method_example.answer }}</strong></div>
              <div class="explanation">{{ pkg.method_example.explanation }}</div>
              <div class="distractors">
                <div class="distractor-title">常见错误路径：</div>
                <div
                  v-for="(d, key) in pkg.method_example.distractors"
                  :key="key"
                  class="distractor-item"
                >
                  <span class="distractor-key">选项{{ key }}</span>
                  <span class="distractor-type">{{ d.type }}</span>
                  <span class="distractor-formula">{{ d.error_formula }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 渐进训练区 -->
      <el-card class="section-card" shadow="never">
        <template #header>
          <div class="section-header">
            <span class="section-icon">②</span>
            <span>渐进训练（简单 → 中等 → 较难）</span>
          </div>
        </template>
        <div
          v-for="(q, idx) in pkg.progressive"
          :key="q.question_id"
          class="question-block"
        >
          <div class="q-header">
            <span class="q-index">第{{ idx + 1 }}题</span>
            <el-tag :type="diffTagType(q.difficulty)" size="small">{{ q.difficulty_label }}</el-tag>
            <span class="q-subtype">{{ q.subtype }}</span>
          </div>
          <div class="q-stem">{{ q.stem }}</div>
          <el-radio-group
            v-model="answers[q.question_id]"
            class="q-options"
            @change="onProgressiveAnswer(q)"
          >
            <el-radio
              v-for="(label, key) in q.options"
              :key="key"
              :value="key"
              :class="{
                'opt-correct': realtimeFeedback[q.question_id]?.is_correct && realtimeFeedback[q.question_id]?.selected === key,
                'opt-wrong': !realtimeFeedback[q.question_id]?.is_correct && realtimeFeedback[q.question_id]?.selected === key,
              }"
            >
              {{ key }}. {{ label }}
            </el-radio>
          </el-radio-group>
          <div v-if="realtimeFeedback[q.question_id]" class="realtime-feedback">
            <el-tag :type="realtimeFeedback[q.question_id].is_correct ? 'success' : 'danger'" size="small">
              {{ realtimeFeedback[q.question_id].is_correct ? '回答正确' : '回答错误' }}
            </el-tag>
            <span v-if="!realtimeFeedback[q.question_id].is_correct" class="correct-hint">
              正确答案：{{ q.answer }}
            </span>
          </div>
        </div>
      </el-card>

      <!-- 材料题组区 -->
      <el-card class="section-card" shadow="never">
        <template #header>
          <div class="section-header">
            <span class="section-icon">③</span>
            <span>材料题组（5题共享同一材料，模拟真实考试）</span>
          </div>
        </template>
        <div class="material-block">
          <pre class="material-text">{{ pkg.material_content }}</pre>
        </div>
        <div
          v-for="(q, idx) in pkg.material_set"
          :key="q.question_id"
          class="question-block"
        >
          <div class="q-header">
            <span class="q-index">第{{ idx + 1 }}题</span>
            <el-tag size="small" type="info">{{ q.subtype }}</el-tag>
          </div>
          <div class="q-stem">{{ q.stem }}</div>
          <el-radio-group v-model="answers[q.question_id]" class="q-options">
            <el-radio v-for="(label, key) in q.options" :key="key" :value="key">
              {{ key }}. {{ label }}
            </el-radio>
          </el-radio-group>
        </div>
      </el-card>

      <!-- 提交区 -->
      <el-card class="section-card submit-card" shadow="never">
        <div class="submit-row">
          <el-button type="primary" size="large" :loading="submitting" @click="onSubmit">
            提交全部答案
          </el-button>
          <span class="answered-count">
            已作答 {{ answeredCount }} / {{ pkg.total_questions }} 题
          </span>
        </div>
      </el-card>

      <!-- 得分与错因分析区 -->
      <template v-if="submitResult">
        <el-card class="section-card" shadow="never">
          <template #header>
            <div class="section-header">
              <span class="section-icon">④</span>
              <span>作答结果 &amp; 错因分析</span>
            </div>
          </template>
          <div class="score-row">
            <div class="score-box">
              <div class="score-num">{{ submitResult.correct_count }}</div>
              <div class="score-label">正确</div>
            </div>
            <div class="score-box wrong">
              <div class="score-num">{{ submitResult.wrong_count }}</div>
              <div class="score-label">错误</div>
            </div>
            <div class="score-box">
              <div class="score-num">{{ submitResult.total }}</div>
              <div class="score-label">总题数</div>
            </div>
            <div class="score-box rate">
              <div class="score-num">{{ accuracyRate }}%</div>
              <div class="score-label">正确率</div>
            </div>
          </div>

          <!-- 错题列表 -->
          <div v-if="wrongResults.length" class="wrong-list">
            <div class="wrong-title">错题详情（{{ wrongResults.length }}题）</div>
            <div v-for="r in wrongResults" :key="r.question_id" class="wrong-item">
              <div class="wrong-q-header">
                <span class="wrong-qid">{{ r.question_id }}</span>
                <el-tag type="danger" size="small">错</el-tag>
              </div>
              <div class="wrong-answers">
                <span>你的答案：<strong class="wrong-ans">{{ r.user_answer || '未作答' }}</strong></span>
                <span>正确答案：<strong class="correct-ans-text">{{ r.correct_answer }}</strong></span>
              </div>
              <div v-if="r.error_path" class="error-path-box">
                <div class="ep-label">错误路径：</div>
                <el-tag type="warning" size="small">{{ r.error_path.type }}</el-tag>
                <div class="ep-formula">错误公式：{{ r.error_path.error_formula || '—' }}</div>
                <div class="ep-correct">正确公式：{{ r.error_path.correct_formula }}</div>
              </div>
              <div class="wrong-explanation">{{ r.explanation }}</div>
            </div>
          </div>
          <div v-else class="all-correct">
            <el-result icon="success" title="全部正确！" sub-title="本次练习没有错题，继续保持。" />
          </div>
        </el-card>

        <!-- 错因复习卡 -->
        <el-card v-if="reviewCard" class="section-card" shadow="never">
          <template #header>
            <div class="section-header">
              <span class="section-icon">⑤</span>
              <span>错因复习卡</span>
            </div>
          </template>
          <div v-if="reviewCard.error_paths.length" class="review-cards">
            <div
              v-for="ep in reviewCard.error_paths"
              :key="ep.type"
              class="review-card-item"
            >
              <div class="rc-header">
                <el-tag type="warning">{{ ep.type }}</el-tag>
                <span class="rc-count">{{ ep.count }}次</span>
              </div>
              <div class="rc-body">
                <div class="rc-row">
                  <span class="rc-label">正确公式</span>
                  <span class="rc-value">{{ ep.correct_formula }}</span>
                </div>
                <div v-if="ep.error_formula" class="rc-row">
                  <span class="rc-label">错误公式</span>
                  <span class="rc-value error">{{ ep.error_formula }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="no-errors">
            <el-empty description="本次无错误路径需要复习" />
          </div>
        </el-card>
      </template>
    </template>

    <el-empty v-else-if="!loading && !pkg" description="选择技能和日期，点击「生成今日练习」开始" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getDaily,
  getReview,
  listSkills,
  submitAnswers,
  type DailyPackage,
  type PracticeQuestion,
  type PracticeSkill,
  type ReviewCard,
  type SubmitResult,
  type SubmitResultItem,
} from '@/api/practice'

const skills = ref<PracticeSkill[]>([])
const selectedSkill = ref('base_period')
const selectedDate = ref('2026-09-03')
const loading = ref(false)
const submitting = ref(false)
const pkg = ref<DailyPackage | null>(null)
const showExampleAnswer = ref(false)

const answers = reactive<Record<string, string>>({})
const realtimeFeedback = reactive<Record<string, { is_correct: boolean; selected: string }>>({})
const submitResult = ref<SubmitResult | null>(null)
const reviewCard = ref<ReviewCard | null>(null)

const answeredCount = computed(() => {
  if (!pkg.value) return 0
  let count = 0
  const all = getAllQuestions()
  for (const q of all) {
    if (answers[q.question_id]) count++
  }
  return count
})

const accuracyRate = computed(() => {
  if (!submitResult.value || submitResult.value.total === 0) return 0
  return Math.round((submitResult.value.correct_count / submitResult.value.total) * 100)
})

const wrongResults = computed<SubmitResultItem[]>(() => {
  if (!submitResult.value) return []
  return submitResult.value.results.filter((r) => !r.is_correct)
})

function getAllQuestions(): PracticeQuestion[] {
  if (!pkg.value) return []
  const list: PracticeQuestion[] = []
  if (pkg.value.method_example) list.push(pkg.value.method_example)
  list.push(...pkg.value.progressive)
  list.push(...pkg.value.material_set)
  return list
}

function diffTagType(diff: number) {
  if (diff <= 1) return 'success'
  if (diff === 2) return 'warning'
  return 'danger'
}

function onProgressiveAnswer(q: PracticeQuestion) {
  const ua = answers[q.question_id]
  if (!ua) return
  realtimeFeedback[q.question_id] = {
    is_correct: ua.toUpperCase() === q.answer.toUpperCase(),
    selected: ua,
  }
}

async function onGenerate() {
  if (!selectedSkill.value || !selectedDate.value) {
    ElMessage.warning('请选择技能和日期')
    return
  }
  loading.value = true
  submitResult.value = null
  reviewCard.value = null
  showExampleAnswer.value = false
  Object.keys(answers).forEach((k) => delete answers[k])
  Object.keys(realtimeFeedback).forEach((k) => delete realtimeFeedback[k])
  try {
    pkg.value = await getDaily(selectedSkill.value, selectedDate.value)
    ElMessage.success(`已生成 ${pkg.value.skill_name} 练习包，共 ${pkg.value.total_questions} 题`)
  } catch (e) {
    ElMessage.error((e as Error).message || '生成失败')
  } finally {
    loading.value = false
  }
}

async function onSubmit() {
  if (!pkg.value) return
  const all = getAllQuestions()
  const payload = all
    .filter((q) => answers[q.question_id])
    .map((q) => ({ question_id: q.question_id, user_answer: answers[q.question_id] }))
  if (payload.length === 0) {
    ElMessage.warning('请至少作答一题')
    return
  }
  submitting.value = true
  try {
    submitResult.value = await submitAnswers(pkg.value.daily_id, payload)
    // 加载复习卡
    reviewCard.value = await getReview(pkg.value.daily_id)
    ElMessage.success(
      `提交完成：正确 ${submitResult.value.correct_count} / ${submitResult.value.total}`,
    )
  } catch (e) {
    ElMessage.error((e as Error).message || '提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    skills.value = await listSkills()
  } catch {
    // fallback
    skills.value = [
      { skill: 'base_period', name: '基期量', formula: '' },
      { skill: 'growth_rate', name: '增长率', formula: '' },
      { skill: 'proportion', name: '比重', formula: '' },
      { skill: 'average', name: '平均数', formula: '' },
      { skill: 'multiple', name: '倍数', formula: '' },
      { skill: 'mixed_growth', name: '混合增长率', formula: '' },
    ]
  }
})
</script>

<style scoped>
.practice-proto {
  max-width: 960px;
  margin: 0 auto;
}
.proto-banner {
  margin-bottom: 16px;
}
.control-card {
  margin-bottom: 16px;
}
.control-row {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}
.control-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.control-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.pkg-info {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-left: auto;
}
.section-card {
  margin-bottom: 16px;
}
.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.section-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 13px;
  font-weight: 700;
}
.formula-box {
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.formula-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--el-color-primary);
  margin-bottom: 8px;
}
.formula-tip {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}
.example-question {
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 16px;
}
.q-stem {
  font-size: 14px;
  line-height: 1.7;
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
}
.material-preview {
  margin-bottom: 12px;
}
.material-text {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  padding: 12px;
  border-radius: 6px;
  margin: 0;
  font-family: inherit;
}
.calc-tree {
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}
.calc-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--el-text-color-secondary);
}
.calc-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.step-num {
  background: var(--el-color-primary);
  color: #fff;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 11px;
}
.step-formula {
  font-weight: 600;
  color: var(--el-color-primary);
}
.step-result {
  color: var(--el-text-color-regular);
}
.answer-reveal {
  margin-top: 8px;
}
.answer-detail {
  margin-top: 12px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
}
.correct-ans {
  font-size: 14px;
  margin-bottom: 8px;
}
.explanation {
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
  margin-bottom: 12px;
}
.distractors {
  border-top: 1px dashed var(--el-border-color);
  padding-top: 8px;
}
.distractor-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}
.distractor-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.distractor-key {
  font-weight: 600;
  color: var(--el-color-danger);
}
.distractor-type {
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
  padding: 1px 6px;
  border-radius: 4px;
}
.distractor-formula {
  color: var(--el-text-color-secondary);
}
.question-block {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}
.q-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.q-index {
  font-weight: 600;
  font-size: 14px;
}
.q-subtype {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-left: auto;
}
.q-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.q-options :deep(.el-radio) {
  margin-right: 0;
}
.opt-correct :deep(.el-radio__label) {
  color: var(--el-color-success);
  font-weight: 600;
}
.opt-wrong :deep(.el-radio__label) {
  color: var(--el-color-danger);
}
.realtime-feedback {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.correct-hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.material-block {
  margin-bottom: 16px;
}
.submit-card {
  text-align: center;
}
.submit-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}
.answered-count {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.score-row {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}
.score-box {
  flex: 1;
  text-align: center;
  padding: 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}
.score-box.wrong {
  background: var(--el-color-danger-light-9);
}
.score-box.rate {
  background: var(--el-color-primary-light-9);
}
.score-num {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}
.score-box.wrong .score-num {
  color: var(--el-color-danger);
}
.score-box.rate .score-num {
  color: var(--el-color-primary);
}
.score-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.wrong-list {
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 16px;
}
.wrong-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}
.wrong-item {
  border: 1px solid var(--el-border-color-lighter);
  border-left: 3px solid var(--el-color-danger);
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
}
.wrong-q-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.wrong-qid {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
}
.wrong-answers {
  display: flex;
  gap: 16px;
  font-size: 13px;
  margin-bottom: 8px;
}
.wrong-ans {
  color: var(--el-color-danger);
}
.correct-ans-text {
  color: var(--el-color-success);
}
.error-path-box {
  background: var(--el-color-warning-light-9);
  border-radius: 6px;
  padding: 10px;
  margin-bottom: 8px;
}
.ep-label {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--el-text-color-secondary);
}
.ep-formula,
.ep-correct {
  font-size: 12px;
  margin-top: 4px;
  color: var(--el-text-color-regular);
}
.ep-correct {
  color: var(--el-color-success);
}
.wrong-explanation {
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
}
.all-correct {
  padding: 20px 0;
}
.review-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.review-card-item {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  overflow: hidden;
}
.rc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--el-color-warning-light-9);
}
.rc-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-warning);
}
.rc-body {
  padding: 12px;
}
.rc-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 6px;
  line-height: 1.5;
}
.rc-label {
  flex-shrink: 0;
  color: var(--el-text-color-secondary);
  min-width: 56px;
}
.rc-value {
  color: var(--el-text-color-primary);
}
.rc-value.error {
  color: var(--el-color-danger);
}
.no-errors {
  padding: 20px 0;
}
</style>
