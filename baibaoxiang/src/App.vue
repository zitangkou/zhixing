<script setup lang="ts">
import { computed, ref } from 'vue'
import { categories, tools, type Tool } from './data/tools'

const activeTab = ref<'home' | 'mine'>('home')
const activeCategory = ref('全部')
const searchText = ref('')
const toast = ref('')
let toastTimer: number | undefined

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

function notify(message: string) {
  toast.value = message
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => (toast.value = ''), 2200)
}
function openTool(tool: Tool) {
  notify(`${tool.name}即将开放，敬请期待`)
}
function chooseCategory(category: string) {
  activeCategory.value = category
}
</script>

<template>
  <div class="app-shell">
    <main v-if="activeTab === 'home'" class="home-page">
      <header class="topbar">
        <div class="brand-lockup">
          <div class="brand-mark"><span>✦</span></div>
          <div><div class="brand-name">AI百宝箱</div><div class="brand-caption">让 AI 帮你多一点</div></div>
        </div>
        <button class="avatar-button" aria-label="个人中心" @click="activeTab = 'mine'">林</button>
      </header>

      <section class="welcome-block">
        <div class="eyebrow"><span class="sparkle">✦</span> YOUR DAILY AI TOOLKIT</div>
        <h1>把想法交给 AI，<br /><span>把时间留给生活。</span></h1>
        <p>图片、文件、语音与日常灵感，一个百宝箱就够了。</p>
      </section>

      <section class="search-box" aria-label="搜索工具">
        <span class="search-icon">⌕</span>
        <input v-model="searchText" placeholder="搜一搜，想用什么 AI 工具？" />
        <button v-if="searchText" class="clear-search" @click="searchText = ''">×</button>
        <span v-else class="search-shortcut">AI</span>
      </section>

      <section class="hero-card" @click="openTool(recommended[0]!)">
        <div class="hero-copy">
          <div class="hero-label"><span class="hero-dot"></span> 本周灵感推荐</div>
          <h2>把脑海里的画面<br />变成一张好图</h2>
          <p>从一句描述开始，探索你的创作灵感</p>
          <button class="hero-cta">开始创作 <span>↗</span></button>
        </div>
        <div class="hero-art" aria-hidden="true">
          <div class="art-orbit orbit-one"></div><div class="art-orbit orbit-two"></div>
          <div class="art-sun"></div><div class="art-moon">✦</div>
          <div class="art-card card-back"></div><div class="art-card card-front"><span>✺</span></div>
          <div class="art-spark spark-one">✦</div><div class="art-spark spark-two">✧</div>
        </div>
      </section>

      <section class="section-block">
        <div class="section-heading"><div><span class="section-kicker">PICKED FOR YOU</span><h2>为你推荐</h2></div><button class="text-link" @click="activeCategory = '全部'">全部工具 <span>→</span></button></div>
        <div class="recommend-grid">
          <button v-for="tool in recommended" :key="tool.id" class="recommend-card" @click="openTool(tool)">
            <span class="tool-icon" :class="`tint-${tool.tint}`">{{ tool.icon }}</span>
            <span v-if="tool.badge" class="mini-badge">{{ tool.badge }}</span>
            <strong>{{ tool.name }}</strong><small>{{ tool.description }}</small>
          </button>
        </div>
      </section>

      <section class="section-block directory-block">
        <div class="section-heading"><div><span class="section-kicker">EXPLORE TOOLS</span><h2>发现工具</h2></div><span class="tool-count">{{ visibleTools.length }} 个工具</span></div>
        <div class="category-row">
          <button v-for="category in categories" :key="category" class="category-chip" :class="{ selected: activeCategory === category }" @click="chooseCategory(category)">{{ category }}</button>
        </div>
        <div v-if="visibleTools.length" class="tool-list">
          <button v-for="tool in visibleTools" :key="tool.id" class="tool-row" @click="openTool(tool)">
            <span class="tool-icon row-icon" :class="`tint-${tool.tint}`">{{ tool.icon }}</span>
            <span class="tool-info"><strong>{{ tool.name }} <span v-if="tool.badge" class="row-badge">{{ tool.badge }}</span></strong><small>{{ tool.description }}</small></span>
            <span class="tool-arrow">↗</span>
          </button>
        </div>
        <div v-else class="empty-state"><span>⌕</span><strong>没有找到相关工具</strong><small>试试其他关键词或分类</small></div>
      </section>
      <footer class="home-footer"><span>✦</span> 好用的 AI，装进一个小小百宝箱</footer>
    </main>

    <main v-else class="mine-page">
      <header class="mine-top"><div><span class="section-kicker">YOUR SPACE</span><h1>我的</h1></div><button class="settings-button" @click="notify('设置功能即将开放')">⚙</button></header>
      <section class="profile-card">
        <div class="profile-avatar">林<span class="online-dot"></span></div>
        <div class="profile-copy"><strong>林同学</strong><span>让每个日常，都有 AI 灵感</span></div>
        <button class="profile-edit" @click="notify('个人资料编辑即将开放')">编辑资料 <span>›</span></button>
      </section>
      <section class="usage-card"><div class="usage-top"><div><span class="section-kicker">YOUR AI JOURNEY</span><strong>本月使用概览</strong></div><span class="usage-period">10 月 <span>⌄</span></span></div><div class="usage-stats"><div><strong>12<span>次</span></strong><small>工具使用</small></div><i></i><div><strong>4<span>种</span></strong><small>尝试工具</small></div><i></i><div><strong>2.5<span>h</span></strong><small>预计省时</small></div></div><div class="usage-note"><span>✦</span> 你比上个月多探索了 3 次 AI 工具</div></section>
      <section class="mine-section"><div class="section-heading"><div><span class="section-kicker">QUICK ACCESS</span><h2>我的工具</h2></div><button class="text-link" @click="activeTab = 'home'">去发现 <span>→</span></button></div><div class="saved-tools"><button v-for="tool in popular.slice(0, 2)" :key="tool.id" class="saved-tool" @click="openTool(tool)"><span class="tool-icon" :class="`tint-${tool.tint}`">{{ tool.icon }}</span><strong>{{ tool.name }}</strong><span class="saved-arrow">→</span></button></div><div class="empty-saved" @click="activeTab = 'home'"><span>＋</span> 添加更多常用工具</div></section>
      <section class="mine-section menu-section"><button class="menu-row" @click="notify('使用记录即将开放')"><span class="menu-glyph glyph-violet">◷</span><span><strong>使用记录</strong><small>回顾最近用过的 AI 工具</small></span><b>›</b></button><button class="menu-row" @click="notify('收藏夹即将开放')"><span class="menu-glyph glyph-amber">☆</span><span><strong>我的收藏</strong><small>收藏的工具都在这里</small></span><b>›</b></button><button class="menu-row" @click="notify('帮助与反馈即将开放')"><span class="menu-glyph glyph-blue">♡</span><span><strong>帮助与反馈</strong><small>告诉我们你的想法</small></span><b>›</b></button><button class="menu-row" @click="notify('设置功能即将开放')"><span class="menu-glyph glyph-green">⚙</span><span><strong>通用设置</strong><small>账号与隐私偏好</small></span><b>›</b></button></section>
      <div class="version-label">AI 百宝箱 <span>·</span> 版本 1.0.0</div>
    </main>

    <nav class="tabbar">
      <button :class="{ active: activeTab === 'home' }" @click="activeTab = 'home'"><span class="tab-icon">⌂</span><span>首页</span></button>
      <button :class="{ active: activeTab === 'mine' }" @click="activeTab = 'mine'"><span class="tab-icon">◉</span><span>我的</span></button>
    </nav>
    <Transition name="toast"><div v-if="toast" class="toast-message">{{ toast }}</div></Transition>
  </div>
</template>
