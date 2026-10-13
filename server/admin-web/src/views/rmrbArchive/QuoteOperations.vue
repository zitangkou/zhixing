<template>
  <div class="page">
    <header class="topbar">
      <div><div class="eyebrow">PEOPLE'S DAILY · CONTENT STUDIO</div><h2>金句运营库</h2><p>审核通过的评论金句统一入库；按日选句，整理小红书与公众号发布物料。</p></div>
      <el-button @click="reload">刷新数据</el-button>
    </header>

    <el-tabs v-model="activeTab" class="tabs">
      <el-tab-pane label="金句库与当日组稿" name="pool">
        <section class="filters">
          <el-input v-model="search" clearable placeholder="搜索金句或仿写" @keyup.enter="loadPool" @clear="loadPool" />
          <el-input v-model="topicFilter" clearable placeholder="主题标签，如基层治理" @keyup.enter="loadPool" @clear="loadPool" />
          <el-select v-model="usageFilter" @change="loadPool"><el-option label="未使用" value="unused" /><el-option label="已使用" value="used" /><el-option label="全部" value="all" /></el-select>
          <el-button type="primary" plain @click="loadPool">查询</el-button>
        </section>
        <el-alert class="rule" type="info" :closable="false" show-icon title="运营池仅展示审核通过的金句。草稿选择不占用金句；在运营内容包中标记对应平台‘已发布’后，金句才计为已使用并从未使用池移出。" />
        <el-table v-loading="poolLoading" :data="pool" row-key="id" @selection-change="selection = $event">
          <el-table-column type="selection" width="48" :selectable="isSelectable" />
          <el-table-column label="金句 / 适用方向" min-width="470"><template #default="{ row }">
            <blockquote>{{ row.text }}</blockquote>
            <div class="meta-row"><el-tag v-for="topic in row.topics" :key="topic" size="small" effect="plain">{{ topic }}</el-tag><span class="muted">适用：{{ row.useCases.join('、') || '待补充' }}</span></div>
            <p v-if="row.applicationExample" class="example">仿写参考：{{ row.applicationExample }}</p>
          </template></el-table-column>
          <el-table-column label="来源文章" min-width="230"><template #default="{ row }"><a v-if="row.sourceUrl" :href="row.sourceUrl" target="_blank" rel="noopener">{{ row.articleTitle }}</a><span v-else>{{ row.articleTitle }}</span><div class="muted">{{ row.articleDate }} · {{ row.author || '未署名' }}</div></template></el-table-column>
          <el-table-column label="使用状态" width="105"><template #default="{ row }"><el-tag :type="row.used ? 'info' : 'success'">{{ row.used ? '已用' : '未使用' }}</el-tag></template></el-table-column>
        </el-table>
        <div class="selection-bar"><span>已选择 <b>{{ selection.length }}</b> 条 <span class="muted">（建议每条内容选 3–5 条，主题尽量集中）</span></span><el-button type="primary" :disabled="!selection.length" @click="openCreate">整理当日运营内容</el-button></div>
      </el-tab-pane>

      <el-tab-pane label="运营内容包" name="packages">
        <el-empty v-if="!packagesLoading && packages.length === 0" description="暂无运营内容包。可从金句库选择金句开始组稿。" />
        <el-table v-else v-loading="packagesLoading" :data="packages" stripe>
          <el-table-column prop="issueDate" label="运营日期" width="120" />
          <el-table-column label="主题 / 标题" min-width="260"><template #default="{ row }"><b>{{ row.topic || '未设主题' }}</b><div class="muted">{{ row.title || '未生成标题' }}</div></template></el-table-column>
          <el-table-column label="平台" width="190"><template #default="{ row }"><el-tag v-for="channel in row.channels" :key="channel" size="small" :type="channel === 'wechat' ? 'success' : 'warning'">{{ channelLabel(channel) }}</el-tag></template></el-table-column>
          <el-table-column label="金句" width="90"><template #default="{ row }">{{ row.quotes.length }} 条</template></el-table-column>
          <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="row.status === 'published' ? 'success' : 'info'">{{ row.status === 'published' ? '已发布' : '草稿/待审核' }}</el-tag></template></el-table-column>
          <el-table-column label="操作" width="240" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openPackage(row)">编辑 / 预览</el-button><el-button link type="success" @click="downloadPackage(row)">导出物料</el-button></template></el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="createVisible" title="建立当日运营内容包" width="540px">
      <el-form label-width="100px"><el-form-item label="运营日期"><el-date-picker v-model="createForm.issueDate" type="date" value-format="YYYY-MM-DD" /></el-form-item><el-form-item label="主题"><el-input v-model="createForm.topic" placeholder="如基层治理、科技创新、民生服务" /></el-form-item><el-form-item label="发布平台"><el-checkbox-group v-model="createForm.channels"><el-checkbox value="xiaohongshu">小红书</el-checkbox><el-checkbox value="wechat">微信公众号</el-checkbox></el-checkbox-group></el-form-item></el-form>
      <template #footer><el-button @click="createVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="createPackage">创建并整理</el-button></template>
    </el-dialog>

    <el-dialog v-model="editorVisible" :title="`${editor?.issueDate || ''} 运营内容包`" width="min(1180px, 96vw)" top="3vh" destroy-on-close>
      <div v-if="editor" class="editor">
        <div class="editor-toolbar"><div><el-tag :type="editor.status === 'published' ? 'success' : 'warning'">{{ editor.status === 'published' ? '已发布：金句已计入使用' : '草稿 / 待审核' }}</el-tag><span class="muted">共 {{ editor.quotes.length }} 条金句 · {{ editor.topic || '未设主题' }}</span></div><div class="toolbar-actions"><el-button :disabled="editor.status === 'published'" :loading="generating" @click="generate">按模板生成初稿</el-button><el-button :disabled="editor.status === 'published'" type="primary" :loading="saving" @click="savePackage">保存修改</el-button></div></div>
        <el-alert class="editor-note" type="warning" :closable="false" title="自动生成的文案是可编辑初稿。发布前请核对引文、来源、仿写标识、标题和平台合规；系统不会自动发布到平台。" />
        <el-tabs v-model="editorChannel">
          <el-tab-pane v-if="editor.channels.includes('xiaohongshu')" label="小红书图文" name="xiaohongshu">
            <el-form label-position="top"><el-form-item label="笔记标题"><el-input v-model="editor.xhsTitle" maxlength="20" show-word-limit /></el-form-item><el-form-item label="发布正文"><el-input v-model="editor.xhsContent" type="textarea" :rows="16" /></el-form-item></el-form>
            <div class="platform-actions"><el-button @click="showPreview('xiaohongshu')">品牌版式预览</el-button><el-button @click="downloadChannel('xiaohongshu')">导出 HTML / 文案</el-button><el-button v-if="!editor.xhsPublishedAt" type="success" @click="confirmPublish('xiaohongshu')">标记小红书已发布</el-button><el-tag v-else type="success">已发布 {{ formatTime(editor.xhsPublishedAt) }}</el-tag></div>
          </el-tab-pane>
          <el-tab-pane v-if="editor.channels.includes('wechat')" label="微信公众号" name="wechat">
            <el-form label-position="top"><el-form-item label="公众号标题"><el-input v-model="editor.wechatTitle" maxlength="64" show-word-limit /></el-form-item><el-form-item label="摘要"><el-input v-model="editor.wechatSummary" type="textarea" :rows="2" maxlength="120" show-word-limit /></el-form-item><el-form-item label="正文"><el-input v-model="editor.wechatContent" type="textarea" :rows="16" /></el-form-item></el-form>
            <div class="platform-actions"><el-button @click="showPreview('wechat')">品牌版式预览</el-button><el-button @click="downloadChannel('wechat')">导出 HTML / 文案</el-button><el-button v-if="!editor.wechatPublishedAt" type="success" @click="confirmPublish('wechat')">标记公众号已发布</el-button><el-tag v-else type="success">已发布 {{ formatTime(editor.wechatPublishedAt) }}</el-tag></div>
          </el-tab-pane>
          <el-tab-pane label="选用金句 / 来源" name="sources"><div v-for="(quote, index) in editor.quotes" :key="quote.id" class="source-quote"><b>{{ String(index + 1).padStart(2, '0') }}</b><div><blockquote>{{ quote.text }}</blockquote><div class="muted">{{ quote.topics.join('、') }} · {{ quote.articleTitle }} · {{ quote.articleDate }} <a v-if="quote.sourceUrl" :href="quote.sourceUrl" target="_blank" rel="noopener">查看原文</a></div></div></div></el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
    <el-dialog v-model="previewVisible" :title="previewTitle" width="min(760px, 94vw)" top="3vh"><iframe class="preview" :srcdoc="previewHtml" sandbox="" /></el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createRmrbOpsPackage, generateRmrbOpsCopy, listRmrbOpsPackages, listRmrbOpsQuotes, markRmrbOpsPublished, updateRmrbOpsPackage, type RmrbOpsPackage, type RmrbOpsQuote } from '@/api/rmrbComments'

