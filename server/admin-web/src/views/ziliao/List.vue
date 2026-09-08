<template>
  <div class="page">
    <div class="toolbar">
      <el-button type="primary" @click="onSeed(false)">同步种子</el-button>
      <el-button @click="onSeed(true)">强制覆盖种子</el-button>
      <el-button @click="showGuide = true">真题导入规范</el-button>
      <span class="tip">从 server/data/ziliao JSON 写入公式/题型/技巧；刷题难度靠真题导入，不靠样例卷</span>
    </div>
    <el-alert type="warning" :closable="false" style="margin-bottom: 12px">
      系统样例仅联调用。请到「试卷题库」导入
      <code>server/data/ziliao/examples/guokao-style-sample.md</code>
      或真实国考/省考资料分析；有真题后默认练习池会自动排除样例。
    </el-alert>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="公式库" name="formulas">
        <FormulasTab />
      </el-tab-pane>
      <el-tab-pane label="题型模型" name="types">
        <TypesTab />
      </el-tab-pane>
      <el-tab-pane label="速算技巧" name="tricks">
        <TricksTab />
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="showGuide" title="资料分析真题导入规范" size="50%">
      <pre class="guide-md">{{ guideMd }}</pre>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchImportGuide, seedZiliao } from '@/api/ziliao'
import FormulasTab from './FormulasTab.vue'
import TypesTab from './TypesTab.vue'
import TricksTab from './TricksTab.vue'

const activeTab = ref('formulas')
const showGuide = ref(false)
const guideMd = ref('加载中…')

async function onSeed(force: boolean) {
  if (force) {
    await ElMessageBox.confirm('将按 code 覆盖已有种子内容，是否继续？', '强制覆盖')
  }
  const res = await seedZiliao(force)
  ElMessage.success(
    `已同步：公式 ${res.formulas} · 题型 ${res.types} · 技巧 ${res.tricks}` +
      (res.samplePaper ? ' · 样例卷已写入' : ''),
  )
}

onMounted(async () => {
  try {
    const g = await fetchImportGuide()
    guideMd.value = g.markdown
  } catch {
    guideMd.value = '无法加载规范，请直接打开 server/data/ziliao/IMPORT.md'
  }
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.guide-md {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.55;
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
</style>
