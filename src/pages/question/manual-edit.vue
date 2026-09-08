<template>
  <view class="page-edit" :class="themeClass">
    <view class="mode-tabs">
      <text class="mode" :class="{ on: mode === 'photo' }" @tap="mode = 'photo'">图片上传</text>
      <text class="mode" :class="{ on: mode === 'full' }" @tap="mode = 'full'">完整录入</text>
    </view>

    <view class="form-card">
      <!-- 图片模式：图片优先 -->
      <view v-if="mode === 'photo'" class="field">
        <text class="label">错题图片</text>
        <view class="img-row">
          <view v-for="(img, idx) in form.images" :key="idx" class="img-item">
            <image class="img" :src="resolveMediaUrl(img)" mode="aspectFill" @tap="preview(idx)" />
            <text class="img-del" @tap="removeImg(idx)">×</text>
          </view>
          <view v-if="form.images.length < 3" class="img-add" @tap="onPickImage">
            <text class="add-icon">+</text>
            <text class="add-text">拍照/相册</text>
          </view>
        </view>
        <text class="img-tip">最多 3 张，每张 ≤5MB；支持拍照或相册</text>
      </view>

      <view class="field">
        <text class="label">分类</text>
        <view class="subject-row">
          <text
            v-for="s in subjects"
            :key="s"
            class="subj-chip"
            :class="{ active: form.subject === s }"
            @tap="form.subject = s"
          >{{ s }}</text>
        </view>
      </view>

      <view class="field">
        <text class="label">考点</text>
        <KnowledgePointPicker v-model="knowledge" :subject="form.subject" />
      </view>

      <view class="field">
        <text class="label">错因</text>
        <view class="reason-row">
          <text
            v-for="r in reasons"
            :key="r"
            class="reason-chip"
            :class="{ active: form.wrongReason === r }"
            @tap="form.wrongReason = form.wrongReason === r ? '' : r"
          >{{ r }}</text>
        </view>
      </view>

      <view class="field">
        <text class="label">解析（可选）</text>
        <nut-textarea v-model="form.analysis" :rows="2" placeholder="解题思路、易错点..." />
      </view>

      <!-- 完整模式：额外文本字段 -->
      <template v-if="mode === 'full'">
        <view class="field">
          <text class="label">题型细分（可选）</text>
          <nut-input v-model="form.questionType" placeholder="如 逻辑判断、概括归纳" clearable />
        </view>

        <view class="field">
          <text class="label">题干（可选）</text>
          <nut-textarea v-model="form.stem" :rows="3" placeholder="题干文本..." />
        </view>

        <view class="field">
          <text class="label">我的答案</text>
          <nut-input v-model="form.myAnswer" placeholder="如 A / AB / 错" clearable />
        </view>

        <view class="field">
          <text class="label">正确答案</text>
          <nut-input v-model="form.correctAnswer" placeholder="如 B / ACD / 对" clearable />
        </view>

        <view class="field">
          <text class="label">备注（可选）</text>
          <nut-textarea v-model="form.note" :rows="2" placeholder="补充想法..." />
        </view>

        <view class="field">
          <text class="label">错题图片</text>
          <view class="img-row">
            <view v-for="(img, idx) in form.images" :key="idx" class="img-item">
              <image class="img" :src="resolveMediaUrl(img)" mode="aspectFill" @tap="preview(idx)" />
              <text class="img-del" @tap="removeImg(idx)">×</text>
            </view>
            <view v-if="form.images.length < 3" class="img-add" @tap="onPickImage">
              <text class="add-icon">+</text>
              <text class="add-text">添加图片</text>
            </view>
          </view>
          <text class="img-tip">支持拍照或相册，最多 3 张</text>
        </view>
      </template>
    </view>

    <nut-button type="primary" block class="primary-btn" :loading="saving" @click="onSave">
      {{ isEdit ? '保存修改' : '录入错题' }}
    </nut-button>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import { Button as NutButton, Input as NutInput, Textarea as NutTextarea } from '@nutui/nutui-taro'
import KnowledgePointPicker from '@/components/KnowledgePointPicker.vue'
import { api } from '@/api'
import { flushFormBeforeSave } from '@/utils/formFlush'
import type { KnowledgePickValue } from '@/utils/knowledge'
import { resolveMediaUrl } from '@/utils/media'
import { showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '录入错题' })

const { themeClass } = useThemeClass()
const router = useRouter()
const editId = ref('')
const isEdit = ref(false)
const saving = ref(false)
/** 避免页面缓存导致重复 load；id 变化时强制重载 */
const loadedForId = ref<string | null>(null)
/** 默认图片上传模式 */
const mode = ref<'photo' | 'full'>('photo')

const subjects = ['常识', '言语', '数量', '判断', '资料']
const reasons = ['粗心', '方法不会', '知识点盲', '时间不够', '审题错误']

const form = reactive({
  subject: '',
  questionType: '',
  stem: '',
  myAnswer: '',
  correctAnswer: '',
  wrongReason: '',
  analysis: '',
  note: '',
  images: [] as string[],
})

const knowledge = ref<KnowledgePickValue>({ nodeId: '', treeKey: '', path: '' })