const activeTab = ref('pool'), editorChannel = ref('xiaohongshu')
const pool = ref<RmrbOpsQuote[]>([]), packages = ref<RmrbOpsPackage[]>([]), selection = ref<RmrbOpsQuote[]>([])
const poolLoading = ref(false), packagesLoading = ref(false), saving = ref(false), generating = ref(false)
const search = ref(''), topicFilter = ref(''), usageFilter = ref('unused')
const createVisible = ref(false), editorVisible = ref(false), previewVisible = ref(false)
const editor = ref<RmrbOpsPackage | null>(null), previewHtml = ref(''), previewTitle = ref('')
const createForm = ref({ issueDate: new Date().toLocaleDateString('en-CA'), topic: '', channels: ['xiaohongshu', 'wechat'] })
function isSelectable(row: RmrbOpsQuote) { return !row.used }
async function loadPool() { poolLoading.value = true; try { pool.value = await listRmrbOpsQuotes({ q: search.value, topic: topicFilter.value, used: usageFilter.value }) } catch (e) { ElMessage.error(String(e)) } finally { poolLoading.value = false } }
async function loadPackages() { packagesLoading.value = true; try { packages.value = await listRmrbOpsPackages() } catch (e) { ElMessage.error(String(e)) } finally { packagesLoading.value = false } }
async function reload() { await Promise.all([loadPool(), loadPackages()]) }
function openCreate() { createForm.value = { issueDate: new Date().toLocaleDateString('en-CA'), topic: selection.value[0]?.topics[0] || '', channels: ['xiaohongshu', 'wechat'] }; createVisible.value = true }
async function createPackage() { saving.value = true; try { const result = await createRmrbOpsPackage({ ...createForm.value, quoteIds: selection.value.map(q => q.id) }); createVisible.value = false; await openPackage(result); activeTab.value = 'packages'; await reload() } catch (e) { ElMessage.error(String(e)) } finally { saving.value = false } }
async function openPackage(row: RmrbOpsPackage) { editor.value = { ...row, channels: [...row.channels], quotes: [...row.quotes] }; editorChannel.value = row.channels.includes('xiaohongshu') ? 'xiaohongshu' : 'wechat'; editorVisible.value = true }
async function savePackage() { if (!editor.value) return; saving.value = true; try { editor.value = await updateRmrbOpsPackage(editor.value.id, { topic: editor.value.topic, title: editor.value.title, channels: editor.value.channels, xhsTitle: editor.value.xhsTitle, xhsContent: editor.value.xhsContent, wechatTitle: editor.value.wechatTitle, wechatSummary: editor.value.wechatSummary, wechatContent: editor.value.wechatContent }); ElMessage.success('运营文案已保存'); await loadPackages() } catch (e) { ElMessage.error(String(e)) } finally { saving.value = false } }
async function generate() { if (!editor.value) return; generating.value = true; try { editor.value = await generateRmrbOpsCopy(editor.value.id); ElMessage.success('已按统一内容结构生成初稿，请编辑并审核'); await loadPackages() } catch (e) { ElMessage.error(String(e)) } finally { generating.value = false } }
function esc(value: string) { return value.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c)) }
function makeHtml(channel: string) {
  if (!editor.value) return ''
  const xhs = channel === 'xiaohongshu'
  const title = xhs ? editor.value.xhsTitle : editor.value.wechatTitle
  const body = xhs ? editor.value.xhsContent : editor.value.wechatContent
  const summary = xhs ? '' : editor.value.wechatSummary
  const paragraphs = body.split(/\n+/).filter(Boolean).map(line => {
    const safe = esc(line)
    if (line.startsWith('> ')) return `<blockquote>${esc(line.slice(2))}</blockquote>`
    if (line.startsWith('## ')) return `<h2>${esc(line.slice(3))}</h2>`
    if (line.startsWith('【') || line.startsWith('#申论')) return `<p class="accent">${safe}</p>`
    return `<p>${safe}</p>`
  }).join('\n')
  const cards = editor.value.quotes.map((quote, index) => `<section class="card"><div class="card-top"><span>申论表达 · ${esc(editor.value!.issueDate)}</span><b>${String(index + 1).padStart(2, '0')} / ${String(editor.value!.quotes.length).padStart(2, '0')}</b></div><div class="topic">${esc(quote.topics.join(' · ') || editor.value!.topic || '申论素材')}</div><blockquote>${esc(quote.text)}</blockquote><div class="usage"><b>考场怎么用</b><p>${esc(quote.useCases.join('、') || '分论点论证、结尾升华')}</p></div>${quote.applicationExample ? `<div class="rewrite"><b>迁移仿写 · 非原文</b><p>${esc(quote.applicationExample)}</p></div>` : ''}<div class="card-source">来源：${esc(quote.articleTitle)} · 人民日报 ${esc(quote.articleDate)}${quote.sourceUrl ? ` · <a href="${esc(quote.sourceUrl)}">原文</a>` : ''}</div><div class="card-brand">杜衡阁　｜　申论素材精读</div></section>`).join('\n')
  const main = xhs ? `<section class="cover"><div class="brand">杜 衡 阁　·　申 论 素 材</div><div class="kicker">人民日报评论 · ${esc(editor.value.issueDate)}</div><h1>${esc(title)}</h1><p>${esc(editor.value.topic || '主题素材积累')} · 原文金句与考场用法</p><div class="cover-mark">今日<br>精选</div></section><div class="card-list">${cards}</div>` : `<article class="paper"><div class="brand">杜 衡 阁　·　申 论 素 材</div><div class="kicker">人民日报评论 · ${esc(editor.value.issueDate)} · 公众号学习素材</div><h1 class="title">${esc(title)}</h1>${summary ? `<div class="summary">${esc(summary)}</div>` : ''}<main>${paragraphs}</main><div class="footer">学习参考｜原文引句均标注来源，仿写内容不代表原文观点。发布前请完成内容与版权合规审核。</div></article>`
  return `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title><style>*{box-sizing:border-box}body{margin:0;background:#f1eee8;color:#292622;font:16px/1.9 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}.paper{max-width:720px;margin:28px auto;padding:44px 48px;background:#fff;box-shadow:0 12px 42px #342b2012}.brand{color:#a21d25;font-size:12px;letter-spacing:.18em;border-bottom:1px solid #e7d8d2;padding-bottom:14px}.kicker{margin-top:34px;color:#ad2830;font-size:13px}.title{font-size:30px;line-height:1.45;margin:10px 0 12px}.summary{color:#776f69;font-size:14px;padding:12px 16px;background:#faf6f2;border-left:3px solid #aa222b}p{margin:16px 0}h2{font-size:19px;color:#9f1f27;margin:28px 0 8px}blockquote{margin:18px 0;padding:18px 22px;background:#faf6f2;border-left:4px solid #aa222b;font-size:18px;color:#352e2a}.accent{color:#9f1f27;font-weight:600}.footer{border-top:1px solid #eee;margin-top:38px;padding-top:16px;color:#8a817a;font-size:12px}.cover,.card{width:min(440px,94vw);aspect-ratio:3/4;margin:28px auto;padding:34px 32px;background:linear-gradient(155deg,#fff 0%,#fffdfa 70%,#f3e9df 100%);border:1px solid #e7d8d2;box-shadow:0 14px 34px #3b2b2015;position:relative;display:flex;flex-direction:column}.cover{justify-content:center;background:linear-gradient(145deg,#5b1219,#a5232b 60%,#d28d57);color:#fff;border:0}.cover .brand{color:#fff;border-color:#ffffff66}.cover h1{font-size:34px;line-height:1.4;margin:28px 0 8px;max-width:330px}.cover p{color:#f7e9dc}.cover-mark{position:absolute;right:30px;bottom:38px;border:1px solid #ffffff99;padding:8px 12px;line-height:1.2;font-size:13px}.card-top{display:flex;justify-content:space-between;color:#8d8177;font-size:11px;border-bottom:1px solid #eadfd7;padding-bottom:12px}.card-top b{color:#a3222c;letter-spacing:.08em}.topic{margin-top:32px;color:#a3222c;font-size:13px;letter-spacing:.08em}.card blockquote{background:transparent;border:0;padding:0;margin:18px 0 22px;font-size:23px;line-height:1.7;font-weight:600;color:#302723}.usage,.rewrite{padding:12px 14px;background:#f7f3ef;margin-top:10px}.usage b,.rewrite b{color:#a3222c;font-size:12px}.usage p,.rewrite p{margin:4px 0 0;font-size:13px;line-height:1.7}.rewrite{background:#f8f5e9}.card-source{margin-top:auto;padding-top:18px;color:#82786f;font-size:10px;line-height:1.6}.card-source a{color:#a3222c}.card-brand{margin-top:10px;padding-top:10px;border-top:1px solid #eadfd7;color:#9b8d81;font-size:10px;letter-spacing:.1em}.card-list{padding:1px 0}.cover,.card{page-break-after:always;break-after:page}@media(max-width:600px){.paper{margin:0;padding:28px 22px}.title{font-size:25px}}@media print{body{background:#fff}.cover,.card{margin:0 auto;box-shadow:none;width:100vw;height:133.333vw;aspect-ratio:3/4;page-break-after:always;break-after:page}.paper{box-shadow:none;margin:0 auto}}</style>${main}</html>`
}
function showPreview(channel: string) { if (!editor.value) return; previewTitle.value = channel === 'wechat' ? '公众号品牌排版预览' : '小红书品牌排版预览'; previewHtml.value = makeHtml(channel); previewVisible.value = true }
function saveBlob(name: string, content: string, type: string) { const url = URL.createObjectURL(new Blob([content], { type })); const link = document.createElement('a'); link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url) }
function downloadChannel(channel: string) { if (!editor.value) return; const xhs = channel === 'xiaohongshu'; const text = xhs ? `${editor.value.xhsTitle}\n\n${editor.value.xhsContent}` : `${editor.value.wechatTitle}\n\n摘要：${editor.value.wechatSummary}\n\n${editor.value.wechatContent}`; const prefix = `${editor.value.issueDate}_${xhs ? '小红书' : '公众号'}`; saveBlob(`${prefix}_发布文案.txt`, text, 'text/plain;charset=utf-8'); saveBlob(`${prefix}_品牌排版.html`, makeHtml(channel), 'text/html;charset=utf-8') }
function downloadPackage(row: RmrbOpsPackage) { editor.value = row; for (const channel of row.channels) downloadChannel(channel) }
async function confirmPublish(channel: string) { if (!editor.value) return; const label = channelLabel(channel); try { await ElMessageBox.confirm(`确认已在${label}完成发布？确认后，本运营包所选金句将标记为已使用，后续不再进入未使用金句池。`, '确认发布记录', { type: 'warning', confirmButtonText: '确认已发布', cancelButtonText: '返回检查' }) } catch { return }; try { if (editor.value.status !== 'published') editor.value = await updateRmrbOpsPackage(editor.value.id, { topic: editor.value.topic, title: editor.value.title, channels: editor.value.channels, xhsTitle: editor.value.xhsTitle, xhsContent: editor.value.xhsContent, wechatTitle: editor.value.wechatTitle, wechatSummary: editor.value.wechatSummary, wechatContent: editor.value.wechatContent }); editor.value = await markRmrbOpsPublished(editor.value.id, channel); ElMessage.success(`已记录${label}发布，所选金句已标记为已使用`); await reload() } catch (e) { ElMessage.error(String(e)) } }
function channelLabel(channel: string) { return channel === 'wechat' ? '微信公众号' : '小红书' }
function formatTime(value?: string | null) { return value ? new Date(value).toLocaleString() : '' }
onMounted(reload)
</script>

