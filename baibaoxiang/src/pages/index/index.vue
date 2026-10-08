<script setup>
import { computed, ref } from 'vue'
import Taro from '@tarojs/taro'
import { categories, tools } from '../../data/tools.js'
import { storage } from '../../utils/storage'
import { loginWithWechat, saveRemoteProfile, sendFeedback } from '../../utils/api'

const activeTab = ref('home')
const activeCategory = ref('全部')
const searchText = ref('')
const toast = ref('')
const view = ref('main')
const profile = ref(storage.profile())
const user = ref(storage.user())
const favorites = ref(storage.favorites())
const history = ref(storage.history())
const settings = ref(storage.settings())
const editNickname = ref(profile.value.nickname || user.value?.nickname || '')
const feedbackText = ref('')
let toastTimer

const visibleTools = computed(() => {
  const query = searchText.value.trim().toLowerCase()
  return tools.filter((tool) => {
    const categoryMatch = activeCategory.value === '全部' || tool.category === activeCategory.value
    const queryMatch = !query || `${tool.name} ${tool.description} ${tool.category}`.toLowerCase().includes(query)
    return categoryMatch && queryMatch
  })
})
const recommended = tools.filter((tool) => tool.badge === '推荐' || tool.hot).slice(0, 3)
const popular = tools.filter((tool) => tool.hot)
const favoriteTools = computed(() => tools.filter((tool) => favorites.value.includes(tool.id)))
const quickFavorites = computed(() => favoriteTools.value.slice(0, 2))
const displayName = computed(() => user.value?.nickname || profile.value.nickname || '访客用户')
const displayInitial = computed(() => displayName.value.slice(0, 1))
const pageTitles = { profile: '个人资料', settings: '通用设置', privacy: '隐私说明', history: '使用记录', favorites: '我的收藏', feedback: '帮助与反馈' }
const currentPageTitle = computed(() => pageTitles[view.value] || '')
function toolName(toolId) { return tools.find((tool) => tool.id === toolId)?.name || '工具' }
const monthCount = computed(() => history.value.filter((item) => item.date.slice(0, 7) === new Date().toISOString().slice(0, 7)).length)

function notify(message) {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2300)
}
function openTool(tool) {
  if (!tool) return
  const next = [{ id: tool.id, date: new Date().toISOString() }, ...history.value.filter((item) => item.id !== tool.id)].slice(0, 30)
  history.value = next
  storage.saveHistory(next)
  notify(`${tool.name}正在准备中`)
}
function toggleFavorite(tool) {
  const next = favorites.value.includes(tool.id)
    ? favorites.value.filter((id) => id !== tool.id)
    : [...favorites.value, tool.id]
  favorites.value = next
  storage.saveFavorites(next)
  notify(next.includes(tool.id) ? '已加入收藏' : '已取消收藏')
}
function onSearchInput(event) { searchText.value = event.detail.value }
function chooseCategory(category) { activeCategory.value = category }
function openPage(page) { view.value = page }
function backToMain() { view.value = 'main' }

function editProfile() {
  editNickname.value = user.value?.nickname || profile.value.nickname || ''
  openPage('profile')
}
async function saveProfile() {
  const nickname = editNickname.value.trim()
  if (!nickname) return notify('昵称不能为空')
  if (nickname.length > 32) return notify('昵称最多 32 个字')
  if (storage.token()) {
    try {
      const result = await saveRemoteProfile(nickname)
      user.value = result
      Taro.setStorageSync('baibaoxiang.user', result)
    } catch (error) { return notify(error.message || '资料保存失败') }
  }
  profile.value = { ...profile.value, nickname }
  storage.saveProfile(profile.value)
  notify('资料已保存')
  backToMain()
}
async function doLogin() {
  try {
    const result = await loginWithWechat()
    if (!storage.saveSession(result.access_token, result.user)) throw new Error('本地空间不足，登录状态未保存')
    user.value = result.user
    notify('微信登录成功')
  } catch (error) {
    notify(error.message || '登录失败，请稍后重试')
  }
}
function logout() {
  Taro.showModal({ title: '退出登录', content: '退出后仍可继续以访客模式浏览。', success: ({ confirm }) => {
    if (confirm) { storage.clearSession(); user.value = null; notify('已退出登录') }
  } })
}
function clearLocalData() {
  Taro.showModal({ title: '清理本地数据', content: '将删除本机保存的昵称、收藏、使用记录和偏好设置，且无法恢复。', confirmText: '清理', confirmColor: '#7057e8', success: ({ confirm }) => {
    if (confirm) {
      storage.clearAll()
      profile.value = { nickname: '', tagline: '' }
      favorites.value = []
      history.value = []
      settings.value = { reminders: false, compactMode: false }
      notify('本地数据已清理')
    }
  } })
}
function toggleSetting(key) {
  settings.value = { ...settings.value, [key]: !settings.value[key] }
  storage.saveSettings(settings.value)
}
async function submitFeedback() {
  const content = feedbackText.value.trim()
  if (!content) return notify('请先填写反馈内容')
  if (!storage.token()) return notify('登录后即可提交反馈')
  try {
    await sendFeedback(content)
    feedbackText.value = ''
    notify('反馈已提交，感谢支持')
    backToMain()
  } catch (error) { notify(error.message || '反馈提交失败') }
}
</script>