async function load() {
  const currentId = (router.params?.id || '').trim()
  if (loadedForId.value === currentId) return
  editId.value = currentId
  isEdit.value = !!currentId
  if (!currentId) {
    loadedForId.value = ''
    return
  }
  const res = await api.listManualWrongs()
  if (res.code === 0 && res.data) {
    const w = res.data.find((x) => x.id === currentId)
    if (w) {
      form.subject = w.subject
      form.questionType = w.questionType
      form.stem = w.stem
      form.myAnswer = w.myAnswer
      form.correctAnswer = w.correctAnswer
      form.wrongReason = w.wrongReason
      form.analysis = w.analysis
      form.note = w.note
      form.images = w.images || []
      knowledge.value = {
        nodeId: w.knowledgeNodeId || '',
        treeKey: w.knowledgeTreeKey || '',
        path: w.knowledgePath || '',
      }
      // 有较多文本字段时用完整模式，否则保持图片模式
      const hasText =
        !!(w.stem || w.myAnswer || w.correctAnswer || w.note || w.questionType)
      mode.value = hasText ? 'full' : 'photo'
    }
  }
  loadedForId.value = currentId
}

async function onPickImage() {
  try {
    const res = await Taro.chooseImage({
      count: 3 - form.images.length,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
    })
    const paths = res.tempFilePaths || []
    const files = res.tempFiles || []
    for (let i = 0; i < paths.length; i++) {
      const filePath = paths[i]
      const file = (files[i] as { originalFileObj?: File } | undefined)?.originalFileObj
      const upRes = await api.uploadWrongImage(filePath, file)
      if (upRes.code === 0 && upRes.data?.url) {
        form.images.push(upRes.data.url)
      } else {
        showToast(upRes.message || '上传失败', 'error')
      }
    }
  } catch (e) {
    if (e instanceof Error && /cancel/i.test(e.message)) return
    showToast(e instanceof Error ? e.message : '选择图片失败', 'error')
  }
}

function preview(idx: number) {
  Taro.previewImage({
    urls: form.images.map(resolveMediaUrl),
    current: resolveMediaUrl(form.images[idx]),
  })
}

function removeImg(idx: number) {
  form.images.splice(idx, 1)
}

async function onSave() {
  await flushFormBeforeSave()

  if (mode.value === 'photo') {
    if (!form.subject) {
      showToast('请选择分类', 'error')
      return
    }
    if (!form.images.length) {
      showToast('请至少上传一张错题图片', 'error')
      return
    }
  } else if (!form.subject && !form.stem && form.images.length === 0) {
    showToast('至少填写分类/题干/图片之一', 'error')
    return
  }

  saving.value = true
  try {
    const kb = {
      knowledgeNodeId: knowledge.value.nodeId || null,
      knowledgeTreeKey: knowledge.value.treeKey || '',
      knowledgePath: knowledge.value.path || '',
    }
    const payload = {
      subject: form.subject,
      questionType: form.questionType,
      stem: form.stem,
      myAnswer: form.myAnswer,
      correctAnswer: form.correctAnswer,
      wrongReason: form.wrongReason,
      analysis: form.analysis,
      note: form.note,
      images: form.images,
      ...kb,
    }
    // 新建且图片模式：不写入未展示的文本字段
    if (mode.value === 'photo' && !isEdit.value) {
      payload.questionType = ''
      payload.stem = ''
      payload.myAnswer = ''
      payload.correctAnswer = ''
      payload.note = ''
    }

    if (isEdit.value) {
      const res = await api.updateManualWrong(editId.value, payload)
      if (res.code !== 0) {
        showToast(res.message || '保存失败', 'error')
        return
      }
      showToast('已保存', 'success')
    } else {
      const res = await api.createManualWrong({
        ...payload,
        source: form.images.length ? 'photo' : 'manual',
      })
      if (res.code !== 0) {
        showToast(res.message || '录入失败', 'error')
        return
      }
      showToast('已录入', 'success')
    }
    setTimeout(() => Taro.navigateBack(), 600)
  } finally {
    saving.value = false
  }
}

useDidShow(() => {
  const currentId = (router.params?.id || '').trim()
  if (loadedForId.value !== currentId) {
    loadedForId.value = null
  }
  load()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-edit {
  @include page-padding;
  padding-bottom: 40px;
}

.mode-tabs {
  display: flex;
  gap: 4px;
  background: $page-bg;
  border-radius: 10px;
  padding: 3px;
  margin-bottom: 12px;
  .mode {
    flex: 1;
    text-align: center;
    padding: 8px 0;
    font-size: 13px;
    color: $text-secondary;
    border-radius: 8px;
    &.on {
      background: $card-bg;
      color: $primary-color;
      font-weight: 600;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }
  }
}

.form-card {
  @include card;
  padding: 14px 16px;
  border-radius: $radius-lg;
  margin-bottom: 12px;
}

.field {
  margin-bottom: 14px;
  .label {
    display: block;
    font-size: 13px;
    color: $text-secondary;
    margin-bottom: 6px;
  }
}

.subject-row, .reason-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.subj-chip, .reason-chip {
  padding: 4px 12px;
  border-radius: 8px;
  font-size: 12px;
  background: $page-bg;
  color: $text-secondary;
  &.active {
    background: $primary-light;
    color: $primary-color;
    font-weight: 600;
  }
}

.img-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.img-item {
  position: relative;
  .img {
    width: 80px;
    height: 80px;
    border-radius: 8px;
    background: $page-bg;
  }
  .img-del {
    position: absolute;
    top: -6px;
    right: -6px;
    width: 20px;
    height: 20px;
    line-height: 20px;
    text-align: center;
    background: $primary-color;
    color: #fff;
    border-radius: 50%;
    font-size: 12px;
  }
}

.img-add {
  width: 80px;
  height: 80px;
  border-radius: 8px;
  border: 1px dashed $border-color;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: $text-muted;
  .add-icon { font-size: 22px; }
  .add-text { font-size: 10px; margin-top: 2px; }
}

.img-tip {
  display: block;
  margin-top: 6px;
  font-size: 11px;
  color: $text-muted;
}

.primary-btn {
  margin-top: 4px;
}
</style>
