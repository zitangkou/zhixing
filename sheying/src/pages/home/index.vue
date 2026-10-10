<template>
  <view class="page">
    <view class="brand"><view class="mark">光</view><view><text class="brand-name">光线练习簿</text><text class="brand-sub">LIGHT · PHOTO PRACTICE</text></view><text class="streak">{{ practiceCount }} 次练习</text></view>
    <view class="hero"><text class="eyebrow">从灵感，到作品</text><text class="hero-title">今天，练习看见光。</text><text class="hero-copy">每天一个摄影概念，一次小练习，慢慢搭起自己的摄影知识框架。</text><view class="hero-cta" @tap="openLesson(nextLesson.id)">{{ practiceCount ? '继续学习' : '开始今日练习' }} <text>→</text></view><view class="sun">◉</view></view>
    <view class="section-head"><view><text class="kicker">LEARN BY DOING</text><text class="section-title">从一个技巧开始</text></view><text class="link" @tap="openRoadmap">学习地图 ›</text></view>
    <view class="lesson-card" @tap="openLesson(nextLesson.id)"><view class="lesson-top"><text class="tag">{{ nextLesson.category }} · {{ nextLesson.level }}</text><text class="duration">{{ nextLesson.time }}</text></view><text class="lesson-title">{{ nextLesson.title }}</text><text class="lesson-sub">{{ nextLesson.subtitle }}</text><view class="lesson-bottom"><text>看原理 · 做练习 · 写复盘</text><text class="go">去学习 ↗</text></view></view>
    <view class="section-head"><view><text class="kicker">PICK A PRACTICE</text><text class="section-title">技巧课</text></view><text class="link" @tap="openCourses">全部 {{ lessons.length }} 节 ›</text></view>
    <view class="course-list"><view v-for="lesson in lessons.slice(0, 3)" :key="lesson.id" class="course-row" @tap="openLesson(lesson.id)"><view class="course-dot">{{ lesson.category.slice(0, 1) }}</view><view class="course-copy"><text class="course-title">{{ lesson.title }}</text><text class="course-meta">{{ lesson.category }} · {{ lesson.time }}</text></view><text class="stage-arrow">›</text></view></view>
    <view class="section-head roadmap-head"><view><text class="kicker">YOUR PHOTO FOUNDATION</text><text class="section-title">摄影知识地图</text></view><text class="muted">{{ roadmap.length }} 个阶段</text></view>
    <view class="map-card"><view v-for="(stage, index) in roadmap" :key="stage.title" class="stage" @tap="openRoadmap"><view class="stage-no" :class="{ current: index === 0 }">0{{ index + 1 }}</view><view class="stage-copy"><text class="stage-title">{{ stage.title }}</text><text class="stage-items">{{ stage.items }}</text></view><text class="stage-arrow">›</text></view></view>
    <view class="quote">技巧不是收藏起来的知识，<text>而是亲手验证过的经验。</text></view>
  </view>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { lessons, roadmap, loadCatalog } from '@/data/catalog'