<template>
  <view class="app-shell">
    <view v-if="view === 'main' && activeTab === 'home'" class="home-page">
      <view class="topbar">
        <view class="brand-lockup"><view class="brand-mark"><view>✦</view></view><view><view class="brand-name">AI百宝箱</view><view class="brand-caption">让 AI 帮你多一点</view></view></view>
        <button class="button-reset avatar-button" aria-label="个人中心" @tap="activeTab = 'mine'">{{ displayInitial }}</button>
      </view>
      <view class="welcome-block"><view class="eyebrow"><text class="sparkle">✦</text> YOUR DAILY AI TOOLKIT</view><view class="welcome-title">把想法交给 AI，
<text>把时间留给生活。</text></view><view class="welcome-desc">图片、文件、语音与日常灵感，一个百宝箱就够了。</view></view>
      <view class="search-box" aria-label="搜索工具"><text class="search-icon">⌕</text><input :value="searchText" @input="onSearchInput" placeholder="搜一搜，想用什么 AI 工具？" /><button v-if="searchText" class="button-reset clear-search" @tap="searchText = ''">×</button><view v-else class="search-shortcut">AI</view></view>
      <view class="hero-card" @tap="openTool(recommended[0])"><view class="hero-copy"><view class="hero-label"><view class="hero-dot"></view> 本周灵感推荐</view><view class="hero-title">把脑海里的画面
