<template>
  <div class="page">
    <div class="heading"><div><h2>言遇英语 · 学习概览</h2><p>查看课程供给和学员完成情况。</p></div><el-button :loading="loading" @click="load">刷新</el-button></div>
    <el-row :gutter="16">
      <el-col :span="6"><el-card shadow="never"><div class="metric"><span>场景数</span><strong>{{ summary.scenes }}</strong><small>后台维护的练习场景</small></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="metric"><span>课程单元</span><strong>{{ summary.units }}</strong><small>包含草稿与已发布内容</small></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="metric"><span>已发布单元</span><strong>{{ summary.publishedUnits }}</strong><small>学员端可见</small></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="metric"><span>累计完成</span><strong>{{ summary.completions }}</strong><small>包含重练记录</small></div></el-card></el-col>
    </el-row>
    <el-card shadow="never" class="guide">
      <template #header><strong>首期学习闭环</strong></template>
      <div class="steps"><div><b>01</b><span>听对话</span></div><i>→</i><div><b>02</b><span>学句块</span></div><i>→</i><div><b>03</b><span>录音模仿</span></div><i>→</i><div><b>04</b><span>情境表达</span></div><i>→</i><div><b>05</b><span>间隔复习</span></div></div>
      <p>录音当前只保存在学员设备。课程与学习进度由本管理后台维护，发布前请确认英文表达、中文释义和音频授权。</p>
    </el-card>
  </div>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchEnglishSummary } from '@/api/english'
const loading = ref(false)
const summary = reactive({ scenes: 0, units: 0, publishedUnits: 0, completions: 0 })
async function load() {
  loading.value = true
  try { Object.assign(summary, await fetchEnglishSummary()) }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '学习概览加载失败') }
  finally { loading.value = false }
}
onMounted(load)
</script>
<style scoped>
.heading { display:flex; justify-content:space-between; margin-bottom:18px; }
.heading h2 { margin:0 0 8px; font-size:20px; }
.heading p,.guide p { color:#77817d; margin:0; }
.metric { display:flex; flex-direction:column; gap:9px; color:#71807a; }
.metric strong { color:#256d73; font-size:27px; }
.metric small { color:#9aa39f; }
.guide { margin-top:18px; }
.steps { display:flex; align-items:center; justify-content:space-between; max-width:850px; margin:8px auto 20px; }
.steps div { display:flex; align-items:center; gap:8px; color:#334943; }
.steps b { display:inline-flex; align-items:center; justify-content:center; width:30px; height:30px; border-radius:50%; color:#256d73; background:#eaf2ee; }
.steps i { color:#a6b4ae; font-style:normal; }
</style>
