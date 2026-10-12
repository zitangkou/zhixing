<template>
  <div class="page">
    <div class="page-heading">
      <div>
        <h2>人民日报全量文章</h2>
        <p>全量文章逐篇评估体裁、申论价值与原文证据；高/中关联文章保存全文，AI 结论经人工确认后生效。</p>
      </div>
      <div class="heading-actions"><el-button type="primary" :disabled="!dateRange?.[0] || !dateRange?.[1]" :loading="batchEvaluating" @click="evaluateDateRange">评估所选日期全部</el-button><el-button :disabled="!selectedIds.length" :loading="batchEvaluating" @click="evaluateSelected(false)">评估选中 {{ selectedIds.length || '' }}</el-button><el-button :disabled="!selectedIds.length" :loading="batchEvaluating" @click="evaluateSelected(true)">重评选中</el-button><el-button @click="openCreate">新增文章</el-button></div>
    </div>

    <el-card shadow="never" class="filters-card">
      <el-form inline @submit.prevent="search">
        <el-form-item label="出版日期">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" clearable />
        </el-form-item>
        <el-form-item label="版面号"><el-input v-model="filters.page_no" clearable placeholder="如 01" style="width: 100px" /></el-form-item>
        <el-form-item label="版面名称"><el-input v-model="filters.page_name" clearable placeholder="要闻/评论" style="width: 130px" /></el-form-item>
        <el-form-item label="标题"><el-input v-model="filters.title" clearable placeholder="标题关键词" style="width: 180px" @keyup.enter="search" /></el-form-item>
        <el-form-item label="稿件类型"><el-select v-model="filters.article_type" clearable placeholder="全部" style="width: 150px"><el-option v-for="item in articleTypes" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="对象性质"><el-select v-model="filters.record_class" clearable placeholder="全部" style="width: 135px"><el-option v-for="item in recordClasses" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="申论关联"><el-select v-model="filters.exam_relevance" clearable placeholder="全部" style="width: 125px"><el-option v-for="item in relevanceLevels" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="保存等级"><el-select v-model="filters.retention_tier" clearable placeholder="全部" style="width: 140px"><el-option v-for="item in retentionTiers" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="作者"><el-input v-model="filters.author" clearable placeholder="作者署名" style="width: 130px" /></el-form-item>
        <el-form-item label="编辑"><el-input v-model="filters.editor" clearable placeholder="编辑署名" style="width: 130px" /></el-form-item>
        <el-form-item label="来源渠道"><el-select v-model="filters.source_channel" clearable placeholder="全部" style="width: 170px"><el-option label="人民日报电子报" value="people_daily_epaper" /><el-option label="客户端首页" value="peopleapp_home" /><el-option label="客户端评论" value="peopleapp_opinion" /></el-select></el-form-item>
        <el-form-item label="正文状态"><el-select v-model="filters.body_status" clearable placeholder="全部" style="width: 140px"><el-option label="已保存全文" value="full" /><el-option label="评估后未留存" value="evaluated_transient" /><el-option label="未获取" value="not_fetched" /><el-option label="受限" value="restricted" /></el-select></el-form-item>
        <el-form-item label="AI评估"><el-select v-model="filters.evaluation_status" clearable placeholder="全部" style="width: 130px"><el-option label="未进入队列" value="not_evaluated" /><el-option label="待评估" value="queued" /><el-option label="评估中" value="processing" /><el-option label="已完成" value="completed" /><el-option label="失败" value="failed" /></el-select></el-form-item>
        <el-form-item label="复核状态"><el-select v-model="filters.review_status" clearable placeholder="全部" style="width: 140px"><el-option label="待复核" value="pending" /><el-option label="人工已确认" value="approved" /><el-option label="规则自动确认" value="auto_approved" /><el-option label="需修订" value="revise" /></el-select></el-form-item>
        <el-form-item><el-button type="primary" @click="search">查询</el-button><el-button @click="reset">重置</el-button></el-form-item>
      </el-form>
      <div class="result-count">共 {{ total }} 篇；当前页可批量评估。采集批次完成后会自动排队评估该刊期全部文章。</div>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="items" row-key="id" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="issueDate" label="出版日期" width="115" />
        <el-table-column label="版面" width="145"><template #default="{ row }"><span v-if="row.pageRefs?.length">{{ pageNumbers(row) }}版</span><span v-else>—</span><div v-if="row.pageRefs?.length" class="sub-title">{{ pageNames(row) }}</div></template></el-table-column>
        <el-table-column label="标题" min-width="240" show-overflow-tooltip><template #default="{ row }"><el-button link type="primary" @click="openDetail(row)">{{ row.displayTitle }}</el-button><div v-if="row.subtitle" class="sub-title">{{ row.subtitle }}</div></template></el-table-column>
        <el-table-column label="稿件类型" width="155"><template #default="{ row }"><div>{{ labelOf(articleTypes, row.sourceArticleType) }}</div><small v-if="row.classificationSuggestion?.sourceArticleType && row.classificationSuggestion.sourceArticleType !== 'undetermined' && row.sourceArticleType === 'undetermined'" class="muted">建议：{{ labelOf(articleTypes, row.classificationSuggestion.sourceArticleType) }} · {{ Math.round((row.classificationSuggestion.confidence || 0) * 100) }}%</small><small v-else-if="row.sourceArticleType === 'undetermined'" class="muted">需人工判定</small></template></el-table-column>
        <el-table-column label="申论关联" width="130"><template #default="{ row }"><el-tag size="small" :type="relevanceTag(row.examRelevance)">{{ labelOf(relevanceLevels, row.examRelevance) }}</el-tag><small v-if="row.classificationSuggestion?.examRelevance && row.classificationSuggestion.examRelevance !== 'pending' && row.examRelevance === 'pending'" class="muted">建议：{{ labelOf(relevanceLevels, row.classificationSuggestion.examRelevance) }}</small></template></el-table-column>
        <el-table-column label="AI 评估" width="130"><template #default="{ row }"><el-tag size="small" :type="evaluationTag(row.latestEvaluation?.status)">{{ evaluationLabel(row.latestEvaluation?.status) }}</el-tag><small v-if="row.latestEvaluation?.result?.overallScore" class="muted">{{ row.latestEvaluation.result.overallScore }} 分</small><small v-if="row.latestEvaluation?.reviewStatus && row.latestEvaluation.reviewStatus !== 'pending'" class="muted">{{ evaluationReviewLabel(row.latestEvaluation.reviewStatus) }}</small></template></el-table-column>
        <el-table-column label="观点/分析" width="130"><template #default="{ row }"><el-tag v-if="row.latestEvaluation?.status === 'completed'" size="small" :type="opinionTag(row.latestEvaluation.result.opinionNature)">{{ opinionLabel(row.latestEvaluation.result.opinionNature) }}</el-tag><span v-else class="muted">—</span><small v-if="row.latestEvaluation?.result?.opinionNature" class="muted">置信 {{ Math.round((row.latestEvaluation.result.opinionNature.confidence || 0) * 100) }}%</small></template></el-table-column>
        <el-table-column label="复核状态" width="115"><template #default="{ row }"><el-tag size="small" :type="row.reviewStatus === 'approved' ? 'success' : row.reviewStatus === 'auto_approved' ? 'success' : row.reviewStatus === 'revise' ? 'danger' : 'warning'">{{ reviewLabel(row.reviewStatus) }}</el-tag></template></el-table-column>
        <el-table-column label="保存/正文" width="150"><template #default="{ row }"><div>{{ labelOf(retentionTiers, row.retentionTier) }}</div><small class="muted">{{ bodyStatusLabel(row.bodyStatus) }}</small></template></el-table-column>
        <el-table-column label="作者 / 编辑" width="180" show-overflow-tooltip><template #default="{ row }"><div>{{ row.authorLine || '作者未标注' }}</div><small v-if="row.editorLine" class="muted">编辑：{{ row.editorLine }}</small></template></el-table-column>
        <el-table-column label="来源" width="90"><template #default="{ row }"><el-link v-if="row.primarySourceUrl" :href="row.primarySourceUrl" target="_blank" rel="noopener" type="primary">打开原文</el-link><span v-else class="muted">暂无</span></template></el-table-column>
        <el-table-column label="操作" width="190" fixed="right"><template #default="{ row }"><el-button link type="primary" :loading="evaluatingId === row.id" @click="evaluateOne(row)">AI评估</el-button><el-button link type="primary" :disabled="!row.latestEvaluation" @click="openEvaluation(row)">报告</el-button><el-button link @click="openEdit(row)">编辑</el-button><el-popconfirm title="将文章移入归档？" @confirm="archive(row)"><template #reference><el-button link type="danger">归档</el-button></template></el-popconfirm></template></el-table-column>
      </el-table>
      <el-empty v-if="!loading && !items.length" description="暂无文章档案" />
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" class="pager" :total="total" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next, jumper" @change="load" />
    </el-card>

    <el-dialog v-model="formVisible" :title="editingId ? '编辑文章档案' : '新增文章档案'" width="860px" top="5vh" destroy-on-close>
      <el-form :model="form" label-width="100px" class="article-form">
        <el-alert v-if="editingId && activeSuggestion" type="info" :closable="false" class="suggestion-alert">
          <template #title>系统建议 · {{ suggestionMethodLabel(activeSuggestion.method) }} · 置信度 {{ Math.round((activeSuggestion.confidence || 0) * 100) }}%</template>
          <div>稿件体裁：{{ labelOf(articleTypes, activeSuggestion.sourceArticleType) }}；申论关联：{{ labelOf(relevanceLevels, activeSuggestion.examRelevance) }}</div>
          <div v-for="reason in activeSuggestion.reasons || []" :key="reason">{{ reason }}</div>
          <div class="muted">系统建议不会自动作为最终分类；请结合原文确认。无法判断时保持“待复核”。</div>
          <div class="suggestion-actions"><el-button size="small" @click="applyClassificationSuggestion">填入建议值</el-button><el-link v-if="activeArticle?.primarySourceUrl" :href="activeArticle.primarySourceUrl" target="_blank" rel="noopener" type="primary">打开原文核对</el-link></div>
        </el-alert>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="出版日期" required><el-date-picker v-model="form.issueDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="版面号"><el-input v-model="form.pageNo" placeholder="01" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="版面名称"><el-input v-model="form.pageName" placeholder="要闻、评论、经济" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="人工复核"><el-select v-model="form.reviewStatus" style="width: 100%"><el-option label="待复核" value="pending" /><el-option label="人工已确认" value="approved" /><el-option v-if="form.reviewStatus === 'auto_approved'" label="规则自动确认（系统状态）" value="auto_approved" disabled /><el-option label="需修订" value="revise" /></el-select><div class="muted">人工确认时必须选择确定的稿件体裁和申论关联；无法判断的内容继续留在复核队列。</div></el-form-item>
        <el-form-item label="显示标题" required><el-input v-model="form.displayTitle" /></el-form-item>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="主标题"><el-input v-model="form.headline" /></el-form-item></el-col><el-col :span="12"><el-form-item label="副标题"><el-input v-model="form.subtitle" /></el-form-item></el-col></el-row>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="栏目"><el-input v-model="form.columnLabel" /></el-form-item></el-col><el-col :span="12"><el-form-item label="专题/系列"><el-input v-model="form.seriesLabel" /></el-form-item></el-col></el-row>
        <el-row :gutter="16"><el-col :span="8"><el-form-item label="作者署名"><el-input v-model="form.authorLine" /></el-form-item></el-col><el-col :span="8"><el-form-item label="编辑"><el-input v-model="form.editorLine" placeholder="责任编辑/文字编辑" /></el-form-item></el-col><el-col :span="8"><el-form-item label="来源链接"><el-input v-model="form.primarySourceUrl" placeholder="https://..." /></el-form-item></el-col></el-row>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="对象性质"><el-select v-model="form.recordClass" style="width: 100%"><el-option v-for="item in recordClasses" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="稿件类型"><el-select v-model="form.sourceArticleType" style="width: 100%"><el-option v-for="item in articleTypes" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="申论关联"><el-select v-model="form.examRelevance" style="width: 100%"><el-option v-for="item in relevanceLevels" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="保存等级"><el-select v-model="form.retentionTier" style="width: 100%"><el-option v-for="item in retentionTiers" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col><el-col :span="12"><el-form-item label="主题标签"><el-input v-model="topicsText" placeholder="逗号分隔，如基层治理、公共服务" /></el-form-item></el-col></el-row>
        <el-form-item label="关联理由"><el-input v-model="reasonsText" type="textarea" :rows="2" placeholder="说明适用主题、申论能力或事实价值" /></el-form-item>
        <el-form-item label="文章正文"><el-input v-model="form.bodyText" type="textarea" :rows="12" placeholder="仅在保存等级为‘完整正文’时填写；支持 Markdown" /></el-form-item>
        <el-alert v-if="!editingId" type="info" :closable="false" title="未选择全文保存时，只保存元数据和来源链接；新增档案不会自动抓取或分析文章内容。" />
      </el-form>
      <template #footer><el-button @click="formVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存档案</el-button></template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="文章档案详情" size="58%">
      <template v-if="detail">
        <h2>{{ detail.displayTitle }}</h2>
        <p class="detail-meta">{{ detail.issueDate }} · {{ detail.pageRefs?.length ? detail.pageRefs.map((item) => `${item.pageNo}版 ${item.pageName}`).join('、') : '版面未标注' }} · {{ detail.authorLine || '作者未标注' }}<span v-if="detail.editorLine"> · 编辑：{{ detail.editorLine }}</span></p>
        <div class="detail-tags"><el-tag>{{ labelOf(articleTypes, detail.sourceArticleType) }}</el-tag><el-tag :type="relevanceTag(detail.examRelevance)">{{ labelOf(relevanceLevels, detail.examRelevance) }}</el-tag><el-tag>{{ labelOf(retentionTiers, detail.retentionTier) }}</el-tag><el-tag>{{ reviewLabel(detail.reviewStatus) }}</el-tag></div>
        <p v-if="detail.primarySourceUrl"><el-link :href="detail.primarySourceUrl" target="_blank" rel="noopener" type="primary">打开原文</el-link></p>
        <h3>文章正文</h3><pre class="body-preview">{{ detail.bodyText || '当前档案未保存全文。' }}</pre>
        <h3>来源记录</h3><ul><li v-for="source in detail.sources" :key="source.id"><el-link :href="source.sourceUrl" target="_blank" rel="noopener">{{ source.sourceDisplayTitle || source.sourceUrl }}</el-link> · {{ source.sourceRelation }}</li></ul>
        <h3>人工分类复核历史</h3>
        <el-empty v-if="!detail.classificationHistory.length" description="暂无人工确认记录" :image-size="56" />
        <ul v-else><li v-for="(entry, index) in detail.classificationHistory" :key="index">{{ historySummary(entry) }}</li></ul>
        <h3>正文版本</h3><el-table :data="detail.revisions" size="small"><el-table-column prop="revisionNo" label="版本" width="70" /><el-table-column prop="bodySizeBytes" label="字节数" width="100" /><el-table-column prop="changeNote" label="说明" /><el-table-column prop="createdAt" label="保存时间" min-width="170" /></el-table>
      </template>
    </el-drawer>

    <el-dialog v-model="evaluationVisible" :title="evaluationArticle?.displayTitle ? `AI评估｜${evaluationArticle.displayTitle}` : 'AI文章评估'" width="min(1000px, 94vw)" top="4vh" destroy-on-close>
      <template v-if="evaluation">
        <el-alert v-if="evaluation.status === 'failed'" type="error" :closable="false" :title="evaluation.errorMessage || '评估失败'" />
        <el-alert v-else-if="evaluation.status !== 'completed'" type="info" :closable="false" :title="`评估状态：${evaluationLabel(evaluation.status)}；可稍后刷新报告`" />
        <template v-if="evaluation.status === 'completed'">
          <div class="eval-summary"><el-tag :type="relevanceTag(evalDraft.examRelevance)">{{ labelOf(relevanceLevels, evalDraft.examRelevance) }}关联</el-tag><el-tag>{{ labelOf(articleTypes, evalDraft.articleType) }}</el-tag><el-tag :type="evalDraft.isOpinion ? 'warning' : 'info'">{{ evalDraft.isOpinion ? '观点/分析型素材' : '非观点/分析型素材' }}</el-tag><el-tag type="warning">综合 {{ evaluation.result.overallScore }} 分</el-tag><span>正文 {{ evaluation.bodyCharCount }} 字 · 模型 {{ evaluation.modelName }}</span></div>
          <el-form label-width="110px" class="eval-form">
            <el-form-item label="文章类型"><el-select v-model="evalDraft.articleType"><el-option v-for="item in articleTypes" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item label="申论关联"><el-select v-model="evalDraft.examRelevance"><el-option v-for="item in relevanceLevels" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item label="观点/分析属性"><el-switch v-model="evalDraft.isOpinion" active-text="是" inactive-text="否" /><span class="muted">{{ evaluation.result.opinionNature?.reason }}</span></el-form-item>
            <el-form-item label="主题标签"><el-input v-model="evalDraft.topicsText" placeholder="用顿号分隔主题" /></el-form-item>
            <el-form-item label="摘要"><div>{{ evaluation.result.abstract || '—' }}</div></el-form-item>
            <el-form-item label="关联理由"><ul><li v-for="(item, index) in evaluation.result.examRelevance?.reasons || []" :key="index">{{ item }}</li></ul></el-form-item>
            <el-form-item label="核心观点"><ul><li v-for="(item, index) in evaluation.result.coreViews || []" :key="index">{{ typeof item === 'string' ? item : item.view || JSON.stringify(item) }}</li></ul></el-form-item>
            <el-form-item label="适用场景"><el-tag v-for="item in evaluation.result.useCases || []" :key="item" class="topic-tag" effect="plain">{{ item }}</el-tag></el-form-item>
            <el-form-item label="结构分析"><ul><li v-for="(item, index) in evaluation.result.structure || []" :key="index">{{ item.part }}：{{ item.role }}<span v-if="item.evidence">（{{ item.evidence }}）</span></li></ul></el-form-item>
            <el-form-item label="分项评分"><div class="score-list"><el-tag v-for="(score, key) in evaluation.result.scores || {}" :key="key" effect="plain">{{ scoreLabel(String(key)) }} {{ score }}/5</el-tag></div></el-form-item>
            <el-form-item label="原文证据"><ul class="evidence-list"><li v-for="(item, index) in evaluation.result.evidence || []" :key="index"><strong>“{{ item.quote }}”</strong><span>{{ item.why }} · {{ item.paragraph || '段落未标' }}</span></li></ul></el-form-item>
            <el-form-item label="可用物料"><div class="material-block"><strong>可引用表达</strong><ul><li v-for="(item, index) in evaluation.result.materials?.quotableSentences || []" :key="`q${index}`">{{ typeof item === 'string' ? item : item.text || JSON.stringify(item) }}</li></ul><strong>案例素材</strong><ul><li v-for="(item, index) in evaluation.result.materials?.caseMaterials || []" :key="`c${index}`">{{ typeof item === 'string' ? item : item.summary || item.text || JSON.stringify(item) }}</li></ul><strong>可复用表达 / 重点词</strong><ul><li v-for="(item, index) in [...(evaluation.result.materials?.reusableExpressions || []), ...(evaluation.result.materials?.keyTerms || [])]" :key="`m${index}`">{{ typeof item === 'string' ? item : item.text || item.term || JSON.stringify(item) }}</li></ul></div></el-form-item>
            <el-form-item label="需核查项"><div>{{ (evaluation.result.riskFlags || []).join('；') || '无' }}<span v-if="evaluation.result.humanReviewReason">；{{ evaluation.result.humanReviewReason }}</span></div></el-form-item>
            <el-form-item label="审核备注"><el-input v-model="evalDraft.note" type="textarea" :rows="2" placeholder="记录人工核对结论或修改意见" /></el-form-item>
          </el-form>
        </template>
      </template>
      <template #footer><el-button @click="evaluationVisible = false">关闭</el-button><el-button v-if="evaluation?.status !== 'completed'" @click="refreshEvaluation">刷新报告</el-button><el-button v-if="evaluation?.status === 'completed'" @click="submitEvaluationReview('changes_requested')">退回修改</el-button><el-button v-if="evaluation?.status === 'completed'" type="success" :loading="reviewingEvaluation" @click="submitEvaluationReview('approved')">人工确认并应用</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  archiveRmrbArchiveArticle,
  createRmrbArchiveArticle,
  getRmrbArchiveArticle,
  listRmrbArchiveArticles,
  updateRmrbArchiveArticle,
  getRmrbEvaluation,
  reviewRmrbEvaluation,
  runRmrbEvaluations,
  type RmrbArchiveArticle,
  type RmrbArticleEvaluation,
  type RmrbArchiveFilters,
} from '@/api/rmrbArchive'