变成一张好图</view><view class="hero-desc">从一句描述开始，探索你的创作灵感</view><button class="button-reset hero-cta">开始创作 <text>↗</text></button></view><view class="hero-art" aria-hidden="true"><view class="art-orbit orbit-one"></view><view class="art-orbit orbit-two"></view><view class="art-sun"></view><view class="art-moon">✦</view><view class="art-card card-back"></view><view class="art-card card-front"><text>✺</text></view><view class="art-spark spark-one">✦</view><view class="art-spark spark-two">✧</view></view></view>
      <view class="section-block"><view class="section-heading"><view><view class="section-kicker">PICKED FOR YOU</view><view class="section-title">为你推荐</view></view><button class="button-reset text-link" @tap="activeCategory = '全部'">全部工具 <text>→</text></button></view><view class="recommend-grid"><view v-for="tool in recommended" :key="tool.id" class="recommend-card"><button class="button-reset recommend-open" @tap="openTool(tool)"><view class="tool-icon" :class="`tint-${tool.tint}`">{{ tool.icon }}</view><view v-if="tool.badge" class="mini-badge">{{ tool.badge }}</view><view class="recommend-name">{{ tool.name }}</view><view class="recommend-desc">{{ tool.description }}</view></button><button class="button-reset favorite-toggle" :aria-label="favorites.includes(tool.id) ? '取消收藏' : '收藏工具'" @tap="toggleFavorite(tool)">{{ favorites.includes(tool.id) ? '★' : '☆' }}</button></view></view></view>
      <view class="section-block directory-block"><view class="section-heading"><view><view class="section-kicker">EXPLORE TOOLS</view><view class="section-title">发现工具</view></view><view class="tool-count">{{ visibleTools.length }} 个工具</view></view><scroll-view scroll-x class="category-row"><button v-for="category in categories" :key="category" class="button-reset category-chip" :class="{ selected: activeCategory === category }" @tap="chooseCategory(category)">{{ category }}</button></scroll-view><view v-if="visibleTools.length" class="tool-list"><view v-for="tool in visibleTools" :key="tool.id" class="tool-row"><button class="button-reset tool-main" @tap="openTool(tool)"><view class="tool-icon row-icon" :class="`tint-${tool.tint}`">{{ tool.icon }}</view><view class="tool-info"><view class="tool-name">{{ tool.name }} <text v-if="tool.badge" class="row-badge">{{ tool.badge }}</text></view><view class="tool-desc">{{ tool.description }}</view></view><view class="tool-arrow">↗</view></button><button class="button-reset favorite-toggle" :aria-label="favorites.includes(tool.id) ? '取消收藏' : '收藏工具'" @tap="toggleFavorite(tool)">{{ favorites.includes(tool.id) ? '★' : '☆' }}</button></view></view><view v-else class="empty-state"><view>⌕</view><view>没有找到相关工具</view><view>试试其他关键词或分类</view></view></view>
      <view class="home-footer"><text>✦</text> 好用的 AI，装进一个小小百宝箱</view>
    </view>

    <view v-else-if="view === 'main'" class="mine-page">
      <view class="mine-top"><view><view class="section-kicker">YOUR SPACE</view><view class="mine-heading">我的</view></view><button class="button-reset settings-button" @tap="openPage('settings')">⚙</button></view>
      <view class="profile-card"><view class="profile-avatar">{{ displayInitial }}<view class="online-dot"></view></view><view class="profile-copy"><view class="profile-name">{{ displayName }}</view><view class="profile-tagline">{{ user ? '微信账号已登录' : '访客模式 · 数据仅保存在本机' }}</view></view><button class="button-reset profile-edit" @tap="editProfile">编辑资料 <text>›</text></button></view>
      <view v-if="!user" class="login-card"><view><view class="login-title">体验模式</view><view class="login-desc">当前体验版可浏览目录、编辑本机昵称、收藏和查看记录</view></view><text>无需登录</text></view>
      <view class="usage-card"><view class="usage-top"><view><view class="section-kicker">YOUR AI JOURNEY</view><view class="usage-title">使用概览</view></view><view class="usage-period">本月</view></view><view class="usage-stats"><view><view class="usage-number">{{ monthCount }}<text>次</text></view><view class="usage-label">查看/打开工具</view></view><view class="usage-divider"></view><view><view class="usage-number">{{ favoriteTools.length }}<text>个</text></view><view class="usage-label">已收藏</view></view><view class="usage-divider"></view><view><view class="usage-number">{{ history.length }}<text>条</text></view><view class="usage-label">本地记录</view></view></view><view class="usage-note"><text>✦</text> 当前工具入口为功能规划展示</view></view>
      <view class="mine-section"><view class="section-heading"><view><view class="section-kicker">QUICK ACCESS</view><view class="section-title">我的收藏</view></view><button class="button-reset text-link" @tap="openPage('favorites')">查看全部 <text>→</text></button></view><view v-if="favoriteTools.length" class="saved-tools"><button v-for="tool in quickFavorites" :key="tool.id" class="button-reset saved-tool" @tap="openTool(tool)"><view class="tool-icon" :class="`tint-${tool.tint}`">{{ tool.icon }}</view><view class="saved-name">{{ tool.name }}</view><view class="saved-arrow">→</view></button></view><view v-else class="empty-saved" @tap="activeTab = 'home'"><text>＋</text> 收藏常用工具</view></view>
      <view class="mine-section menu-section"><button class="button-reset menu-row" @tap="openPage('history')"><view class="menu-glyph glyph-violet">◷</view><view class="menu-copy"><view class="menu-title">使用记录</view><view class="menu-desc">最近浏览的工具（{{ history.length }}）</view></view><text class="menu-arrow">›</text></button><button class="button-reset menu-row" @tap="openPage('favorites')"><view class="menu-glyph glyph-amber">☆</view><view class="menu-copy"><view class="menu-title">我的收藏</view><view class="menu-desc">收藏的工具都在这里</view></view><text class="menu-arrow">›</text></button><button class="button-reset menu-row" @tap="openPage('feedback')"><view class="menu-glyph glyph-blue">♡</view><view class="menu-copy"><view class="menu-title">帮助与反馈</view><view class="menu-desc">告诉我们你的想法</view></view><text class="menu-arrow">›</text></button><button class="button-reset menu-row" @tap="openPage('privacy')"><view class="menu-glyph glyph-green">▤</view><view class="menu-copy"><view class="menu-title">隐私说明</view><view class="menu-desc">了解信息如何被使用</view></view><text class="menu-arrow">›</text></button><button class="button-reset menu-row" @tap="openPage('settings')"><view class="menu-glyph glyph-green">⚙</view><view class="menu-copy"><view class="menu-title">通用设置</view><view class="menu-desc">账号与本机数据管理</view></view><text class="menu-arrow">›</text></button></view>
      <view class="version-label">AI 百宝箱 <text>·</text> 版本 1.0.0</view>
    </view>

    <view v-else class="subpage">
      <view class="subpage-top"><button class="button-reset back-button" @tap="backToMain">‹</button><view>{{ currentPageTitle }}</view></view>
      <view v-if="view === 'profile'" class="panel"><view class="field-label">昵称</view><input class="form-input" :value="editNickname" maxlength="32" placeholder="请输入昵称" @input="editNickname = $event.detail.value" /><view class="form-note">昵称仅用于本机展示；登录后会同步到账号资料。</view><button class="button-reset primary-action" @tap="saveProfile">保存资料</button><button v-if="user" class="button-reset secondary-action" @tap="logout">退出登录</button><view class="privacy-short">头像昵称等微信资料不会在此自动获取；需要你主动填写。</view></view>
      <view v-else-if="view === 'settings'" class="panel"><view class="setting-row"><view><view class="setting-title">消息提醒</view><view class="form-note">当前版本暂不发送推送通知</view></view><switch :checked="settings.reminders" color="#7057e8" @change="toggleSetting('reminders')" /></view><view class="setting-row"><view><view class="setting-title">紧凑列表</view><view class="form-note">偏好仅保存在当前设备</view></view><switch :checked="settings.compactMode" color="#7057e8" @change="toggleSetting('compactMode')" /></view><button class="button-reset secondary-action danger-action" @tap="clearLocalData">清理本地数据</button><button class="button-reset text-action" @tap="openPage('privacy')">查看隐私说明</button></view>
      <view v-else-if="view === 'privacy'" class="panel legal-copy"><view class="legal-heading">隐私说明（体验版）</view><view class="legal-updated">更新日期：2026 年 10 月 8 日</view><view class="legal-heading">运营主体</view><view>个人（个人主体小程序）。</view><view class="legal-heading">1. 当前处理范围</view><view>体验版提供工具目录浏览、搜索、收藏、最近使用记录和昵称设置。收藏、浏览记录、昵称及设置保存在当前设备，不会因这些操作自动上传。体验版暂不开放微信账号登录和在线反馈。</view><view class="legal-heading">2. 微信信息</view><view>本体验版不读取微信头像、昵称、手机号、通讯录或位置信息，也不会调用微信登录。</view><view class="legal-heading">3. 本地数据管理</view><view>你可以在“通用设置”清理本机保存的昵称、收藏、使用记录和偏好。卸载小程序也会移除该设备上的本地数据。</view><view class="legal-heading">4. 后续功能</view><view>AI 工具尚未开放。未来启用账号、图片、文件、录音等功能前，将更新隐私说明和微信平台隐私保护指引，说明信息类型、处理目的、保存期限、第三方服务和删除方式。</view><view class="legal-heading">5. 隐私问题联系</view><view>正式体验邀请前，请通过体验邀请渠道向体验者提供个人主体的隐私问题联系邮箱或其他可用联系方式，并在微信公众平台隐私保护指引中完成相应配置。</view><view class="legal-callout">本说明仅覆盖当前体验版功能；发布前需补全联系方式并完成平台隐私保护配置。</view></view>
      <view v-else-if="view === 'history'" class="panel"><view v-if="history.length" class="entry-list"><view v-for="item in history" :key="item.id" class="entry-row"><view class="entry-name">{{ toolName(item.id) }}</view><view class="form-note">{{ new Date(item.date).toLocaleString() }}</view></view></view><view v-else class="empty-panel">还没有使用记录。打开工具目录查看感兴趣的工具吧。</view><button v-if="history.length" class="button-reset secondary-action" @tap="history = []; storage.saveHistory([]); notify('记录已清除')">清除使用记录</button></view>
      <view v-else-if="view === 'favorites'" class="panel"><view v-if="favoriteTools.length" class="entry-list"><view v-for="tool in favoriteTools" :key="tool.id" class="entry-row"><view class="entry-name">{{ tool.icon }}　{{ tool.name }}</view><button class="button-reset text-action" @tap="toggleFavorite(tool)">取消收藏</button></view></view><view v-else class="empty-panel">还没有收藏工具。回到首页点按星标即可收藏。</view></view>
      <view v-else-if="view === 'feedback'" class="panel"><view class="field-label">意见或问题</view><textarea class="feedback-input" maxlength="500" :value="feedbackText" placeholder="请描述你希望改进的地方（最多 500 字）" @input="feedbackText = $event.detail.value" /><view class="form-note">体验版暂未开放在线提交，请通过体验邀请方提供的渠道反馈；请勿填写敏感个人信息。</view></view>
    </view>

    <view v-if="view === 'main'" class="tabbar"><button class="button-reset" :class="{ active: activeTab === 'home' }" @tap="activeTab = 'home'"><view class="tab-icon">⌂</view><view>首页</view></button><button class="button-reset" :class="{ active: activeTab === 'mine' }" @tap="activeTab = 'mine'"><view class="tab-icon">◉</view><view>我的</view></button></view>
    <view v-if="toast" class="toast-message">{{ toast }}</view>
  </view>
</template>
