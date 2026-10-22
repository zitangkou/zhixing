<template>
  <page-meta v-if="isWeapp" :page-style="pageMeta.pageStyle" :background-color="pageMeta.backgroundColor" :background-color-top="pageMeta.backgroundColorTop" :background-color-bottom="pageMeta.backgroundColorBottom" :background-text-style="pageMeta.backgroundTextStyle" />
  <view class="se-page" :class="themeClass">
    <view v-if="loading" class="se-state">正在加载…</view>
    <view v-else-if="!item" class="se-state"><text class="se-state-title">练习暂不可用</text><text class="se-state-desc">请返回练习列表后重试。</text></view>
    <template v-else>
      <view class="se-heading">
        <text class="se-kind">{{ typeName(item.question_type) }}</text>
        <text v-if="item.difficulty" class="se-difficulty">{{ item.difficulty }}</text>
        <text class="se-heading-title">{{ item.title }}</text>
        <text class="se-source">{{ item.source_title }}<text v-if="item.source_date"> · {{ item.source_date }}</text></text>
      </view>
      <view v-if="item.fact_material_summary" class="se-fact-card">
        <text class="se-fact-label">已审核事实素材</text><text class="se-fact-summary">{{ item.fact_material_summary }}</text>
        <text v-if="item.fact_material_limit" class="se-fact-limit">使用边界：{{ item.fact_material_limit }}</text>
      </view>
      <view v-if="isGuidedEssay && item.fact_training?.related_materials?.length" class="se-section se-related-facts">
        <text class="se-section-title">AI筛选的相关事实素材</text><text class="se-material-tip">对照适配主题，判断不同案例能否共同支撑论点</text>
        <view v-for="material in item.fact_training.related_materials" :key="material.id" class="se-related-item"><text class="se-related-title">{{ material.source_title }} · {{ material.source_date }}</text><text class="se-related-text">{{ material.text }}</text><text class="se-related-reason">关联角度：{{ material.relation_reason }}</text><text v-if="material.source_url" class="se-source-link" @tap="copySource(material.source_url)">查看来源链接 ↗</text></view>
      </view>
      <view class="se-section">
        <view class="se-section-head"><text class="se-section-title">事实材料</text><text class="se-material-tip">先读事实，再判断它能证明什么</text></view>
        <text class="se-material">{{ item.source_excerpt }}</text>
        <text v-if="item.source_url" class="se-source-link" @tap="openSource">查看来源文章 ↗</text>
      </view>
      <view class="se-section se-prompt">
        <text class="se-section-title">作答任务</text><text class="se-prompt-text">{{ item.prompt }}</text>
        <text v-if="item.requirements" class="se-requirement">{{ item.requirements }}</text>
        <text v-if="item.max_chars" class="se-limit">建议 {{ item.max_chars }} 字以内</text>
      </view>

      <template v-if="isGuidedEssay && !submitted">
        <view class="se-guide-intro"><text class="se-guide-title">事实素材论证训练</text><text class="se-guide-desc">一步一步把材料事实转化成论证段；先自己分析，提交后再对照参考示例。</text></view>
        <view class="se-stepper">
          <view v-for="(step,index) in guidedSteps" :key="step.key" class="se-step" :class="{active:stepIndex===index,done:stepIndex>index}" @tap="goToStep(index)">
            <text class="se-step-no">{{ index + 1 }}</text><text class="se-step-name">{{ step.short }}</text>
          </view>
        </view>
        <view class="se-section se-work-card">
          <view class="se-work-heading"><text class="se-work-kicker">第 {{ stepIndex + 1 }} 步 / {{ guidedSteps.length }}</text><text class="se-work-title">{{ activeStep.title }}</text><text class="se-work-desc">{{ activeStep.description }}</text></view>
          <text v-if="activeStep.key==='fact'" class="se-work-prompt">从材料中找出“谁做了什么，带来什么变化”。只记录原文事实，不加推断。</text>
          <text v-else-if="activeStep.key==='theme'" class="se-work-prompt">结合主素材与相关素材，选择一个能被材料共同支撑的适配主题，再继续写观点。</text>
          <text v-else-if="activeStep.key==='point'" class="se-work-prompt">围绕题目写一句分论点。观点要明确，并且能被这则事实支撑。</text>
          <text v-else-if="activeStep.key==='analysis'" class="se-work-prompt">解释事实为什么能证明观点：做法通过什么机制解决问题或产生效果？</text>
          <view v-if="activeStep.key==='theme' && item.fact_training?.themes?.length" class="se-theme-options">
            <view v-for="theme in item.fact_training.themes" :key="theme.id" class="se-theme-option" :class="{selected: guidedWork.theme_id===theme.id}" @tap="selectTheme(theme.id)"><text class="se-theme-name">{{ theme.theme }}</text><text class="se-theme-reason">{{ theme.fit_reason }}</text><text v-if="guidedWork.theme_id===theme.id" class="se-theme-task">训练焦点：{{ theme.task_prompt }}</text></view>
          </view>
          <view v-if="activeStep.key==='paragraph'" class="se-work-summary">
            <text class="se-summary-label">你的拆解</text>
            <text class="se-summary-line"><text class="se-summary-key">事实</text>{{ guidedWork.fact || '尚未填写' }}</text>
            <text class="se-summary-line"><text class="se-summary-key">主题</text>{{ guidedWork.theme || '尚未填写' }}</text>
            <text class="se-summary-line"><text class="se-summary-key">观点</text>{{ guidedWork.point || '尚未填写' }}</text>
            <text class="se-summary-line"><text class="se-summary-key">分析</text>{{ guidedWork.analysis || '尚未填写' }}</text>
          </view>
          <view v-if="activeStep.key!=='theme' || !item.fact_training?.themes?.length" class="se-answer-head"><text class="se-section-title">{{ activeStep.inputLabel }}</text><text class="se-count">{{ activeValue.length }} 字</text></view>
          <textarea v-if="activeStep.key!=='theme' || !item.fact_training?.themes?.length" class="se-textarea se-guided-textarea" :value="activeValue" :maxlength="activeStep.key==='paragraph'?12000:2000" :placeholder="activeStep.placeholder" @input="onGuidedInput" />
          <text v-if="item.hint && stepIndex===0" class="se-hint-inline">审题提示：{{ item.hint }}</text>
          <view class="se-guide-actions">
            <button v-if="stepIndex>0" class="se-secondary se-nav-button" @tap="previousStep">上一步</button>
            <button v-if="stepIndex<guidedSteps.length-1" class="se-primary se-nav-button" :disabled="activeStep.key==='theme' && item.fact_training?.themes?.length ? !guidedWork.theme_id : !activeValue.trim()" @tap="nextStep">下一步</button>
            <button v-else class="se-primary se-nav-button" :disabled="!guidedWork.paragraph.trim()||saving" @tap="submit">{{ saving?'提交中…':'提交论证段' }}</button>
          </view>
        </view>
      </template>

      <template v-else-if="!submitted">
        <view v-if="item.hint" class="se-hint" @tap="toggleHint"><text class="se-hint-label">审题提示 {{ showHint?'收起':'展开' }}</text><text v-if="showHint" class="se-hint-text">{{ item.hint }}</text></view>
        <view class="se-section se-answer"><view class="se-answer-head"><text class="se-section-title">写下你的答案</text><text class="se-count">{{ answer.length }}{{ item.max_chars?` / ${item.max_chars}`:'' }}</text></view><textarea class="se-textarea" :value="answer" :maxlength="12000" placeholder="先独立完成，再提交查看参考要点" @input="onAnswerInput" /></view>
        <view class="se-actions"><button class="se-primary" :disabled="!answer.trim()||saving" @tap="submit">{{ saving?'提交中…':'提交并查看解析' }}</button></view>
      </template>

      <template v-if="submitted">
        <view class="se-section se-my-answer"><text class="se-section-title">我的作答</text><text class="se-material">{{ answer }}</text></view>
        <view v-if="isGuidedEssay && hasSavedWork" class="se-section se-work-review">
          <text class="se-section-title">我的拆解过程</text>
          <view v-for="step in guidedSteps" :key="step.key" class="se-work-review-row"><text>{{ step.short }}</text><text>{{ guidedWork[step.key] || '未填写' }}</text></view>
        </view>
        <view class="se-feedback-head"><text class="se-feedback-title">参考答案与自查</text><text class="se-feedback-tip">逐项核对材料依据，不以措辞完全一致为标准。</text></view>
        <view v-if="item.key_points.length" class="se-section"><text class="se-section-title">关键要点与材料依据</text><view v-for="(point,index) in item.key_points" :key="`${index}-${point.point}`" class="se-point"><text class="se-point-num">{{ String(index+1).padStart(2,'0') }}</text><view class="se-point-body"><text class="se-point-title">{{ point.point }}</text><text class="se-point-evidence">材料依据：{{ point.evidence }}</text></view></view></view>
        <view v-if="item.rubric.length" class="se-section"><text class="se-section-title">自查清单</text><view v-for="row in item.rubric" :key="row.name" class="se-rubric"><text class="se-rubric-name">{{ row.name }}</text><text class="se-rubric-desc">{{ row.description }}</text></view></view>
        <view v-if="item.sample_answer" class="se-section"><text class="se-section-title">参考答案</text><text class="se-material">{{ item.sample_answer }}</text></view>
        <view v-if="item.analysis" class="se-section"><text class="se-section-title">解析</text><text class="se-material">{{ item.analysis }}</text></view>
        <view v-if="isGuidedEssay && selectedTheme" class="se-section se-reference-training"><text class="se-section-title">AI 参考训练示例 · {{ selectedTheme.theme }}</text><text class="se-reference-label">参考观点</text><text class="se-material">{{ selectedTheme.point }}</text><text class="se-reference-label">分析逻辑</text><text class="se-material">{{ selectedTheme.analysis }}</text><text class="se-reference-label">示例论证段</text><text class="se-material">{{ selectedTheme.paragraph }}</text><view v-for="(citation,index) in selectedTheme.citations||[]" :key="index" class="se-reference-citation"><text>材料依据 {{ index+1 }}</text><text>{{ citation.exact_evidence }}</text></view></view>
        <view class="se-section se-revise"><text class="se-section-title">订正一遍</text><text class="se-revise-tip">先对照要点修改答案，再写一句本次发现。</text><textarea class="se-textarea" :value="revision" :maxlength="12000" placeholder="写下修订后的答案" @input="onRevisionInput" /><textarea class="se-reflection" :value="reflection" :maxlength="2000" placeholder="我这次漏掉 / 改进的是…" @input="onReflectionInput" /><button class="se-secondary" :disabled="!revision.trim()||saving" @tap="saveRevision">{{ saving?'保存中…':item.attempt?.revision?'更新订正':'保存订正' }}</button><text v-if="item.attempt?.revision" class="se-saved">订正已保存，可继续修改。</text></view>
        <view v-if="item.related_assets.length" class="se-section"><text class="se-section-title">相关积累</text><text v-for="asset in item.related_assets" :key="`${asset.type}-${asset.id}`" class="se-asset">{{ asset.title }}</text></view>
      </template>
      <view class="se-footer">内容基于已审核材料 · 作答建议结合题目要求与原文依据</view>
    </template>
  </view>
