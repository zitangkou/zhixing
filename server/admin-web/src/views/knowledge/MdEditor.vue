<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { EditorView, basicSetup } from 'codemirror'
import { Compartment, EditorState } from '@codemirror/state'
import { markdown } from '@codemirror/lang-markdown'
import { linter, type Diagnostic } from '@codemirror/lint'
import type { KnowledgeIssue } from '@/api/knowledge'

const props = defineProps<{
  modelValue: string
  issues?: KnowledgeIssue[]
  readonly?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [string]
  change: [string]
}>()

const host = ref<HTMLDivElement | null>(null)
let view: EditorView | null = null
const lintCompartment = new Compartment()

function issuesToDiagnostics(issues: KnowledgeIssue[] | undefined): Diagnostic[] {
  if (!issues?.length) return []
  return issues.map((iss) => ({
    from: linePos(iss.line).from,
    to: linePos(iss.line).to,
    severity: iss.level === 'error' ? 'error' : 'warning',
    message: `[${iss.code}] ${iss.message}`,
  }))
}

function linePos(line: number): { from: number; to: number } {
  if (!view) return { from: 0, to: 0 }
  const doc = view.state.doc
  const ln = Math.max(1, Math.min(line || 1, doc.lines))
  const info = doc.line(ln)
  return { from: info.from, to: info.to }
}

function buildLint() {
  return linter(() => issuesToDiagnostics(props.issues))
}

onMounted(() => {
  if (!host.value) return
  view = new EditorView({
    parent: host.value,
    state: EditorState.create({
      doc: props.modelValue || '',
      extensions: [
        basicSetup,
        markdown(),
        EditorView.editable.of(!props.readonly),
        EditorView.lineWrapping,
        lintCompartment.of(buildLint()),
        EditorView.updateListener.of((u) => {
          if (u.docChanged) {
            const v = u.state.doc.toString()
            emit('update:modelValue', v)
            emit('change', v)
          }
        }),
        EditorView.theme({
          '&': { height: '100%', fontSize: '13px' },
          '.cm-scroller': { fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" },
          '.cm-content': { minHeight: '100%' },
        }),
      ],
    }),
  })
})

watch(
  () => props.modelValue,
  (v) => {
    if (!view) return
    if (view.state.doc.toString() === v) return
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: v || '' },
    })
  },
)

watch(
  () => props.issues,
  () => {
    if (!view) return
    view.dispatch({ effects: lintCompartment.reconfigure(buildLint()) })
  },
  { deep: true },
)

onBeforeUnmount(() => {
  view?.destroy()
  view = null
})

function gotoLine(line: number) {
  if (!view) return
  const { from, to } = linePos(line)
  view.dispatch({
    selection: { anchor: from, head: to },
    scrollIntoView: true,
  })
  view.focus()
}

defineExpose({ gotoLine })
</script>

<template>
  <div ref="host" class="md-editor" />
</template>

<style scoped>
.md-editor {
  height: 100%;
  min-height: 320px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
}
.md-editor :deep(.cm-editor) {
  height: 100%;
}
</style>
