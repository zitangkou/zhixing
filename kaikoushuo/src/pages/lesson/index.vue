<template>
  <view v-if="lesson" class="page lesson-page">
    <text class="eyebrow">{{ lesson.level }} · {{ lesson.minutes }} MIN</text>
    <text class="title">{{ lesson.title }}</text>
    <view class="goal card"><text class="goal-label">本节目标</text><text>{{ lesson.goal }}</text></view>

    <text class="section-title">先看 / 听素材</text>
    <video v-if="playableVideo" class="lesson-video" :src="lesson.videoUrl" :poster="lesson.posterUrl" controls object-fit="contain" />
    <view v-if="lesson.sourceUrl && lesson.rightsStatus !== 'rejected' && !playableVideo && !playableAudio" class="source-note card">
      <text>这节课使用官方外链素材，小程序暂不直接播放。</text>
      <text class="source-action" @tap="copySource">复制官方来源链接</text>
    </view>
    <text v-if="playableVideo" class="media-tip">先完整观看一次，再用字幕和台词精听。</text>
    <text class="section-title">台词与字幕</text>
    <button class="caption-toggle" @tap="showTranslation = !showTranslation">{{ showTranslation ? '隐藏中文' : '显示中文' }}</button>
    <view class="card dialogue">
      <view v-for="(turn, i) in lesson.dialogue" :key="i" class="turn" :class="{ mine: turn.speaker === 'You' }">
        <text class="speaker">{{ turn.speaker === 'You' ? '你' : turn.speaker }}</text>
        <text class="english">{{ turn.en }}</text>
        <text v-if="showTranslation && turn.zh" class="translation">{{ turn.zh }}</text>
      </view>
      <text v-if="lesson.dialogue.length === 0" class="audio-note">本课暂未添加台词文本。</text>
    </view>
    <button v-if="playableAudio" class="listen" @tap="listen">{{ speaking ? '正在播放…' : '▶ 听示范音频' }}</button>
    <text v-else-if="!playableVideo && !lesson.sourceUrl" class="audio-note">本课暂未配置示范音频或视频，可以先按台词练习并录下自己的表达。</text>

    <text class="section-title">带走这几句</text>
    <view v-for="phrase in lesson.phrases" :key="phrase.en" class="phrase card"><text class="phrase-en">{{ phrase.en }}</text><text class="muted">{{ phrase.zh }}</text></view>

    <view class="challenge card"><text class="challenge-label">轮到你说</text><text class="challenge-text">{{ lesson.prompt }}</text><text class="muted">先开口完成任务，再对照上面的句块检查。你可以录音回放，首版暂不上传录音。</text>
      <button class="primary record" @tap="record">{{ recording ? '停止录音并保存' : '开始录音练习' }}</button>
      <view v-if="audioPath" class="audio-actions"><text class="playback" @tap="playRecording">▶ 回放我的录音</text><text class="playback" @tap="clearRecording">删除录音</text></view>
    </view>
    <button class="complete" @tap="complete">{{ completed ? '已完成 · 再练一次' : '完成本节并安排复习' }}</button>
    <text v-if="saved" class="saved">已记录本地学习进度，明天再用提示练一次。</text>
  </view>
  <view v-else class="page"><text class="title">课程暂不可用</text><button class="primary" @tap="back">返回</button></view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Taro, { useRouter } from '@tarojs/taro'
import { lessons, loadLessons, markLessonComplete, progressKey, readProgress } from '@/data'

