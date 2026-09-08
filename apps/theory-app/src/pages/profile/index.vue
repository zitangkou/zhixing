<template>
  <view class="page">
    <view class="eyebrow">学习档案</view><view class="page-title">我的时政学习</view><view class="profile-card card">
      <view class="profile-avatar">{{ initial }}</view><view>
        <view class="card-title">{{ user?.nickname || user?.username || '学习者' }}</view><view class="card-desc">{{ user?.username || '正在加载账号' }}</view>
      </view><view class="profile-points">{{ user?.points || 0 }} 积分</view>
    </view><view class="section-head"><view class="section-title">学习资产</view></view><view v-for="item in items" :key="item.key" class="card row" @tap="openItem(item.key)">
      <view class="card-title">{{ item.label }}</view><view class="tag">查看</view>
    </view><view class="section-head"><view class="section-title">关于</view></view><view class="card row" @tap="openFeedback">
      <view class="card-title">意见反馈</view><view class="tag">去提交</view>
    </view><view class="card row" @tap="openLegal">
      <view class="card-title">用户协议与隐私政策</view><view class="tag">查看</view>
    </view><view class="logout" @tap="logout">退出登录</view>
  </view>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { api, type UserMe } from '@/api'
import { clearToken, isLoggedIn } from '@/utils/auth'
import { showConfirm, showToast } from '@/utils/platform'
const user = ref<UserMe | null>(null)
const initial = computed(() =>
  String(user.value?.nickname || user.value?.username || '知').slice(0, 1),
)
const items = [
  { key: 'wrong', label: '错题本与到期复习' },
  { key: 'practice', label: '练习进度' },
]
function openItem(key: string) {
  if (key === 'wrong') Taro.navigateTo({ url: '/pages/question/wrong' })
  else if (key === 'practice') Taro.switchTab({ url: '/pages/practice/index' })
}
function openLegal() {
  Taro.navigateTo({ url: '/pages/legal/index' })
}
function openFeedback() {
  Taro.navigateTo({ url: '/pages/feedback/index' })
}
async function load() {
  if (!isLoggedIn()) return Taro.navigateTo({ url: '/pages/auth/login' })
  const response = await api.getMe()
  if (response.code === 0 && response.data) user.value = response.data
  else showToast(response.message || '账号信息加载失败')
}
async function logout() {
  if (!(await showConfirm('退出当前账号？'))) return
  clearToken()
  user.value = null
  Taro.navigateTo({ url: '/pages/auth/login' })
}
useDidShow(() => void load())
</script>
