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
      <view class="qc-card">
        <text class="qc-title">资料分析 · 速算训练</text>
        <text class="qc-copy">
          按方法适用场景出题，练习先判断、再计算。每题四选一，答后看推导。
        </text>
        <text class="qc-note">后台规则生成的教学模拟题 · 练习记录会同步到个人账号</text>
        <text v-if="storageError" class="qc-caution">{{ storageError }}</text>
        <nut-button v-if="storageError" plain type="primary" block @click="handleLoadAction">
          {{ loginRequired ? '前往登录' : '重试加载' }}
        </nut-button>
      </view>
      <view class="qc-card">
        <text class="qc-heading">选择训练方法</text>
        <view
          class="qc-method"
          :class="{ 'qc-active': mode === 'mixed' }"
          @tap="chooseMode('mixed')"
        >
          <text class="qc-heading">混合训练</text><text class="qc-copy">混合七类场景，答题前不提示推荐方法。</text>
        </view>
        <view
          v-for="method in methods"
          :key="method.id"
          class="qc-method"
          :class="{ 'qc-active': mode === method.code }"
          @tap="chooseMode(method.code)"
        >
          <text class="qc-heading">{{ method.name }}</text><text class="qc-copy">{{ method.scene }}</text>
        </view>
        <text v-if="!methods.length" class="qc-caution">暂无已发布训练方法，请稍后再试或联系管理员完成方法预览与发布。</text>
        <text class="qc-heading">每组题数</text>
        <view class="qc-row">
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
        <nut-button type="primary" block :disabled="!methods.length" @click="start">开始训练</nut-button>
      </view>
      <view class="qc-card">
        <text class="qc-heading">为你推荐</text>
        <text v-if="!recommendations.length" class="qc-copy">完成一定数量的练习后，会根据薄弱方法推荐专项训练。</text>
        <view v-for="item in recommendations" :key="item.code" class="qc-history">
          <view>
            <text>{{ item.name }} · {{ item.accuracy }}% 正确率</text>
            <text class="qc-note">近 {{ item.attempts }} 题需要加强</text>
          </view>
          <nut-button size="small" plain type="primary" @click="startMethod(item.code)">专项练习</nut-button>
        </view>
      </view>
      <view class="qc-card">
        <text class="qc-heading">最近训练</text>
        <text v-if="storageError" class="qc-caution">{{ storageError }}</text>
        <text v-if="!history.length" class="qc-copy">完成一组后，这里会显示账号下的训练记录。</text>
        <view v-for="record in history.slice(0, 5)" :key="record.id" class="qc-history">
          <text>{{ historyLabel(record.mode) }} · {{ record.correct }}/{{ record.total }}</text>
          <text class="qc-note">{{ record.date }} · {{ formatTime(record.seconds) }}</text>
        </view>
      </view>
    </template>

    <template v-else-if="stage === 'practice' && current">
      <view class="qc-row qc-between">
        <text class="qc-heading">{{ index + 1 }} / {{ questions.length }}</text>
        <text class="qc-copy">{{ formatTime(elapsed) }}</text>
      </view>
      <view class="qc-card">
        <text class="qc-note">
          教学模拟题 · {{ methodById(current.method)?.name || current.method }}
        </text>
        <text class="qc-stem">{{ current.stem }}</text>
        <LatexBlock :latex="current.latex" :plain="current.plain" :show-plain="false" size="lg" />
      </view>
      <view
        v-for="(option, optionIndex) in current.options"
        :key="optionIndex"
        class="qc-option"
        :class="optionClass(optionIndex)"
        @tap="answer(optionIndex)"
      >
        <text class="qc-letter">{{ letters[optionIndex] }}</text><text>{{ option }}</text>
      </view>
      <view v-if="answered" class="qc-card">
        <text class="qc-heading" :class="isCorrect ? 'qc-correct' : 'qc-wrong'">
          {{ isCorrect ? '回答正确' : `正确答案：${letters[current.answer]}` }} ·
          {{ methodById(current.method)?.name || current.method }}
        </text>
        <text class="qc-note">{{ methodById(current.method)?.knowledgePath }}</text>
        <text class="qc-copy">适用条件：{{ methodById(current.method)?.scene }}</text>
        <view v-for="(step, stepIndex) in current.steps" :key="stepIndex" class="qc-step">
          <text class="qc-copy">{{ stepIndex + 1 }}. {{ step.text }}</text>
          <LatexBlock v-if="step.latex" :latex="step.latex" :show-plain="false" />
        </view>
        <text class="qc-caution">易错点：{{ current.pitfall }}</text>
        <view class="qc-link" @tap="openKnowledge">查看对应知识节点 ›</view>
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
          <nut-button plain type="primary" @click="setup">选择方法</nut-button>
          <nut-button type="primary" @click="start">再练一组</nut-button>
        </view>
        <nut-button v-if="wrongQuestions.length" plain type="primary" block @click="retryWrong">
          重练本组错题（{{ wrongQuestions.length }}）
        </nut-button>
      </view>
      <view v-for="(attempt, attemptIndex) in attempts" :key="attempt.question.id" class="qc-card">
        <text class="qc-heading">
          {{ attemptIndex + 1 }}. {{ methodById(attempt.question.method)?.name || attempt.question.method }}
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
import type { QuickMode, QuickQuestion, QuickStep } from '@/utils/quickCalc'
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
const mode = ref<QuickMode>('mixed')
const count = ref(10)
const questions = ref<QuickQuestion[]>([])
const index = ref(0)
const attempts = ref<Attempt[]>([])
const history = ref<History[]>([])
const recommendations = ref<Array<{ code: QuickQuestion['method']; name: string; accuracy: number; attempts: number }>>([])
const methods = ref<Array<{ id: string; code: QuickQuestion['method']; name: string; scene: string; knowledgePath: string; nodeTitle: string; nodeParent: string }>>([])
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
function methodById(id: string) { return methods.value.find((method) => method.code === id) }
function historyLabel(value: string) { return value === 'mixed' ? '混合训练' : value === 'retry' ? '错题重练' : methodById(value)?.name || value }
function formatTime(seconds: number) {
  return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
}
function chooseMode(value: QuickMode) {
  mode.value = value
}
function chooseCount(value: number) {
  count.value = value
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
function begin(session: { id: string; questions: Array<Omit<QuickQuestion, 'answer' | 'check' | 'steps' | 'pitfall'> & { id: string }> }) {
  pause()
  sessionId.value = session.id
  questions.value = session.questions.map((question) => ({ ...question, answer: -1, check: { kind: 'number', target: 0, values: [], unit: '' }, steps: [], pitfall: '' }))
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
      questionId: current.value.id, selected, seconds: elapsed.value,
    })
    if (response.code !== 0 || !response.data) throw new Error(response.message || '提交失败')
    const question = current.value
    question.answer = question.options.indexOf(response.data.correctOption)
    question.steps = response.data.steps as QuickStep[]
    question.pitfall = response.data.pitfall
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
    const response = await api.completeQuickCalcSession(sessionId.value, { totalSeconds: totalSeconds.value })
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
  api.retryQuickCalcWrong(sessionId.value, ids).then((response) => {
    if (response.code !== 0 || !response.data) throw new Error(response.message || '错题重练创建失败')
    begin(response.data)
  }).catch(() => showToast('错题重练创建失败，请重试', 'error'))
}
function setup() {
  pause()
  stage.value = 'setup'
}
function openKnowledge() {
  if (!current.value) return
  const info = methodById(current.value.method)
  if (!info) return
  const params = { treeKey: '资料分析', nodeTitle: info.nodeTitle, nodeParent: info.nodeParent || '' }
  const query = Object.entries(params).map(([key, value]) => `${key}=${encodeURIComponent(value)}`).join('&')
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
function goLogin() { Taro.navigateTo({ url: '/pages/auth/login' }) }
function handleLoadAction() { if (loginRequired.value) goLogin(); else reloadData() }
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
.qc-option {
  @include hit-target;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  margin-bottom: 12px;
  background: $card-bg;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  color: $text-primary;
}
.qc-letter {
  font-weight: 700;
  color: $text-secondary;
}
.qc-option-selected {
  border-color: $primary-color;
  background: $primary-light;
}
.qc-option-correct {
  border-color: $success;
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
</style>
