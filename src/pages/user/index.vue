<template>
  <page-meta
    v-if="isWeapp"
    :page-style="pageMeta.pageStyle"
    :background-color="pageMeta.backgroundColor"
    :background-color-top="pageMeta.backgroundColorTop"
    :background-color-bottom="pageMeta.backgroundColorBottom"
    :background-text-style="pageMeta.backgroundTextStyle"
  />
  <view class="page-user page-with-tabbar" :class="themeClass">
    <view class="profile-header">
      <view class="profile-main" @tap="onProfileHeader">
        <nut-avatar size="large" class="avatar">
          <image v-if="avatarUrl" class="avatar-img" :src="avatarUrl" mode="aspectFill" />
          <text v-else>
            {{ loggedIn ? userStore.userInfo?.nickname?.slice(0, 1) : '游' }}
          </text>
        </nut-avatar>
        <view class="info">
          <text class="name">
            {{ loggedIn ? userStore.userInfo?.nickname : '游客浏览' }}
          </text>
          <text class="member-tip">
            {{ loggedIn ? `@${userStore.userInfo?.username || '学员'}` : '登录后同步进度与错题' }}
          </text>
        </view>
        <text class="profile-chevron" aria-hidden="true"> › </text>
      </view>
      <PointsBadge
        v-if="loggedIn"
        :points="userStore.points"
        show-label
        tone="on-brand"
        @tap="go('/pages/user/points')"
      />
      <view v-else class="guest-auth" @tap.stop="goLogin">
        <text>登录 / 注册</text>
      </view>
    </view>

    <text class="section-label"> 学习 </text>
    <view class="menu-group">
      <nut-cell title="今日错题" is-link @click="go('/pages/question/wrong')">
        <template #icon>
          <view class="cell-icon">
            <Order :color="brandIcon" size="18" />
          </view>
        </template>
        <template #link>
          <text v-if="dueWrongCount" class="due-count">{{ dueWrongCount }}</text>
        </template>
      </nut-cell>
      <nut-cell title="每日签到" is-link @click="go('/pages/user/signin')">
        <template #icon>
          <view class="cell-icon">
            <Clock :color="brandIcon" size="18" />
          </view>
        </template>
        <template #link>
          <text v-if="loggedIn" class="signed" :class="{ pending: !userStore.hasSignedToday }">
            {{ userStore.hasSignedToday ? '已签到' : '未签到' }}
          </text>
        </template>
      </nut-cell>
    </view>

    <text class="section-label"> 账户 </text>
    <view class="menu-group">
      <nut-cell title="积分" is-link @click="go('/pages/user/points')">
        <template #icon>
          <view class="cell-icon">
            <StarFill :color="brandIcon" size="18" />
          </view>
        </template>
        <template #link>
          <text v-if="loggedIn" class="due-count">{{ userStore.points }}</text>
        </template>
      </nut-cell>
      <nut-cell title="刷题排行" is-link @click="go('/pages/user/rank')">
        <template #icon>
          <view class="cell-icon">
            <StarFill :color="brandIcon" size="18" />
          </view>
        </template>
      </nut-cell>
    </view>

    <!-- 设置 -->
    <text class="section-label"> 设置 </text>
    <view class="menu-group">
      <nut-cell title="主题色" is-link @click="themeVisible = true">
        <template #icon>
          <view class="cell-icon">
            <Photograph :color="brandIcon" size="18" />
          </view>
        </template>
        <template #link>
          <text class="theme-name">
            {{ currentThemeName }}
          </text>
        </template>
      </nut-cell>
      <nut-cell title="深色模式" :is-link="false">
        <template #icon>
          <view class="cell-icon">
            <Setting :color="brandIcon" size="18" />
          </view>
        </template>
        <template #link>
          <nut-switch v-model="darkMode" :active-color="brandIcon" />
        </template>
      </nut-cell>
      <nut-cell title="反馈建议" is-link @click="go('/pages/user/feedback')">
        <template #icon>
          <view class="cell-icon">
            <Message :color="brandIcon" size="18" />
          </view>
        </template>
      </nut-cell>
      <nut-cell v-if="loggedIn" title="退出登录" is-link @click="onLogout">
        <template #icon>
          <view class="cell-icon">
            <PoweroffCircleFill color="#999999" size="18" />
          </view>
        </template>
      </nut-cell>
    </view>

    <AppTabBar active="user" />
    <ThemePicker v-model:visible="themeVisible" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDidShow } from '@tarojs/taro'
