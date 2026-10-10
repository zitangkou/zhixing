<template>
  <view class="page">
    <view class="tabs"><text :class="{active: tab === 'journal'}" @tap="tab = 'journal'">拍摄练习</text><text :class="{active: tab === 'map'}" @tap="tab = 'map'">知识地图</text></view>
    <template v-if="tab === 'journal'">
      <view class="intro"><text class="eyebrow">FIELD NOTES</text><text class="title">每次按下快门，都留下线索。</text><text class="copy">记下拍摄条件与复盘，下次就知道从哪里改进。</text></view>
      <view class="form"><text class="label">今天练了什么</text><picker :range="lessonTitles" @change="onLessonChange"><view class="picker">{{ selectedTitle }} <text>⌄</text></view></picker><text class="label">拍摄主题</text><input v-model="subject" placeholder="例如：窗边的咖啡杯"/><text class="label">我观察到的光线 / 构图</text><textarea v-model="observation" placeholder="光从哪里来？主体和背景是什么关系？"/><text class="label">下次我想调整</text><textarea v-model="nextTry" placeholder="曝光补偿、机位、背景……"/></view>
      <view class="save" @tap="saveNote">保存这次练习</view>
      <view class="section-title">最近练习 <text>{{ notes.length }} 条</text></view>
      <view v-if="!notes.length" class="empty">还没有练习记录。先去拍一张吧。<text @tap="goHome">浏览今日技巧 ›</text></view>
      <view v-for="note in notes" :key="note.id" class="note"><view class="note-top"><text class="note-tag">{{ note.lessonTitle || note.lesson || '摄影练习' }}</text><text class="note-date">{{ note.date }}</text></view><text class="note-subject">{{ note.subject || '未命名练习' }}</text><text class="note-text">{{ note.observation || '还没有写观察笔记。' }}</text><text class="note-next">下次试试：{{ note.nextTry || '继续观察光线与画面边缘' }}</text></view>
    </template>
    <template v-else>
      <view class="intro"><text class="eyebrow">LEARNING ROADMAP</text><text class="title">从看见，到表达</text><text class="copy">循序渐进，不必一次学完。每一项都配一条可执行的拍摄练习。</text></view>
      <view v-for="(stage, index) in roadmap" :key="stage.title" class="map-stage"><view class="map-no">0{{ index + 1 }}</view><view class="map-main"><text class="map-title">{{ stage.title }}</text><text class="map-items">{{ stage.items }}</text><text class="map-note">{{ mapDescription[index] }}</text></view></view>
      <view class="note"><text class="note-subject">建议学习节奏</text><text class="note-text">每周 2–3 次，每次 15–30 分钟。先观察 → 学一个概念 → 控制一个变量拍摄 → 挑片复盘。连续练习比一次学很多更有效。</text></view>
    </template>
  </view>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { lessons, roadmap, loadCatalog } from '@/data/catalog'