definePageConfig({ navigationBarTitleText: '口语练习' })
const router = useRouter()
const lesson = computed(() => lessons.find((item) => item.id === router.params.id))
const showTranslation = ref(false)
const playableAudio = computed(() => !!lesson.value?.audioUrl && (!lesson.value.rightsStatus || lesson.value.rightsStatus === 'licensed_hosting'))
const playableVideo = computed(() => !!lesson.value?.videoUrl && (!lesson.value.rightsStatus || lesson.value.rightsStatus === 'licensed_hosting'))
const speaking = ref(false)
const recording = ref(false)
const audioPath = ref('')
const completed = ref(false)
const saved = ref(false)
let recorder: ReturnType<typeof Taro.getRecorderManager> | undefined
let player: ReturnType<typeof Taro.createInnerAudioContext> | undefined
function listen() {
  if (!playableAudio.value || !lesson.value?.audioUrl || speaking.value) return
  speaking.value = true
  player?.destroy()
  player = Taro.createInnerAudioContext()
  player.src = lesson.value.audioUrl
  player.onEnded(() => { speaking.value = false })
  player.onError(() => { speaking.value = false; Taro.showToast({ title: '音频暂时无法播放', icon: 'none' }) })
  player.play()
}
function copySource() {
  if (!lesson.value?.sourceUrl) return
  Taro.setClipboardData({ data: lesson.value.sourceUrl, success: () => Taro.showToast({ title: '来源链接已复制', icon: 'success' }) })
}
function record() {
  if (!recording.value) {
    recorder = Taro.getRecorderManager()
    recorder.onStop((res) => { audioPath.value = res.tempFilePath; recording.value = false })
    recorder.onError(() => { recording.value = false; Taro.showToast({ title: '录音失败，请检查麦克风权限', icon: 'none' }) })
    recorder.start({ duration: 60000, format: 'mp3' })
    recording.value = true
    return
  }
  recorder?.stop()
}
function playRecording() {
  if (!audioPath.value) return
  player?.destroy()
  player = Taro.createInnerAudioContext()
  player.src = audioPath.value
  player.play()
}
function clearRecording() { audioPath.value = ''; Taro.showToast({ title: '录音已删除', icon: 'none' }) }
function complete() {
  if (!lesson.value) return
  const ids = new Set(readProgress())
  ids.add(lesson.value.id)
  Taro.setStorageSync(progressKey, JSON.stringify([...ids]))
  void markLessonComplete(lesson.value)
  completed.value = true
  saved.value = true
  Taro.showToast({ title: '完成得很好', icon: 'success' })
}
function back() { Taro.navigateBack() }
onMounted(async () => { await loadLessons(); completed.value = !!lesson.value && readProgress().includes(lesson.value.id) })
</script>

<style lang="scss">
.lesson-page { padding-bottom: 70rpx; }
.goal { display:flex; flex-direction:column; gap:10rpx; background:#e9f2ee; color:#435d56; font-size:27rpx; line-height:1.55; }
.goal-label,.challenge-label { color:#256d73; font-weight:700; font-size:24rpx; }
.dialogue { padding:10rpx 24rpx; }
.turn { padding:24rpx 4rpx; border-bottom:1rpx solid #edf0ed; }
.turn:last-child { border:0; }
.speaker { color:#6d817b; font-size:22rpx; display:block; margin-bottom:8rpx; }
.english { color:#203432; font-size:30rpx; font-weight:650; display:block; line-height:1.5; }
.translation { color:#85918c; font-size:24rpx; display:block; margin-top:6rpx; }
.mine .english { color:#256d73; }
.listen { margin-top:18rpx; border-radius:16rpx; background:#fff; color:#256d73; font-size:25rpx; border:1rpx solid #d9e6e1; }
.listen[disabled] { color:#8d9994; background:#eff1ee; border-color:#e4e8e4; }
.audio-note { display:block; color:#899590; text-align:center; font-size:22rpx; margin:12rpx 0 4rpx; }
.lesson-video { display:block; width:100%; height:420rpx; margin:18rpx 0 8rpx; border-radius:18rpx; background:#172b2c; }
.media-tip { display:block; margin:8rpx 0 12rpx; color:#899590; font-size:22rpx; }
.source-note { display:flex; flex-direction:column; gap:14rpx; color:#75847f; font-size:24rpx; }
.source-action,.caption-toggle { color:#256d73; font-size:23rpx; }
.caption-toggle { display:block; margin:0 0 12rpx auto; padding:6rpx 18rpx; background:#e9f2ee; border-radius:18rpx; }
.listen::after,.complete::after { border:0; }
.phrase { padding:22rpx 26rpx; }
.phrase-en { display:block; font-size:29rpx; font-weight:650; margin-bottom:8rpx; }
.challenge { border:1rpx solid #f0c7b4; background:#fffaf6; }
.challenge-text { display:block; font-size:28rpx; font-weight:650; margin:12rpx 0; line-height:1.5; }
.record { width:100%; margin-top:22rpx; }
.audio-actions { display:flex; justify-content:space-between; margin-top:20rpx; }
.playback { color:#256d73; font-size:24rpx; padding:8rpx 0; }
.complete { background:#eaf0ec; color:#256d73; border-radius:18rpx; margin-top:24rpx; font-size:28rpx; }
.saved { display:block; text-align:center; color:#75847f; margin-top:16rpx; font-size:23rpx; }
</style>
