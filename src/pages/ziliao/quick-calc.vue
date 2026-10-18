<template>
  <page-meta
    v-if="isWeapp"
    :page-style="pageMeta.pageStyle"
    :background-color="pageMeta.backgroundColor"
    :background-color-top="pageMeta.backgroundColorTop"
    :background-color-bottom="pageMeta.backgroundColorBottom"
    :background-text-style="pageMeta.backgroundTextStyle"
  />
  <view class="qc-page" :class="themeClass">
    <template v-if="stage === 'setup'">
      <view class="qc-card qc-intro">
        <text class="qc-eyebrow">资料分析 · 题型训练</text>
        <text class="qc-title">速算训练</text>
        <text class="qc-copy">按题目类型练习；答题后查看推导和更快的解题建议。</text>
        <view class="qc-meta"
          ><text>四选一</text><text>即时解析</text><text>练习记录同步</text></view
        >
        <text v-if="storageError" class="qc-caution">{{ storageError }}</text>
        <nut-button v-if="storageError" plain type="primary" block @click="handleLoadAction">
          {{ loginRequired ? '前往登录' : '重试加载' }}
        </nut-button>
      </view>
      <view class="qc-card qc-setup-card">
        <view class="qc-section-head">
          <view>
            <text class="qc-heading qc-section-title">选择训练题型</text>
            <text class="qc-note qc-section-note">{{ selectedMethodLabel }} · {{ count }} 题</text>
          </view>
          <text class="qc-count-badge">{{ methods.length }} 种题型</text>
        </view>
        <view class="qc-method-grid">
          <view
            class="qc-method"
            :class="{ 'qc-active': mode === 'mixed' }"
            @tap="chooseMode('mixed')"
          >
            <view class="qc-method-head"
            ><text class="qc-method-name">混合训练</text
              ><text v-if="mode === 'mixed'" class="qc-check">✓</text></view
            >
            <text class="qc-method-copy">多种题型随机组合，答后查看解题建议</text>
          </view>
          <view
            v-for="method in methods"
            :key="method.id"
            class="qc-method"
            :class="{ 'qc-active': mode === method.code }"
            @tap="chooseMode(method.code)"
          >
            <view class="qc-method-head"
              ><text class="qc-method-name">{{ method.name }}</text
              ><text v-if="mode === method.code" class="qc-check">✓</text></view
            >
            <text class="qc-method-copy">{{ method.scene }}</text>
          </view>
        </view>
        <text v-if="!methods.length" class="qc-caution"
          >暂无已发布训练题型，请稍后再试或联系管理员完成题型发布。</text
        >
        <view class="qc-count-head"
          ><text class="qc-heading">每组题数</text><text class="qc-note">按练习节奏选择</text></view
        >
        <view class="qc-row qc-count-row">
          <view
            v-for="size in [5, 10, 20]"
            :key="size"
            class="qc-chip"
            :class="{ 'qc-active': count === size }"
            @tap="chooseCount(size)"
          >
            {{ size }} 题
          </view>
        </view>
        <nut-button
          class="qc-start-button"
          type="primary"
          block
          :disabled="!methods.length"
          @click="start"
          >开始训练</nut-button
        >
      </view>
      <view class="qc-card qc-insights">
        <view class="qc-insight-toggle" @tap="toggleRecommendations">
          <view
            ><text class="qc-heading">为你推荐</text
            ><text class="qc-note">{{
              recommendations.length ? '根据近期正确率安排专项练习' : '完成练习后生成薄弱项建议'
            }}</text></view
          >
          <text class="qc-chevron" :class="{ 'qc-chevron-open': recommendationsOpen }">⌄</text>
        </view>
        <view v-if="recommendationsOpen">
          <view v-if="recommendations.length">
            <view v-for="item in recommendations" :key="item.code" class="qc-history">
              <view>
                <text>{{ item.name }} · {{ item.accuracy }}% 正确率</text>
                <text class="qc-note">近 {{ item.attempts }} 题需要加强</text>
              </view>
              <nut-button size="small" plain type="primary" @click="startMethod(item.code)">
                专项练习
              </nut-button>
            </view>
          </view>
          <text v-else class="qc-copy qc-insight-empty"
            >完成一些练习后，这里会显示需要加强的题型。</text
          >
        </view>
      </view>
      <view class="qc-card qc-insights qc-last-card">
        <view class="qc-insight-toggle" @tap="toggleHistory">
          <view
            ><text class="qc-heading">最近训练</text
            ><text class="qc-note">{{
              history.length ? `最近完成 ${history.length} 组` : '完成一组后，在这里回顾练习记录'
            }}</text></view
          >
          <text class="qc-chevron" :class="{ 'qc-chevron-open': historyOpen }">⌄</text>
        </view>
        <text v-if="storageError" class="qc-caution">{{ storageError }}</text>
        <view v-if="historyOpen">
          <view v-if="history.length">
            <view v-for="record in history.slice(0, 5)" :key="record.id" class="qc-history">
              <text>{{ historyLabel(record.mode) }} · {{ record.correct }}/{{ record.total }}</text>
              <text class="qc-note">{{ record.date }} · {{ formatTime(record.seconds) }}</text>
            </view>
          </view>
          <text v-else class="qc-copy qc-insight-empty">完成一组训练后，记录会显示在这里。</text>
        </view>
      </view>
    </template>

    <template v-else-if="stage === 'practice' && current">
      <view class="qc-row qc-between">
        <text class="qc-heading">{{ index + 1 }} / {{ questions.length }}</text>
        <text class="qc-copy">{{ formatTime(elapsed) }}</text>
      </view>
      <view class="qc-card">
        <text class="qc-note">{{ questionCategoryLabel(current) }}</text>
        <text class="qc-stem">{{ current.stem }}</text>
        <view v-if="current.material" class="qc-material">
          <text class="qc-material-title">{{ current.material.title }}</text>
          <view class="qc-material-row qc-material-header">
            <text v-for="(cell, cellIndex) in current.material.headers" :key="cellIndex">{{ cell }}</text>
          </view>
          <view v-for="(row, rowIndex) in current.material.rows" :key="rowIndex" class="qc-material-row">
            <text v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</text>
          </view>
        </view>
        <LatexBlock v-else :latex="current.latex" :plain="current.plain" :show-plain="false" size="lg" />
      </view>
      <view
        v-for="(option, optionIndex) in current.options"
        :key="optionIndex"
        class="qc-option"
        :class="optionClass(optionIndex)"
        @tap="answer(optionIndex)"
      >
        <text class="qc-letter">{{ letters[optionIndex] }}</text
        ><text>{{ option }}</text>
        <text
          v-if="answered && current.optionFeedback?.[optionIndex]"
          class="qc-option-feedback"
          :class="current.optionFeedback[optionIndex] === '该计算成立' ? 'qc-correct' : 'qc-wrong'"
        >
          {{ current.optionFeedback[optionIndex] }}
        </text>
      </view>
      <view v-if="answered" class="qc-card">
        <text class="qc-heading" :class="isCorrect ? 'qc-correct' : 'qc-wrong'">
          {{ isCorrect ? '回答正确' : `正确答案：${letters[current.answer]}` }} ·
          {{ questionConceptLabel(current) }}
        </text>
        <template v-if="current.method === 'mixed'">
          <text class="qc-note">涉及知识点：增长量、增长率、基期量、现期量</text>
        </template>
        <template v-else>
          <text class="qc-note">{{ methodById(current.method)?.knowledgePath }}</text>
          <text class="qc-copy">适用条件：{{ methodById(current.method)?.scene }}</text>
        </template>
        <text class="qc-note">解题方法与公式</text>
        <view v-for="(step, stepIndex) in current.steps" :key="stepIndex" class="qc-step">
          <text class="qc-copy">{{ stepIndex + 1 }}. {{ step.text }}</text>
          <LatexBlock v-if="step.latex" :latex="step.latex" :show-plain="false" />
        </view>
        <text class="qc-caution">易错点：{{ current.pitfall }}</text>
        <template v-if="current.method === 'mixed'">
          <view class="qc-link" @tap="openKnowledge('增长量（X）', '增长')">复习增长量知识节点 ›</view>
          <view class="qc-link" @tap="openKnowledge('增长率（R）', '增长')">复习增长率知识节点 ›</view>
          <view class="qc-link" @tap="openKnowledge('基期值（A）', '增长')">复习基期量知识节点 ›</view>
          <view class="qc-link" @tap="openKnowledge('现期值（B）', '增长')">复习现期量知识节点 ›</view>
        </template>
        <view v-else class="qc-link" @tap="openKnowledge">查看对应知识节点 ›</view>
      </view>
      <view class="qc-actions">
        <nut-button plain type="primary" @click="leave">结束本组</nut-button>
        <nut-button type="primary" :disabled="!answered" @click="next">
          {{ index === questions.length - 1 ? '查看结果' : '下一题' }}
        </nut-button>
      </view>
    </template>

    <template v-else-if="stage === 'result'">
      <view class="qc-card">
        <text class="qc-title">{{ correctCount }} / {{ attempts.length }} 题正确</text>
        <text class="qc-copy">
          {{ attempts.length ? Math.round((correctCount / attempts.length) * 100) : 0 }}% 正确率 ·
          答题用时 {{ formatTime(totalSeconds) }}
        </text>
        <text class="qc-note">
          {{
            attempts.length < questions.length ? '提前结束，仅统计已作答题目。' : '本组已完成。'
          }}记录已同步到账号。
        </text>
        <text v-if="storageError" class="qc-caution">{{ storageError }}</text>
        <view class="qc-actions">
          <nut-button plain type="primary" @click="setup">选择题型</nut-button>
          <nut-button type="primary" @click="start">再练一组</nut-button>
        </view>
        <nut-button v-if="wrongQuestions.length" plain type="primary" block @click="retryWrong">
          重练本组错题（{{ wrongQuestions.length }}）
        </nut-button>
      </view>
      <view v-for="(attempt, attemptIndex) in attempts" :key="attempt.question.id" class="qc-card">
        <text class="qc-heading">
          {{ attemptIndex + 1 }}.
          {{ methodById(attempt.question.method)?.name || attempt.question.method }}
        </text>
        <text class="qc-copy">{{ attempt.question.stem }}</text>
        <LatexBlock
          :latex="attempt.question.latex"
          :plain="attempt.question.plain"
          :show-plain="false"
        />
        <text
          class="qc-copy"
          :class="attempt.selected === attempt.question.answer ? 'qc-correct' : 'qc-wrong'"
        >
          你的答案：{{ attempt.question.options[attempt.selected] }}
        </text>
        <text class="qc-copy">
          正确答案：{{ attempt.question.options[attempt.question.answer] }} · 用时
          {{ formatTime(attempt.seconds) }}
        </text>
        <text class="qc-note">解题方法与公式</text>
        <view v-for="(step, stepIndex) in attempt.question.steps" :key="stepIndex" class="qc-step">
          <text class="qc-copy">{{ step.text }}</text>
          <LatexBlock v-if="step.latex" :latex="step.latex" :show-plain="false" />
        </view>
        <text class="qc-caution">{{ attempt.question.pitfall }}</text>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import Taro, { useDidHide, useDidShow } from '@tarojs/taro'