const articleTypes = [
  { value: 'news_brief', label: '消息/简讯' }, { value: 'news_report', label: '通讯/报道' },
  { value: 'feature_investigation', label: '深度/调研报道' }, { value: 'profile', label: '人物报道' },
  { value: 'interview', label: '专访/访谈' }, { value: 'commentary', label: '评论/时评' },
  { value: 'editorial', label: '社论/评论员文章' }, { value: 'theory', label: '理论文章' },
  { value: 'policy_document', label: '政策文件/意见方案' }, { value: 'policy_qa', label: '政策解读/问答' }, { value: 'data_report', label: '数据/统计报道' },
  { value: 'picture_report', label: '图片/图表报道' }, { value: 'cultural_work', label: '副刊/文艺作品' },
  { value: 'notice', label: '公告/公示' }, { value: 'other', label: '其他' }, { value: 'undetermined', label: '待判定' },
]
const recordClasses = [
  { value: 'article', label: '正式文章' }, { value: 'notice', label: '公告/公示' },
  { value: 'advertisement', label: '广告' }, { value: 'non_article', label: '非文章' }, { value: 'undetermined', label: '待判定' },
]
const relevanceLevels = [
  { value: 'high', label: '高' }, { value: 'medium', label: '中' }, { value: 'low', label: '低' },
  { value: 'not_applicable', label: '不适用' }, { value: 'pending', label: '待评估' },
]
const retentionTiers = [
  { value: 'full_text', label: '完整正文' }, { value: 'metadata_only', label: '仅元数据' },
  { value: 'temporary', label: '短期暂存' }, { value: 'excluded', label: '排除' },
]
const loading = ref(false)
const saving = ref(false)
const batchEvaluating = ref(false)
const evaluatingId = ref('')
const reviewingEvaluation = ref(false)
const selectedIds = ref<string[]>([])
const evaluationVisible = ref(false)
const evaluationArticle = ref<RmrbArchiveArticle | null>(null)
const evaluation = ref<RmrbArticleEvaluation | null>(null)
const evalDraft = reactive({ articleType: 'undetermined', examRelevance: 'pending', isOpinion: false, topicsText: '', note: '' })
const items = ref<RmrbArchiveArticle[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dateRange = ref<string[] | null>([])
const filters = reactive<RmrbArchiveFilters>({ page_no: '', page_name: '', title: '', article_type: '', record_class: '', exam_relevance: '', retention_tier: '', author: '', editor: '', source_channel: '', body_status: '', review_status: '', evaluation_status: '' })
const formVisible = ref(false)
const editingId = ref('')
const activeSuggestion = ref<RmrbArchiveArticle['classificationSuggestion'] | null>(null)
const activeArticle = ref<RmrbArchiveArticle | null>(null)
const detailVisible = ref(false)
const detail = ref<RmrbArchiveArticle | null>(null)
const topicsText = ref('')
const reasonsText = ref('')
const form = reactive({
  issueDate: '', pageNo: '', pageName: '', displayTitle: '', headline: '', subtitle: '', columnLabel: '', seriesLabel: '',
  authorLine: '', editorLine: '', primarySourceUrl: '', recordClass: 'article', sourceArticleType: 'undetermined', examRelevance: 'pending',
  retentionTier: 'metadata_only', bodyText: '', reviewStatus: 'pending',
})

function labelOf(options: Array<{ value: string; label: string }>, value: string) {
  return options.find((item) => item.value === value)?.label || value || '—'
}
function pageNumbers(row: RmrbArchiveArticle) {
  return [...new Set(row.pageRefs.map((ref) => ref.pageNo))].join('、')
}
function pageNames(row: RmrbArchiveArticle) {
  return [...new Set(row.pageRefs.map((ref) => ref.pageName).filter(Boolean))].join(' / ')
}
function relevanceTag(level: string) {
  return level === 'high' ? 'danger' : level === 'medium' ? 'warning' : 'info'
}
function reviewLabel(status: string) {
  return status === 'approved' ? '人工已确认' : status === 'auto_approved' ? '规则自动确认' : status === 'revise' ? '需修订' : '待复核'
}
function suggestionMethodLabel(method: string) { return ({ llm_fulltext_v1: '全文 AI 评估', human_pattern_v1: '参考历史人工复核', metadata_rules_v1: '元数据规则初筛' } as Record<string, string>)[method] || method || '待评估' }
function evaluationLabel(status?: string) { return ({ pending: '待评估', queued: '待评估', processing: '评估中', completed: '已完成', failed: '失败' } as Record<string, string>)[status || ''] || '未评估' }
function evaluationReviewLabel(status: string) { return ({ approved: '人工已确认', changes_requested: '已退回修改' } as Record<string, string>)[status] || status }
function opinionLabel(value: { isOpinion?: boolean; confidence?: number } | undefined) { if (!value) return '未判断'; return value.isOpinion ? ((value.confidence || 0) >= 0.85 ? '观点/分析素材' : '观点候选') : ((value.confidence || 0) < 0.85 ? '待确认' : '未识别') }
function opinionTag(value: { isOpinion?: boolean; confidence?: number } | undefined) { return value?.isOpinion ? ((value.confidence || 0) >= 0.85 ? 'warning' : 'info') : 'info' }
function evaluationTag(status?: string) { return status === 'completed' ? 'success' : status === 'failed' ? 'danger' : status === 'processing' ? 'warning' : 'info' }
function bodyStatusLabel(status: string) { return ({ full: '全文已保存', evaluated_transient: '评估后未留存', failed: '获取失败', restricted: '来源受限' } as Record<string, string>)[status] || '尚未获取' }
function scoreLabel(key: string) { return ({ topicValue: '主题价值', transferability: '可迁移性', evidenceValue: '事实素材', expressionQuality: '表达质量', argumentStructure: '论证结构', timeliness: '时效性' } as Record<string, string>)[key] || key }
function historySummary(entry: Record<string, unknown>) {
  const reasons = Array.isArray(entry.reasons) ? entry.reasons.map(String).join('；') : ''
  return `${String(entry.reviewedAt || '')} · ${labelOf(articleTypes, String(entry.sourceArticleType || ''))} · ${labelOf(relevanceLevels, String(entry.examRelevance || ''))} · ${reasons}`
}
function queryParams(): RmrbArchiveFilters {
  return {
    ...filters,
    date_from: dateRange.value?.[0] || undefined,
    date_to: dateRange.value?.[1] || undefined,
    page: page.value,
    page_size: pageSize.value,
  }
}
async function load() {
  loading.value = true
  try {
    const result = await listRmrbArchiveArticles(queryParams())
    items.value = result.items
    total.value = result.total
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '文章列表加载失败')
  } finally {
    loading.value = false
  }
}
function onSelectionChange(rows: RmrbArchiveArticle[]) { selectedIds.value = rows.map((row) => row.id) }
async function evaluateSelected(force: boolean) {
  if (!selectedIds.value.length) return
  batchEvaluating.value = true
  try {
    const result = await runRmrbEvaluations({ articleIds: selectedIds.value, force })
    ElMessage.success(`已提交 ${result.queued} 篇文章评估`)
    await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '提交评估失败') }
  finally { batchEvaluating.value = false }
}
async function evaluateDateRange() {
  if (!dateRange.value?.[0] || !dateRange.value?.[1]) return
  batchEvaluating.value = true
  try {
    const result = await runRmrbEvaluations({ dateFrom: dateRange.value[0], dateTo: dateRange.value[1] })
    ElMessage.success(`已提交 ${result.queued} 篇文章评估`)
    await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '提交评估失败') }
  finally { batchEvaluating.value = false }
}
async function evaluateOne(row: RmrbArchiveArticle) {
  evaluatingId.value = row.id
  try {
    const result = await runRmrbEvaluations({ articleIds: [row.id], force: row.latestEvaluation?.status === 'completed' })
    ElMessage.success(result.queued ? '评估任务已提交' : '该文章已有进行中或已完成的评估')
    await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '提交评估失败') }
  finally { evaluatingId.value = '' }
}
async function openEvaluation(row: RmrbArchiveArticle) {
  evaluationArticle.value = row
  evaluationVisible.value = true
  try {
    evaluation.value = await getRmrbEvaluation(row.id)
    const classification = evaluation.value.result.classification || {}
    const relevance = evaluation.value.result.examRelevance || {}
    Object.assign(evalDraft, { articleType: classification.primaryType || 'undetermined', examRelevance: relevance.level || 'pending', isOpinion: Boolean(evaluation.value.result.opinionNature?.isOpinion), topicsText: (evaluation.value.result.topics || []).join('、'), note: evaluation.value.reviewNote || '' })
  } catch (error) { evaluation.value = null; ElMessage.error(error instanceof Error ? error.message : '评估报告加载失败') }
}
async function refreshEvaluation() {
  if (!evaluationArticle.value) return
  await openEvaluation(evaluationArticle.value)
  await load()
}
async function submitEvaluationReview(decision: string) {
  if (!evaluationArticle.value || !evaluation.value) return
  reviewingEvaluation.value = true
  try {
    const result = JSON.parse(JSON.stringify(evaluation.value.result)) as Record<string, any>
    result.classification.primaryType = evalDraft.articleType
    result.examRelevance.level = evalDraft.examRelevance
    result.opinionNature.isOpinion = evalDraft.isOpinion
    result.topics = evalDraft.topicsText.split(/[、，,]/).map((item) => item.trim()).filter(Boolean)
    evaluation.value = await reviewRmrbEvaluation(evaluationArticle.value.id, { decision, result, note: evalDraft.note })
    ElMessage.success(decision === 'approved' ? '人工确认已应用到文章档案' : '已退回修改')
    evaluationVisible.value = false
    await load()
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存审核结果失败') }
  finally { reviewingEvaluation.value = false }
}
function search() { page.value = 1; void load() }
function reset() {
  dateRange.value = []
  Object.assign(filters, { page_no: '', page_name: '', title: '', article_type: '', record_class: '', exam_relevance: '', retention_tier: '', author: '', editor: '', source_channel: '', body_status: '', review_status: '', evaluation_status: '' })
  search()
}
function clearForm() {
  activeSuggestion.value = null
  activeArticle.value = null
  Object.assign(form, { issueDate: new Date().toLocaleDateString('sv-SE'), pageNo: '', pageName: '', displayTitle: '', headline: '', subtitle: '', columnLabel: '', seriesLabel: '', authorLine: '', editorLine: '', primarySourceUrl: '', recordClass: 'article', sourceArticleType: 'undetermined', examRelevance: 'pending', retentionTier: 'metadata_only', bodyText: '' })
  form.reviewStatus = 'pending'
  topicsText.value = ''
  reasonsText.value = ''
}
function openCreate() { editingId.value = ''; clearForm(); formVisible.value = true }
function openEdit(row: RmrbArchiveArticle) {
  editingId.value = row.id
  activeArticle.value = row
  activeSuggestion.value = row.classificationSuggestion
  Object.assign(form, {
    issueDate: row.issueDate, pageNo: row.pageNo, pageName: row.pageName, displayTitle: row.displayTitle, headline: row.headline,
    subtitle: row.subtitle, columnLabel: row.columnLabel, seriesLabel: row.seriesLabel, authorLine: row.authorLine, editorLine: row.editorLine,
    primarySourceUrl: row.primarySourceUrl, recordClass: row.recordClass, sourceArticleType: row.sourceArticleType,
    examRelevance: row.examRelevance, retentionTier: row.retentionTier, bodyText: '', reviewStatus: row.reviewStatus,
  })
  topicsText.value = row.topics.join('，')
  reasonsText.value = row.examRelevanceReasons.join('，')
  formVisible.value = true
}
function applyClassificationSuggestion() {
  if (!activeSuggestion.value) return
  if (activeSuggestion.value.sourceArticleType !== 'undetermined') form.sourceArticleType = activeSuggestion.value.sourceArticleType
  if (activeSuggestion.value.examRelevance !== 'pending') form.examRelevance = activeSuggestion.value.examRelevance
  ElMessage.info('已填入建议值；请核对原文后再提交人工确认')
}
async function save() {
  if (!form.issueDate || !form.displayTitle.trim()) return ElMessage.warning('出版日期和显示标题必填')
  if (form.retentionTier === 'full_text' && !form.bodyText.trim() && !editingId.value) return ElMessage.warning('完整正文保存等级需要填写正文')
  if (editingId.value && form.reviewStatus === 'approved' && (form.sourceArticleType === 'undetermined' || form.examRelevance === 'pending')) return ElMessage.warning('人工确认前，请先确认稿件体裁和申论关联；不能判断时请保持待复核')
  const data: Record<string, unknown> = {
    ...form,
    topics: topicsText.value.split(/[，,]/).map((s) => s.trim()).filter(Boolean),
    examRelevanceReasons: reasonsText.value.split(/[，,]/).map((s) => s.trim()).filter(Boolean),
    bodyText: form.bodyText || undefined,
  }
  saving.value = true
  try {
    if (editingId.value) await updateRmrbArchiveArticle(editingId.value, data)
    else await createRmrbArchiveArticle(data)
    ElMessage.success('文章档案已保存')
    formVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}
async function openDetail(row: RmrbArchiveArticle) {
  try {
    detail.value = await getRmrbArchiveArticle(row.id)
    detailVisible.value = true
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '文章详情加载失败')
  }
}
async function archive(row: RmrbArchiveArticle) {
  try {
    await archiveRmrbArchiveArticle(row.id)
    ElMessage.success('文章已归档')
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '归档失败')
  }
}
onMounted(load)
</script>