import { showToast } from '@/utils/feedback'
import { readPracticeNotes, savePracticeNotes, type PracticeNote } from '@/utils/practiceStorage'
definePageConfig({ navigationBarTitleText: '练习与地图' })
const params = Taro.getCurrentInstance().router?.params || {}
const tab = ref(params.tab === 'map' ? 'map' : 'journal')
const selected = ref(Math.max(0, lessons.value.findIndex((item) => item.id === params.lessonId)))
const lessonTitles = computed(() => lessons.value.map((item) => item.title))
const selectedTitle = computed(() => lessonTitles.value[selected.value] || '')
const subject = ref(''); const observation = ref(''); const nextTry = ref('')
const notes = ref<PracticeNote[]>([])
const mapDescription = ['练习判断光源方向、软硬和色彩，用光塑造质感。', '控制画面边缘、主体位置与空间关系，让视线有落点。', '理解光圈、快门、ISO、测光和对焦，建立可控的拍摄习惯。', '围绕人物、静物、街景和风光，练习把感受转成画面选择。', '通过选片、基础调整和系列组织，让单张照片形成作品表达。']
function onLessonChange(event: { detail: { value: string } }) { selected.value = Number(event.detail.value) }
function loadNotes() { notes.value = readPracticeNotes() }
function syncSelectedLesson() { const index = lessons.value.findIndex((item) => item.id === params.lessonId); selected.value = index >= 0 ? index : 0 }
async function refreshPracticePage() { await loadCatalog(true); syncSelectedLesson(); loadNotes() }
function saveNote() {
  const cleanSubject = subject.value.trim()
  const cleanObservation = observation.value.trim()
  if (!cleanSubject && !cleanObservation) { showToast('写下拍摄主题或观察再保存'); return }
  const item: PracticeNote = { id: `${Date.now()}`, lessonId: lessons.value[selected.value].id, lessonTitle: selectedTitle.value, subject: cleanSubject, observation: cleanObservation, nextTry: nextTry.value.trim(), date: new Date().toLocaleDateString('zh-CN') }
  notes.value = [item, ...notes.value]
  savePracticeNotes(notes.value)
  subject.value = ''; observation.value = ''; nextTry.value = ''
  showToast('练习已记录')
}
function goHome() { void Taro.switchTab({ url: '/pages/home/index' }) }
useDidShow(() => { void refreshPracticePage() })
</script>
<style lang="scss">
@import '../../styles/tokens.scss';
.page{padding:12px 20px 35px}.tabs{display:flex;gap:22px;height:40px;align-items:flex-start}.tabs text{color:$muted;font-size:11px}.tabs .active{color:$green;font-weight:750;border-bottom:2px solid $green;padding-bottom:8px}.intro{padding:18px;border-radius:17px;color:#fff;background:linear-gradient(140deg,$dark,#55766b)}.eyebrow{display:block;color:#bed0c3;font-size:8px;letter-spacing:1.5px}.title{display:block;margin-top:10px;font-size:19px;font-weight:750}.copy{display:block;margin-top:7px;color:rgba(255,255,255,.75);font-size:10px;line-height:1.6}.form{margin-top:14px;padding:16px;border-radius:15px;background:$card}.label{display:block;margin:5px 0 8px;color:$green;font-size:10px;font-weight:700}.picker,input,textarea{box-sizing:border-box;width:100%;padding:11px 12px;margin-bottom:13px;border:1px solid $line;border-radius:9px;background:#fff;color:$ink;font-size:11px}.picker{display:flex;justify-content:space-between}.picker text{color:$muted}textarea{height:70px}.save{margin-top:12px;padding:13px;border-radius:11px;background:$green;color:#fff;text-align:center;font-size:11px;font-weight:700}.section-title{display:flex;justify-content:space-between;margin:23px 1px 10px;font-size:13px;font-weight:750}.section-title text{color:$muted;font-size:9px;font-weight:400}.empty{padding:22px 12px;border-radius:13px;background:$card;color:$muted;text-align:center;font-size:10px}.empty text{display:block;margin-top:9px;color:$green}.note{margin-top:10px;padding:14px;border-radius:13px;background:$card}.note-top{display:flex;justify-content:space-between}.note-tag{color:$green;font-size:9px}.note-date{color:$muted;font-size:9px}.note-subject{display:block;margin-top:9px;font-size:12px;font-weight:700}.note-text,.note-next{display:block;margin-top:6px;color:$body;font-size:10px;line-height:1.6}.note-next{color:$gold}.map-stage{display:flex;gap:12px;margin-top:11px;padding:14px;border-radius:14px;background:$card}.map-no{width:30px;height:30px;display:grid;place-items:center;flex:none;border-radius:50%;background:$green-soft;color:$green;font-size:9px;font-weight:750}.map-main{flex:1}.map-title{display:block;font-size:12px;font-weight:750}.map-items{display:block;margin-top:5px;color:$green;font-size:9px;line-height:1.5}.map-note{display:block;margin-top:6px;color:$muted;font-size:9px;line-height:1.5}
</style>
