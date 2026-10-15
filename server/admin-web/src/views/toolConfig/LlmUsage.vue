<template>
  <div class="usage-page">
    <div class="toolbar"><h2>大模型用量</h2><el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期"/><el-button type="primary" :loading="loading" @click="load">查询</el-button></div>
    <el-alert v-if="!pricingConfigured" title="当前只统计 token 和调用量。配置 LLM_INPUT_PRICE_PER_MILLION / LLM_OUTPUT_PRICE_PER_MILLION 后显示费用估算；价格单位按服务商配置。" type="info" :closable="false" />
    <div class="cards"><el-card><span>调用次数</span><strong>{{ totals.calls }}</strong></el-card><el-card><span>输入 Token</span><strong>{{ totals.input.toLocaleString() }}</strong></el-card><el-card><span>输出 Token</span><strong>{{ totals.output.toLocaleString() }}</strong></el-card><el-card><span>失败调用</span><strong>{{ totals.failures }}</strong></el-card><el-card v-if="pricingConfigured"><span>估算费用</span><strong>{{ totals.cost.toFixed(4) }}</strong></el-card></div>
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="date" label="日期" width="120"/><el-table-column label="模块 / 环节" min-width="190"><template #default="{ row }">{{ purposes[row.purpose] || row.purpose }}</template></el-table-column><el-table-column prop="model" label="模型" min-width="160"/><el-table-column prop="calls" label="调用" width="90"/><el-table-column prop="successes" label="成功" width="90"/><el-table-column prop="failures" label="失败" width="90"/><el-table-column label="输入 Token" width="130"><template #default="{ row }">{{ row.promptTokens.toLocaleString() }}</template></el-table-column><el-table-column label="输出 Token" width="130"><template #default="{ row }">{{ row.completionTokens.toLocaleString() }}</template></el-table-column><el-table-column label="总 Token" width="130"><template #default="{ row }">{{ row.totalTokens.toLocaleString() }}</template></el-table-column><el-table-column label="均耗时" width="110"><template #default="{ row }">{{ (row.avgDurationMs / 1000).toFixed(1) }} 秒</template></el-table-column><el-table-column v-if="pricingConfigured" label="估算费用" width="120"><template #default="{ row }">{{ (row.estimatedCost || 0).toFixed(4) }}</template></el-table-column>
    </el-table>
    <p class="footnote">只统计接入用量记录后的调用，历史调用不会回填。用量来自模型服务返回的 usage 字段；未返回 token 统计时显示为0。页面不存储提示词、文章正文或模型输出。费用按当前配置单价估算。</p>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getLlmUsageSummary, type LlmUsageRow } from '@/api/llmUsage'
const purposes: Record<string,string> = { rmrb_quote_directory:'金句·目录筛选', rmrb_quote_selection:'金句·候选筛选', rmrb_quote_examples:'金句·精选仿写', rmrb_comment_quote_enrichment:'客户端评论·加粗句补充标签', rmrb_comment_quote_selection:'客户端评论·候选金句筛选', rmrb_comment_three_knife:'评论文章·三刀解剖', rmrb_archive_article_evaluation:'人民日报·文章评估', rmrb_vocabulary_extraction:'词汇·全版提取', rmrb_combined_article_analysis:'人民日报·金句与词汇联合筛选', general:'其他模型调用' }
const today = new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai'}).format(new Date())
const prior = new Date(`${today}T00:00:00+08:00`); prior.setDate(prior.getDate()-29)
const range = ref([new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai'}).format(prior),today])
const loading=ref(false),items=ref<LlmUsageRow[]>([]),pricingConfigured=ref(false)
const totals=computed(()=>items.value.reduce((a,r)=>({calls:a.calls+r.calls,input:a.input+r.promptTokens,output:a.output+r.completionTokens,failures:a.failures+r.failures,cost:a.cost+(r.estimatedCost||0)}),{calls:0,input:0,output:0,failures:0,cost:0}))
async function load(){loading.value=true;try{const result=await getLlmUsageSummary({start:range.value[0],end:range.value[1]});items.value=result.items;pricingConfigured.value=result.pricingConfigured}catch(e){ElMessage.error(e instanceof Error?e.message:'用量读取失败')}finally{loading.value=false}}
onMounted(load)
</script>
<style scoped>
.usage-page{padding:20px}.toolbar{display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap}.toolbar h2{margin-right:auto}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}.cards .el-card{display:flex}.cards span{color:var(--el-text-color-secondary)}.cards strong{display:block;font-size:24px;margin-top:10px}.footnote{font-size:12px;color:var(--el-text-color-secondary);margin-top:14px}
</style>