<style scoped>
.page{padding:22px;display:flex;flex-direction:column;gap:16px;background:#f7f8fa;min-height:calc(100vh - 60px)}.topbar{display:flex;justify-content:space-between;align-items:center;background:#fff;padding:20px 24px;border:1px solid #ebecef;border-radius:10px}.topbar h2{margin:5px 0;font-size:23px;color:#252a31}.topbar p{margin:0;color:#7a8089;font-size:13px}.eyebrow{color:#a3222c;font-size:10px;letter-spacing:.18em;font-weight:700}.tabs{background:#fff;padding:0 20px 20px;border:1px solid #ebecef;border-radius:10px}.filters{display:flex;gap:12px;margin:16px 0}.filters .el-input:first-child{max-width:300px}.filters .el-input:nth-child(2){max-width:230px}.filters .el-select{width:120px}.rule{margin-bottom:14px}.muted{font-size:12px;color:#858b94}.meta-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.example{padding:8px 10px;background:#f8f6f2;color:#756c62;font-size:12px;margin:9px 0 0}.el-table blockquote,.source-quote blockquote{margin:8px 0;padding:10px 14px;border-left:3px solid #a9212b;background:#fbf9f7;line-height:1.8;color:#30343b}.selection-bar{display:flex;justify-content:space-between;align-items:center;padding:14px 4px}.editor{min-height:55vh}.editor-toolbar,.toolbar-actions,.platform-actions{display:flex;align-items:center;gap:12px}.editor-toolbar{justify-content:space-between;margin-bottom:12px}.editor-toolbar>div:first-child{display:flex;align-items:center;gap:10px}.editor-note{margin-bottom:14px}.platform-actions{justify-content:flex-end;padding:10px 0}.preview{width:100%;height:78vh;border:0;background:#f4f1ec}.source-quote{display:grid;grid-template-columns:36px 1fr;gap:8px;padding:12px 4px;border-bottom:1px solid #eee}.source-quote>b{color:#a9212b;padding-top:12px}@media(max-width:760px){.page{padding:10px}.topbar,.editor-toolbar{align-items:flex-start;flex-direction:column;gap:12px}.filters{flex-wrap:wrap}.filters .el-input:first-child,.filters .el-input:nth-child(2){max-width:none;width:100%}.selection-bar{align-items:flex-start;flex-direction:column;gap:10px}.toolbar-actions{flex-wrap:wrap}}
</style>