</template>
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { api } from '@/api'
import type { ShenlunExerciseCard } from '@/api/domains/rmrb'
import { useThemeClass, usePageMeta } from '@/utils/brandColor'
import { showToast } from '@/utils/platform'

definePageConfig({ navigationBarTitleText: '申论练习' })
const router = useRouter(), { themeClass } = useThemeClass(), pageMeta = usePageMeta(), isWeapp = process.env.TARO_ENV === 'weapp'
const item = ref<ShenlunExerciseCard | null>(null), loading = ref(true), saving = ref(false)
const answer = ref(''), revision = ref(''), reflection = ref(''), submitted = ref(false), showHint = ref(false), stepIndex = ref(0)
const id = String(router.params?.id || ''), storageKey = `shenlun-exercise-draft:${id}`
type WorkKey = 'fact' | 'theme' | 'point' | 'analysis' | 'paragraph'
type GuidedWork = Record<WorkKey, string> & { theme_id: string }
const emptyWork = (): GuidedWork => ({ fact: '', theme: '', theme_id: '', point: '', analysis: '', paragraph: '' })
const guidedWork = reactive<GuidedWork>(emptyWork())
const guidedSteps: { key: WorkKey; short: string; title: string; description: string; inputLabel: string; placeholder: string }[] = [
  { key: 'fact', short: '找事实', title: '从材料中提取事实', description: '抓住可核对的信息，不先急着拔高主题。', inputLabel: '事实记录', placeholder: '主体 + 做法 + 问题变化或实际效果' },
  { key: 'theme', short: '定主题', title: '归纳这则事实的主题', description: '主题要从材料中来，范围尽量具体。', inputLabel: '主题概括', placeholder: '例如：基层公共服务如何提升可及性' },
  { key: 'point', short: '提观点', title: '写出分论点', description: '把主题转成一句明确、可论证的判断。', inputLabel: '分论点', placeholder: '围绕题目写一句观点，避免只复述材料' },
  { key: 'analysis', short: '做分析', title: '解释事实如何支撑观点', description: '补出原因、机制或作用，不要停留在“做了什么”。', inputLabel: '分析说明', placeholder: '这项做法解决了什么问题？通过什么机制产生作用？' },
  { key: 'paragraph', short: '成段落', title: '整合成一段论证', description: '组织观点、分析和事实，形成完整论证段。', inputLabel: '论证段', placeholder: '建议先写观点，再解释逻辑，嵌入材料事实，最后回扣主题。' },
]
const isGuidedEssay = computed(() => item.value?.question_type === 'essay' && Boolean(item.value.source_material_id))
const selectedTheme = computed(() => item.value?.fact_training?.themes?.find(theme => theme.id === guidedWork.theme_id))
const activeStep = computed(() => guidedSteps[stepIndex.value])
const activeValue = computed(() => guidedWork[activeStep.value.key])
const hasSavedWork = computed(() => guidedSteps.some(step => Boolean(guidedWork[step.key])))
function typeName(v: string) { return ({ summary: '归纳概括', countermeasure: '提出对策', implementation: '贯彻执行', essay: '申发论述 · 事实论证' } as Record<string, string>)[v] || '申论练习' }
function restoreWork(value: unknown) {
  const next = emptyWork()
  if (value && typeof value === 'object') {
    for (const key of ['fact', 'theme', 'point', 'analysis', 'paragraph'] as WorkKey[]) {
      const text = (value as Record<string, unknown>)[key]
      if (typeof text === 'string') next[key] = text
    }
    const themeId = (value as Record<string, unknown>).theme_id
    if (typeof themeId === 'string') next.theme_id = themeId
  }
  Object.assign(guidedWork, next)
}
function persistWork() { Taro.setStorageSync(storageKey, JSON.stringify({ work: { ...guidedWork }, stepIndex: stepIndex.value })) }
async function load() {
  loading.value = true
  try {
    const res = await api.getShenlunExercise(id)
    if (res.code !== 0 || !res.data) { showToast(res.message || '练习加载失败', 'error'); return }
    item.value = res.data
    submitted.value = Boolean(res.data.attempt)
    if (submitted.value) {
      answer.value = res.data.attempt?.answer || ''
      revision.value = res.data.attempt?.revision || ''
      reflection.value = res.data.attempt?.reflection || ''
      restoreWork(res.data.attempt?.work)
    } else {
      const saved = Taro.getStorageSync(storageKey)
      if (isGuidedEssay.value && saved) {
        try { const parsed = typeof saved === 'string' ? JSON.parse(saved) : saved; restoreWork(parsed?.work); stepIndex.value = Math.max(0, Math.min(guidedSteps.length - 1, Number(parsed?.stepIndex) || 0)) }
        catch { restoreWork({}) }
      } else answer.value = saved || ''
    }
  } catch { showToast('练习加载失败', 'error') }
  finally { loading.value = false }
}
function onAnswerInput(e: { detail: { value: string } }) { answer.value = e.detail.value; Taro.setStorageSync(storageKey, answer.value) }
function onGuidedInput(e: { detail: { value: string } }) { guidedWork[activeStep.value.key] = e.detail.value; persistWork() }
function selectTheme(themeId:string) { const theme=item.value?.fact_training?.themes?.find(value=>value.id===themeId);if(!theme)return;guidedWork.theme_id=theme.id;guidedWork.theme=theme.theme;persistWork() }
function nextStep() { if (!activeValue.value.trim()) return; stepIndex.value = Math.min(guidedSteps.length - 1, stepIndex.value + 1); persistWork() }
function previousStep() { stepIndex.value = Math.max(0, stepIndex.value - 1); persistWork() }
function goToStep(index: number) { if (index <= stepIndex.value) stepIndex.value = index; else if (guidedSteps.slice(0, index).every(step => guidedWork[step.key].trim())) stepIndex.value = index; persistWork() }
function toggleHint() { showHint.value = !showHint.value }
function onRevisionInput(e: { detail: { value: string } }) { revision.value = e.detail.value }
function onReflectionInput(e: { detail: { value: string } }) { reflection.value = e.detail.value }
function openSource() { if (item.value?.source_url) Taro.setClipboardData({ data: item.value.source_url }).then(() => showToast('来源链接已复制', 'success')) }
function copySource(url:string) { if(url) Taro.setClipboardData({data:url}).then(()=>showToast('来源链接已复制','success')) }
async function submit() {
  const finalAnswer = isGuidedEssay.value ? guidedWork.paragraph : answer.value
  if (!finalAnswer.trim()) { showToast('先写下你的作答'); return }
  saving.value = true
  try {
    const res = await api.submitShenlunExercise(id, finalAnswer.trim(), isGuidedEssay.value ? { ...guidedWork } : {})
    if (res.code === 0 && res.data) { item.value = res.data; submitted.value = true; answer.value = finalAnswer.trim(); Taro.removeStorageSync(storageKey); showToast('已提交，参考解析已解锁', 'success') }
    else showToast(res.message || '提交失败', 'error')
  } catch { showToast('提交失败，请稍后重试', 'error') }
  finally { saving.value = false }
}
async function saveRevision() {
  if (!item.value?.attempt?.id || !revision.value.trim()) return
  saving.value = true
  try { const res = await api.reviseShenlunExercise(id, item.value.attempt.id, revision.value.trim(), reflection.value.trim()); if (res.code === 0 && res.data) { item.value = res.data; showToast('订正已保存', 'success') } else showToast(res.message || '保存失败', 'error') }
  catch { showToast('保存失败，请稍后重试', 'error') }
  finally { saving.value = false }
}
onMounted(load)
</script>
<style lang="scss" scoped>
@import '@/styles/variables.scss';
.se-page{@include page-padding;padding-bottom:36px}.se-heading{@include card;margin-bottom:12px}.se-kind{@include brand-chip;display:inline-block}.se-difficulty{margin-left:8px;@include muted-chip}.se-heading-title{display:block;margin-top:12px;font-size:20px;line-height:1.4;font-weight:700;color:$text-primary}.se-source{display:block;margin-top:8px;font-size:12px;color:$text-muted}.se-section{@include card;margin-bottom:10px}.se-fact-card{padding:14px;margin-bottom:10px;border:1px solid $border-color;border-radius:$radius-md;background:$elevated}.se-fact-label{display:block;margin-bottom:6px;color:$primary-color;font-size:12px;font-weight:700}.se-fact-summary{display:block;color:$text-primary;font-size:14px;line-height:1.65}.se-fact-limit{display:block;margin-top:8px;color:$text-muted;font-size:12px;line-height:1.5}.se-section-head{display:flex;justify-content:space-between;align-items:center;gap:8px}.se-section-title{display:block;margin-bottom:10px;font-size:15px;font-weight:700;color:$text-primary}.se-material-tip{margin-bottom:10px;font-size:11px;color:$text-muted}.se-material,.se-prompt-text{display:block;white-space:pre-wrap;font-size:14px;line-height:1.75;color:$text-primary}.se-source-link{display:inline-block;margin-top:10px;font-size:12px;color:$primary-color}.se-requirement{display:block;margin-top:10px;font-size:13px;line-height:1.6;color:$text-secondary}.se-limit{display:inline-block;margin-top:10px;padding:4px 8px;border-radius:8px;background:$elevated;color:$text-muted;font-size:12px}.se-guide-intro{padding:14px 4px 10px}.se-guide-title{display:block;font-size:18px;font-weight:700;color:$text-primary}.se-guide-desc{display:block;margin-top:5px;font-size:12px;line-height:1.55;color:$text-secondary}.se-stepper{display:flex;justify-content:space-between;gap:4px;padding:8px 2px 14px}.se-step{display:flex;flex:1;flex-direction:column;align-items:center;gap:5px;color:$text-muted}.se-step-no{display:flex;width:25px;height:25px;align-items:center;justify-content:center;border:1px solid $border-color;border-radius:50%;font-size:12px}.se-step-name{font-size:10px;white-space:nowrap}.se-step.active{color:$primary-color;font-weight:700}.se-step.active .se-step-no,.se-step.done .se-step-no{border-color:$primary-color;background:$primary-color;color:#fff}.se-step.done{color:$primary-color}.se-work-card{padding:16px}.se-work-heading{margin-bottom:14px}.se-work-kicker{display:block;color:$primary-color;font-size:11px;font-weight:700}.se-work-title{display:block;margin-top:5px;color:$text-primary;font-size:17px;font-weight:700}.se-work-desc{display:block;margin-top:4px;color:$text-secondary;font-size:12px;line-height:1.5}.se-work-prompt{display:block;margin-bottom:10px;color:$text-secondary;font-size:13px;line-height:1.6}.se-work-summary{padding:10px 12px;margin-bottom:12px;border-radius:$radius-md;background:$elevated}.se-summary-label{display:block;margin-bottom:5px;color:$text-muted;font-size:11px}.se-summary-line{display:block;margin-top:5px;color:$text-secondary;font-size:12px;line-height:1.5}.se-summary-key{display:inline-block;min-width:32px;color:$text-primary;font-weight:700}.se-answer-head{display:flex;justify-content:space-between;align-items:center}.se-count{font-size:12px;color:$text-muted}.se-guided-textarea{min-height:135px}.se-textarea,.se-reflection{display:block;width:100%;min-height:170px;padding:12px;border:1px solid $border-color;border-radius:$radius-md;background:$input-bg;color:$text-primary;font-size:14px;line-height:1.65;box-sizing:border-box}.se-reflection{min-height:72px;margin-top:10px}.se-hint-inline{display:block;margin-top:8px;color:$text-muted;font-size:12px;line-height:1.55}.se-guide-actions{display:flex;gap:10px;margin-top:14px}.se-nav-button{flex:1;width:auto;margin:0}.se-primary,.se-secondary{width:100%;min-height:46px;border:0;border-radius:$radius-md;background:$primary-color;color:#fff;font-size:15px;font-weight:600}.se-primary[disabled],.se-secondary[disabled]{opacity:.55}.se-actions{position:sticky;bottom:12px;padding:4px 0 12px}.se-feedback-head{padding:16px 4px 8px}.se-feedback-title{display:block;font-size:18px;font-weight:700;color:$text-primary}.se-feedback-tip,.se-revise-tip{display:block;margin-top:5px;font-size:12px;line-height:1.55;color:$text-muted}.se-point{display:flex;gap:10px;padding:12px 0;border-top:1px solid $border-color}.se-point-num{color:$primary-color;font-size:12px;font-weight:700}.se-point-body{flex:1}.se-point-title{display:block;font-size:14px;line-height:1.5;font-weight:600;color:$text-primary}.se-point-evidence{display:block;margin-top:6px;font-size:12px;line-height:1.55;color:$text-secondary}.se-rubric{padding:9px 0;border-top:1px solid $border-color}.se-rubric-name{display:block;font-size:13px;font-weight:600;color:$text-primary}.se-rubric-desc{display:block;margin-top:3px;font-size:12px;line-height:1.5;color:$text-secondary}.se-secondary{margin-top:10px;background:$elevated;color:$primary-color;border:1px solid $border-color}.se-saved{display:block;margin-top:8px;color:$success;font-size:12px}.se-asset{display:block;padding:8px 0;border-top:1px solid $border-color;font-size:13px;color:$text-secondary}.se-work-review-row{padding:9px 0;border-top:1px solid $border-color}.se-work-review-row text:first-child{display:block;color:$primary-color;font-size:12px;font-weight:700}.se-work-review-row text:last-child{display:block;margin-top:4px;color:$text-primary;font-size:13px;line-height:1.55}.se-revise{margin-top:10px}.se-footer{padding:10px 2px;color:$text-muted;font-size:11px;line-height:1.5}.se-state{@include page-state-box;margin-top:28px}.se-state-title{display:block;font-size:15px;font-weight:600;color:$text-primary}.se-state-desc{display:block;margin-top:5px;font-size:13px;color:$text-muted}
.se-related-item{padding:10px 0;border-top:1px solid $border-color}.se-related-title,.se-related-text,.se-related-reason{display:block}.se-related-title{font-size:12px;font-weight:700;color:$primary-color}.se-related-text{margin-top:5px;font-size:13px;line-height:1.6;color:$text-primary}.se-related-reason{margin-top:5px;font-size:11px;line-height:1.5;color:$text-muted}.se-theme-options{margin:6px 0 12px}.se-theme-option{padding:12px;margin-top:8px;border:1px solid $border-color;border-radius:$radius-md;background:$elevated}.se-theme-option.selected{border-color:$primary-color;box-shadow:0 0 0 1px $primary-color}.se-theme-name,.se-theme-reason,.se-theme-task{display:block}.se-theme-name{font-size:14px;font-weight:700;color:$text-primary}.se-theme-reason,.se-theme-task{margin-top:5px;font-size:12px;line-height:1.55;color:$text-secondary}.se-reference-training{border:1px solid $border-color}.se-reference-label{display:block;margin:10px 0 4px;color:$primary-color;font-size:12px;font-weight:700}.se-reference-citation{padding:9px 0;border-top:1px solid $border-color}.se-reference-citation text{display:block;font-size:12px;line-height:1.55;color:$text-secondary}.se-reference-citation text:first-child{margin-bottom:3px;color:$primary-color;font-weight:700}
</style>
