<template>
  <div class="qdp" v-loading="loading">
    <div v-if="detail" class="qdp-content">
      <!-- 题干 -->
      <div class="qdp-section">
        <div class="qdp-label">题干</div>
        <div class="qdp-stem">{{ detail.stem }}</div>
      </div>

      <!-- 材料（资料分析题） -->
      <div class="qdp-section" v-if="detail.material && (detail.material as any).content">
        <div class="qdp-label">材料</div>
        <div class="qdp-material">{{ (detail.material as any).content }}</div>
      </div>

      <!-- 选项 + 答案 -->
      <div class="qdp-section">
        <div class="qdp-label">选项与答案</div>
        <div class="qdp-options">
          <div v-for="(text, key) in detail.options" :key="key"
               class="qdp-option"
               :class="{ 'is-correct': key === detail.answer }">
            <span class="qdp-opt-key">{{ key }}.</span>
            <span class="qdp-opt-text">{{ text }}</span>
            <el-tag v-if="key === detail.answer" type="success" size="small">正确答案</el-tag>
          </div>
        </div>
      </div>

      <!-- 解析 -->
      <div class="qdp-section" v-if="detail.explanation">
        <div class="qdp-label">解析</div>
        <div class="qdp-explanation">{{ detail.explanation }}</div>
      </div>

      <!-- 计算树 -->
      <div class="qdp-section" v-if="detail.calc_tree && detail.calc_tree.length">
        <div class="qdp-label">计算树</div>
        <el-timeline>
          <el-timeline-item v-for="(step, i) in detail.calc_tree" :key="i"
                            :timestamp="`步骤 ${(step as any).step || i + 1}`" placement="top">
            <div class="calc-step">
              <div v-if="(step as any).operation" class="calc-op">操作：{{ (step as any).operation }}</div>
              <div v-if="(step as any).formula" class="calc-formula">公式：{{ (step as any).formula }}</div>
              <div v-if="(step as any).description" class="calc-desc">{{ (step as any).description }}</div>
              <div v-if="(step as any).inputs" class="calc-inputs">
                输入：<code>{{ JSON.stringify((step as any).inputs) }}</code>
              </div>
              <div class="calc-result">结果：{{ (step as any).result }}</div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>

      <!-- 干扰项错误路径 -->
      <div class="qdp-section" v-if="detail.distractors && Object.keys(detail.distractors).length">
        <div class="qdp-label">干扰项错误路径</div>
        <div class="qdp-distractors">
          <div v-for="(d, key) in detail.distractors" :key="key" class="qdp-distractor">
            <el-tag size="small" type="warning">{{ key }}</el-tag>
            <span class="d-type">{{ (d as any).type }}</span>
            <span class="d-formula">{{ (d as any).error_formula }}</span>
            <span class="d-value">计算值：{{ (d as any).computed_value }}</span>
          </div>
        </div>
      </div>

      <!-- 双求解结果 -->
      <div class="qdp-section" v-if="detail.dual_solve">
        <div class="qdp-label">双求解结果</div>
        <div class="qdp-dual">
          <div class="dual-row"><span>求解器 A：</span>{{ (detail.dual_solve as any).solver_a_result }}</div>
          <div class="dual-row"><span>求解器 B：</span>{{ (detail.dual_solve as any).solver_b_result }}</div>
          <div class="dual-row"><span>B 方法：</span>{{ (detail.dual_solve as any).solver_b_method }}</div>
          <div class="dual-row">
            <span>一致性：</span>
            <el-tag :type="(detail.dual_solve as any).match ? 'success' : 'danger'" size="small">
              {{ (detail.dual_solve as any).match ? '一致 ✅' : '不一致 ❌' }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 生成元信息 -->
      <div class="qdp-section" v-if="detail.generation_meta">
        <div class="qdp-label">生成元信息</div>
        <pre class="qdp-meta">{{ JSON.stringify(detail.generation_meta, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { fetchGenQuestionDetail, type GenQuestionDetail } from '@/api/generation'

const props = defineProps<{ questionId: string }>()

const loading = ref(false)
const detail = ref<GenQuestionDetail | null>(null)

async function load() {
  if (!props.questionId) return
  loading.value = true
  try {
    detail.value = await fetchGenQuestionDetail(props.questionId)
  } catch {
    detail.value = null
  } finally {
    loading.value = false
  }
}

watch(() => props.questionId, load, { immediate: true })
</script>

<style scoped>
.qdp { padding: 12px 20px; background: var(--admin-page-bg, #fafafa); border-radius: 6px; }
.qdp-section { margin-bottom: 16px; }
.qdp-section:last-child { margin-bottom: 0; }
.qdp-label { font-size: 13px; font-weight: 600; color: var(--el-text-color-primary); margin-bottom: 8px; }
.qdp-stem { font-size: 14px; line-height: 1.6; color: var(--el-text-color-primary); }
.qdp-material { font-size: 13px; line-height: 1.6; color: var(--el-text-color-secondary); white-space: pre-wrap; max-height: 200px; overflow-y: auto; }

.qdp-options { display: flex; flex-direction: column; gap: 6px; }
.qdp-option { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 4px; background: var(--el-bg-color); }
.qdp-option.is-correct { background: var(--el-color-success-light-9, #f0f9eb); }
.qdp-opt-key { font-weight: 600; }
.qdp-opt-text { flex: 1; }

.qdp-explanation { font-size: 13px; line-height: 1.6; white-space: pre-wrap; color: var(--el-text-color-primary); }

.calc-step { font-size: 13px; }
.calc-op { color: var(--el-color-primary); }
.calc-formula { color: var(--el-text-color-primary); font-family: monospace; }
.calc-desc { color: var(--el-text-color-primary); }
.calc-inputs { color: var(--el-text-color-secondary); font-size: 12px; margin: 4px 0; }
.calc-result { color: var(--el-color-success); font-weight: 600; margin-top: 4px; }

.qdp-distractors { display: flex; flex-direction: column; gap: 8px; }
.qdp-distractor { display: flex; align-items: center; gap: 10px; font-size: 13px; flex-wrap: wrap; }
.d-type { color: var(--el-color-warning); font-weight: 500; }
.d-formula { color: var(--el-text-color-secondary); font-family: monospace; font-size: 12px; }
.d-value { color: var(--el-text-color-secondary); font-size: 12px; }

.qdp-dual { font-size: 13px; display: flex; flex-direction: column; gap: 6px; }
.dual-row span { color: var(--el-text-color-secondary); }

.qdp-meta { font-size: 12px; background: var(--el-bg-color); padding: 10px; border-radius: 4px; max-height: 200px; overflow-y: auto; }
</style>
