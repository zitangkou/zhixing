<script setup>
import { computed, onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { fetchImageStyles, generateImageStyle, loginWithWechat } from '../../utils/api'
import { storage } from '../../utils/storage'

const styles = ref([])
const selectedStyleId = ref('')
const imagePath = ref('')
const loading = ref(false)
const loadError = ref('')
const step = ref('choose')
const consented = ref(false)
const generating = ref(false)
const resultPath = ref('')
const generationStatus = ref('queued')
const generationError = ref('')
const selectedStyle = computed(() => styles.value.find((item) => item.id === selectedStyleId.value) || null)

async function loadStyles() {
  loading.value = true
  loadError.value = ''
  try {
    const result = await fetchImageStyles()
    styles.value = Array.isArray(result?.items) ? result.items : []
    if (!styles.value.some((item) => item.id === selectedStyleId.value)) {
      selectedStyleId.value = styles.value[0]?.id || ''
    }
  } catch (error) {
    loadError.value = error?.message || '风格列表加载失败，请检查网络后重试'
  } finally {
    loading.value = false
  }
}

async function choosePhoto() {
  try {
    const result = await Taro.chooseImage({ count: 1, sizeType: ['compressed', 'original'], sourceType: ['album', 'camera'] })
    imagePath.value = result.tempFilePaths?.[0] || ''
    step.value = 'choose'
  } catch (error) {
    if (error?.errMsg && !error.errMsg.includes('cancel')) {
      Taro.showToast({ title: '选择照片失败，请重试', icon: 'none' })
    }
  }
}

function goConfirm() {
  if (!imagePath.value) {
    Taro.showToast({ title: '请先选择一张照片', icon: 'none' })
    return
  }
  if (!selectedStyle.value) {
    Taro.showToast({ title: '当前没有可用风格', icon: 'none' })
    return
  }
  step.value = 'confirm'
}

function backToStyles() {
  step.value = 'choose'
}

function returnHome() {
  Taro.navigateBack({ delta: 1 })
}

async function ensureLogin() {
  if (storage.token()) return true
  const { confirm } = await Taro.showModal({ title: '登录后生成', content: '图片转换需要登录账号。登录成功后，点击开始转换会将所选照片上传至服务器和模型服务处理。', confirmText: '微信登录' })
  if (!confirm) return false
  const session = await loginWithWechat()
  if (!storage.saveSession(session.access_token, session.user)) throw new Error('本地存储空间不足，登录状态未保存')
  return true
}

async function generate() {
  if (!consented.value) {
    Taro.showToast({ title: '请先确认图片处理说明', icon: 'none' })
    return
  }
  if (generating.value || !selectedStyle.value || !imagePath.value) return
  generating.value = true
  generationError.value = ''
  generationStatus.value = 'queued'
  try {
    if (!await ensureLogin()) return
    resultPath.value = await generateImageStyle(imagePath.value, selectedStyle.value.id, (status) => { generationStatus.value = status })
    Taro.showToast({ title: '转换完成', icon: 'success' })
  } catch (error) {
    generationError.value = error?.message || '图片生成失败，请稍后重试'
    Taro.showToast({ title: '图片生成失败', icon: 'none', duration: 2800 })
  } finally {
    generating.value = false
  }
}

async function saveResult() {
  if (!resultPath.value) return
  try {
    await Taro.saveImageToPhotosAlbum({ filePath: resultPath.value })
    Taro.showToast({ title: '已保存到相册', icon: 'success' })
  } catch (error) {
    if (error?.errMsg?.includes('auth deny')) {
      Taro.showModal({ title: '需要相册权限', content: '请在设置中允许保存图片到相册。', success: ({ confirm }) => confirm && Taro.openSetting() })
    } else Taro.showToast({ title: '保存失败，请重试', icon: 'none' })
  }
}

onMounted(loadStyles)
</script>

<template>
  <view class="photo-page">
    <view class="intro">
      <view class="eyebrow">AI PHOTO STYLE</view>
      <view class="page-title">{{ step === 'confirm' ? '确认转换信息' : '让照片换种表达' }}</view>
      <view class="page-subtitle">选择一张照片和喜欢的风格，开始前可以再次确认。</view>
    </view>

    <template v-if="step === 'choose'">
      <view class="section-title">1. 选择照片</view>
      <button v-if="!imagePath" class="photo-picker" @tap="choosePhoto">
        <view class="picker-icon">＋</view>
        <view class="picker-title">选择一张照片</view>
        <view class="picker-note">支持从相册选择或直接拍摄</view>
      </button>
      <view v-else class="photo-preview-card">
        <image class="photo-preview" :src="imagePath" mode="aspectFit" />
        <button class="button-reset replace-photo" @tap="choosePhoto">重新选择</button>
      </view>

      <view class="style-heading">
        <view class="section-title">2. 选择风格</view>
        <button class="button-reset retry-link" :disabled="loading" @tap="loadStyles">{{ loading ? '加载中…' : '刷新' }}</button>
      </view>
      <view v-if="loading" class="state-card">正在加载已上架的图片风格…</view>
      <view v-else-if="loadError" class="state-card error-state">
        <view class="error-message-row">
          <view class="error-icon">!</view>
          <view class="error-message">{{ loadError }}</view>
        </view>
        <button class="button-reset retry-button" @tap="loadStyles">重新加载</button>
      </view>
      <view v-else-if="!styles.length" class="state-card">暂时没有可用图片风格。请稍后再来，或检查后台是否已启用模型和对应风格。</view>
      <view v-else class="style-list">
        <button
          v-for="style in styles"
          :key="style.id"
          class="button-reset style-card"
          :class="{ selected: selectedStyleId === style.id }"
          @tap="selectedStyleId = style.id"
        >
          <view class="style-mark">✦</view>
          <view class="style-copy">
            <view class="style-name">{{ style.name }}</view>
            <view class="style-description">{{ style.description || '为照片尝试一种新的艺术表达。' }}</view>
          </view>
          <view class="radio-mark">{{ selectedStyleId === style.id ? '✓' : '' }}</view>
        </button>
      </view>

      <view class="privacy-note">选择照片和浏览风格时不会上传图片。只有确认并登录后开始转换，才会上传至服务器和模型服务处理。</view>
      <button class="button-reset primary-action" :disabled="!imagePath || !selectedStyle || loading" @tap="goConfirm">下一步：确认信息</button>
    </template>

    <template v-else>
      <view class="confirm-card">
        <image class="confirm-image" :src="imagePath" mode="aspectFit" />
        <view class="confirm-meta">
          <view class="confirm-label">所选风格</view>
          <view class="confirm-name">{{ selectedStyle?.name }}</view>
          <view class="confirm-description">{{ selectedStyle?.description }}</view>
        </view>
      </view>
      <view class="privacy-panel">
        <view class="privacy-title">图片处理说明</view>
        <view class="privacy-copy">开始转换后，照片会上传至服务端并发送给所选模型服务处理。生成结果在服务器临时保存 24 小时，之后需重新生成。请勿上传他人或涉及隐私的照片。</view>
      </view>
      <view v-if="!resultPath" class="consent-row" @tap="consented = !consented"><view class="consent-box" :class="{ checked: consented }">{{ consented ? '✓' : '' }}</view><view>我已了解照片将上传至服务器和模型服务处理</view></view>
      <view v-if="generating" class="generation-status" aria-live="polite">
        <view class="generation-spinner" />
        <view>
          <view class="generation-title">{{ generationStatus === 'queued' ? '任务已提交，正在排队…' : 'AI 正在处理图片…' }}</view>
          <view class="generation-note">生成时间可能较长，请保持页面打开。完成后会立即提示。</view>
        </view>
      </view>
      <view v-if="generationError && !generating" class="generation-error">
        <view class="generation-error-title">生成未完成</view>
        <view>{{ generationError }}</view>
        <view class="generation-error-note">任务失败原因已记录，管理员可在后台「工具配置 → 图片生成记录」查看。</view>
      </view>
      <button v-if="!resultPath" class="button-reset primary-action" :disabled="generating || !selectedStyle || !consented" @tap="generate">{{ generating ? '正在生成…' : '开始转换' }}</button>
      <view v-else class="result-panel">
        <view class="result-title">转换完成 · {{ selectedStyle?.name }}</view>
        <image class="result-image" :src="resultPath" mode="aspectFit" />
        <button class="button-reset primary-action" @tap="saveResult">保存到相册</button>
        <button class="button-reset secondary-action" @tap="resultPath = ''; consented = false">重新转换</button>
      </view>
      <button class="button-reset secondary-action" @tap="backToStyles">返回修改</button>
      <button class="button-reset text-action" @tap="returnHome">返回首页</button>
    </template>
  </view>
</template>

<style scoped>
.photo-page { min-height: 100vh; padding: 20px 20px 36px; box-sizing: border-box; color: #24243a; }
.intro { padding: 5px 0 22px; }
.eyebrow { color: #8984a6; font-size: 10px; font-weight: 700; letter-spacing: 1.6px; }
.page-title { margin-top: 8px; font-size: 24px; font-weight: 800; letter-spacing: -.5px; }
.page-subtitle { margin-top: 7px; color: #85859a; font-size: 12px; line-height: 1.7; }
.section-title { font-size: 14px; font-weight: 750; }
.photo-picker,.photo-preview-card,.state-card,.style-card,.confirm-card,.privacy-panel { box-sizing: border-box; width: 100%; margin-top: 12px; border: 1px solid #ecebf3; border-radius: 16px; background: #fff; }
.photo-picker { height: 158px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.picker-icon { width: 37px; height: 37px; border-radius: 12px; background: #f0edff; color: #7057e8; font-size: 25px; line-height: 35px; }
.picker-title { margin-top: 9px; color: #343349; font-size: 12px; font-weight: 700; }
.picker-note { margin-top: 5px; color: #9999aa; font-size: 10px; }
.photo-preview-card { position: relative; height: 218px; overflow: hidden; background: #f7f7fa; }
.photo-preview { width: 100%; height: 100%; }
.replace-photo { position: absolute; right: 10px; bottom: 10px; padding: 7px 10px; border-radius: 8px; background: #fff; color: #5f50b1; font-size: 10px; }
.style-heading { display: flex; align-items: center; justify-content: space-between; margin-top: 22px; }
.retry-link { color: #7057e8; font-size: 10px; }
.state-card { padding: 17px 14px; color: #85859a; font-size: 11px; line-height: 1.7; }
.error-state { color: #a9525d; }
.retry-button { margin-top: 8px; color: #7057e8; font-size: 11px; }
.style-card { display: flex; align-items: center; gap: 11px; padding: 13px 12px; text-align: left; }
.style-card.selected { border-color: #8a78ee; background: #faf9ff; box-shadow: 0 0 0 2px #eeeaff; }
.style-mark { width: 40px; height: 40px; flex: none; border-radius: 13px; background: #f0edff; color: #7057e8; font-size: 21px; line-height: 40px; text-align: center; }
.style-copy { min-width: 0; flex: 1; }
.style-name { color: #35344b; font-size: 12px; font-weight: 700; }
.style-description { margin-top: 4px; color: #9090a2; font-size: 10px; line-height: 1.55; }
.radio-mark { width: 19px; height: 19px; flex: none; border: 1px solid #d8d6e5; border-radius: 50%; color: #fff; font-size: 12px; line-height: 19px; text-align: center; }
.selected .radio-mark { border-color: #7057e8; background: #7057e8; }
.privacy-note { margin-top: 14px; color: #9999aa; font-size: 9px; line-height: 1.7; }
.primary-action { width: 100%; height: 45px; margin-top: 17px; border-radius: 12px; background: #7057e8; color: #fff; font-size: 12px; font-weight: 700; }
.primary-action[disabled] { opacity: .48; }
.confirm-card { overflow: hidden; }
.confirm-image { width: 100%; height: 245px; background: #f7f7fa; }
.confirm-meta { padding: 14px; }
.confirm-label { color: #9291a4; font-size: 9px; }
.confirm-name { margin-top: 5px; font-size: 14px; font-weight: 750; }
.confirm-description { margin-top: 5px; color: #8d8da0; font-size: 10px; line-height: 1.6; }
.privacy-panel { padding: 14px; background: #f8f6ff; border-color: #ece7ff; }
.privacy-title { color: #52458f; font-size: 11px; font-weight: 700; }
.privacy-copy { margin-top: 6px; color: #77758e; font-size: 10px; line-height: 1.7; }
.consent-row { display: flex; align-items: center; gap: 8px; margin-top: 16px; color: #77758e; font-size: 10px; line-height: 1.5; }
.consent-box { width: 17px; height: 17px; flex: none; box-sizing: border-box; border: 1px solid #b9b5ca; border-radius: 5px; color: #fff; background: #fff; text-align: center; line-height: 16px; }
.consent-box.checked { border-color: #7057e8; background: #7057e8; }
.result-panel { margin-top: 16px; padding: 14px; border: 1px solid #ecebf3; border-radius: 16px; background: #fff; }
.result-title { margin-bottom: 10px; font-size: 12px; font-weight: 700; }
.result-image { width: 100%; height: 280px; background: #f7f7fa; }
.secondary-action { width: 100%; height: 42px; margin-top: 10px; border-radius: 11px; background: #fff; color: #6354b0; font-size: 11px; }
.text-action { display: block; margin: 14px auto 0; color: #89889b; font-size: 10px; }
.generation-status, .generation-error { display: flex; gap: 12px; align-items: flex-start; margin: 16px 0; padding: 16px; border: 1px solid #e6e0ff; border-radius: 14px; background: #f8f6ff; color: #55469a; font-size: 14px; line-height: 1.6; }
.generation-spinner { width: 18px; height: 18px; flex: 0 0 18px; margin-top: 2px; border: 2px solid #d7ceff; border-top-color: #7053e8; border-radius: 50%; animation: generation-spin 0.8s linear infinite; }
.generation-title, .generation-error-title { font-weight: 600; }
.generation-note, .generation-error-note { margin-top: 4px; color: #8b879d; font-size: 12px; }
.generation-error { display: block; border-color: #f3d4d7; background: #fff8f8; color: #a83e4b; overflow-wrap: anywhere; }
@keyframes generation-spin { to { transform: rotate(360deg); } }
</style>
