<template>
  <el-container class="layout">
    <el-aside :width="asideWidth" class="aside" :class="{ collapsed }">
      <div class="brand">
        <span v-if="!collapsed" class="brand-text">知行管理后台</span>
        <span v-else class="brand-short" title="知行管理后台">知</span>
        <button
          type="button"
          class="collapse-btn"
          :title="collapsed ? '展开菜单' : '折叠菜单'"
          :aria-label="collapsed ? '展开菜单' : '折叠菜单'"
          @click="toggleCollapse"
        >
          <el-icon :size="18">
            <Expand v-if="collapsed" />
            <Fold v-else />
          </el-icon>
        </button>
      </div>
      <el-menu
        :default-active="activeMenu"
        :default-openeds="defaultOpeneds"
        :collapse="collapsed"
        :collapse-transition="false"
        router
        class="aside-menu"
        background-color="var(--admin-aside-bg)"
        text-color="var(--admin-aside-text)"
        active-text-color="var(--admin-aside-active)"
      >
        <template v-for="group in visibleGroups" :key="group.key">
          <el-sub-menu v-if="group.children.length > 1" :index="group.key">
            <template #title>
              <el-icon><component :is="group.icon" /></el-icon>
              <span>{{ group.title }}</span>
            </template>
            <el-menu-item v-for="item in group.children" :key="item.path" :index="item.path">
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>{{ item.title }}</template>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="group.children[0].path">
            <el-icon><component :is="group.icon" /></el-icon>
            <template #title>{{ group.children[0].title }}</template>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: homePath }">首页</el-breadcrumb-item>
          <el-breadcrumb-item v-for="(c, i) in crumbs" :key="i">{{ c }}</el-breadcrumb-item>
        </el-breadcrumb>
        <div class="header-right">
          <span class="user-meta">{{ auth.username }}（{{ auth.role || '管理员' }}）</span>
          <el-button type="danger" plain @click="onLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Expand, Fold } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { NAV_GROUPS, ROUTE_TITLES, canAccess } from '@/config/nav'
import type { NavGroup } from '@/config/nav'

const COLLAPSE_KEY = 'zhengkao_admin_aside_collapsed'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const collapsed = ref(localStorage.getItem(COLLAPSE_KEY) === '1')

const asideWidth = computed(() => (collapsed.value ? '64px' : '220px'))

const visibleGroups = computed<NavGroup[]>(() =>
  NAV_GROUPS.map((group) => ({
    ...group,
    children: group.children.filter(
      (item) => auth.isSuperAdmin || canAccess(auth.permissions, item.permissions),
    ),
  })).filter((group) => group.children.length > 0),
)

/** 默认展开当前路由所在分组；无匹配时展开第一个分组 */
const defaultOpeneds = computed(() => {
  const path = route.path
  const current = visibleGroups.value.find((g) => g.children.some((c) => path.startsWith(c.path)))
  return [current?.key ?? visibleGroups.value[0]?.key].filter(Boolean) as string[]
})

const homePath = computed(() => visibleGroups.value[0]?.children[0]?.path || '/articles')

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/articles')) return '/articles'
  return path
})

const crumbs = computed(() => {
  const path = route.path
  if (path.startsWith('/articles/') && path !== '/articles/new') {
    return ['文章管理', '编辑文章']
  }
  if (path === '/articles/new') return ['文章管理', '新建文章']
  const title = ROUTE_TITLES[path] || (route.meta.title as string) || ''
  return title ? [title] : []
})

watch(collapsed, (v) => {
  localStorage.setItem(COLLAPSE_KEY, v ? '1' : '0')
})

function toggleCollapse() {
  collapsed.value = !collapsed.value
}

onMounted(() => {
  auth.loadMe().catch(() => auth.logout())
})

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout { min-height: 100vh; }
.aside {
  background: var(--admin-aside-bg);
  transition: width 0.2s ease;
  overflow: hidden;
}
.brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  min-height: 56px;
  padding: 0 10px 0 16px;
  border-bottom: 1px solid #333;
  color: var(--admin-aside-active);
}
.aside.collapsed .brand {
  padding: 0;
  justify-content: center;
  flex-direction: column;
  gap: 2px;
  padding: 8px 0;
}
.brand-text {
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
  overflow: hidden;
}
.brand-short {
  font-weight: 700;
  font-size: 18px;
  line-height: 1;
}
.collapse-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  margin: 0;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--admin-aside-text);
  cursor: pointer;
  flex-shrink: 0;
  outline: none;
  transition: color 0.15s ease, background 0.15s ease;
}
.collapse-btn:hover,
.collapse-btn:focus-visible {
  color: var(--admin-aside-active);
  background: rgba(255, 255, 255, 0.08);
}
.collapse-btn:active {
  color: var(--admin-aside-active);
  background: rgba(255, 255, 255, 0.14);
}
.aside-menu {
  border-right: none;
  width: 100%;
}
.aside-menu:not(.el-menu--collapse) {
  width: 220px;
}
.aside-menu :deep(.el-menu-item.is-active) {
  background: var(--admin-aside-active-bg) !important;
}
/* 两级菜单：分组标题与嵌套层级 */
.aside-menu :deep(.el-sub-menu__title) {
  font-weight: 600;
  letter-spacing: 0.04em;
}
.aside-menu :deep(.el-sub-menu__title:hover) {
  background: rgba(255, 255, 255, 0.06);
}
.aside-menu :deep(.el-sub-menu .el-menu .el-menu-item) {
  min-width: auto;
  padding-left: 48px !important;
  font-size: 13px;
}
.aside-menu :deep(.el-sub-menu.is-opened > .el-sub-menu__title) {
  color: var(--admin-aside-active);
}
.aside-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.06);
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: var(--admin-card-bg);
  border-bottom: 1px solid var(--admin-border);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.user-meta {
  font-size: 14px;
  color: #606266;
}
.main {
  background: var(--admin-page-bg);
}
</style>