import { readPracticeNotes } from '@/utils/practiceStorage'
definePageConfig({ navigationBarTitleText: '光线练习簿' })
const practiceCount = ref(0)
const practicedLessonIds = ref<string[]>([])
const nextLesson = computed(() => lessons.find((lesson) => !practicedLessonIds.value.includes(lesson.id)) || lessons[0])
async function loadProgress() { await loadCatalog(); const notes = readPracticeNotes(); practiceCount.value = notes.length; practicedLessonIds.value = [...new Set(notes.map((note) => note.lessonId).filter(Boolean))] }
function openLesson(id: string) { void Taro.navigateTo({ url: `/pages/lesson/index?id=${id}` }) }
function openCourses() { void Taro.navigateTo({ url: '/pages/courses/index' }) }
function openRoadmap() { void Taro.navigateTo({ url: '/pages/practice/index?tab=map' }) }
useDidShow(() => { void loadProgress() })
</script>
<style lang="scss">
@import '../../styles/tokens.scss';
.page { padding: 0 20px 34px; }
.brand { height:66px; display:flex; align-items:center; gap:10px; }.mark { width:38px;height:38px;border-radius:13px;background:$green;color:#f4ecd9;display:grid;place-items:center;font-size:19px;font-weight:800; }.brand-name,.brand-sub {display:block}.brand-name{font-size:15px;font-weight:750;letter-spacing:1px}.brand-sub{margin-top:3px;color:$muted;font-size:8px;letter-spacing:1px}.streak{margin-left:auto;color:$green;font-size:10px;background:$green-soft;padding:7px 10px;border-radius:20px}
.hero {position:relative;overflow:hidden;margin-top:7px;padding:24px 20px 20px;border-radius:22px;color:#f9f5ea;background:linear-gradient(138deg,#29473f,#547669)}.eyebrow,.kicker{display:block;font-size:9px;letter-spacing:1.5px;color:#a9c5b4}.hero-title{display:block;margin-top:11px;font-size:23px;font-weight:750;letter-spacing:.2px}.hero-copy{display:block;max-width:255px;margin-top:9px;color:rgba(255,255,255,.75);font-size:11px;line-height:1.7}.hero-cta{display:inline-flex;gap:17px;align-items:center;margin-top:17px;padding:10px 14px;border-radius:9px;background:#e6d5ad;color:#283d36;font-size:11px;font-weight:700}.sun{position:absolute;right:19px;top:32px;color:rgba(232,210,161,.25);font-size:82px}
.section-head{display:flex;align-items:flex-end;justify-content:space-between;margin:25px 0 11px}.kicker{color:#a19b8d;font-size:8px}.section-title{display:block;margin-top:5px;font-size:16px;font-weight:750}.link,.muted{color:$muted;font-size:10px;padding-bottom:2px}.lesson-card{padding:16px;border:1px solid $line;border-radius:16px;background:$card}.lesson-top,.lesson-bottom{display:flex;align-items:center;justify-content:space-between}.tag{padding:5px 8px;border-radius:6px;background:$green-soft;color:$green;font-size:9px}.duration{color:$muted;font-size:9px}.lesson-title{display:block;margin-top:14px;font-size:16px;font-weight:750}.lesson-sub{display:block;margin-top:6px;color:$body;font-size:10px}.lesson-bottom{margin-top:17px;padding-top:11px;border-top:1px solid $line;color:$muted;font-size:9px}.go{color:$green;font-weight:700}
.roadmap-head{margin-top:25px}.map-card{padding:3px 14px;border-radius:16px;background:$card}.stage{display:flex;align-items:center;gap:12px;min-height:61px;border-bottom:1px solid $line}.stage:last-child{border:0}.stage-no{width:29px;height:29px;display:grid;place-items:center;border-radius:50%;background:#eeeae1;color:#98958d;font-size:9px;font-weight:700}.stage-no.current{background:$green;color:#fff}.stage-copy{flex:1}.stage-title,.stage-items{display:block}.stage-title{font-size:11px;font-weight:700}.stage-items{margin-top:4px;color:$muted;font-size:9px}.stage-arrow{color:#b1aea6;font-size:19px}.quote{margin:19px 5px;color:$muted;font-size:10px;text-align:center}.quote text{color:$green}
.course-list{padding:0 13px;border-radius:15px;background:$card}.course-row{display:flex;align-items:center;gap:11px;min-height:60px;border-bottom:1px solid $line}.course-row:last-child{border:0}.course-dot{width:31px;height:31px;display:grid;place-items:center;border-radius:50%;background:$green-soft;color:$green;font-size:11px;font-weight:700}.course-copy{flex:1}.course-title,.course-meta{display:block}.course-title{font-size:10px;font-weight:700}.course-meta{margin-top:4px;color:$muted;font-size:9px}
</style>