import { Button as NutButton } from '@nutui/nutui-taro'
import LatexBlock from '@/components/LatexBlock.vue'
import type { QuickTrainingMode, QuickQuestion, QuickStep } from '@/utils/quickCalc'
import { api } from '@/api'
import { useThemeClass, usePageMeta } from '@/utils/brandColor'
import { showConfirm, showToast } from '@/utils/platform'

definePageConfig({ navigationBarTitleText: '速算训练' })
const { themeClass } = useThemeClass()
const pageMeta = usePageMeta()
const isWeapp = process.env.TARO_ENV === 'weapp'
const letters = ['A', 'B', 'C', 'D']
interface Attempt {
  question: QuickQuestion
  selected: number
  seconds: number
}
interface History {
  id: string
  mode: string
  date: string
  correct: number
  total: number
  seconds: number
}
const stage = ref<'setup' | 'practice' | 'result'>('setup')
const mode = ref<QuickTrainingMode>('mixed')
const count = ref(10)
const recommendationsOpen = ref(false)
const historyOpen = ref(false)
const questions = ref<QuickQuestion[]>([])
const index = ref(0)
const attempts = ref<Attempt[]>([])
const history = ref<History[]>([])
const recommendations = ref<
  Array<{ code: QuickQuestion['method']; name: string; accuracy: number; attempts: number }>
