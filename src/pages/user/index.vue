<template>
  <view class="page-user page-with-tabbar" :class="themeClass">
    <view class="profile-header">
      <view class="profile-main" @tap="go('/pages/user/profile')">
        <nut-avatar size="large" class="avatar">
          <image v-if="avatarUrl" class="avatar-img" :src="avatarUrl" mode="aspectFill" />
          <text v-else>
            {{ userStore.userInfo?.nickname?.slice(0, 1) || '学' }}
          </text>
        </nut-avatar>
        <view class="info">
          <text class="name">
            {{ userStore.userInfo?.nickname || '知行学员' }}
          </text>
          <text class="member-tip"> @{{ userStore.userInfo?.username || '学员' }} </text>
        </view>
        <text class="profile-chevron" aria-hidden="true"> › </text>
      </view>
      <PointsBadge
        :points="userStore.points"
        show-label
        tone="on-brand"
        @tap="go('/pages/user/points')"
      />
    </view>

    <!-- 学习 -->
    <text class="section-label"> 学习 </text>
    <view class="menu-group">
      <nut-cell title="今日清单" is-link @click="go('/pages/plan/today')">
        <template #icon>
          <view class="cell-icon">
            <CheckChecked :color="brandIcon" size="18" />
          </view>
        </template>
      </nut-cell>
      <nut-cell title="今日复习" is-link @click="go('/pages/review/hub')">
        <template #icon>
          <view class="cell-icon">
            <Order :color="brandIcon" size="18" />
          </view>
        </template>
      </nut-cell>
      <nut-cell title="本周计划" is-link @click="go('/pages/plan/week')">
        <template #icon>
          <view class="cell-icon">
            <Date :color="brandIcon" size="18" />
          </view>
        </template>
      </nut-cell>
      <nut-cell title="每日签到" is-link @click="go('/pages/user/signin')">
        <template #icon>
          <view class="cell-icon">
            <Clock :color="brandIcon" size="18" />
          </view>
        </template>
        <template #link>
          <nut-tag v-if="!userStore.hasSignedToday" type="primary" size="small"> 未签到 </nut-tag>
        </template>
      </nut-cell>
      <nut-cell title="知行足迹" is-link @click="go('/pages/user/growth')">
        <template #icon>
          <view class="cell-icon">
            <Fabulous :color="brandIcon" size="18" />
          </view>
        </template>
      </nut-cell>
      <nut-cell title="语料本" is-link @click="go('/pages/corpus/index')">
        <template #icon>
          <view class="cell-icon">
            <Edit :color="brandIcon" size="18" />
          </view>
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

    <!-- 专项：进各模块首页，子功能在模块内再进 -->
    <text class="section-label"> 专项 </text>
    <view class="menu-group">
      <nut-cell title="人民日报" is-link @click="go('/pages/rmrb/index')">
        <template #icon>
          <view class="cell-icon">
            <Edit :color="brandIcon" size="18" />
          </view>
        </template>
      </nut-cell>
      <nut-cell title="时事印象" is-link @click="go('/pages/events/index')">
        <template #icon>
          <view class="cell-icon">
            <Date :color="brandIcon" size="18" />
          </view>
        </template>
      </nut-cell>
      <nut-cell title="知识框架" is-link @click="go('/pages/knowledge/index')">
        <template #icon>
          <view class="cell-icon">
            <Category :color="brandIcon" size="18" />
          </view>
        </template>
      </nut-cell>
      <nut-cell title="真题套卷" is-link @click="go('/pages/exam/list')">
        <template #icon>
          <view class="cell-icon">
            <Order :color="brandIcon" size="18" />
          </view>
        </template>
      </nut-cell>
      <nut-cell
        title="错题本"
        :is-link="false"
        :aria-expanded="expanded.wrong"
        @click="toggle('wrong')"
      >
        <template #icon>
          <view class="cell-icon">
            <Edit :color="brandIcon" size="18" />
          </view>
        </template>
        <template #link>
          <text class="collapse-arrow" aria-hidden="true">
            {{ expanded.wrong ? '▾' : '▸' }}
          </text>
        </template>
      </nut-cell>
      <view v-if="expanded.wrong">
        <nut-cell title="文章错题" is-link @click="go('/pages/question/wrong')">
          <template #icon>
            <view class="cell-icon sub-icon">
              <Order :color="brandIcon" size="18" />
            </view>
          </template>
        </nut-cell>
        <nut-cell title="行测错题" is-link @click="go('/pages/question/manual-list')">
          <template #icon>
            <view class="cell-icon sub-icon">
              <Edit :color="brandIcon" size="18" />
            </view>
          </template>
        </nut-cell>
      </view>
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
      <nut-cell title="数据导出/导入" is-link @click="go('/pages/user/data')">
        <template #icon>
          <view class="cell-icon">
            <Download :color="brandIcon" size="18" />
          </view>
        </template>
      </nut-cell>
      <nut-cell title="退出登录" is-link @click="onLogout">
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
import { computed, reactive, ref } from 'vue'
import Taro from '@tarojs/taro'
import {
  Avatar as NutAvatar,
  Cell as NutCell,
  Switch as NutSwitch,
  Tag as NutTag,
} from '@nutui/nutui-taro'
import {
  Category,
  CheckChecked,
  Clock,
  Date,
  Download,
  Edit,
  Fabulous,
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
import { resetBootstrap } from '@/utils/bootstrap'
import { resolveMediaUrl } from '@/utils/media'
import { showConfirm } from '@/utils/platform'
import { useBrandColor, useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '我的' })

const { themeClass } = useThemeClass()
const userStore = useUserStore()
const settingsStore = useSettingsStore()
const avatarUrl = computed(() => resolveMediaUrl(userStore.userInfo?.avatar))
const { brandColor: brandIcon } = useBrandColor()
const darkMode = computed({
  get: () => settingsStore.darkMode,
  set: (v: boolean) => settingsStore.setDarkMode(!!v),
})

const themeVisible = ref(false)
const currentThemeName = computed(() => getBrandTheme(settingsStore.brandTheme).name)

const expanded = reactive({ wrong: false })

function toggle(key: 'wrong') {
  expanded[key] = !expanded[key]
}

function go(url: string) {
  Taro.navigateTo({ url })
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

  .profile-header {
    /* 与首页 banner 同一套品牌渐变；布局对齐首页：身份左、积分右 */
    background: linear-gradient(168deg, $primary-color 0%, $primary-mid 48%, $primary-dark 100%);
    padding: 32px 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    color: $on-primary;

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