import {
  Avatar as NutAvatar,
  Cell as NutCell,
  Switch as NutSwitch,
  Tag as NutTag,
} from '@nutui/nutui-taro'
import {
  Clock,
  Message,
  Order,
  Photograph,
  PoweroffCircleFill,
  Setting,
  StarFill,
} from '@nutui/icons-vue-taro'
import AppTabBar from '@/components/AppTabBar.vue'
import PointsBadge from '@/components/PointsBadge.vue'
import ThemePicker from '@/components/ThemePicker.vue'
import { getBrandTheme } from '@/constants/theme'
import { useSettingsStore } from '@/store/settings'
import { useUserStore } from '@/store/user'
import { useQuestionStore } from '@/store/question'
import { resetBootstrap } from '@/utils/bootstrap'
import { resolveMediaUrl } from '@/utils/media'
import { bumpAuthView, isLoggedIn, requireLogin } from '@/utils/auth'
import { navigateTo, showConfirm } from '@/utils/platform'
import { useBrandColor, usePageMeta, useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '我的' })

const { themeClass } = useThemeClass()
const pageMeta = usePageMeta()
const isWeapp = process.env.TARO_ENV === 'weapp'
const userStore = useUserStore()
const questionStore = useQuestionStore()
const settingsStore = useSettingsStore()
const loggedIn = computed(() => isLoggedIn() && !!userStore.userInfo?.id)
const dueWrongCount = computed(() => (loggedIn.value ? questionStore.wrongCount : 0))

useDidShow(() => {
  bumpAuthView()
  if (isLoggedIn() && !userStore.userInfo?.id) {
    void userStore.bootstrap()
  }
  if (isLoggedIn()) void questionStore.loadWrongQuestions('review')
})

const avatarUrl = computed(() => resolveMediaUrl(userStore.userInfo?.avatar))
const { brandColor: brandIcon } = useBrandColor()
const darkMode = computed({
  get: () => settingsStore.darkMode,
  set: (v: boolean) => settingsStore.setDarkMode(!!v),
})

const themeVisible = ref(false)
const currentThemeName = computed(() => getBrandTheme(settingsStore.brandTheme).name)

function go(url: string) {
  navigateTo(url)
}

function goLogin() {
  requireLogin('/pages/user/index')
}

function onProfileHeader() {
  if (loggedIn.value) go('/pages/user/profile')
  else goLogin()
}

async function onLogout() {
  const ok = await showConfirm('退出登录', '确定要退出当前账号吗？')
  if (!ok) return
  resetBootstrap()
  userStore.logout()
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-user {
  min-height: 100vh;
  background: $page-bg;
  padding-bottom: 8px;

  .due-count { font-size: 14px; font-weight: 700; color: $primary-color; }
  .signed { font-size: 12px; color: $text-muted; }
  .signed.pending { color: $primary-color; font-weight: 600; }
  .profile-header {
    /* 与首页 banner 同一套品牌渐变；布局对齐首页：身份左、积分右 */
    background: linear-gradient(168deg, $primary-color 0%, $primary-mid 48%, $primary-dark 100%);
    padding: 32px 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    color: $on-primary;

    .guest-auth {
      flex-shrink: 0;
      padding: 8px 12px;
      border-radius: $radius-md;
      background: rgba(255, 255, 255, 0.18);
      font-size: 13px;
    }

    :deep(.points-badge) {
      flex-shrink: 0;
    }
  }

  .profile-main {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    min-width: 0;
    min-height: 44px;

    &:active {
      opacity: 0.92;
    }

    .avatar {
      flex-shrink: 0;
      overflow: hidden;
      border: 2px solid rgba(255, 255, 255, 0.35);
      background: rgba(255, 255, 255, 0.2);
    }
    .avatar-img {
      width: 100%;
      height: 100%;
    }
    .info {
      flex: 1;
      min-width: 0;
      .name {
        display: block;
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 4px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .member-tip {
        display: block;
        font-size: 12px;
        opacity: 0.8;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
    .profile-chevron {
      flex-shrink: 0;
      font-size: 20px;
      line-height: 1;
      opacity: 0.65;
      padding: 0 2px;
    }
  }

  .section-label {
    display: block;
    margin: 20px 20px 6px;
    font-size: 12px;
    font-weight: 600;
    color: $text-muted;
    letter-spacing: 0.04em;
  }

  .menu-group {
    margin: 0 16px 4px;
    background: $card-bg;
    border-radius: $radius-lg;
    overflow: hidden;
    box-shadow: $shadow-card;
    border: 1px solid $border-color;
    .cell-icon {
      margin-right: 10px;
      display: flex;
      align-items: center;
    }
    .sub-icon {
      margin-left: 16px;
    }
    .collapse-arrow {
      color: $text-muted;
      font-size: 14px;
    }
    .theme-name {
      color: $text-muted;
      font-size: 14px;
    }
  }

  .menu-group .nut-cell {
    margin: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    background: transparent !important;
    border-bottom: 1px solid $border-color;
  }
  .menu-group .nut-cell::after {
    display: none !important;
  }
  .menu-group .nut-cell:last-child {
    border-bottom: none;
  }
}

html.theme-dark .page-user {
  .menu-group {
    background: $card-bg;
    border-color: $border-color;
    box-shadow: none;
  }
  .menu-group .nut-cell__title {
    color: $text-primary !important;
    font-weight: 500;
  }
  .menu-group .nut-cell__link {
    color: $text-muted !important;
  }
}
</style>