<style scoped>
.page-heading { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; }
.heading-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.page-heading h2 { margin: 0 0 6px; font-size: 20px; }
.page-heading p, .muted, .sub-title { color: var(--el-text-color-secondary); }
.page-heading p { margin: 0; font-size: 13px; }
.filters-card { margin-bottom: 16px; }
.filters-card :deep(.el-card__body) { padding-bottom: 8px; }
.suggestion-alert { margin-bottom: 16px; }
.suggestion-actions { display: flex; align-items: center; gap: 12px; margin-top: 8px; }
.result-count { color: var(--el-text-color-secondary); font-size: 13px; margin: -4px 0 8px; }
.sub-title { font-size: 12px; margin-top: 3px; }
.pager { justify-content: flex-end; margin-top: 16px; }
.article-form { max-height: 70vh; overflow-y: auto; padding-right: 12px; }
.detail-meta { color: var(--el-text-color-secondary); }
.detail-tags { display: flex; gap: 8px; }
.body-preview { white-space: pre-wrap; overflow-wrap: anywhere; background: var(--el-fill-color-light); padding: 16px; border-radius: 6px; max-height: 55vh; overflow: auto; }
.eval-summary, .score-list { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.eval-summary span { color: var(--el-text-color-secondary); font-size: 13px; }
.eval-form { max-height: 68vh; overflow: auto; padding-right: 10px; }
.eval-form :deep(.el-form-item__content) { align-items: flex-start; }
.eval-form ul { margin: 0; padding-left: 20px; }
.topic-tag { margin: 0 6px 6px 0; }
.evidence-list li { margin: 0 0 10px; }
.evidence-list span { display: block; color: var(--el-text-color-secondary); font-size: 12px; }
.material-block { max-height: 260px; overflow: auto; }
</style>