>([])
const methods = ref<
  Array<{
    id: string
    code: QuickQuestion['method']
    name: string
    scene: string
    knowledgePath: string
    nodeTitle: string
    nodeParent: string
  }>
>([])
const sessionId = ref('')
const answering = ref(false)
const storageError = ref('')
const loginRequired = ref(false)
const elapsed = ref(0)
let activeSince = 0
let previousMs = 0
let ticker: ReturnType<typeof setInterval> | undefined
const current = computed(() => questions.value[index.value])
const answered = computed(() => !!attempts.value[index.value])
const isCorrect = computed(() => attempts.value[index.value]?.selected === current.value?.answer)
const correctCount = computed(
  () => attempts.value.filter((a) => a.selected === a.question.answer).length,
)
const totalSeconds = computed(() => attempts.value.reduce((sum, a) => sum + a.seconds, 0))
const wrongQuestions = computed(() =>
  attempts.value.filter((a) => a.selected !== a.question.answer).map((a) => a.question),
)
const selectedMethodLabel = computed(() =>
  mode.value === 'mixed' ? '混合训练' : methodById(mode.value)?.name || '专项训练',
)
function methodById(id: string) {
  const code = ['direct', 'difference', 'position', 'split'].includes(id) ? 'fraction-compare' : id
  return methods.value.find((method) => method.code === code)
}
function questionCategoryLabel(question: QuickQuestion) {
  return question.method === 'mixed'
    ? questionFormLabel(question.questionForm)
    : `${questionFormLabel(question.questionForm)} · ${methodById(question.method)?.name || question.method}`
}
function questionConceptLabel(question: QuickQuestion) {
  return question.method === 'mixed'
    ? '多指标综合计算'
    : methodById(question.method)?.name || question.method
}
function historyLabel(value: string) {
  return value === 'mixed'
    ? '混合训练'
    : value === 'retry'
      ? '错题重练'
      : ['direct', 'difference', 'position', 'split'].includes(value)
        ? '分数比较'
      : methodById(value)?.name || value
}
function questionFormLabel(value?: QuickQuestion['questionForm']) {
  const labels: Record<NonNullable<QuickQuestion['questionForm']>, string> = {
    pair: '两个分数比较',
    'multi-extrema': '多个分数选最大/最小',
    'multi-sort': '多个分数排序',
    calculation: '直接计算',
    'calculation-correct': '计算辨析·选正确项',
    'calculation-incorrect': '计算辨析·选错误项',
    'material-correct': '多指标材料·选正确项',
    'material-incorrect': '多指标材料·选错误项',
    'share-current': '现期比重',
    'share-base': '基期比重',
    'share-change': '两期比重差',
    'average-current': '单位平均数',
    'average-change': '平均数变化量',
    'average-growth': '平均数增长率',
    'multiple-current': '现期倍数',
    'multiple-base': '基期倍数',
    'multiple-excess': '多几倍辨析',
    'mixed-rate': '加权混合增长率',
    'interval-growth': '隔年增长率',
    'annual-growth': '年均增长率',
    'annual-amount': '年均增长量',
    'contribution-rate': '贡献率',
    'growth-pull': '拉动百分点',
  }
  return value ? labels[value] : '教学模拟题'
}
function formatTime(seconds: number) {
  return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
}
function chooseMode(value: QuickTrainingMode) {
  mode.value = value
}
function chooseCount(value: number) {
  count.value = value
}
function toggleRecommendations() {
  recommendationsOpen.value = !recommendationsOpen.value
}
function toggleHistory() {
  historyOpen.value = !historyOpen.value
}
function updateTime() {
  elapsed.value = Math.floor((previousMs + (activeSince ? Date.now() - activeSince : 0)) / 1000)
}
function pause() {
  if (activeSince) previousMs += Date.now() - activeSince
  activeSince = 0
  if (ticker) clearInterval(ticker)
  ticker = undefined
  updateTime()
}
function resume() {
  if (stage.value !== 'practice' || answered.value || activeSince) return
  activeSince = Date.now()
  ticker = setInterval(updateTime, 250)
}
function resetClock() {
  pause()
  previousMs = 0
  elapsed.value = 0
  resume()
}
function begin(session: {
  id: string
  questions: Array<Omit<QuickQuestion, 'answer' | 'check' | 'steps' | 'pitfall'> & { id: string }>
}) {
  pause()
  sessionId.value = session.id
  questions.value = session.questions.map((question) => ({
    ...question,
    answer: -1,
    check: { kind: 'number', target: 0, values: [], unit: '' },
    steps: [],
    pitfall: '',
  }))
  attempts.value = []
  index.value = 0
  storageError.value = ''
  stage.value = 'practice'
  resetClock()
}
async function start() {
  try {
    const response = await api.createQuickCalcSession({ mode: mode.value, count: count.value })
    if (response.code !== 0 || !response.data) throw new Error(response.message || '练习创建失败')
    begin(response.data)
  } catch {
    showToast('练习创建失败，请检查网络后重试', 'error')
  }
}
async function startMethod(code: QuickQuestion['method']) {
  mode.value = code
  await start()
}
async function answer(selected: number) {
  if (answered.value || !current.value || answering.value) return
  answering.value = true
  pause()
  try {
    const response = await api.answerQuickCalcQuestion(sessionId.value, {
      questionId: current.value.id,
      selected,
      seconds: elapsed.value,
    })
    if (response.code !== 0 || !response.data) throw new Error(response.message || '提交失败')
    const question = current.value
    question.answer = question.options.indexOf(response.data.correctOption)
    question.steps = response.data.steps as QuickStep[]
    question.pitfall = response.data.pitfall
    question.optionFeedback = response.data.optionFeedback
    attempts.value.push({ question, selected, seconds: elapsed.value })
  } catch {
    showToast('答案暂未提交，请检查网络后重试', 'error')
    resume()
  } finally {
    answering.value = false
  }
}
function optionClass(option: number) {
  const selected = attempts.value[index.value]?.selected
  return {
    'qc-option-selected': selected === option,
    'qc-option-correct': answered.value && current.value.answer === option,
    'qc-option-wrong': answered.value && selected === option && option !== current.value.answer,
  }
}
async function finish() {
  pause()
  if (!attempts.value.length) return
  try {
    const response = await api.completeQuickCalcSession(sessionId.value, {
      totalSeconds: totalSeconds.value,
    })
    if (response.code !== 0 || !response.data) throw new Error(response.message || '结果同步失败')
    stage.value = 'result'
    await loadHistory()
  } catch {
    showToast('结果还未同步，请保持网络后再点查看结果', 'error')
  }
}
function next() {
  if (!answered.value) return
  if (index.value === questions.value.length - 1) finish()
  else {
    index.value++
    resetClock()
    Taro.pageScrollTo({ scrollTop: 0, duration: 0 })
  }
}
async function leave() {
  pause()
  if (await showConfirm('结束训练', '仅统计已作答题目；尚未作答的题目不会计入正确率。')) finish()
  else resume()
}
function retryWrong() {
  const ids = wrongQuestions.value.map((question) => question.id)
  api
    .retryQuickCalcWrong(sessionId.value, ids)
    .then((response) => {
      if (response.code !== 0 || !response.data)
        throw new Error(response.message || '错题重练创建失败')
      begin(response.data)
    })
    .catch(() => showToast('错题重练创建失败，请重试', 'error'))
}
function setup() {
  pause()
  stage.value = 'setup'
}
function openKnowledge(nodeTitle?: string, nodeParent?: string) {
  if (!current.value) return
  const info = methodById(current.value.method)
  const params = {
    treeKey: '资料分析',
    nodeTitle: nodeTitle || info?.nodeTitle || '',
    nodeParent: nodeParent || info?.nodeParent || '',
  }
  if (!params.nodeTitle) return
  const query = Object.entries(params)
    .map(([key, value]) => `${key}=${encodeURIComponent(value)}`)
    .join('&')
  Taro.navigateTo({ url: '/pages/knowledge/index?' + query })
}
async function loadHistory() {
  const response = await api.getQuickCalcHistory(10)
  if (response.code === 0 && response.data) {
    history.value = response.data.sessions
    recommendations.value = response.data.recommendations
  }
}
async function reloadData() {
  storageError.value = ''
  loginRequired.value = false
  try {
    const methodResponse = await api.listQuickCalcMethods()
    if (methodResponse.code === 401) {
      loginRequired.value = true
      storageError.value = '登录后才能同步训练记录并使用后台发布的题目。'
      return
    }
    if (methodResponse.code !== 0 || !methodResponse.data) throw new Error(methodResponse.message)
    methods.value = methodResponse.data
    await loadHistory()
  } catch {
    storageError.value = '训练配置暂不可用，请检查网络后重试。'
  }
}
function goLogin() {
  Taro.navigateTo({ url: '/pages/auth/login' })
}
function handleLoadAction() {
  if (loginRequired.value) goLogin()
  else reloadData()
}
onMounted(reloadData)
useDidHide(pause)
useDidShow(resume)
onUnmounted(pause)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
.qc-page {
  @include page-padding;
  padding-bottom: calc(28px + env(safe-area-inset-bottom));
}
.qc-card {
  @include card;
}
.qc-title {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: $text-primary;
  margin-bottom: 10px;
}
.qc-heading {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 8px;
}
.qc-copy {
  display: block;
  font-size: 14px;
  line-height: 1.65;
  color: $text-secondary;
  margin-bottom: 8px;
}
.qc-note {
  display: block;
  font-size: 12px;
  line-height: 1.6;
  color: $text-muted;
  margin-bottom: 8px;
}
.qc-method {
  @include hit-target;
  padding: 12px;
  margin-bottom: 10px;
  border: 1px solid $border-color;
  border-radius: $radius-md;
}
.qc-active {
  border-color: $primary-color;
  background: $primary-light;
}
.qc-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.qc-chip.qc-active {
  border-color: $primary-color;
}
.qc-between {
  justify-content: space-between;
  align-items: center;
}
.qc-chip {
  @include hit-target;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: $text-primary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
}
.qc-stem {
  display: block;
  font-size: 17px;
  color: $text-primary;
  line-height: 1.7;
  margin-bottom: 20px;
}
.qc-material {
  overflow: hidden;
  margin: 14px 0 4px;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  background: $card-bg;
}
.qc-material-title {
  display: block;
  padding: 10px 12px 6px;
  font-size: 12px;
  line-height: 1.5;
  color: $text-muted;
}
.qc-material-row {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 9px 12px;
  border-top: 1px solid $border-color;
  font-size: 12px;
  line-height: 1.4;
  color: $text-primary;
}
.qc-material-row text:first-child {
  flex: 1;
  min-width: 0;
  word-break: break-all;
}
.qc-material-row text:not(:first-child) {
  flex: 0 0 64px;
  text-align: right;
  white-space: nowrap;
}
.qc-material-header {
  font-weight: 600;
  color: $text-secondary;
  background: $page-bg;
}
.qc-option {
  @include hit-target;
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 14px;
  padding: 14px 16px;
  margin-bottom: 12px;
  background: $card-bg;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  color: $text-primary;
}
.qc-letter {
  flex: 0 0 22px;
  font-weight: 700;
  color: $text-secondary;
}
.qc-option text:last-child {
  flex: 1;
  min-width: 0;
  line-height: 1.55;
  word-break: break-word;
}
.qc-option-selected {
  border-color: $primary-color;
  background: $primary-light;
}
.qc-option-correct {
  border-color: $success;
}
.qc-option-feedback {
  flex: 0 0 auto !important;
  font-size: 12px;
  white-space: nowrap;
}
.qc-option-wrong {
  border-color: $danger;
}
.qc-correct {
  color: $success;
}
.qc-wrong {
  color: $danger;
}
.qc-step {
  margin-top: 12px;
}
.qc-caution {
  display: block;
  background: var(--zk-warn-soft);
  padding: 12px;
  font-size: 13px;
  color: $text-primary;
  line-height: 1.7;
  border-radius: $radius-md;
  margin-top: 12px;
}
.qc-actions {
  display: flex;
  gap: 12px;
  margin: 16px 0;
}
.qc-actions :deep(.nut-button) {
  flex: 1;
}
.qc-link {
  @include hit-target;
  display: flex;
  align-items: center;
  color: $primary-color;
  font-size: 14px;
  margin-top: 10px;
}
.qc-history {
  padding: 12px 0;
  border-bottom: 1px solid $border-color;
  color: $text-primary;
  font-size: 14px;
}
.qc-intro {
  padding: 16px;
}
.qc-eyebrow {
  display: block;
  color: $primary-color;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  margin-bottom: 5px;
}
.qc-intro .qc-title {
  font-size: 22px;
  line-height: 1.25;
  margin-bottom: 6px;
}
.qc-intro .qc-copy {
  margin-bottom: 10px;
}
.qc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.qc-meta text {
  display: inline-flex;
  padding: 4px 8px;
  border-radius: 999px;
  background: $chip-bg;
  color: $text-secondary;
  font-size: 11px;
  line-height: 1.3;
}
.qc-setup-card {
  padding: 16px;
}
.qc-section-head,
.qc-insight-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.qc-section-title {
  margin-bottom: 2px;
}
.qc-section-note {
  margin-bottom: 0;
}
.qc-count-badge {
  flex-shrink: 0;
  padding: 4px 8px;
  border-radius: 999px;
  background: $primary-light;
  color: $primary-color;
  font-size: 11px;
}
.qc-method-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0 16px;
}
.qc-method {
  box-sizing: border-box;
  width: calc(50% - 4px);
  min-width: 0;
  min-height: 80px;
  padding: 10px;
  margin: 0;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  background: $card-bg;
}
.qc-method.qc-active {
  border-color: $primary-color;
  background: $primary-light;
}
.qc-method-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  margin-bottom: 5px;
}
.qc-method-name {
  display: block;
  min-width: 0;
  color: $text-primary;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
  word-break: break-all;
}
.qc-check {
  flex: 0 0 auto;
  margin-left: 4px;
  color: $primary-color;
  font-size: 12px;
  font-weight: 700;
}
.qc-method-copy {
  display: -webkit-box;
  overflow: hidden;
  color: $text-secondary;
  font-size: 11px;
  line-height: 1.45;
  word-break: break-all;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.qc-count-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 8px;
}
.qc-count-head .qc-heading,
.qc-count-head .qc-note {
  margin-bottom: 0;
}
.qc-count-row {
  gap: 8px;
  margin-bottom: 12px;
}
.qc-chip {
  min-height: 40px;
  box-sizing: border-box;
  padding: 0 8px;
  font-size: 13px;
}
.qc-start-button {
  margin-top: 2px;
}
.qc-insights {
  padding: 12px 16px;
}
.qc-insight-toggle {
  min-height: 40px;
}
.qc-insight-toggle .qc-heading,
.qc-insight-toggle .qc-note {
  margin-bottom: 0;
}
.qc-chevron {
  padding: 0 5px;
  color: $text-muted;
  font-size: 20px;
  line-height: 1;
  transform: rotate(0deg);
  transition: transform 160ms ease;
}
.qc-chevron-open {
  transform: rotate(180deg);
}
.qc-last-card {
  margin-bottom: 0;
}
.qc-insight-empty {
  margin: 6px 0 0;
  padding-top: 10px;
  border-top: 1px solid $border-color;
}
</style>
