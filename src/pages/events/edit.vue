<template>
  <view class="page-event-edit" :class="themeClass">
    <text class="tip">记清时间地点与核心内容，并挂到知识框架，方便以后按考点串联回忆。</text>

    <view class="field">
      <text class="label">事件标题 *</text>
      <nut-input v-model="form.title" placeholder="如：神舟十号飞船发射成功" />
    </view>

    <view class="row-2">
      <view class="field half">
        <text class="label">日期</text>
        <nut-input v-model="form.eventDate" placeholder="YYYY-MM-DD" />
      </view>
      <view class="field half">
        <text class="label">地点</text>
        <nut-input v-model="form.place" placeholder="如：酒泉卫星发射中心" />
      </view>
    </view>

    <view class="field">
      <view class="label-row">
        <text class="label">核心内容 *</text>
        <VoiceInputBtn v-model="form.coreContent" />
      </view>
      <nut-textarea
        v-model="form.coreContent"
        :rows="5"
        placeholder="用自己的话写清：发生了什么、为何重要、和考点有什么联系"
      />
    </view>

    <view class="field">
      <view class="label-row">
        <text class="label">补充联想（可选）</text>
        <VoiceInputBtn v-model="form.note" />
      </view>
      <nut-textarea
        v-model="form.note"
        :rows="3"
        placeholder="可写：相关人物、对比事件、易混点…"
      />
    </view>

    <view class="field">
      <text class="label">归属知识框架</text>
      <text class="field-tip">如：航天常识 → 神舟系列；选中后可在「按框架」视图归类回顾</text>
      <KnowledgePointPicker v-model="knowledge" />
    </view>

    <view class="foot">
      <nut-button type="primary" block :loading="saving" @click="onSave">保存</nut-button>
      <text v-if="editId" class="del" @tap="onDelete">删除</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import { Button as NutButton, Input as NutInput, Textarea as NutTextarea } from '@nutui/nutui-taro'
import KnowledgePointPicker from '@/components/KnowledgePointPicker.vue'
import VoiceInputBtn from '@/components/VoiceInputBtn.vue'
import { api } from '@/api'
import { flushFormBeforeSave } from '@/utils/formFlush'
import type { KnowledgePickValue } from '@/utils/knowledge'
import { showConfirm, showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '记事件印象' })

const { themeClass } = useThemeClass()
const router = useRouter()
const editId = ref('')
const saving = ref(false)
/** 避免页面缓存导致重复 load 闪烁；id 变化时强制重载 */
const loadedForId = ref<string | null>(null)

const form = reactive({
  title: '',
  eventDate: new Date().toISOString().slice(0, 10),
  place: '',
  coreContent: '',
  note: '',
})

const knowledge = ref<KnowledgePickValue>({
  nodeId: '',
  treeKey: '',
  path: '',
})

async function load() {
  const id = (router.params?.id || '').trim()
  editId.value = id
  if (!id) {
    if (loadedForId.value === '') return
    loadedForId.value = ''
    form.title = ''
    form.eventDate = new Date().toISOString().slice(0, 10)
    form.place = ''
    form.coreContent = ''
    form.note = ''
    knowledge.value = { nodeId: '', treeKey: '', path: '' }
    return
  }
  if (loadedForId.value === id) return
  const res = await api.getEvent(id)
  if (res.code !== 0 || !res.data) {
    showToast(res.message || '加载失败', 'error')
    return
  }
  const e = res.data
  form.title = e.title
  form.eventDate = e.eventDate || ''
  form.place = e.place || ''
  form.coreContent = e.coreContent || ''
  form.note = e.note || ''
  knowledge.value = {
    nodeId: e.knowledgeNodeId || '',
    treeKey: e.knowledgeTreeKey || '',
    path: e.knowledgePath || '',
  }
  loadedForId.value = id
}

async function onSave() {
  await flushFormBeforeSave()

  if (!form.title.trim()) {
    showToast('请填写事件标题')
    return
  }
  if (!form.coreContent.trim()) {
    showToast('请填写核心内容')
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      eventDate: form.eventDate.trim(),
      place: form.place.trim(),
      coreContent: form.coreContent.trim(),
      note: form.note.trim(),
      knowledgeNodeId: knowledge.value.nodeId || null,
      knowledgeTreeKey: knowledge.value.treeKey || '',
      knowledgePath: knowledge.value.path || '',
    }
    const res = editId.value
      ? await api.updateEvent(editId.value, payload)
      : await api.createEvent(payload)
    if (res.code === 0) {
      showToast('已保存', 'success')
      if (!editId.value && res.data?.id) {
        editId.value = res.data.id
        loadedForId.value = res.data.id
      } else if (res.data?.title != null) {
        form.title = res.data.title
      }
      setTimeout(() => {
        Taro.navigateBack({
          fail: () => Taro.redirectTo({ url: '/pages/events/index' }),
        })
      }, 400)
    } else {
      showToast(res.message || '保存失败', 'error')
    }
  } finally {
    saving.value = false
  }
}

async function onDelete() {
  if (!editId.value) return
  const ok = await showConfirm('删除事件', '确定删除这条事件印象？')
  if (!ok) return
  const res = await api.deleteEvent(editId.value)
  if (res.code === 0) {
    showToast('已删除', 'success')
    Taro.navigateBack()
  } else {
    showToast(res.message || '删除失败', 'error')
  }
}

useDidShow(() => {
  // 页面可能被缓存：每次显示按路由 id 重新对齐
  const id = (router.params?.id || '').trim()
  if (loadedForId.value !== id) {
    loadedForId.value = null
  }
  load()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-event-edit {
  @include page-padding;
  padding-bottom: 100px;
}

.tip {
  display: block;
  font-size: 12px;
  color: $text-muted;
  line-height: 1.5;
  margin-bottom: 14px;
}

.row-2 {
  display: flex;
  gap: 10px;
  .half { flex: 1; min-width: 0; }
}

.field {
  margin-bottom: 14px;
  .label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 6px;
  }
  .label-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
    .label { margin-bottom: 0; }
  }
  .field-tip {
    display: block;
    font-size: 11px;
    color: $text-muted;
    line-height: 1.4;
    margin: -2px 0 8px;
  }
}

.foot {
  margin-top: 8px;
  .del {
    display: block;
    text-align: center;
    margin-top: 16px;
    font-size: 13px;
    color: $danger;
  }
}

.page-event-edit {
  :deep(.nut-input),
  :deep(.nut-textarea) {
    background: $input-bg;
    border-radius: 8px;
  }
}
</style>
